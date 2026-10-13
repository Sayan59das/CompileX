"""
reviewed_bank.py
Serves reviewed questions from data/reviewed_bank.jsonl (one JSON object per line) when that file exists.

A reviewed question was checked before it got here: two independent solutions agree on all of its tests,
its starter code runs in four languages, and its statement was read by a person. Each one carries typed
fields (function_name, parameters, return_type, starter_code) so the backend does not have to guess a
signature from the text.

Selection is stateless, like question_db: a random question the caller has not excluded, so each player's
own history decides what they get. Every test case is returned (reviewed tests are not trimmed), and a
record that is incomplete is skipped with a message instead of being served.
"""
import copy
import json
import os
import random
import re
from collections import defaultdict
from typing import Optional

from model.titles import normalize_title

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reviewed_bank.jsonl")

_REQUIRED = (
    "title", "problem_statement", "input_format", "output_format", "sample_input", "sample_output",
    "test_cases", "topic", "difficulty", "function_name", "parameters", "return_type", "starter_code",
)
_LANGUAGES = ("python", "cpp", "java", "javascript")
_MIN_TESTS = 3
_ALIASES = {
    "array": "arrays", "string": "strings", "graph": "graphs", "tree": "trees", "stack": "stacks",
    "queue": "queues", "hash": "hashing", "hash table": "hashing", "hash map": "hashing", "hashmap": "hashing",
    "dp": "dynamic programming", "sort": "sorting", "search": "searching", "window": "sliding window",
    "linked list": "linked lists", "bit": "bit manipulation", "bits": "bit manipulation",
}

# { (topic, difficulty) -> [question, ...] }
_store: dict = {}
_loaded = False


def _topic_key(topic: str) -> str:
    key = re.sub(r"[\s_-]+", " ", (topic or "").strip().lower())
    return _ALIASES.get(key, key)


def _problem_with(q: dict) -> Optional[str]:
    """Why this record must not be served, or None when it is complete."""
    missing = [k for k in _REQUIRED if not q.get(k)]
    if missing:
        return f"missing {', '.join(missing)}"
    if str(q["difficulty"]).strip().lower() not in ("easy", "medium", "hard"):
        return f"unknown difficulty {q['difficulty']!r}"
    if len(q["test_cases"]) < _MIN_TESTS:
        return f"fewer than {_MIN_TESTS} test cases"
    if any(not isinstance(c, dict) or "input" not in c or "output" not in c for c in q["test_cases"]):
        return "a test case lacks input or output"
    code = q["starter_code"]
    if not isinstance(code, dict) or any(not str(code.get(lang, "")).strip() for lang in _LANGUAGES):
        return f"starter code must cover {', '.join(_LANGUAGES)}"
    if not isinstance(q["parameters"], list) or any(not isinstance(p, dict) or not p.get("name") or not p.get("type") for p in q["parameters"]):
        return "parameters must be a list of {name, type}"
    return None


def _load(path: Optional[str] = None) -> None:
    global _store, _loaded
    if _loaded:
        return
    path = path or _PATH
    store, seen_titles, skipped = defaultdict(list), set(), 0
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for number, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    q = json.loads(line)
                except ValueError as exc:
                    print(f"[Reviewed] line {number}: not valid JSON ({exc}); skipped")
                    skipped += 1
                    continue
                problem = _problem_with(q)
                title_key = normalize_title(q.get("title", ""))
                if problem is None and title_key in seen_titles:
                    problem = "duplicate title"
                if problem:
                    print(f"[Reviewed] line {number} ({q.get('title', '?')!r}): {problem}; skipped")
                    skipped += 1
                    continue
                seen_titles.add(title_key)
                store[(_topic_key(q["topic"]), q["difficulty"].strip().lower())].append(q)
    _store = dict(store)
    _loaded = True
    total = sum(len(v) for v in _store.values())
    if total or skipped:
        print(f"[Reviewed] Loaded {total} questions across {len(_store)} buckets ({skipped} skipped)")


def reload(path: Optional[str] = None) -> None:
    """Forget what was loaded and read the file again (tests and hot edits)."""
    global _loaded, _store
    _loaded, _store = False, {}
    _load(path)


def pool_size(topic: str, difficulty: str) -> int:
    """Number of reviewed questions for exactly this topic and difficulty."""
    _load()
    return len(_store.get((_topic_key(topic), (difficulty or "").strip().lower()), []))


def get_question(topic: str, difficulty: str, exclude_titles: Optional[list] = None) -> Optional[dict]:
    """A random reviewed question for exactly this topic and difficulty that the caller has not seen, or None."""
    _load()
    candidates = _store.get((_topic_key(topic), (difficulty or "").strip().lower()))
    if not candidates:
        return None
    blocked = {normalize_title(t) for t in (exclude_titles or [])}
    fresh = [q for q in candidates if normalize_title(q["title"]) not in blocked]
    if not fresh:
        return None
    chosen = copy.deepcopy(random.choice(fresh))
    chosen["base_title"] = chosen["title"]
    chosen["source"] = "reviewed"
    return chosen


def get_stats() -> dict:
    """{topic: {difficulty: count}} for what is loaded."""
    _load()
    stats: dict = {}
    for (topic, difficulty), items in _store.items():
        stats.setdefault(topic, {})[difficulty] = len(items)
    return stats
