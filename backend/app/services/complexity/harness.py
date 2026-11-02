"""What the locked Python harness says about the arguments of the player's function.

A Python function has no declared types, but the harness below the marker line reads every argument in a fixed way
(`n = int(...)`, `s = str(...)`, `a = [int(t) for t in ...]`, `words = [str(t) for t in ...]`). Reading that back tells the cost
analysis which parameter is a number, a string, a list of numbers or a list of words, which it cannot see in the signature.
The C, C++ and Java starters already carry the types in the signature, so this is only needed for Python.
"""

from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

_NUMBERS = {"int": "int", "float": "int", "bool": "int"}
_MAX_DEPTH = 5


def _shape(e, defs: Dict[str, ast.AST], depth: int = 0) -> Optional[str]:
    """`int`, `str`, `List[int]`, `List[str]`, `List[List[int]]` for the expression a harness reads an argument with."""
    if depth > _MAX_DEPTH:
        return None
    if isinstance(e, ast.Name):
        return _shape(defs[e.id], defs, depth + 1) if e.id in defs else None
    if isinstance(e, ast.Call):
        f = e.func
        name = f.id if isinstance(f, ast.Name) else None
        if name in _NUMBERS:
            return "int"
        if name == "str":
            return "str"
        if name == "input":
            return "str"
        if name in ("list", "tuple", "sorted") and e.args:
            a = e.args[0]
            if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id == "map" and a.args \
                    and isinstance(a.args[0], ast.Name):
                inner = "str" if a.args[0].id == "str" else "int"
                return f"List[{inner}]"
            return _shape(a, defs, depth + 1)
        if isinstance(f, ast.Attribute):
            if f.attr == "split":
                return "List[str]"
            if f.attr in ("strip", "rstrip", "lstrip"):
                return "str"
        return None
    if isinstance(e, (ast.ListComp, ast.GeneratorExp)):
        inner = _shape(e.elt, defs, depth + 1)
        return f"List[{inner}]" if inner else None
    return None


def python_param_types(code: str) -> Optional[Tuple[str, List[Optional[str]]]]:
    """(the name of the function the harness calls, the type of each argument it passes), or None when no harness is found."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    main = funcs.get("main")
    if main is None:
        return None
    defs: Dict[str, ast.AST] = {}
    for n in ast.walk(main):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            defs[n.targets[0].id] = n.value
    for n in ast.walk(main):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs and n.func.id != "main" \
                and n.args and all(isinstance(a, ast.Name) for a in n.args):
            return n.func.id, [_shape(defs[a.id], defs) if a.id in defs else None for a in n.args]   # type: ignore[attr-defined]
    return None
