"""
Debugger hint generator — loads the trained debugger model and produces
a short JSON hint for a failed test case.

Falls back to a rule-based heuristic if no trained model is found.
"""

import os
import json
import re

_TORCH_AVAILABLE = False
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore

try:
    from .tokenizer import SimpleTokenizer
    from .transformer_model import CodingQuestionTransformer
    from .debugger_dataset import format_debugger_src
except ImportError:
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from tokenizer import SimpleTokenizer
        from transformer_model import CodingQuestionTransformer
        from debugger_dataset import format_debugger_src
    except ImportError:
        SimpleTokenizer = None  # type: ignore
        CodingQuestionTransformer = None  # type: ignore
        format_debugger_src = None  # type: ignore

if _TORCH_AVAILABLE:
    _no_grad = torch.no_grad
else:
    # torch is optional; without it the class body must still be importable so
    # the module can fall back to the rule-based hint path.
    def _no_grad():
        def _decorator(fn):
            return fn
        return _decorator


_DEBUGGER_INSTANCE = None


def get_debugger():
    global _DEBUGGER_INSTANCE
    if _DEBUGGER_INSTANCE is None:
        _DEBUGGER_INSTANCE = DebuggerGenerator()
    return _DEBUGGER_INSTANCE


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def _rule_based_hint(problem_statement: str, user_code: str, language: str,
                     failed_test_input: str, expected_output: str, actual_output: str) -> dict:
    """Very lightweight heuristic hints when no model is available."""
    code_lower = user_code.lower()
    lines = user_code.split("\n")

    # Off-by-one in loop bounds
    for i, line in enumerate(lines, 1):
        if re.search(r"range\s*\(\s*\w+\s*\)", line) and "- 1" not in line and "-1" not in line:
            if "index" in problem_statement.lower() or "array" in problem_statement.lower():
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Possibly missing -1 in range bound",
                    "hint": f"Line {i}: check if the loop bound should be range(n-1) to avoid an off-by-one or index out of bounds.",
                }

    # Initialisation to 0 when 1 is needed (factorial / product)
    if "factorial" in problem_statement.lower() or "product" in problem_statement.lower():
        for i, line in enumerate(lines, 1):
            if re.search(r"=\s*0\b", line) and "count" not in line and "sum" not in line:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Variable likely initialised to 0 instead of 1",
                    "hint": f"Line {i}: for a product/factorial, initialise the accumulator to 1, not 0.",
                }

    # Expected vs actual both non-empty but differ
    if expected_output and actual_output and expected_output.strip() != actual_output.strip():
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": "Output mismatch detected",
            "hint": f"Expected '{expected_output.strip()}' but got '{actual_output.strip()}'; likely a logic error in the core computation.",
        }

    return {
        "status": "No clear logic issue detected",
        "line": "",
        "message": "Could not identify a specific issue",
        "hint": "Review the algorithm logic against the failed test case manually.",
    }


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class DebuggerGenerator:
    MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_debugger_model")
    MODEL_PATH = os.path.join(MODEL_DIR, "model.pt")
    TOKENIZER_PATH = os.path.join(MODEL_DIR, "tokenizer.json")

    MAX_SRC_LEN = 512
    MAX_GEN_LEN = 150

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self._try_load_model()

    def _try_load_model(self):
        if not _TORCH_AVAILABLE:
            print("[Debugger] PyTorch not available. Using rule-based fallback.")
            return
        if not (os.path.exists(self.MODEL_PATH) and os.path.exists(self.TOKENIZER_PATH)):
            print("[Debugger] No trained model found. Using rule-based fallback.")
            return
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = SimpleTokenizer()
            self.tokenizer.load(self.TOKENIZER_PATH)
            self.model = CodingQuestionTransformer(
                vocab_size=self.tokenizer.vocab_size,
                max_seq_len=max(self.MAX_SRC_LEN, self.MAX_GEN_LEN) + 10,
            )
            self.model.load_state_dict(torch.load(self.MODEL_PATH, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            print(f"[Debugger] Model loaded on {self.device}.")
        except Exception as e:
            print(f"[Debugger] Failed to load model: {e}. Using fallback.")
            self.model = None
            self.tokenizer = None

    @property
    def is_model_loaded(self) -> bool:
        return self.model is not None

    def generate(self, problem_statement: str, user_code: str, language: str,
                 failed_test_input: str, expected_output: str, actual_output: str) -> dict:
        if not self.is_model_loaded:
            return _rule_based_hint(problem_statement, user_code, language,
                                    failed_test_input, expected_output, actual_output)
        try:
            return self._model_generate(problem_statement, user_code, language,
                                        failed_test_input, expected_output, actual_output)
        except Exception as e:
            print(f"[Debugger] Generation error: {e}. Falling back.")
            return _rule_based_hint(problem_statement, user_code, language,
                                    failed_test_input, expected_output, actual_output)

    @_no_grad()
    def _model_generate(self, problem_statement, user_code, language,
                        failed_test_input, expected_output, actual_output) -> dict:
        src_text = format_debugger_src({
            "problem_statement": problem_statement,
            "user_code": user_code,
            "language": language,
            "failed_test_input": failed_test_input,
            "expected_output": expected_output,
            "actual_output": actual_output,
        })

        src_ids = self.tokenizer.encode(src_text)[: self.MAX_SRC_LEN]
        src_tensor = torch.tensor([src_ids], dtype=torch.long).to(self.device)
        src_mask = (src_tensor == 0)

        memory = self.model.encode(src_tensor, src_key_padding_mask=src_mask)

        # Greedy decode
        tgt_ids = [self.tokenizer.bos_id]
        for _ in range(self.MAX_GEN_LEN):
            tgt_tensor = torch.tensor([tgt_ids], dtype=torch.long).to(self.device)
            out = self.model.decode(tgt_tensor, memory, memory_key_padding_mask=src_mask)
            logits = self.model.output_projection(out[:, -1, :])
            next_id = logits.argmax(-1).item()
            if next_id == self.tokenizer.eos_id:
                break
            tgt_ids.append(next_id)

        raw = self.tokenizer.decode(tgt_ids[1:])  # strip BOS
        return self._parse_hint(raw)

    def _parse_hint(self, raw: str) -> dict:
        """Try to extract JSON from model output; fall back to wrapping raw text."""
        # Try to find a JSON object in the output
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Wrap raw output as a hint
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": raw[:120] if raw else "See hint",
            "hint": raw[:200] if raw else "Review your logic against the failed test case.",
        }
