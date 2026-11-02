"""Hidden tests stay on the server.

A question's tests used to travel to the browser in full: the generator's answer carried every input and expected output,
the client echoed them back to `POST /questions`, and `/run-tests` and `/submissions` returned every test's input, expected
output and actual output. Anyone could read the hidden tests and hardcode the answers.

Now a generated question is kept in `issued_questions` and the browser gets a public copy:
  * the first SAMPLE_TESTS tests as they are (they are the examples in the statement),
  * every other test blanked (empty input and output, `hidden: true`), so the list keeps its length and the pages still show
    "Case 1..N" with the later ones locked,
  * a `ref`. `POST /questions` takes the `ref` back and builds the stored question from the server's copy, not the client's.

`/run-tests` and `/submissions` give input, expected and actual output only for the sample tests; for the rest the player
gets pass/fail. The logic analyzer, whose advice text is shown to the player, is only given those redacted details too.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.assessment_grading import SAMPLE_TESTS, parse_tests

TTL_SECONDS = 24 * 3600   # how long the server keeps a generated question waiting to be created

# What a stored question takes from the server's copy when it is created from a ref. Everything that decides how it is
# graded (tests, harness, signature) comes from the server; title, description, difficulty and topic stay the client's.
SERVER_FIELDS = ("test_cases", "starter_code", "function_name", "parameters", "return_type", "return_description")


def public_tests(raw: Any) -> str:
    """The tests as the browser may hold them, as a JSON string: samples intact, the rest blanked."""
    shown = []
    for i, test in enumerate(parse_tests(raw)):
        shown.append(dict(test) if i < SAMPLE_TESTS else {"input": "", "output": "", "hidden": True})
    return json.dumps(shown)


def public_question(question: dict, ref: str) -> dict:
    """A generated question as the browser gets it."""
    return {**question, "test_cases": public_tests(question.get("test_cases")), "ref": ref}


def redact_details(details: list[dict]) -> list[dict]:
    """Per-test results as the player may see them: input and outputs only for the sample tests."""
    shown = []
    for i, d in enumerate(details):
        if i < SAMPLE_TESTS:
            shown.append(d)
            continue
        shown.append({
            "index": d.get("index", i),
            "input": "",
            "expected_output": "",
            "actual_output": "",
            "passed": d.get("passed"),
            "error": "The code failed on this test" if d.get("error") else None,
            "hidden": True,
        })
    return shown
