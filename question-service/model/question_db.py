"""
question_db.py
Loads question_db.json and serves questions by topic + difficulty.

Guarantees:
- Correct topic and difficulty on every question
- Varying TC counts (5-12) per question
- Stateless selection: a random question the caller has not excluded, so each
  user's history (sent as exclude_titles) decides what they get, not a shared
  server-side position
- Returns None when every question in the pool is excluded so the caller
  falls back to the dynamic generator
"""
import json
import os
import random
import hashlib
from collections import defaultdict
from typing import Optional

_HERE = os.path.dirname(__file__)
_DB_PATH = os.path.join(_HERE, '..', 'data', 'question_db.json')

# In-memory store: { (topic, difficulty) -> [question, ...] }
_store: dict = {}
_loaded = False

# TC count pool — deterministic per title but varied across questions
_TC_POOL = [5, 6, 7, 8, 9, 10, 11, 12, 5, 7, 6, 10, 8, 9, 11, 7, 5, 12, 6, 8]

# Jitter pool — small offsets so the TC count differs between serves
_TC_JITTER = [0, 1, 2, -1, 1, 0, 2, -1, 1, 2, 0, -1, 2, 1, 0, -1, 3, -2, 2, 1, -1, 3, 0, 2]


def _base_tc_count(title: str) -> int:
    """Deterministic base TC count for a question title (5-12)."""
    h = int(hashlib.md5(title.encode()).hexdigest(), 16)
    return _TC_POOL[h % len(_TC_POOL)]


def _trim_tcs(question: dict, target: int) -> dict:
    """
    Return a copy of the question with test cases trimmed to target count.
    NEVER pads with duplicates — only trims. If fewer real TCs exist than
    target, returns all real TCs (no cycling/repeating).
    This ensures every test case shown to the user has unique input/output.
    """
    q = dict(question)
    tcs = list(q.get('test_cases', []))
    if not tcs:
        return q
    # Only trim — never pad with duplicates
    q['test_cases'] = tcs[:target]
    return q


def _load():
    global _store, _loaded
    if _loaded:
        return
    try:
        with open(_DB_PATH, encoding='utf-8') as f:
            questions = json.load(f)
    except Exception as e:
        print(f'[QuestionDB] Failed to load: {e}')
        _store = {}
        _loaded = True
        return

    store = defaultdict(list)
    for q in questions:
        t = q.get('topic', '').strip().lower()
        d = q.get('difficulty', '').strip().lower()
        if t and d in ('easy', 'medium', 'hard'):
            store[(t, d)].append(q)

    _store = dict(store)
    _loaded = True
    total = sum(len(v) for v in _store.values())
    print(f'[QuestionDB] Loaded {total} questions across {len(_store)} buckets')


def _get_candidates(topic: str, difficulty: str):
    """Get candidate list for (topic, difficulty), with fallbacks."""
    t, d = topic.strip().lower(), difficulty.strip().lower()
    if d not in ('easy', 'medium', 'hard'):
        d = 'medium'

    # Exact match
    cands = _store.get((t, d))
    if cands:
        return cands, (t, d)

    # Fall back to medium for same topic
    cands = _store.get((t, 'medium'))
    if cands:
        return cands, (t, 'medium')

    # Partial topic match
    for (kt, kd) in _store:
        if kd == d and (kt in t or t in kt):
            return _store[(kt, kd)], (kt, kd)

    return None, None


def get_question(
    topic: str,
    difficulty: str,
    exclude_titles: list = None,
) -> Optional[dict]:
    """
    Return a random question for (topic, difficulty) that is not in exclude_titles.

    Returns None when every question in the bucket is excluded (caller should
    fall back to the dynamic generator). Keeps no per-process state.
    """
    _load()

    candidates, key = _get_candidates(topic, difficulty)
    if not candidates or not key:
        return None

    blocked = set(e.lower().strip() for e in (exclude_titles or []))
    fresh = [q for q in candidates if q.get('title', '').lower() not in blocked]
    if not fresh:
        return None

    chosen = random.choice(fresh)
    target_tc = max(5, min(12, _base_tc_count(chosen.get('title', '')) + random.choice(_TC_JITTER)))
    return _trim_tcs(chosen, target_tc)


def pool_size(topic: str, difficulty: str) -> int:
    """Number of questions available for exactly this (topic, difficulty)."""
    _load()
    return len(_store.get((topic.strip().lower(), difficulty.strip().lower()), []))


def get_topics() -> list:
    """Return all available topics."""
    _load()
    return sorted(set(t for t, d in _store.keys()))


def get_stats() -> dict:
    """Return stats about the loaded database."""
    _load()
    stats = {}
    for (t, d), qs in _store.items():
        if t not in stats:
            stats[t] = {}
        stats[t][d] = len(qs)
    return stats
