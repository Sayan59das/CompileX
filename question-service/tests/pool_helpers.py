"""Small builders shared by the pool tests. Nothing here depends on the private qgen folder."""

import copy


def make_question(n, topic="arrays", difficulty="easy", title=None):
    return {
        "title": title or f"Question {n}", "problem_statement": f"Statement number {n} about trays of rolls.",
        "input_format": "First line: n.", "output_format": "One integer.", "constraints": "1 <= n <= 5",
        "sample_input": "1\n2", "sample_output": f"SAMPLE-{n}",
        "test_cases": [{"input": f"{i}\n{i}", "output": f"HIDDEN-{n}-{i}"} for i in range(5)],
        "function_name": f"solve_{n}",
        "parameters": [{"name": "n", "type": "int", "description": "a number", "example": "1"}],
        "return_type": "int", "return_description": "the answer", "input_schema": "n:int", "output_schema": "int",
        "starter_code": {"python": "def f(): pass", "cpp": "int f();", "java": "class S {}", "javascript": "function f() {}"},
        "topic": topic, "difficulty": difficulty, "core_idea": f"idea {n}",
    }


def make_spec(n, topic="arrays", difficulty="easy"):
    return {"structural_signature": f"sig-{topic}-{difficulty}-{n}", "seed": n, "topic": topic, "difficulty": difficulty, "steps": []}


def add_pending(repo, n, topic="arrays", difficulty="easy"):
    question_id, reason = repo.add_pending(make_question(n, topic, difficulty), make_spec(n, topic, difficulty))
    assert question_id is not None, reason
    return question_id


def add_live(repo, n, topic="arrays", difficulty="easy", by="tester"):
    question_id = add_pending(repo, n, topic, difficulty)
    assert repo.approve(question_id, by) and repo.publish(question_id)
    return question_id


class FakeBank:
    """Stands in for model.reviewed_bank: {(topic, difficulty): [question, ...]}."""

    def __init__(self, data=None):
        self.data = data or {}

    def buckets(self):
        return list(self.data)

    def topic_key(self, topic):
        key = " ".join(topic.strip().lower().replace("_", " ").split())
        return {"array": "arrays", "string": "strings", "graph": "graphs"}.get(key, key)

    def questions(self, topic, difficulty):
        return [copy.deepcopy(q) for q in self.data.get((self.topic_key(topic), difficulty.strip().lower()), [])]


class Counter:
    """A clock that moves one second per call, so 'served longest ago' is deterministic."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 1.0
        return self.now
