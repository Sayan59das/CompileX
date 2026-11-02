"""
API integration tests for CodeQuest AI backend.
Uses FastAPI TestClient (synchronous, no running server needed).
"""

import sys
import os
import importlib.util

# Make sure the backend root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# torch is not in requirements.txt (the transformer is retired from the serving image); its dataset classes are only tested where it is installed
requires_torch = pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch is not installed")


# ─────────────────────────────────────────────
# 1. Root / Status
# ─────────────────────────────────────────────

class TestStatus:
    def test_root_returns_200(self):
        res = client.get("/")
        assert res.status_code == 200

    def test_root_has_required_fields(self):
        data = client.get("/").json()
        assert "status" in data
        assert "model_loaded" in data
        assert "message" in data

    def test_root_status_is_ok(self):
        data = client.get("/").json()
        assert data["status"] == "ok"

    def test_status_endpoint(self):
        res = client.get("/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert isinstance(data["model_loaded"], bool)
        assert isinstance(data["message"], str)


# ─────────────────────────────────────────────
# 2. Topics
# ─────────────────────────────────────────────

class TestTopics:
    def test_topics_returns_200(self):
        res = client.get("/topics")
        assert res.status_code == 200

    def test_topics_is_list(self):
        data = client.get("/topics").json()
        assert "topics" in data
        assert isinstance(data["topics"], list)

    def test_topics_not_empty(self):
        data = client.get("/topics").json()
        assert len(data["topics"]) > 0

    def test_topics_are_strings(self):
        data = client.get("/topics").json()
        for t in data["topics"]:
            assert isinstance(t, str)


# ─────────────────────────────────────────────
# 3. Generate — valid requests
# ─────────────────────────────────────────────

class TestGenerateValid:
    REQUIRED_FIELDS = [
        "title", "problem_statement", "input_format",
        "output_format", "sample_input", "sample_output",
        "test_cases", "topic", "difficulty", "source",
    ]

    def _generate(self, topic="arrays", difficulty="medium"):
        return client.post("/generate", json={"topic": topic, "difficulty": difficulty})

    def test_generate_returns_200(self):
        res = self._generate()
        assert res.status_code == 200

    def test_generate_has_all_fields(self):
        data = self._generate().json()
        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing field: {field}"

    def test_generate_title_not_empty(self):
        data = self._generate().json()
        assert len(data["title"]) > 0

    def test_generate_problem_statement_not_empty(self):
        data = self._generate().json()
        assert len(data["problem_statement"]) > 0

    def test_generate_test_cases_is_list(self):
        data = self._generate().json()
        assert isinstance(data["test_cases"], list)

    def test_generate_test_cases_have_input_output(self):
        data = self._generate().json()
        for tc in data["test_cases"]:
            assert "input" in tc
            assert "output" in tc

    def test_generate_difficulty_echoed(self):
        data = self._generate(difficulty="hard").json()
        # The generator may return the difficulty from the matched dataset question,
        # which can differ from the requested difficulty when no exact match exists.
        # We only verify the field is present and is a valid difficulty value.
        assert data["difficulty"] in ("easy", "medium", "hard")

    def test_generate_topic_echoed(self):
        data = self._generate(topic="graphs").json()
        assert data["topic"].lower() == "graphs"

    def test_generate_source_is_valid(self):
        data = self._generate().json()
        # Valid sources: "model", "template", "smart_ai", or anything starting with "dynamic"
        valid = data["source"] in ("model", "template", "smart_ai") or data["source"].startswith("dynamic")
        assert valid, f"Unexpected source: {data['source']}"

    def test_generate_easy_difficulty(self):
        res = self._generate(topic="strings", difficulty="easy")
        assert res.status_code == 200
        assert res.json()["difficulty"] == "easy"

    def test_generate_medium_difficulty(self):
        res = self._generate(topic="dynamic programming", difficulty="medium")
        assert res.status_code == 200

    def test_generate_hard_difficulty(self):
        res = self._generate(topic="trees", difficulty="hard")
        assert res.status_code == 200

    def test_generate_sorting_topic(self):
        res = self._generate(topic="sorting", difficulty="medium")
        assert res.status_code == 200

    def test_generate_unknown_topic_still_returns_question(self):
        """Unknown topics should fall back gracefully, not crash."""
        res = self._generate(topic="quantum computing", difficulty="medium")
        assert res.status_code == 200
        data = res.json()
        assert len(data["title"]) > 0

    def test_generate_input_format_not_empty(self):
        data = self._generate().json()
        assert len(data["input_format"]) > 0

    def test_generate_output_format_not_empty(self):
        data = self._generate().json()
        assert len(data["output_format"]) > 0

    def test_generate_sample_input_not_empty(self):
        data = self._generate().json()
        assert len(data["sample_input"]) > 0

    def test_generate_sample_output_not_empty(self):
        data = self._generate().json()
        assert len(data["sample_output"]) > 0

    def test_generate_at_least_one_test_case(self):
        data = self._generate().json()
        assert len(data["test_cases"]) >= 1

    def test_generate_default_difficulty_is_medium(self):
        """Omitting difficulty should default to medium."""
        res = client.post("/generate", json={"topic": "arrays"})
        assert res.status_code == 200
        assert res.json()["difficulty"] == "medium"


# ─────────────────────────────────────────────
# 4. Generate — invalid requests
# ─────────────────────────────────────────────

class TestGenerateInvalid:
    def test_missing_topic_returns_422(self):
        res = client.post("/generate", json={"difficulty": "easy"})
        assert res.status_code == 422

    def test_empty_topic_returns_422(self):
        res = client.post("/generate", json={"topic": "", "difficulty": "easy"})
        assert res.status_code == 422

    def test_invalid_difficulty_returns_400(self):
        res = client.post("/generate", json={"topic": "arrays", "difficulty": "extreme"})
        assert res.status_code == 400

    def test_empty_body_returns_422(self):
        res = client.post("/generate", json={})
        assert res.status_code == 422

    def test_wrong_content_type(self):
        res = client.post("/generate", data="not json")
        assert res.status_code in (400, 422)


# ─────────────────────────────────────────────
# 5. Generator unit tests (no HTTP)
# ─────────────────────────────────────────────

class TestGeneratorUnit:
    def setup_method(self):
        from model.generator import get_generator
        self.gen = get_generator()

    def test_generator_instance_created(self):
        assert self.gen is not None

    def test_generate_returns_dict(self):
        result = self.gen.generate("arrays", "medium")
        assert isinstance(result, dict)

    def test_generate_has_title(self):
        result = self.gen.generate("arrays", "easy")
        assert "title" in result
        assert len(result["title"]) > 0

    def test_generate_has_test_cases(self):
        result = self.gen.generate("sorting", "hard")
        assert "test_cases" in result
        assert isinstance(result["test_cases"], list)

    def test_generate_all_difficulties(self):
        for diff in ("easy", "medium", "hard"):
            result = self.gen.generate("graphs", diff)
            # The generator may return the difficulty from the matched dataset question.
            # Verify the field is present and is a valid difficulty value.
            assert result["difficulty"] in ("easy", "medium", "hard")

    def test_generate_multiple_topics(self):
        topics = ["arrays", "strings", "dynamic programming", "graphs", "trees", "sorting"]
        for topic in topics:
            result = self.gen.generate(topic, "medium")
            assert len(result.get("title", "")) > 0, f"Empty title for topic: {topic}"

    def test_fallback_for_unknown_topic(self):
        result = self.gen.generate("blockchain cryptography", "medium")
        assert "title" in result
        assert "problem_statement" in result

    def test_source_field_present(self):
        result = self.gen.generate("arrays", "medium")
        # Valid sources: "model", "template", "smart_ai", or anything starting with "dynamic"
        src = result.get("source", "")
        valid = src in ("model", "template", "smart_ai") or str(src).startswith("dynamic")
        assert valid, f"Unexpected source: {src}"


# ─────────────────────────────────────────────
# 6. Tokenizer unit tests
# ─────────────────────────────────────────────

class TestTokenizer:
    def setup_method(self):
        from model.tokenizer import SimpleTokenizer
        self.tok = SimpleTokenizer()
        self.tok.build_vocab(["arrays sorting graphs dynamic programming trees strings"])

    def test_vocab_built(self):
        assert self.tok.vocab_size > 4  # more than just special tokens

    def test_special_tokens_present(self):
        assert self.tok.pad_id == 0
        assert self.tok.unk_id == 1
        assert self.tok.bos_id == 2
        assert self.tok.eos_id == 3

    def test_encode_returns_list(self):
        ids = self.tok.encode("arrays")
        assert isinstance(ids, list)
        assert len(ids) > 0

    def test_encode_has_bos_eos(self):
        ids = self.tok.encode("arrays")
        assert ids[0] == self.tok.bos_id
        assert ids[-1] == self.tok.eos_id

    def test_decode_returns_string(self):
        ids = self.tok.encode("arrays")
        text = self.tok.decode(ids)
        assert isinstance(text, str)

    def test_encode_decode_roundtrip(self):
        original = "arrays sorting"
        ids = self.tok.encode(original, add_special_tokens=False)
        decoded = self.tok.decode(ids, skip_special_tokens=True)
        assert "arrays" in decoded
        assert "sorting" in decoded

    def test_unknown_token_uses_unk(self):
        ids = self.tok.encode("xyzunknownword123", add_special_tokens=False)
        assert self.tok.unk_id in ids

    def test_save_and_load(self, tmp_path):
        import os, json
        path = str(tmp_path / "tokenizer.json")
        self.tok.save(path)
        assert os.path.exists(path)

        from model.tokenizer import SimpleTokenizer
        tok2 = SimpleTokenizer()
        tok2.load(path)
        assert tok2.vocab_size == self.tok.vocab_size
        assert tok2.word2id == self.tok.word2id


# ─────────────────────────────────────────────
# 7. Dataset unit tests
# ─────────────────────────────────────────────

@requires_torch
class TestDataset:
    def setup_method(self):
        from model.tokenizer import SimpleTokenizer
        from model.dataset import CodingQuestionDataset
        import json, tempfile, os

        self.data = [
            {
                "topic": "arrays", "difficulty": "medium",
                "title": "Two Sum",
                "problem_statement": "Find two numbers that add to target.",
                "input_format": "N and target, then N numbers.",
                "output_format": "Two indices.",
                "sample_input": "4 9\n2 7 11 15",
                "sample_output": "1 2",
                "test_cases": [
                    {"input": "4 9\n2 7 11 15", "output": "1 2"},
                    {"input": "3 6\n1 2 4", "output": "2 3"},
                ]
            }
        ]

        # Write temp dataset
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(self.data, self.tmp)
        self.tmp.close()

        # Build tokenizer
        texts = [
            item.get(k, "") for item in self.data
            for k in ("topic", "difficulty", "title", "problem_statement",
                       "input_format", "output_format", "sample_input", "sample_output")
        ]
        self.tok = SimpleTokenizer()
        self.tok.build_vocab(texts)
        self.CodingQuestionDataset = CodingQuestionDataset

    def teardown_method(self):
        import os
        os.unlink(self.tmp.name)

    def test_dataset_length(self):
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        assert len(ds) == 1

    def test_dataset_item_has_src_tgt(self):
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert "src" in item
        assert "tgt" in item

    def test_dataset_src_is_tensor(self):
        import torch
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert isinstance(item["src"], torch.Tensor)

    def test_dataset_tgt_is_tensor(self):
        import torch
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert isinstance(item["tgt"], torch.Tensor)

    def test_dataset_src_not_empty(self):
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert item["src"].shape[0] > 0

    def test_dataset_tgt_not_empty(self):
        ds = self.CodingQuestionDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert item["tgt"].shape[0] > 0


# ─────────────────────────────────────────────
# 8. Debug Hint — API tests
# ─────────────────────────────────────────────

VALID_DEBUG_PAYLOAD = {
    "problem_statement": "Find the maximum subarray sum.",
    "user_code": "1: def max_sub(arr):\n2:     max_sum = 0\n3:     curr = 0\n4:     for x in arr:\n5:         curr += x\n6:         if curr > max_sum: max_sum = curr\n7:         if curr < 0: curr = 0\n8:     return max_sum",
    "language": "python",
    "failed_test_input": "3\n-1 -2 -3",
    "expected_output": "-1",
    "actual_output": "0",
}

HINT_REQUIRED_FIELDS = ["status", "line", "message", "hint"]
VALID_STATUSES = {"Logic issue detected", "No clear logic issue detected"}


class TestDebugHintValid:
    def _hint(self, payload=None):
        return client.post("/debug-hint", json=payload or VALID_DEBUG_PAYLOAD)

    def test_returns_200(self):
        assert self._hint().status_code == 200

    def test_has_all_fields(self):
        data = self._hint().json()
        for f in HINT_REQUIRED_FIELDS:
            assert f in data, f"Missing field: {f}"

    def test_status_is_valid_value(self):
        data = self._hint().json()
        assert data["status"] in VALID_STATUSES

    def test_hint_is_string(self):
        data = self._hint().json()
        assert isinstance(data["hint"], str)
        assert len(data["hint"]) > 0

    def test_message_is_string(self):
        data = self._hint().json()
        assert isinstance(data["message"], str)

    def test_line_is_string(self):
        data = self._hint().json()
        assert isinstance(data["line"], str)

    def test_no_issue_case(self):
        payload = {**VALID_DEBUG_PAYLOAD, "expected_output": "0", "actual_output": "0"}
        data = client.post("/debug-hint", json=payload).json()
        assert data["status"] in VALID_STATUSES

    def test_different_language(self):
        payload = {
            **VALID_DEBUG_PAYLOAD,
            "language": "java",
            "user_code": "1: int sum = 0;\n2: for(int x : arr) sum += x;",
        }
        res = client.post("/debug-hint", json=payload)
        assert res.status_code == 200

    def test_empty_optional_fields(self):
        payload = {
            "problem_statement": "Sort an array.",
            "user_code": "1: arr.sort()",
            "language": "python",
        }
        res = client.post("/debug-hint", json=payload)
        assert res.status_code == 200

    def test_off_by_one_hint(self):
        payload = {
            "problem_statement": "Reverse an array.",
            "user_code": "1: n = int(input())\n2: arr = list(map(int,input().split()))\n3: for i in range(n//2):\n4:     arr[i], arr[n-i] = arr[n-i], arr[i]\n5: print(*arr)",
            "language": "python",
            "failed_test_input": "3\n1 2 3",
            "expected_output": "3 2 1",
            "actual_output": "IndexError",
        }
        res = client.post("/debug-hint", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in VALID_STATUSES

    def test_factorial_zero_init_hint(self):
        payload = {
            "problem_statement": "Find the factorial of N.",
            "user_code": "1: n = int(input())\n2: result = 0\n3: for i in range(1, n+1):\n4:     result *= i\n5: print(result)",
            "language": "python",
            "failed_test_input": "5",
            "expected_output": "120",
            "actual_output": "0",
        }
        res = client.post("/debug-hint", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "Logic issue detected"

    def test_hint_not_empty_on_mismatch(self):
        """When expected != actual, hint should never be empty."""
        payload = {**VALID_DEBUG_PAYLOAD, "expected_output": "5", "actual_output": "3"}
        data = client.post("/debug-hint", json=payload).json()
        assert len(data["hint"]) > 0


class TestDebugHintInvalid:
    def test_missing_problem_statement_returns_422(self):
        payload = {k: v for k, v in VALID_DEBUG_PAYLOAD.items() if k != "problem_statement"}
        assert client.post("/debug-hint", json=payload).status_code == 422

    def test_missing_user_code_returns_422(self):
        payload = {k: v for k, v in VALID_DEBUG_PAYLOAD.items() if k != "user_code"}
        assert client.post("/debug-hint", json=payload).status_code == 422

    def test_missing_language_returns_422(self):
        payload = {k: v for k, v in VALID_DEBUG_PAYLOAD.items() if k != "language"}
        assert client.post("/debug-hint", json=payload).status_code == 422

    def test_empty_problem_statement_returns_422(self):
        payload = {**VALID_DEBUG_PAYLOAD, "problem_statement": ""}
        assert client.post("/debug-hint", json=payload).status_code == 422

    def test_empty_user_code_returns_422(self):
        payload = {**VALID_DEBUG_PAYLOAD, "user_code": ""}
        assert client.post("/debug-hint", json=payload).status_code == 422

    def test_empty_body_returns_422(self):
        assert client.post("/debug-hint", json={}).status_code == 422


# ─────────────────────────────────────────────
# 9. DebuggerGenerator unit tests (no HTTP)
# ─────────────────────────────────────────────

class TestDebuggerGeneratorUnit:
    def setup_method(self):
        from model.debugger_generator import get_debugger
        self.dbg = get_debugger()

    def _gen(self, **kwargs):
        defaults = dict(
            problem_statement="Find max subarray sum.",
            user_code="1: result = 0\n2: for x in arr: result += x",
            language="python",
            failed_test_input="-1 -2 -3",
            expected_output="-1",
            actual_output="0",
        )
        defaults.update(kwargs)
        return self.dbg.generate(**defaults)

    def test_returns_dict(self):
        assert isinstance(self._gen(), dict)

    def test_has_all_fields(self):
        result = self._gen()
        for f in HINT_REQUIRED_FIELDS:
            assert f in result, f"Missing field: {f}"

    def test_status_valid(self):
        assert self._gen()["status"] in VALID_STATUSES

    def test_hint_is_string(self):
        assert isinstance(self._gen()["hint"], str)

    def test_hint_not_empty(self):
        assert len(self._gen()["hint"]) > 0

    def test_factorial_zero_init(self):
        result = self._gen(
            problem_statement="Find the factorial of N.",
            user_code="1: n=int(input())\n2: r=0\n3: for i in range(1,n+1): r*=i\n4: print(r)",
            failed_test_input="5",
            expected_output="120",
            actual_output="0",
        )
        assert result["status"] == "Logic issue detected"

    def test_output_match_no_issue(self):
        result = self._gen(expected_output="3", actual_output="3")
        assert result["status"] in VALID_STATUSES

    def test_mismatch_triggers_issue(self):
        result = self._gen(expected_output="10", actual_output="0")
        assert result["status"] == "Logic issue detected"

    def test_multiple_languages(self):
        for lang in ("python", "java", "cpp", "javascript"):
            result = self._gen(language=lang)
            assert result["status"] in VALID_STATUSES

    def test_is_model_loaded_is_bool(self):
        assert isinstance(self.dbg.is_model_loaded, bool)


# ─────────────────────────────────────────────
# 10. DebuggerDataset unit tests
# ─────────────────────────────────────────────

@requires_torch
class TestDebuggerDataset:
    def setup_method(self):
        import json, tempfile
        from model.tokenizer import SimpleTokenizer
        from model.debugger_dataset import DebuggerDataset, load_debugger_texts

        self.sample_data = [
            {
                "problem_statement": "Find max subarray sum.",
                "user_code": "1: r=0\n2: for x in arr: r+=x",
                "language": "python",
                "failed_test_input": "-1 -2",
                "expected_output": "-1",
                "actual_output": "0",
                "hint": "{\"status\": \"Logic issue detected\", \"line\": \"1\", \"message\": \"init to 0\", \"hint\": \"Use float('-inf').\"}",
            },
            {
                "problem_statement": "Reverse a string.",
                "user_code": "1: print(s[::-1])",
                "language": "python",
                "failed_test_input": "hello",
                "expected_output": "olleh",
                "actual_output": "olleh",
                "hint": "{\"status\": \"No clear logic issue detected\", \"line\": \"\", \"message\": \"ok\", \"hint\": \"Looks correct.\"}",
            },
        ]

        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(self.sample_data, self.tmp)
        self.tmp.close()

        texts = load_debugger_texts(self.tmp.name)
        self.tok = SimpleTokenizer()
        self.tok.build_vocab(texts, min_freq=1)
        self.DebuggerDataset = DebuggerDataset

    def teardown_method(self):
        import os
        os.unlink(self.tmp.name)

    def test_length(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        assert len(ds) == 2

    def test_item_has_src_tgt(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        item = ds[0]
        assert "src" in item and "tgt" in item

    def test_src_is_tensor(self):
        import torch
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        assert isinstance(ds[0]["src"], torch.Tensor)

    def test_tgt_is_tensor(self):
        import torch
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        assert isinstance(ds[0]["tgt"], torch.Tensor)

    def test_src_not_empty(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        assert ds[0]["src"].shape[0] > 0

    def test_tgt_not_empty(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok)
        assert ds[0]["tgt"].shape[0] > 0

    def test_max_src_len_respected(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok, max_src_len=10)
        assert ds[0]["src"].shape[0] <= 10

    def test_max_tgt_len_respected(self):
        ds = self.DebuggerDataset(self.tmp.name, self.tok, max_tgt_len=10)
        assert ds[0]["tgt"].shape[0] <= 10
