"""Selection is stateless and driven by the caller's exclusion list (the user's history)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from model import question_db
from model.smart_generator import generate_smart


def _big_bucket(min_size=15):
    for topic, by_diff in question_db.get_stats().items():
        for difficulty, count in by_diff.items():
            if count >= min_size:
                return topic, difficulty, count
    pytest.skip("no question_db bucket large enough")


def _titles(topic, difficulty):
    question_db._load()
    return [q["title"].lower() for q in question_db._store[(topic, difficulty)]]


def test_picks_vary_instead_of_following_one_fixed_order():
    topic, difficulty, _ = _big_bucket()
    firsts = {question_db.get_question(topic, difficulty)["title"] for _ in range(60)}
    assert len(firsts) > 3


def test_nothing_is_remembered_between_calls():
    topic, difficulty, count = _big_bucket()
    # far more calls than questions: a shared "served" set would run dry and return None
    for _ in range(count * 3):
        assert question_db.get_question(topic, difficulty) is not None


def test_excluded_titles_are_never_returned():
    topic, difficulty, _ = _big_bucket()
    titles = _titles(topic, difficulty)
    keep = titles[0]
    for _ in range(30):
        q = question_db.get_question(topic, difficulty, exclude_titles=titles[1:])
        assert q["title"].lower() == keep


def test_returns_none_when_everything_is_excluded():
    topic, difficulty, _ = _big_bucket()
    assert question_db.get_question(topic, difficulty, exclude_titles=_titles(topic, difficulty)) is None


def test_each_user_never_repeats_but_users_get_different_sequences():
    topic, difficulty, _ = _big_bucket()
    sequences = []
    for _user in range(15):
        history, sequence = [], []
        for _ in range(5):
            q = question_db.get_question(topic, difficulty, exclude_titles=history)
            title = q["title"].lower()
            assert title not in history
            history.append(title)
            sequence.append(title)
        sequences.append(tuple(sequence))
    assert len(set(sequences)) > 1


def test_smart_generator_reports_the_original_title_and_honors_it_as_exclusion():
    first = generate_smart("arrays", "easy")
    assert first and first["base_title"]

    excluded = [first["base_title"]]
    for _ in range(25):
        again = generate_smart("arrays", "easy", exclude_titles=excluded)
        if again is None:
            break
        assert again["base_title"].lower() != first["base_title"].lower()
