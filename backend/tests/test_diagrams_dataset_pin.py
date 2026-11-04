"""Every stored graph or tree question has a reviewed diagram decision, and nothing changes it silently.

A wording nobody has met cannot be proved right in advance, but new wordings can only enter through new stored questions. This test records, for every
graph- or tree-looking question in each file the question service serves from (questions.json, question_db.json, generated_questions.jsonl and the
reviewed bank), typed the way the service sends it, whether it gets a picture and what the picture shows (kind, vertices, edges, direction, edge
labels, marked vertices, values beside vertices).

* a decision that CHANGES (a refused question is now drawn, a drawing now shows something else) fails: look at the picture, then update the pin;
* a question that is NOT IN THE PIN fails: someone has to read its statement against its picture, then add it.

Update after reviewing:   python tests/test_diagrams_dataset_pin.py --update
Run:                      python -m pytest tests/test_diagrams_dataset_pin.py -q
"""

import contextlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import legacy_typing
from app.services.diagram_generator import diagram_generator as dg

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "..", "question-service", "data")
PIN = os.path.join(HERE, "diagram_decisions.json")
FILES = ["questions.json", "question_db.json", "generated_questions.jsonl", "reviewed_bank.jsonl"]
GRAPHY = re.compile(r"\b(graph|vertices|vertex|edges?|tree|nodes?|roads?|cities)\b", re.I)


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    if name.endswith(".jsonl"):
        return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("questions") or [v for v in data.values() if isinstance(v, dict)]
    return [q for q in data if isinstance(q, dict)]


def stored_tests(q):
    tests = [(t["input"], t["output"]) for t in (q.get("test_cases") or []) if isinstance(t, dict) and "input" in t and "output" in t]
    if not tests and q.get("sample_input") is not None and q.get("sample_output") is not None:
        tests = [(str(q["sample_input"]), str(q["sample_output"]))]
    return tests


def decision(q):
    """What the service would do for this question: a signature of the picture, or None for no picture."""
    tests = stored_tests(q)
    sample = str(q.get("sample_input") or (tests[0][0] if tests else ""))
    if q.get("input_schema"):  # a reviewed question carries its own schema and format
        fields = {"input_format": q.get("input_format", ""), "input_schema": q["input_schema"]}
    else:
        typed = legacy_typing.type_question(tests, sample, str(q.get("sample_output") or (tests[0][1] if tests else "")),
                                            input_format=str(q.get("input_format") or "")) if tests else None   # as main_dynamic types it
        fields = {"input_format": (typed or {}).get("input_format", q.get("input_format", "")), "input_schema": (typed or {}).get("input_schema")}
    with contextlib.redirect_stdout(io.StringIO()):
        m = dg.plan({"title": q["title"], "topic": str(q.get("topic", "")).lower(), "problem_statement": q.get("problem_statement") or q.get("description") or "",
                     "sample_input": sample, **fields})
    if not m:
        return None
    return {"kind": m.kind, "n": len(m.nodes), "m": len(m.edges), "directed": m.directed, "weight": m.weight_name,
            "marks": {str(k): v for k, v in sorted(m.marks.items())}, "notes": {str(k): v for k, v in sorted(m.notes.items())},
            "edges": [list(e) for e in m.edges]}


def candidates():
    out = {}
    for name in FILES:
        for q in load(name):
            if not q.get("title"):
                continue
            text = q.get("title", "") + " " + (q.get("problem_statement") or q.get("description") or "")
            if str(q.get("topic", "")).lower() in ("graphs", "trees") or GRAPHY.search(text):
                out.setdefault(f"{name}:{q['title']}", q)
    return out


def current():
    return {key: decision(q) for key, q in candidates().items()}


pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(DATA, "questions.json")), reason="the question service's data is not in this checkout")


def test_every_stored_graph_or_tree_question_has_a_reviewed_decision_and_none_changed():
    pinned = json.load(open(PIN, encoding="utf-8"))
    now = current()
    unreviewed = sorted(set(now) - set(pinned))
    changed = sorted(k for k in now if k in pinned and now[k] != pinned[k])
    assert not unreviewed, f"{len(unreviewed)} stored question(s) have no reviewed diagram decision yet, e.g. {unreviewed[:3]}: read the statement against the picture, then --update"
    assert not changed, f"the diagram decision changed for {len(changed)} question(s), e.g. {changed[:3]}: look at the picture, then --update"


def test_the_pin_covers_every_file_the_service_serves_from_and_is_not_trivially_empty():
    pinned = json.load(open(PIN, encoding="utf-8"))
    assert len(pinned) > 200 and 1 <= sum(1 for v in pinned.values() if v) < len(pinned)
    assert {k.split(":", 1)[0] for k in pinned} >= {"questions.json", "question_db.json", "reviewed_bank.jsonl"}


if __name__ == "__main__":
    if "--update" in sys.argv:
        now = current()
        json.dump(now, open(PIN, "w", encoding="utf-8", newline="\n"), indent=1, sort_keys=True)
        print(f"pinned {len(now)} decisions, {sum(1 for v in now.values() if v)} with a picture")
    else:
        print(__doc__)
