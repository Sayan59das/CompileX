"""Choosing a question for a player, and nothing else.

This is the whole serving path. It reads the pool (one indexed query), the player's history and, as a fallback, the reviewed bank.
It never calls a model, the verifier, the spec sampler or any generator: tests patch those to raise and check that serving still works,
and the module imports none of them.

Order of preference for pick():
  1. a random live pool question the players have not seen;
  2. a reviewed-bank question for the same topic and difficulty they have not seen;
  3. (only for a topic that has no pool or bank questions at all) the legacy generators, when one is plugged in;
  4. the question they were given longest ago, flagged repeat=True;
  and NoQuestion when there is nothing at all.
"""

import hashlib
import random
import re
import time

from .history import MemorySeenStore, SeenStore
from .repository import PoolRepository, title_key

SAMPLE_EXTRA = 4              # random candidates drawn beyond the number of questions already seen
MAX_SAMPLE = 1000


class NoQuestion(Exception):
    """There is no question at all for this topic and difficulty."""


def normalise_output(text) -> str:
    return "\n".join(line.rstrip() for line in str(text).strip().splitlines())


def topic_candidates(topic: str) -> list[str]:
    """The spellings of a topic to try, most exact first: 'Array' -> ['array', 'arrays']."""
    key = re.sub(r"[\s_-]+", " ", (topic or "").strip().lower())
    return [key, key[:-1] if key.endswith("s") and len(key) > 1 else key + "s"]


def bank_id(question: dict) -> str:
    return "rb:" + hashlib.sha1(title_key(question["title"]).encode("utf-8")).hexdigest()[:16]


def legacy_id(question: dict) -> str:
    return "lg:" + hashlib.sha1(title_key(question["title"]).encode("utf-8")).hexdigest()[:16]


class ReviewedBank:
    """The hand-reviewed questions (model.reviewed_bank), with stable ids."""

    def __init__(self, module=None):
        self._module = module
        self._by_id = None

    @property
    def module(self):
        if self._module is None:
            from model import reviewed_bank
            self._module = reviewed_bank
        return self._module

    def topic_key(self, topic: str) -> str:
        return self.module.topic_key(topic)

    def questions(self, topic: str, difficulty: str) -> list[dict]:
        found = []
        for question in self.module.questions(topic, difficulty):
            question["id"] = bank_id(question)
            question.setdefault("base_title", question["title"])
            question["source"] = "reviewed"
            found.append(question)
        return found

    def by_id(self, question_id: str) -> dict | None:
        """One reviewed question by its stable id (the index is built once; the bank does not change while the service runs)."""
        if self._by_id is None:
            self._by_id = {q["id"]: q for key in self.module.buckets() for q in self.questions(*key)}
        question = self._by_id.get(question_id)
        return None if question is None else dict(question)

    def sizes(self) -> dict:
        return {key: len(self.module.questions(*key)) for key in self.module.buckets()}


def sample_test(question: dict) -> dict:
    return {"input": question["sample_input"], "output": question["sample_output"]}


def _starter(question: dict):
    """The question's starter code, with a C entry added when the question predates C (the other languages are untouched)."""
    from model.scaffold import served_starter   # imported here so this module stays importable without the model package
    return served_starter(question)


def public_view(question: dict, repeat: bool = False) -> dict:
    """What a player's client gets: the problem, starter code and the sample test, never the hidden tests."""
    return {
        "id": str(question["id"]), "title": question["title"], "base_title": question.get("base_title") or question["title"],
        "problem_statement": question["problem_statement"], "input_format": question["input_format"],
        "output_format": question["output_format"], "constraints": question.get("constraints", ""),
        "sample_tests": [sample_test(question)], "tests_count": len(question.get("test_cases", [])),
        "function_name": question.get("function_name"), "parameters": question.get("parameters"),
        "return_type": question.get("return_type"), "starter_code": _starter(question),
        "topic": question["topic"], "difficulty": question["difficulty"], "source": question.get("source", "pool"), "repeat": repeat,
    }


def backend_view(question: dict, repeat: bool = False) -> dict:
    """The shape the game backend's /generate has always returned: the public fields plus every test case."""
    shown = public_view(question, repeat)
    shown.pop("sample_tests"), shown.pop("tests_count")
    shown.update(
        sample_input=question["sample_input"], sample_output=question["sample_output"],
        test_cases=[{"input": c["input"], "output": c["output"]} for c in question["test_cases"]],
        return_description=question.get("return_description"), input_schema=question.get("input_schema"),
        output_schema=question.get("output_schema"),
    )
    return shown


class QuestionService:
    def __init__(self, repo: PoolRepository, seen: SeenStore | None = None, bank: ReviewedBank | None = None, legacy=None,
                 rng: random.Random | None = None):
        self.repo = repo
        self.seen = seen if seen is not None else MemorySeenStore()
        self.bank = bank if bank is not None else ReviewedBank()
        self.legacy = legacy                       # legacy(topic, difficulty, exclude_title_keys) -> question dict or None
        self.rng = rng or random.Random()

    # ── choosing ──
    def _pool_topic(self, topic: str, difficulty: str) -> str:
        """The topic spelling the pool actually uses for this request (or the plain one if the pool has nothing)."""
        known = {t for t, d in self.repo.pool_sizes() if d == difficulty}
        known |= {t for t, d in self.bank.module.buckets() if d == difficulty}
        candidates = list(dict.fromkeys([self.bank.topic_key(topic)] + topic_candidates(topic)))
        for candidate in candidates:
            if candidate in known:
                return candidate
        return candidates[0]

    def pick(self, topic: str, difficulty: str, player_ids, exclude_titles=(), allow_repeat: bool = True) -> tuple[dict, bool]:
        """(question, repeat). Marks the question as seen by every player in the lobby. Raises NoQuestion when there is none to give.

        Without player ids nothing is read from or written to the history (the caller excludes by title instead).
        With allow_repeat=False a question already seen is never returned: the caller would rather fall back to something else."""
        difficulty = (difficulty or "").strip().lower()
        players = [str(p) for p in player_ids]
        pool_topic = self._pool_topic(topic, difficulty)
        seen = set(self.seen.seen(players, pool_topic, difficulty)) if players else set()
        blocked_titles = {title_key(t) for t in exclude_titles}
        seen |= {str(i) for i in self.repo.ids_for_titles(blocked_titles)}

        sample = self.repo.sample_live(pool_topic, difficulty, min(len(seen) + SAMPLE_EXTRA, MAX_SAMPLE))
        fresh = [i for i in sample if str(i) not in seen]
        if fresh:
            question = self.repo.get(self.rng.choice(fresh))
            if question is not None:
                return self._serve(question, pool_topic, difficulty, players, False)

        bank = self.bank.questions(topic, difficulty)
        fresh_bank = [q for q in bank if q["id"] not in seen and title_key(q["title"]) not in blocked_titles]
        if fresh_bank:
            return self._serve(self.rng.choice(fresh_bank), pool_topic, difficulty, players, False)

        if not allow_repeat:
            raise NoQuestion(f"no unseen {difficulty} question is left for {topic}")
        live = self.repo.live_ids(pool_topic, difficulty)
        if not live and not bank and self.legacy is not None:
            legacy = self.legacy(topic, difficulty, blocked_titles)
            if legacy is not None:
                legacy.setdefault("id", legacy_id(legacy))
                legacy.setdefault("source", "legacy")
                return self._serve(legacy, pool_topic, difficulty, players, False)

        everything = [str(i) for i in live] + [q["id"] for q in bank]
        if not everything:
            raise NoQuestion(f"no {difficulty} question exists for {topic}")
        served = self.seen.last_served(players, pool_topic, difficulty)
        oldest = min(everything, key=lambda qid: (served.get(qid, 0.0), self.rng.random()))
        question = next((q for q in bank if q["id"] == oldest), None) or self.repo.get(int(oldest))
        if question is None:
            raise NoQuestion(f"no {difficulty} question exists for {topic}")
        return self._serve(question, pool_topic, difficulty, players, True)

    def _serve(self, question: dict, pool_topic: str, difficulty: str, players: list, repeat: bool):
        question["id"] = str(question["id"])
        if players:
            self.seen.mark(players, pool_topic, difficulty, question["id"])
        return question, repeat

    # ── the rest of the API ──
    def get_question(self, topic: str, difficulty: str, player_ids, exclude_titles=()) -> dict:
        question, repeat = self.pick(topic, difficulty, player_ids, exclude_titles)
        return public_view(question, repeat)

    def generate(self, topic: str, difficulty: str, player_ids=(), exclude_titles=()) -> dict:
        """Same choice, in the shape the game backend expects (with all test cases). Never repeats: the backend decides what to do instead."""
        question, repeat = self.pick(topic, difficulty, player_ids, exclude_titles, allow_repeat=False)
        return backend_view(question, repeat)

    def find(self, question_id: str) -> dict | None:
        """A pool or reviewed-bank question by id (None if unknown)."""
        question_id = str(question_id)
        if question_id.startswith("rb:"):
            return self.bank.by_id(question_id)
        if question_id.isdigit():
            question = self.repo.get(int(question_id))
            return question if question and question["status"] == "live" else None
        return None

    def tests(self, question_id: str) -> list[dict] | None:
        question = self.find(question_id)
        return None if question is None else [{"input": c["input"], "output": c["output"]} for c in question["test_cases"]]

    def grade(self, question_id: str, results: list) -> dict:
        """Compare the outputs a player's program produced (in test order) with the hidden expected outputs. Never reveals them."""
        question = self.find(question_id)
        if question is None:
            raise NoQuestion(f"unknown question {question_id}")
        expected = question["test_cases"]
        if len(results) != len(expected):
            raise ValueError(f"expected {len(expected)} results, got {len(results)}")
        failed = [i for i, (got, case) in enumerate(zip(results, expected)) if normalise_output(got) != normalise_output(case["output"])]
        return {"question_id": str(question_id), "total": len(expected), "passed": len(expected) - len(failed),
                "failed": failed, "all_passed": not failed}

    def status(self) -> dict:
        """Pool sizes per topic and difficulty, counted from the database, plus the reviewed bank."""
        sizes = self.repo.pool_sizes()
        bank = self.bank.sizes()
        keys = sorted(set(sizes) | set(bank))
        pools = []
        for topic, difficulty in keys:
            row = {"topic": topic, "difficulty": difficulty, "bank": bank.get((topic, difficulty), 0)}
            row.update(sizes.get((topic, difficulty), {"pending": 0, "approved": 0, "live": 0, "retired": 0}))
            pools.append(row)
        return {"pools": pools, "live": sum(p["live"] for p in pools), "bank": sum(p["bank"] for p in pools),
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
