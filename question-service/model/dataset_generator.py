"""
dataset_generator.py
Serves questions from the curated questions.json dataset.
Falls back to dynamic_generator.py when the dataset has no match.

Strategy:
  1. Load questions.json at startup (once, cached in memory)
  2. Filter by topic + difficulty
  3. Exclude recently-used titles (per-process tracking)
  4. Shuffle and pick — guarantees variety without repeats
  5. If dataset has no match → return None so caller falls back to dynamic
"""

import json
import os
import random
from typing import Optional, List, Dict

from model.quality import keep_playable
from model.titles import normalize_title

# ── Path resolution ───────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_DATA_PATH = os.path.join(_HERE, "..", "data", "questions.json")

# ── In-process title tracker ──────────────────────────────────────────────────
_MAX_TRACKED = 1000
_used_titles: List[str] = []
_used_titles_set: set = set()


def _record(title: str) -> None:
    global _used_titles
    low = title.lower().strip()
    if low in _used_titles_set:
        return
    _used_titles.append(low)
    _used_titles_set.add(low)
    if len(_used_titles) > _MAX_TRACKED:
        oldest = _used_titles.pop(0)
        _used_titles_set.discard(oldest)



def clear_cache() -> None:
    _used_titles.clear()
    _used_titles_set.clear()


# ── Dataset loading ───────────────────────────────────────────────────────────
_dataset: Optional[List[dict]] = None
_dataset_by_topic: Optional[Dict[str, List[dict]]] = None


def _load() -> List[dict]:
    global _dataset, _dataset_by_topic
    if _dataset is not None:
        return _dataset

    if not os.path.exists(_DATA_PATH):
        print(f"[Dataset] questions.json not found at {_DATA_PATH}")
        _dataset = []
        _dataset_by_topic = {}
        return _dataset

    try:
        with open(_DATA_PATH, encoding="utf-8", errors="replace") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[Dataset] Failed to load questions.json: {e}")
        _dataset = []
        _dataset_by_topic = {}
        return _dataset

    # Filter to quality questions only
    good = []
    for q in raw:
        if (
            len(q.get("test_cases", [])) >= 3
            and len(q.get("problem_statement", "").strip()) > 30
            and q.get("title", "").strip()
            and q.get("input_format", "").strip()
            and q.get("output_format", "").strip()
        ):
            good.append(q)

    _dataset = keep_playable(good, "questions.json")   # see model/quality.py

    # Build topic index — normalise topic names
    _dataset_by_topic = {}
    for q in _dataset:
        topic = q.get("topic", "").lower().strip()
        _dataset_by_topic.setdefault(topic, []).append(q)

    print(f"[Dataset] Loaded {len(_dataset)} quality questions across {len(_dataset_by_topic)} topics")
    return _dataset


# ── Topic normalisation ───────────────────────────────────────────────────────
# Maps user-typed topics to dataset topic keys
_TOPIC_ALIASES: Dict[str, List[str]] = {
    "array":              ["arrays"],
    "arrays":             ["arrays"],
    "string":             ["strings"],
    "strings":            ["strings"],
    "sort":               ["sorting"],
    "sorting":            ["sorting"],
    "graph":              ["graphs"],
    "graphs":             ["graphs"],
    "dp":                 ["dynamic programming"],
    "dynamic programming":["dynamic programming"],
    "dynamic-programming":["dynamic programming"],
    "hash":               ["hashing"],
    "hashing":            ["hashing"],
    "greedy":             ["greedy"],
    "math":               ["math"],
    "mathematics":        ["math"],
    "bit manipulation":   ["bit manipulation"],
    "bit":                ["bit manipulation"],
    "recursion":          ["recursion"],
    "tree":               ["trees", "graphs"],
    "trees":              ["trees", "graphs"],
    "binary tree":        ["trees"],
    "bst":                ["trees"],
    "linked list":        ["linked lists"],
    "linked-list":        ["linked lists"],
    "linked lists":       ["linked lists"],
    "stack":              ["stacks"],
    "stacks":             ["stacks"],
    "queue":              ["queues"],
    "queues":             ["queues"],
    "searching":          ["searching", "arrays"],
    "search":             ["searching", "arrays"],
    "backtracking":       ["backtracking", "recursion"],
    "two pointers":       ["arrays"],
    "sliding window":     ["arrays"],
    "prefix sum":         ["arrays"],
    "binary search":      ["searching", "arrays"],
}


def _resolve_topics(topic: str) -> List[str]:
    """Return a list of dataset topic keys to search for the given user topic."""
    t = topic.lower().strip()
    if t in _TOPIC_ALIASES:
        return _TOPIC_ALIASES[t]
    # Partial match
    for alias, keys in _TOPIC_ALIASES.items():
        if alias in t or t in alias:
            return keys
    # Direct match against dataset topics
    return [t]


# ── Public API ────────────────────────────────────────────────────────────────

def get_from_dataset(
    topic: str,
    difficulty: str,
    exclude_titles: Optional[List[str]] = None,
    num_test_cases: int = 5,
) -> Optional[dict]:
    """
    Return a question dict from the dataset, or None if no match found.

    The returned dict has the same shape as dynamic_generator output:
      title, problem_statement, input_format, output_format,
      sample_input, sample_output, test_cases, topic, difficulty, source
    """
    _load()
    if not _dataset:
        return None

    exclude_set = set(normalize_title(t) for t in (exclude_titles or []))
    diff = difficulty.lower().strip()

    # Resolve topic to dataset keys
    topic_keys = _resolve_topics(topic)

    # Gather candidates
    candidates: List[dict] = []
    for key in topic_keys:
        candidates.extend(_dataset_by_topic.get(key, []))

    # Remove duplicates (same question may appear under multiple keys)
    seen_ids = set()
    unique_candidates = []
    for q in candidates:
        qid = q.get("title", "").lower()
        if qid not in seen_ids:
            seen_ids.add(qid)
            unique_candidates.append(q)
    candidates = unique_candidates

    if not candidates:
        print(f"[Dataset] No questions for topic='{topic}' (keys={topic_keys})")
        return None

    # Filter by difficulty
    diff_candidates = [q for q in candidates if q.get("difficulty", "").lower() == diff]
    if not diff_candidates:
        # Relax difficulty — use any difficulty
        print(f"[Dataset] No {diff} questions for topic='{topic}', relaxing difficulty")
        diff_candidates = candidates

    # Filter out titles the caller has excluded (the user's own history)
    fresh = [q for q in diff_candidates if normalize_title(q["title"]) not in exclude_set]

    if not fresh:
        print(f"[Dataset] All {len(diff_candidates)} questions excluded for topic='{topic}'")
        return None

    # Pick randomly
    q = random.choice(fresh)
    _record(q["title"])

    # Trim test cases to requested count
    tcs = q.get("test_cases", [])
    if len(tcs) > num_test_cases:
        # Always keep first (sample) + random selection of rest
        tcs = tcs[:1] + random.sample(tcs[1:], min(num_test_cases - 1, len(tcs) - 1))

    print(f"[Dataset] Serving: '{q['title']}' (topic={q.get('topic')}, diff={q.get('difficulty')})")

    return {
        "title":             q["title"],
        "problem_statement": q["problem_statement"],
        "input_format":      q.get("input_format", ""),
        "output_format":     q.get("output_format", ""),
        "sample_input":      q.get("sample_input", tcs[0]["input"] if tcs else ""),
        "sample_output":     q.get("sample_output", tcs[0]["output"] if tcs else ""),
        "test_cases":        [{"input": t["input"], "output": t["output"]} for t in tcs],
        "topic":             q.get("topic", topic),
        "difficulty":        q.get("difficulty", difficulty),
        "source":            "dataset",
    }


def pool_size(topic: str, difficulty: str) -> int:
    """Number of dataset questions matching this topic and difficulty."""
    _load()
    diff = difficulty.lower().strip()
    seen = {
        q.get("title", "").lower()
        for key in _resolve_topics(topic)
        for q in _dataset_by_topic.get(key, [])
        if q.get("difficulty", "").lower() == diff
    }
    return len(seen)


def dataset_stats() -> dict:
    _load()
    return {
        "total_questions": len(_dataset) if _dataset else 0,
        "topics":          {k: len(v) for k, v in (_dataset_by_topic or {}).items()},
        "used_titles":     len(_used_titles),
    }
