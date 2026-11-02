"""A real cost analysis for the code a player writes (Python, C, C++, Java, JavaScript).

    result = analyze_source(code, "python")      # EngineResult, or None when the code could not be analyzed

See engine.py for how it works.
"""

from __future__ import annotations

import traceback
from typing import Optional

from .engine import Budget, Engine, EngineResult
from .mag import Mag, parse_o

__all__ = ["analyze_source", "EngineResult", "Mag", "parse_o"]


def analyze_source(code: str, language: str, debug: bool = False, harness_code: Optional[str] = None) -> Optional[EngineResult]:
    """`harness_code` is the whole file when `code` is only the player's part: its locked harness tells what the arguments are."""
    lang = (language or "").lower().strip()
    try:
        hints = None
        if lang == "python":
            from . import harness, py_frontend
            module = py_frontend.parse(code)
            found = harness.python_param_types(harness_code if harness_code is not None else code)
            if found:
                hints = {found[0]: found[1]}
        elif lang in ("c", "cpp", "c++", "java", "javascript", "js"):
            from . import ts_frontend
            module = ts_frontend.parse(code, lang)
        else:
            return None
        return Engine(module, lang, hints).run()
    except (Budget, SyntaxError, RecursionError, ImportError):
        return None
    except Exception:
        if debug:
            raise
        traceback.print_exc()
        return None
