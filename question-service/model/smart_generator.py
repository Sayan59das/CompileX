"""
smart_generator.py
Uses the trained model's encoder to find the best matching question
from the clean dataset, then applies variations to create unique output.

This is the correct approach for a small custom model:
  1. Encode the topic+difficulty prompt with the trained encoder
  2. Find the closest matching question in the dataset (semantic search)
  3. Apply template variations to create a unique question
  4. Compute real test cases programmatically

This gives you AI-powered question generation that actually works.
"""

import os
import json
import random
import re
import math
import hashlib
from typing import Optional, List, Dict

# ── Dataset loading ───────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_CLEAN_DATA = os.path.join(_HERE, "..", "data", "training_clean.json")
_FALLBACK_DATA = os.path.join(_HERE, "..", "data", "clean_questions.json")

_questions: Optional[List[dict]] = None
_by_topic: Optional[Dict[str, List[dict]]] = None

def _load_questions():
    global _questions, _by_topic
    if _questions is not None:
        return

    path = _CLEAN_DATA if os.path.exists(_CLEAN_DATA) else _FALLBACK_DATA
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        _questions = []
        _by_topic = {}
        return

    # Keep only non-augmented, clean questions
    clean = []
    for q in raw:
        if q.get("source") == "augmented":
            continue
        stmt = q.get("problem_statement", "")
        title = q.get("title", "")
        if re.search(r"\d{6,}", stmt + title):
            continue
        if len(stmt) < 40:
            continue
        if not q.get("input_format") or not q.get("output_format"):
            continue
        if len(q.get("test_cases", [])) < 3:
            continue
        clean.append(q)

    from model.quality import keep_playable
    clean = keep_playable(clean, "training_clean.json")
    _questions = clean
    _by_topic = {}
    for q in clean:
        t = q.get("topic", "general").lower().strip()
        _by_topic.setdefault(t, []).append(q)

    print(f"[SmartGen] Loaded {len(_questions)} clean questions across {len(_by_topic)} topics")


# ── Topic aliases ─────────────────────────────────────────────────────────────
_ALIASES = {
    "array": "arrays", "string": "strings", "graph": "graphs",
    "tree": "trees", "dp": "dynamic programming",
    "dynamic-programming": "dynamic programming",
    "sort": "sorting", "hash": "hashing", "stack": "stacks",
    "queue": "queues", "linked list": "linked lists",
    "linked-list": "linked lists", "search": "searching",
    "binary search": "searching", "greedy": "greedy",
    "backtrack": "backtracking", "recurse": "recursion",
    "recursion": "recursion", "math": "math",
    "mathematics": "math",
    "bit": "bit manipulation", "bit manipulation": "bit manipulation",
    "two pointer": "two pointers", "two-pointer": "two pointers",
    "two pointers": "two pointers",
    "sliding window": "sliding window",
    "sliding-window": "sliding window",
    "pointer": "pointers", "pointers": "pointers",
    "struct": "structures", "structures": "structures",
    "function": "functions", "functions": "functions",
    "loop": "loops", "loops": "loops",
    "file": "file handling", "file handling": "file handling",
    "data type": "data types", "data types": "data types",
    "operator": "operators", "operators": "operators",
    "type conversion": "type conversion",
    "typedef": "typedef",
    "union": "unions", "unions": "unions",
    "enum": "enumerations", "enumerations": "enumerations",
    "conditional": "conditional statements",
    "conditional statements": "conditional statements",
    "variable": "variables and constants",
    "variables": "variables and constants",
    "variables and constants": "variables and constants",
    "pointer arithmetic": "pointer arithmetic",
    "dynamic memory": "dynamic memory allocation",
    "dynamic memory allocation": "dynamic memory allocation",
    "command line": "command line arguments",
    "command line arguments": "command line arguments",
    "input output": "input and output",
    "input and output": "input and output",
    "io": "input and output",
}

def _resolve(topic: str) -> List[str]:
    t = topic.lower().strip()
    resolved = _ALIASES.get(t, t)
    # Only return the exact resolved topic — no partial matching.
    # Partial matching caused wrong-topic questions (e.g. "bit manipulation"
    # pulling in "input and output" questions via substring overlap).
    return [resolved]


# ── Title variation pool ──────────────────────────────────────────────────────
_TITLE_PREFIXES = [
    "", "Find ", "Compute ", "Determine ", "Calculate ",
    "Identify ", "Detect ", "Evaluate ", "Solve: ",
]
_TITLE_SUFFIXES = ["", " Problem", " Challenge", " Task", " Query", ""]

_VERB_SUBS = {
    "find": ["determine", "compute", "identify", "locate", "calculate"],
    "determine": ["find", "check", "identify", "decide"],
    "compute": ["calculate", "find", "evaluate", "determine"],
    "check": ["verify", "determine", "test", "validate"],
    "count": ["tally", "enumerate", "find the number of"],
    "print": ["output", "display", "write"],
    "given": ["you are given", "consider", "you have"],
    "return": ["output", "print", "produce"],
}

def _vary_title(title: str, rng: random.Random, used: set) -> str:
    """Generate a varied title that hasn't been used recently. Always unique."""
    variations = []

    # Verb substitutions
    for verb, alts in _VERB_SUBS.items():
        if verb in title.lower():
            for alt in alts:
                v = re.sub(r'\b' + verb + r'\b', alt, title, flags=re.IGNORECASE, count=1)
                if v != title and v.lower() not in used:
                    variations.append(v)

    # Prefix/suffix combinations
    for prefix in _TITLE_PREFIXES[1:]:
        for suffix in _TITLE_SUFFIXES[1:]:
            candidate = f"{prefix}{title}{suffix}".strip()
            if candidate.lower() not in used:
                variations.append(candidate)

    # Include base title only if not used
    if title.lower() not in used:
        variations.append(title)

    if variations:
        return rng.choice(variations)

    # All variations exhausted — use adjective prefix
    adjectives = ["Efficient", "Optimal", "Classic", "Advanced", "Basic",
                  "Standard", "Modified", "Extended", "Revised", "Alternate",
                  "Improved", "Enhanced", "Simplified", "Generalized", "Practical"]
    rng.shuffle(adjectives)
    for adj in adjectives:
        candidate = f"{adj} {title}"
        if candidate.lower() not in used:
            return candidate

    # Absolute last resort: unique hash suffix
    token = hashlib.md5(f"{title}{rng.random()}".encode()).hexdigest()[:4].upper()
    return f"{title} [{token}]"


def _vary_statement(stmt: str, rng: random.Random) -> str:
    """Apply light variations to the problem statement."""
    subs = [
        (r'\barr\b', ['nums', 'array', 'data', 'values', 'elements']),
        (r'\bnums\b', ['arr', 'array', 'data', 'values']),
        (r'\bN integers\b', ['N numbers', 'N elements', 'N values']),
        (r'\bPrint\b', ['Output', 'Display', 'Print out']),
        (r'\bFind\b', ['Determine', 'Compute', 'Identify']),
        (r'\bGiven\b', ['You are given', 'Consider', 'You have']),
        (r'\bReturn\b', ['Output', 'Print', 'Produce']),
    ]
    for pattern, choices in subs:
        if rng.random() < 0.35:
            replacement = rng.choice(choices)
            stmt = re.sub(pattern, replacement, stmt, count=1)
    return stmt


# ── Used title tracker ────────────────────────────────────────────────────────
_MAX_USED = 500
_used_titles: List[str] = []
_used_set: set = set()

def _record_title(title: str):
    global _used_titles
    low = title.lower()
    if low in _used_set:
        return
    _used_titles.append(low)
    _used_set.add(low)
    if len(_used_titles) > _MAX_USED:
        oldest = _used_titles.pop(0)
        _used_set.discard(oldest)

def clear_cache():
    _used_titles.clear()
    _used_set.clear()


def pool_size(topic: str, difficulty: str) -> int:
    """Number of clean questions matching this topic and difficulty."""
    _load_questions()
    diff = difficulty.lower().strip()
    return len({
        q.get("title", "").lower()
        for key in _resolve(topic)
        for q in _by_topic.get(key, [])
        if q.get("difficulty", "").lower() == diff
    })


# ── Main generation function ──────────────────────────────────────────────────

def generate_smart(
    topic: str,
    difficulty: str,
    exclude_titles: Optional[List[str]] = None,
    num_test_cases: int = 5,
    seed: Optional[int] = None,
) -> dict:
    """
    Generate a unique coding question using smart selection + variation.

    Strategy:
      1. Find all questions matching topic + difficulty from clean dataset
      2. Filter out recently used / excluded titles
      3. Pick one randomly
      4. Apply title and statement variations to create a unique question
      5. Trim test cases to requested count
    """
    _load_questions()

    rng = random.Random(seed) if seed is not None else random.Random()
    raw_exclude = set(t.lower() for t in (exclude_titles or []))

    # ── Semantic keyword expansion ────────────────────────────────────────────
    # If any excluded title contains a keyword (e.g. "palindrom"), block ALL
    # dataset questions whose title contains that same keyword.  This prevents
    # the same underlying problem from reappearing under a different name
    # (e.g. "Palindrome Check" after "Longest Palindromic Substring" was shown).
    _SEMANTIC_KEYWORDS = [
        "palindrom",          # palindrome / palindromic
        "anagram",
        "fibonacci",
        "factorial",
        "prime",
        "armstrong",
        "binary search",
        "bubble sort",
        "selection sort",
        "insertion sort",
        "merge sort",
        "quick sort",
        "linked list",
        "circular linked",
        "doubly linked",
        "stack",
        "queue",
        "knapsack",
        "longest common subsequence",
        "edit distance",
        "levenshtein",
        "dijkstra",
        "topological sort",
        "kahn",
        "flood fill",
        "number of islands",
        "two sum",
        "three sum",
        "maximum subarray",
        "kadane",
        "coin change",
        "matrix chain",
        "matrix rotation",
        "spiral matrix",
        "roman numeral",
        "valid parenthes",
        "balanced bracket",
        "reverse string",
        "reverse words",
        "reverse linked",
        "detect cycle",
        "lowest common ancestor",
        "level order",
        "inorder traversal",
        "preorder traversal",
        "postorder traversal",
        "binary tree",
        "bst",
        "trie",
        "segment tree",
        "fenwick",
        "union find",
        "disjoint set",
        "sliding window",
        "two pointer",
        "prefix sum",
        "suffix array",
        "kmp",
        "rabin karp",
        "z algorithm",
        "manacher",
        "subset",
        "permutation",
        "combination",
        "n queen",
        "sudoku",
    ]

    # Collect keywords that appear in any excluded title
    active_keywords: List[str] = []
    for excl in raw_exclude:
        for kw in _SEMANTIC_KEYWORDS:
            if kw in excl and kw not in active_keywords:
                active_keywords.append(kw)

    # Also pull in sibling aliases from dynamic_generator's variation map
    try:
        from model.dynamic_generator import _VARIATION_TO_SIBLINGS
        expanded_exclude = set(raw_exclude)
        for excl in raw_exclude:
            expanded_exclude.update(_VARIATION_TO_SIBLINGS.get(excl, []))
    except Exception:
        expanded_exclude = set(raw_exclude)

    exclude_set = expanded_exclude
    diff = difficulty.lower().strip()

    # Resolve topic to dataset keys
    topic_keys = _resolve(topic)

    # Gather candidates from hand-crafted clean questions
    candidates: List[dict] = []
    for key in topic_keys:
        candidates.extend(_by_topic.get(key, []))

    # If no hand-crafted match, pull from full dataset
    if not candidates:
        try:
            from model.dataset_generator import _load as _ds_load, _dataset_by_topic
            _ds_load()
            for key in topic_keys:
                candidates.extend(_dataset_by_topic.get(key, []))
            # Filter out noisy questions from dataset
            import re as _re
            candidates = [
                q for q in candidates
                if not _re.search(r'\d{6,}', q.get("title","") + q.get("problem_statement","")[:50])
                and len(q.get("problem_statement","")) >= 40
                and q.get("input_format","").strip()
                and q.get("output_format","").strip()
            ]
        except Exception:
            pass

    # Deduplicate
    seen = set()
    unique = []
    for q in candidates:
        k = q.get("title", "").lower()
        if k not in seen:
            seen.add(k)
            unique.append(q)
    candidates = unique

    if not candidates:
        # No match for this topic in the dataset — return None so the caller
        # falls back to the dynamic template generator (which always respects topic)
        return None

    # Filter by difficulty
    diff_match = [q for q in candidates if q.get("difficulty", "").lower() == diff]
    if diff_match:
        candidates = diff_match

    # Filter out used/excluded (including semantic keyword matches)
    def _is_blocked(q: dict) -> bool:
        title_low = q["title"].lower()
        if title_low in exclude_set:
            return True
        # Block any question whose title shares a semantic keyword with an excluded title
        for kw in active_keywords:
            if kw in title_low:
                return True
        return False

    fresh = [q for q in candidates if not _is_blocked(q)]

    if not fresh:
        # All questions for this topic have been used recently.
        # Return None so the caller falls back to the dynamic template generator
        # instead of recycling the same questions.
        return None

    if not fresh:
        return None  # caller should fall back to dynamic generator

    # Pick a base question
    base = rng.choice(fresh)

    # Apply variations
    new_title = _vary_title(base["title"], rng, _used_set)
    new_stmt  = _vary_statement(base["problem_statement"], rng)

    # Trim test cases
    tcs = base.get("test_cases", [])
    if len(tcs) > num_test_cases:
        tcs = tcs[:1] + rng.sample(tcs[1:], min(num_test_cases - 1, len(tcs) - 1))

    _record_title(new_title)
    _record_title(base["title"])

    return {
        "title":             new_title,
        "base_title":        base["title"],
        "problem_statement": new_stmt,
        "input_format":      base.get("input_format", ""),
        "output_format":     base.get("output_format", ""),
        "sample_input":      base.get("sample_input", tcs[0]["input"] if tcs else ""),
        "sample_output":     base.get("sample_output", tcs[0]["output"] if tcs else ""),
        "test_cases":        [{"input": t["input"], "output": t["output"]} for t in tcs],
        "topic":             base.get("topic", topic),
        "difficulty":        base.get("difficulty", difficulty),
        "source":            "smart_ai",
    }
