"""A template is one real problem: a player gets each one at most once, and is told when they run out.

The template generator used to dress the same problem in new titles ("Evaluate: Sort Array Method [2BBD]"),
so the player's history never matched and the same two or three problems came back forever.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

import main_dynamic
from model import dynamic_generator as dg

TOPICS = sorted(dg.TOPIC_TEMPLATES)
DIFFICULTIES = ("easy", "medium", "hard")


def drain(topic, difficulty, remember="both"):
    """Keep asking as one player would. Returns the template identities served before it ran dry."""
    seen, bases = [], []
    while True:
        try:
            q = dg.generate_dynamic(topic, difficulty, exclude_titles=seen)
        except dg.NoFreshQuestion:
            return bases
        bases.append(q["base_title"])
        if remember == "both":
            seen += [q["title"].lower(), q["base_title"].lower()]
        else:  # the history stores only the base title
            seen.append(q["base_title"].lower())
        assert len(bases) < 40, "exclusion is not working: the generator never runs out"


@pytest.mark.parametrize("topic", TOPICS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_a_player_gets_each_template_once_then_runs_out(topic, difficulty):
    bases = drain(topic, difficulty)
    assert bases, "every topic and difficulty must offer at least one template"
    assert len(bases) == len(set(bases)), f"a template was served twice: {bases}"


def test_the_player_history_only_needs_the_base_title():
    bases = drain("sorting", "easy", remember="base")
    assert len(bases) == len(set(bases)) >= 1


def test_the_identity_is_the_template_not_its_costume():
    seen_bases, seen_titles = set(), set()
    for _ in range(60):
        q = dg.generate_dynamic("sorting", "easy")
        seen_bases.add(q["base_title"])
        seen_titles.add(q["title"])
        assert "[" not in q["base_title"], "base_title must not carry the random tag"
    # 60 calls may wear many different titles but they are only a few real problems
    assert len(seen_bases) <= 6
    assert len(seen_titles) > len(seen_bases)


def test_running_out_is_per_player_not_global():
    assert drain("sorting", "easy")
    assert drain("sorting", "easy"), "a second player must start from scratch, not inherit the first one's history"


def test_other_topics_are_unaffected_when_one_runs_out():
    drain("sorting", "easy")
    assert dg.generate_dynamic("arrays", "easy", exclude_titles=[])["title"]


@pytest.fixture
def templates_only(monkeypatch):
    """Route /generate straight to the template generator so the banks do not answer first."""
    monkeypatch.setattr(main_dynamic, "_bank_order", lambda topic, difficulty: [])
    monkeypatch.setattr(main_dynamic, "_trained_generator", None)
    return TestClient(main_dynamic.app)


def test_generate_reports_the_identity_and_then_a_clean_404(templates_only):
    client = templates_only
    exclude, served = [], []
    for _ in range(40):
        r = client.post("/generate", json={"topic": "sorting", "difficulty": "easy", "exclude_titles": exclude})
        if r.status_code == 404:
            assert "No unseen" in r.json()["detail"]
            break
        assert r.status_code == 200, r.text
        body = r.json()
        served.append(body["base_title"])
        exclude += [body["title"].lower(), body["base_title"].lower()]
    else:
        pytest.fail("the service never ran out of questions for one player")
    assert 1 <= len(served) == len(set(served))


def test_generate_still_answers_a_new_player_after_another_ran_out(templates_only):
    client = templates_only
    exclude = []
    while True:
        r = client.post("/generate", json={"topic": "math", "difficulty": "easy", "exclude_titles": exclude})
        if r.status_code != 200:
            break
        exclude += [r.json()["title"].lower(), r.json()["base_title"].lower()]
    assert client.post("/generate", json={"topic": "math", "difficulty": "easy"}).status_code == 200
