"""
Smart Debugger — Enhanced rule-based logic analyser that produces precise,
structured JSON hints for failed test cases.

Uses AST analysis + pattern matching + output analysis to identify
the single most likely root-cause logic error.
"""

import re
import ast
import json
from typing import Optional, List, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lines(code: str) -> list[str]:
    return code.split("\n")


def _strip_comments(line: str) -> str:
    return re.sub(r"#.*$", "", line).strip()


def _find_first_match(patterns: list[str], code: str) -> Optional[re.Match]:
    for p in patterns:
        m = re.search(p, code, re.IGNORECASE)
        if m:
            return m
    return None


def _line_of(code: str, pattern: str) -> Optional[int]:
    """Return 1-based line number of first match, or None."""
    for i, line in enumerate(_lines(code), 1):
        if re.search(pattern, line):
            return i
    return None


def _output_diff(expected: str, actual: str) -> Optional[Tuple[str, float]]:
    """Return (description, numeric_diff) if outputs differ numerically."""
    e = expected.strip()
    a = actual.strip()
    if not e or not a:
        return None
    try:
        ev = float(e)
        av = float(a)
        if ev != av:
            diff = av - ev
            return (f"off by {diff:+g}", diff)
    except ValueError:
        pass
    return None


def _parse_python_ast(code: str) -> Optional[ast.Module]:
    """Try to parse Python code into AST."""
    try:
        return ast.parse(code)
    except:
        return None


def _find_function_def(tree: ast.Module, func_name: str = None) -> Optional[ast.FunctionDef]:
    """Find function definition in AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if func_name is None or node.name == func_name:
                return node
    return None


def _has_return_in_loop(tree: ast.Module) -> Optional[int]:
    """Check if there's a return statement inside a loop. Returns line number."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child != node:
                    return child.lineno
    return None


def _analyze_output_pattern(expected: str, actual: str) -> Optional[dict]:
    """Analyze output patterns to detect common issues."""
    e = expected.strip()
    a = actual.strip()

    # ── Runtime / crash errors in actual output ───────────────────────────
    al = a.lower()
    if any(kw in al for kw in ["error", "exception", "traceback", "segfault",
                                "killed", "timeout", "tle", "mle", "runtime"]):
        if "time limit" in al or "tle" in al:
            return {
                "type": "tle",
                "message": "Time Limit Exceeded",
                "hint": "Your solution is too slow. Replace nested loops with a hash map, "
                        "prefix sum, or a more efficient algorithm (O(n) or O(n log n)).",
            }
        if "memory" in al or "mle" in al:
            return {
                "type": "mle",
                "message": "Memory Limit Exceeded",
                "hint": "Your solution uses too much memory. Avoid storing the entire input "
                        "in extra arrays when you can process it in-place.",
            }
        if "zerodivision" in al or "division by zero" in al:
            return {
                "type": "division_by_zero",
                "message": "Division by zero",
                "hint": "Add a guard `if denominator != 0` before dividing.",
            }
        if "index" in al and ("out of range" in al or "out of bounds" in al):
            return {
                "type": "index_error",
                "message": "Index out of bounds",
                "hint": "Check your loop bounds — you're accessing an index that doesn't exist. "
                        "Use `range(len(arr))` and verify `i < len(arr)` before indexing.",
            }
        if "nonetype" in al or "null pointer" in al or "attributeerror" in al:
            return {
                "type": "null_error",
                "message": "Null/None reference error",
                "hint": "A variable is None/null when you try to use it. "
                        "Initialize all variables before using them.",
            }
        if "stackoverflow" in al or "maximum recursion" in al:
            return {
                "type": "stack_overflow",
                "message": "Stack overflow / infinite recursion",
                "hint": "Your recursion has no base case or it's never reached. "
                        "Add a proper base case and ensure each call moves toward it.",
            }
        if "typeerror" in al:
            return {
                "type": "type_error",
                "message": "Type error",
                "hint": "You're mixing incompatible types. "
                        "Convert inputs with `int()`, `float()`, or `str()` as needed.",
            }
        if "syntaxerror" in al or "compilation failed" in al:
            return {
                "type": "syntax_error",
                "message": "Syntax / compilation error",
                "hint": "Fix the syntax error before submitting. "
                        "Check for missing colons, unmatched brackets, or wrong indentation.",
            }
        return {
            "type": "runtime_error",
            "message": f"Runtime error: {a[:100]}",
            "hint": "Your code crashes on this input. Check for: index out of bounds, "
                    "division by zero, None/null access, or type mismatches.",
        }

    # ── No output ─────────────────────────────────────────────────────────
    if e and not a:
        return {
            "type": "empty_output",
            "message": "Output is empty when result is expected",
            "hint": "Check if you're printing/returning the result. "
                    "The function may be missing a return statement or print call.",
        }

    # ── Element count mismatch ────────────────────────────────────────────
    e_parts = e.split()
    a_parts = a.split()
    if len(e_parts) != len(a_parts) and len(e_parts) > 0 and len(a_parts) > 0:
        if len(a_parts) < len(e_parts):
            return {
                "type": "missing_elements",
                "message": f"Output has {len(a_parts)} elements but expected {len(e_parts)}",
                "hint": f"Your output is missing {len(e_parts) - len(a_parts)} element(s). "
                        "Check for early exits (`break`/`return`) inside your loop.",
            }
        else:
            return {
                "type": "extra_elements",
                "message": f"Output has {len(a_parts)} elements but expected {len(e_parts)}",
                "hint": f"Your output has {len(a_parts) - len(e_parts)} extra element(s). "
                        "Check for duplicate appends or an extra iteration.",
            }

    # ── Reversed output ───────────────────────────────────────────────────
    if len(e_parts) == len(a_parts) and len(e_parts) > 1:
        if e_parts == list(reversed(a_parts)):
            return {
                "type": "reversed_output",
                "message": "Output is in reverse order",
                "hint": "Your output is reversed. Check your traversal direction "
                        "or reverse the result before printing.",
            }

    # ── Correct values, wrong order ───────────────────────────────────────
    try:
        e_nums = [float(x) for x in e_parts]
        a_nums = [float(x) for x in a_parts]
        if len(e_nums) == len(a_nums) and len(e_nums) > 1:
            if sorted(e_nums) == sorted(a_nums) and e_nums != a_nums:
                return {
                    "type": "wrong_order",
                    "message": "Output has correct elements but wrong order",
                    "hint": "Your output contains the right values but in the wrong order. "
                            "Check if the problem requires a specific ordering.",
                }
            # All values off by same constant
            diffs = [a - e for a, e in zip(a_nums, e_nums)]
            if len(set(diffs)) == 1 and diffs[0] != 0:
                d = diffs[0]
                if d == 1:
                    return {
                        "type": "off_by_one_high",
                        "message": "All values are 1 too high",
                        "hint": "Every output value is 1 more than expected. "
                                "Check for 1-based vs 0-based indexing or an extra `+1`.",
                    }
                if d == -1:
                    return {
                        "type": "off_by_one_low",
                        "message": "All values are 1 too low",
                        "hint": "Every output value is 1 less than expected. "
                                "Check for 0-based vs 1-based indexing or a missing `+1`.",
                    }
                return {
                    "type": "systematic_offset",
                    "message": f"All values are off by {d:+g}",
                    "hint": f"Every output value differs from expected by {d:+g}. "
                            "There's a systematic error — check your formula or initial value.",
                }
            # Sign flip
            if all(a == -e for a, e in zip(a_nums, e_nums)):
                return {
                    "type": "sign_flip",
                    "message": "All values have the wrong sign",
                    "hint": "Your values are negated. Check your subtraction order or multiplication sign.",
                }
    except ValueError:
        pass

    return None


# ---------------------------------------------------------------------------
# Language-specific analysers
# ---------------------------------------------------------------------------

def _analyse_python(code: str, problem: str, failed_input: str,
                    expected: str, actual: str) -> Optional[dict]:
    lines = _lines(code)
    prob = problem.lower()
    tree = _parse_python_ast(code)

    # ── 0. Output pattern analysis (high priority) ───────────────────────
    pattern_issue = _analyze_output_pattern(expected, actual)
    if pattern_issue:
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": pattern_issue["message"],
            "hint": pattern_issue["hint"],
        }

    # ── 1. Off-by-one in range() ─────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = _strip_comments(raw)
        # range(n) where n-1 is needed (array indexing context)
        m = re.search(r"range\s*\(\s*(\w+)\s*\)", line)
        if m and re.search(r"\[.*" + re.escape(m.group(1)), line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Possible off-by-one: iterating range(n) while indexing with the same variable",
                "hint": f"Line {i}: using `range(n)` and indexing with the loop variable may cause an index-out-of-bounds; consider `range(n-1)` or `range(len(arr))`.",
            }
        # range(1, n) when range(n) or range(n+1) is needed
        m2 = re.search(r"range\s*\(\s*1\s*,\s*(\w+)\s*\)", line)
        if m2:
            diff_result = _output_diff(expected, actual)
            if diff_result and abs(diff_result[1]) == 1:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Loop starts at 1 instead of 0 — possible off-by-one",
                    "hint": f"Line {i}: `range(1, n)` skips index 0. If processing an array, use `range(n)` or `range(len(arr))`.",
                }

    # ── 2. Wrong initialisation for product/factorial ────────────────────
    if any(k in prob for k in ["product", "factorial", "multiply"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if re.search(r"\bresult\s*=\s*0\b|\bprod\s*=\s*0\b|\bans\s*=\s*0\b", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Accumulator initialised to 0 for a product operation",
                    "hint": f"Line {i}: initialise the product variable to 1, not 0, otherwise the result will always be 0.",
                }

    # ── 3. Sorting direction ─────────────────────────────────────────────
    if any(k in prob for k in ["maximum", "largest", "descend", "top k", "kth largest"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if re.search(r"\.sort\s*\(\s*\)", line) or (re.search(r"sorted\s*\(", line) and "reverse" not in line):
                if "reverse" not in line:
                    return {
                        "status": "Logic issue detected",
                        "line": str(i),
                        "message": "Sorting in ascending order when descending is likely needed",
                        "hint": f"Line {i}: problem asks for maximum/largest — use `.sort(reverse=True)` or `sorted(..., reverse=True)`.",
                    }
    
    if any(k in prob for k in ["minimum", "smallest", "ascend", "kth smallest"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if "reverse=True" in line or "reverse = True" in line:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Sorting in descending order when ascending is needed",
                    "hint": f"Line {i}: problem asks for minimum/smallest — remove `reverse=True` to sort in ascending order.",
                }

    # ── 4. Wrong comparison operator (= vs ==) ───────────────────────────
    for i, raw in enumerate(lines, 1):
        line = _strip_comments(raw)
        if re.search(r"\bif\b.*[^=!<>]=[^=]", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Possible assignment inside condition (= instead of ==)",
                "hint": f"Line {i}: looks like an assignment `=` is used where a comparison `==` was intended.",
            }

    # ── 5. Integer division vs float division ────────────────────────────
    if any(k in prob for k in ["average", "mean", "median", "divide"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if re.search(r"//", line) and "floor" not in prob:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Integer (floor) division used where float division may be needed",
                    "hint": f"Line {i}: `//` truncates decimals; use `/` for the average/mean calculation.",
                }

    # ── 6. Missing modulo for circular / wrap-around problems ────────────
    if any(k in prob for k in ["circular", "rotate", "wrap", "cyclic"]):
        has_mod = any("%" in l for l in lines)
        if not has_mod:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No modulo operator found for a circular/rotation problem",
                "hint": "Likely missing `% n` to handle wrap-around indices in a circular array or rotation.",
            }

    # ── 7. Return inside loop (early exit) ───────────────────────────────
    if any(k in prob for k in ["count", "sum", "total", "all"]):
        if tree:
            return_line = _has_return_in_loop(tree)
            if return_line:
                return {
                    "status": "Logic issue detected",
                    "line": str(return_line),
                    "message": "return statement inside loop may cause premature exit",
                    "hint": f"Line {return_line}: `return` inside the loop exits after the first iteration; move it outside to process all elements.",
                }

    # ── 8. Wrong base case in recursion ──────────────────────────────────
    if any(k in prob for k in ["fibonacci", "factorial", "recursive", "recursion"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if re.search(r"\bif\s+n\s*==\s*0\b", line) and "fibonacci" in prob:
                # Check if n==1 base case is also handled
                full = "\n".join(lines)
                if not re.search(r"\bif\s+n\s*==\s*1\b|\belif\s+n\s*==\s*1\b", full):
                    return {
                        "status": "Logic issue detected",
                        "line": str(i),
                        "message": "Fibonacci base case for n==1 may be missing",
                        "hint": f"Line {i}: Fibonacci needs base cases for both n==0 (return 0) and n==1 (return 1).",
                    }

    # ── 9. Two-pointer not moving both pointers ───────────────────────────
    if any(k in prob for k in ["two pointer", "two-pointer", "pair", "sum"]):
        ptr_lines = [i for i, l in enumerate(lines, 1)
                     if re.search(r"\bleft\b|\bright\b|\blo\b|\bhi\b", l)]
        if ptr_lines:
            full = "\n".join(lines)
            moves_left = bool(re.search(r"left\s*\+=|left\s*\-=|lo\s*\+=", full))
            moves_right = bool(re.search(r"right\s*\+=|right\s*\-=|hi\s*\-=", full))
            if moves_left and not moves_right:
                return {
                    "status": "Logic issue detected",
                    "line": str(ptr_lines[0]),
                    "message": "Right pointer never moves in two-pointer approach",
                    "hint": f"Around line {ptr_lines[0]}: the right/hi pointer is never updated; both pointers must move to avoid an infinite loop.",
                }
            if moves_right and not moves_left:
                return {
                    "status": "Logic issue detected",
                    "line": str(ptr_lines[0]),
                    "message": "Left pointer never moves in two-pointer approach",
                    "hint": f"Around line {ptr_lines[0]}: the left/lo pointer is never updated; both pointers must move to avoid an infinite loop.",
                }

    # ── 10. Missing return statement ─────────────────────────────────────
    if tree:
        func_def = _find_function_def(tree)
        if func_def:
            has_return = any(isinstance(node, ast.Return) for node in ast.walk(func_def))
            if not has_return and "print" not in prob:
                return {
                    "status": "Logic issue detected",
                    "line": str(func_def.lineno),
                    "message": "Function has no return statement",
                    "hint": f"Line {func_def.lineno}: function `{func_def.name}` doesn't return anything. Add a `return` statement with the result.",
                }

    # ── 11. Algorithm-level checks ───────────────────────────────────────
    # Greedy: missing sort
    if any(k in prob for k in ["activity", "interval", "schedule", "greedy"]):
        if not any(re.search(r"sort|sorted", l, re.IGNORECASE) for l in lines):
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No sorting found before greedy selection",
                "hint": "Greedy interval/activity problems require sorting by end time first.",
            }

    # BFS/DFS: missing visited
    if any(k in prob for k in ["graph", "bfs", "dfs", "path", "connected"]):
        if not any(re.search(r"visited|seen|marked", l, re.IGNORECASE) for l in lines):
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No visited set found in graph traversal",
                "hint": "Missing a `visited` set will cause infinite loops — track visited nodes.",
            }

    # DP: recursion without memo
    if any(k in prob for k in ["dp", "fibonacci", "knapsack", "coin change", "subsequence"]):
        has_memo = any(re.search(r"memo|dp\[|cache|lru", l, re.IGNORECASE) for l in lines)
        has_rec = any(re.search(r"def\s+\w+", l) for l in lines)
        if has_rec and not has_memo:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "Recursive DP without memoisation",
                "hint": "Add a memo dict to cache subproblem results and avoid recomputation.",
            }

    # ── 12. Output mismatch — numeric off-by-one ─────────────────────────
    diff_result = _output_diff(expected, actual)
    if diff_result:
        diff_desc, diff_val = diff_result
        # Look for +1/-1 boundary errors
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw)
            if re.search(r"[+\-]\s*1\b", line) and re.search(r"\blen\b|\bcount\b|\bsize\b", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": f"Output is {diff_desc} — possible off-by-one near boundary adjustment",
                    "hint": f"Line {i}: output is {diff_desc}; check the ±1 adjustment on the count/length.",
                }
        
        # Check for index-based errors
        if abs(diff_val) == 1:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc} — likely off-by-one error",
                "hint": f"Output is {diff_desc}; check: 1) loop bounds (`<` vs `<=`), 2) index start (0 vs 1), 3) range parameters, 4) ±1 adjustments in calculations.",
            }
        else:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc}",
                "hint": f"Output is {diff_desc}; trace through your algorithm with the failed input to find where the calculation goes wrong.",
            }

    return None


def _analyse_cpp(code: str, problem: str, failed_input: str,
                 expected: str, actual: str) -> Optional[dict]:
    lines = _lines(code)
    prob = problem.lower()

    # ── 0. Output pattern analysis ───────────────────────────────────────
    pattern_issue = _analyze_output_pattern(expected, actual)
    if pattern_issue:
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": pattern_issue["message"],
            "hint": pattern_issue["hint"],
        }

    # ── 1. Integer overflow ───────────────────────────────────────────────
    if any(k in prob for k in ["sum", "product", "large", "10^"]):
        for i, raw in enumerate(lines, 1):
            line = _strip_comments(raw.split("//")[0])
            if re.search(r"\bint\b", line) and re.search(r"\bsum\b|\btotal\b|\bprod\b|\bans\b|\bresult\b", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Possible integer overflow: using `int` for a large sum/product",
                    "hint": f"Line {i}: use `long long` instead of `int` to avoid overflow for large values.",
                }

    # ── 2. Array index out of bounds ─────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        m = re.search(r"for\s*\(.*int\s+(\w+)\s*=\s*0.*\1\s*<=\s*(\w+)", line)
        if m:
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loop uses `<=` with array size — likely off-by-one",
                "hint": f"Line {i}: `i <= n` accesses index n which is out of bounds; use `i < n`.",
            }
        # Check for <= with .size() or .length()
        if re.search(r"<=\s*\w+\.size\(\)|<=\s*\w+\.length\(\)", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loop condition uses `<=` with size() — off-by-one error",
                "hint": f"Line {i}: `i <= arr.size()` goes out of bounds; use `i < arr.size()`.",
            }

    # ── 3. Sorting direction ─────────────────────────────────────────────
    if any(k in prob for k in ["maximum", "largest", "descend", "kth largest"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if re.search(r"\bsort\s*\(", line) and "greater" not in line and "rbegin" not in line:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Sorting ascending when descending is needed",
                    "hint": f"Line {i}: use `sort(v.begin(), v.end(), greater<int>())` for descending order.",
                }
    
    if any(k in prob for k in ["minimum", "smallest", "ascend", "kth smallest"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if "greater" in line or "rbegin" in line:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Sorting descending when ascending is needed",
                    "hint": f"Line {i}: problem asks for minimum/smallest — use normal `sort()` for ascending order.",
                }

    # ── 4. Missing modulo ─────────────────────────────────────────────────
    if any(k in prob for k in ["circular", "rotate", "wrap"]):
        has_mod = any("%" in l for l in lines)
        if not has_mod:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No modulo operator for circular/rotation problem",
                "hint": "Likely missing `% n` for wrap-around index handling.",
            }

    # ── 5. Uninitialized variable ────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        # Check for variable declaration without initialization in accumulator context
        if re.search(r"\bint\s+(sum|total|count|result|ans)\s*;", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Variable declared but not initialized",
                "hint": f"Line {i}: initialize the variable (e.g., `int sum = 0;`) to avoid undefined behavior.",
            }

    # ── 6. Output mismatch ────────────────────────────────────────────────
    diff_result = _output_diff(expected, actual)
    if diff_result:
        diff_desc, diff_val = diff_result
        if abs(diff_val) == 1:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc} — likely off-by-one error",
                "hint": f"Output is {diff_desc}; check loop bounds (`<` vs `<=`), index base, or ±1 adjustments.",
            }
        else:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc}",
                "hint": f"Output is {diff_desc}; check for integer overflow or logic errors in calculations.",
            }

    return None


def _analyse_java(code: str, problem: str, failed_input: str,
                  expected: str, actual: str) -> Optional[dict]:
    lines = _lines(code)
    prob = problem.lower()

    # ── 0. Output pattern analysis ───────────────────────────────────────
    pattern_issue = _analyze_output_pattern(expected, actual)
    if pattern_issue:
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": pattern_issue["message"],
            "hint": pattern_issue["hint"],
        }

    # ── 1. Integer overflow ───────────────────────────────────────────────
    if any(k in prob for k in ["sum", "product", "large"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if re.search(r"\bint\b", line) and re.search(r"\bsum\b|\btotal\b|\bprod\b|\bresult\b", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Possible overflow: `int` used for large accumulator",
                    "hint": f"Line {i}: use `long` instead of `int` to prevent overflow.",
                }

    # ── 2. Off-by-one in loop ─────────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        m = re.search(r"for\s*\(.*int\s+\w+\s*=\s*0.*\w+\s*<=\s*(\w+\.length|\w+\.size\(\)|\w+)\b", line)
        if m:
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loop condition uses `<=` with array length — off-by-one",
                "hint": f"Line {i}: `i <= arr.length` goes out of bounds; use `i < arr.length`.",
            }

    # ── 3. String comparison with == ─────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r'"\w+".*==|==.*"\w+"', line) or re.search(r'\w+\s*==\s*"\w+"', line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "String compared with `==` instead of `.equals()`",
                "hint": f"Line {i}: use `.equals()` to compare String values; `==` checks reference equality.",
            }

    # ── 4. Sorting direction ─────────────────────────────────────────────
    if any(k in prob for k in ["maximum", "largest", "descend", "kth largest"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if re.search(r"Arrays\.sort|Collections\.sort", line) and "reverseOrder" not in line:
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Sorting ascending when descending is needed",
                    "hint": f"Line {i}: use `Collections.reverseOrder()` as comparator for descending sort.",
                }

    # ── 5. Output mismatch ────────────────────────────────────────────────
    diff_result = _output_diff(expected, actual)
    if diff_result:
        diff_desc, diff_val = diff_result
        if abs(diff_val) == 1:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc} — likely off-by-one error",
                "hint": f"Output is {diff_desc}; check loop bounds or index calculations.",
            }
        else:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc}",
                "hint": f"Output is {diff_desc}; check for data type overflow or logic errors.",
            }

    return None


def _analyse_javascript(code: str, problem: str, failed_input: str,
                         expected: str, actual: str) -> Optional[dict]:
    lines = _lines(code)
    prob = problem.lower()

    # ── 0. Output pattern analysis ───────────────────────────────────────
    pattern_issue = _analyze_output_pattern(expected, actual)
    if pattern_issue:
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": pattern_issue["message"],
            "hint": pattern_issue["hint"],
        }

    # ── 1. == vs === ─────────────────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r"[^=!<>]==[^=]", line) and "===" not in line:
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loose equality `==` used instead of strict `===`",
                "hint": f"Line {i}: use `===` for strict comparison to avoid type coercion bugs.",
            }

    # ── 2. parseInt missing radix ─────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r"parseInt\s*\([^,)]+\)", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "parseInt called without radix argument",
                "hint": f"Line {i}: use `parseInt(x, 10)` to ensure base-10 parsing.",
            }

    # ── 3. Sorting direction ─────────────────────────────────────────────
    if any(k in prob for k in ["maximum", "largest", "descend", "kth largest"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if re.search(r"\.sort\s*\(\s*\)", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Sorting without comparator — may not work correctly for numbers",
                    "hint": f"Line {i}: use `.sort((a, b) => b - a)` for descending numeric sort.",
                }
    
    # ── 4. Array length off-by-one ───────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r"<=\s*\w+\.length", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loop condition uses `<=` with array length — off-by-one",
                "hint": f"Line {i}: `i <= arr.length` goes out of bounds; use `i < arr.length`.",
            }

    # ── 5. Output mismatch ────────────────────────────────────────────────
    diff_result = _output_diff(expected, actual)
    if diff_result:
        diff_desc, diff_val = diff_result
        if abs(diff_val) == 1:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc} — likely off-by-one error",
                "hint": f"Output is {diff_desc}; check loop bounds or type coercion issues.",
            }
        else:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc}",
                "hint": f"Output is {diff_desc}; check for type coercion or logic errors.",
            }

    return None


def _analyse_c(code: str, problem: str, failed_input: str,
               expected: str, actual: str) -> Optional[dict]:
    lines = _lines(code)
    prob = problem.lower()

    # ── 0. Output pattern analysis ───────────────────────────────────────
    pattern_issue = _analyze_output_pattern(expected, actual)
    if pattern_issue:
        return {
            "status": "Logic issue detected",
            "line": "",
            "message": pattern_issue["message"],
            "hint": pattern_issue["hint"],
        }

    # ── 1. Integer overflow ───────────────────────────────────────────────
    if any(k in prob for k in ["sum", "product", "large"]):
        for i, raw in enumerate(lines, 1):
            line = raw.split("//")[0]
            if re.search(r"\bint\b", line) and re.search(r"\bsum\b|\btotal\b|\bprod\b|\bresult\b", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Possible overflow: `int` used for large accumulator",
                    "hint": f"Line {i}: use `long long` to prevent integer overflow.",
                }

    # ── 2. Off-by-one ─────────────────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r"for\s*\(.*i\s*=\s*0.*i\s*<=\s*n\b", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Loop uses `i <= n` — likely off-by-one",
                "hint": f"Line {i}: `i <= n` accesses arr[n] which is out of bounds; use `i < n`.",
            }

    # ── 3. Uninitialized variable ────────────────────────────────────────
    for i, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        if re.search(r"\bint\s+(sum|total|count|result|ans)\s*;", line):
            return {
                "status": "Logic issue detected",
                "line": str(i),
                "message": "Variable declared but not initialized",
                "hint": f"Line {i}: initialize the variable (e.g., `int sum = 0;`) to avoid undefined behavior.",
            }

    # ── 4. Output mismatch ────────────────────────────────────────────────
    diff_result = _output_diff(expected, actual)
    if diff_result:
        diff_desc, diff_val = diff_result
        if abs(diff_val) == 1:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc} — likely off-by-one error",
                "hint": f"Output is {diff_desc}; check loop bounds or integer overflow.",
            }
        else:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff_desc}",
                "hint": f"Output is {diff_desc}; check for integer overflow or logic errors.",
            }

    return None


# ---------------------------------------------------------------------------
# Cross-language pattern checks (applied after language-specific)
# ---------------------------------------------------------------------------

def _cross_language_checks(code: str, problem: str, failed_input: str,
                            expected: str, actual: str, language: str) -> Optional[dict]:
    prob = problem.lower()
    lines = _lines(code)

    # ── Greedy: not sorting before greedy selection ───────────────────────
    if any(k in prob for k in ["activity", "interval", "schedule", "greedy"]):
        has_sort = any(re.search(r"sort|sorted", l, re.IGNORECASE) for l in lines)
        if not has_sort:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No sorting found before greedy selection",
                "hint": "Greedy interval/activity problems require sorting by end time first before selecting activities.",
            }

    # ── BFS/DFS: visited set missing ─────────────────────────────────────
    if any(k in prob for k in ["graph", "bfs", "dfs", "path", "connected", "component"]):
        has_visited = any(re.search(r"visited|seen|marked", l, re.IGNORECASE) for l in lines)
        if not has_visited:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "No visited/seen set found in graph traversal",
                "hint": "Missing a `visited` set/array will cause infinite loops or revisiting nodes in BFS/DFS.",
            }

    # ── DP: not using memoisation / table ────────────────────────────────
    if any(k in prob for k in ["dynamic programming", "dp", "fibonacci", "knapsack",
                                "longest common", "coin change", "subsequence"]):
        has_memo = any(re.search(r"memo|dp\[|cache|lru|@cache|@lru_cache", l, re.IGNORECASE) for l in lines)
        has_recursion = any(re.search(r"def\s+\w+.*\(|function\s+\w+|void\s+\w+\s*\(", l) for l in lines)
        if has_recursion and not has_memo:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "Recursive DP without memoisation — likely TLE or wrong answer on overlapping subproblems",
                "hint": "Add a memo/cache dictionary or use @lru_cache decorator to store already-computed subproblem results.",
            }

    # ── Two-sum / pair: wrong index output ───────────────────────────────
    if any(k in prob for k in ["two sum", "pair", "indices"]):
        if expected.strip() and actual.strip():
            exp_parts = expected.strip().split()
            act_parts = actual.strip().split()
            if len(exp_parts) == 2 and len(act_parts) == 2:
                try:
                    exp_0, exp_1 = int(exp_parts[0]), int(exp_parts[1])
                    act_0, act_1 = int(act_parts[0]), int(act_parts[1])
                    if (exp_0 == act_0 + 1 and exp_1 == act_1 + 1) or (exp_0 == act_0 - 1 and exp_1 == act_1 - 1):
                        if exp_0 > act_0:
                            return {
                                "status": "Logic issue detected",
                                "line": "",
                                "message": "Index output off by 1 — likely 0-indexed vs 1-indexed mismatch",
                                "hint": "Problem expects 1-based indices; add 1 to each index before printing/returning.",
                            }
                        else:
                            return {
                                "status": "Logic issue detected",
                                "line": "",
                                "message": "Index output off by 1 — likely 1-indexed vs 0-indexed mismatch",
                                "hint": "Problem expects 0-based indices; subtract 1 from each index or use 0-based indexing.",
                            }
                except ValueError:
                    pass

    # ── Palindrome: not ignoring case/spaces ─────────────────────────────
    if "palindrome" in prob:
        has_lower = any(re.search(r"lower\(\)|toLowerCase\(\)|tolower", l) for l in lines)
        if not has_lower and failed_input and any(c.isupper() for c in failed_input):
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "Palindrome check may not handle mixed case",
                "hint": "Convert the string to lowercase before checking for palindrome.",
            }
        
        # Check for space handling
        has_space_removal = any(re.search(r"replace|strip|filter|isalnum", l, re.IGNORECASE) for l in lines)
        if not has_space_removal and failed_input and " " in failed_input:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "Palindrome check may not handle spaces/punctuation",
                "hint": "Remove spaces and non-alphanumeric characters before checking for palindrome.",
            }

    # ── Binary Search: wrong mid calculation ─────────────────────────────
    if any(k in prob for k in ["binary search", "search", "find"]):
        for i, line in enumerate(lines, 1):
            if re.search(r"mid\s*=\s*\(\s*\w+\s*\+\s*\w+\s*\)\s*/\s*2", line):
                return {
                    "status": "Logic issue detected",
                    "line": str(i),
                    "message": "Binary search mid calculation may overflow",
                    "hint": f"Line {i}: use `mid = left + (right - left) // 2` to avoid integer overflow.",
                }

    # ── Sliding Window: not updating window properly ─────────────────────
    if any(k in prob for k in ["sliding window", "subarray", "substring"]):
        has_window_vars = any(re.search(r"\bleft\b|\bright\b|\bstart\b|\bend\b", l) for l in lines)
        if has_window_vars:
            full = "\n".join(lines)
            moves_left = bool(re.search(r"left\s*\+=|start\s*\+=", full))
            moves_right = bool(re.search(r"right\s*\+=|end\s*\+=", full))
            if moves_right and not moves_left:
                return {
                    "status": "Logic issue detected",
                    "line": "",
                    "message": "Sliding window: right pointer moves but left pointer never moves",
                    "hint": "In sliding window problems, both pointers must move. Update the left pointer when the window becomes invalid.",
                }

    # ── Stack/Queue: using wrong data structure ──────────────────────────
    if "queue" in prob or "bfs" in prob:
        has_queue = any(re.search(r"queue|deque|Queue", l) for l in lines)
        has_stack = any(re.search(r"stack|append.*pop\(\)", l) for l in lines)
        if has_stack and not has_queue:
            return {
                "status": "Logic issue detected",
                "line": "",
                "message": "Using stack (LIFO) for a queue/BFS problem",
                "hint": "BFS requires a queue (FIFO). Use `collections.deque` with `append()` and `popleft()` in Python.",
            }

    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def smart_debug_hint(problem_statement: str, user_code: str, language: str,
                     failed_test_input: str, expected_output: str,
                     actual_output: str) -> dict:
    """
    Analyse a failed submission and return a structured hint dict.
    Returns: { status, line, message, hint }
    """
    lang = language.lower().strip()
    prob = problem_statement

    # Language-specific analysis
    result = None
    if lang == "python":
        result = _analyse_python(user_code, prob, failed_test_input, expected_output, actual_output)
    elif lang in ("cpp", "c++"):
        result = _analyse_cpp(user_code, prob, failed_test_input, expected_output, actual_output)
    elif lang == "java":
        result = _analyse_java(user_code, prob, failed_test_input, expected_output, actual_output)
    elif lang in ("javascript", "js"):
        result = _analyse_javascript(user_code, prob, failed_test_input, expected_output, actual_output)
    elif lang == "c":
        result = _analyse_c(user_code, prob, failed_test_input, expected_output, actual_output)

    # Cross-language checks if no result yet
    if result is None:
        result = _cross_language_checks(user_code, prob, failed_test_input,
                                        expected_output, actual_output, lang)

    # Final fallback: output mismatch
    if result is None:
        diff = _output_diff(expected_output, actual_output)
        if diff:
            result = {
                "status": "Logic issue detected",
                "line": "",
                "message": f"Output is {diff}",
                "hint": f"Output is {diff}; trace through the algorithm with the failed input to find the boundary error.",
            }

    if result is None:
        result = {
            "status": "No clear logic issue detected",
            "line": "",
            "message": "Could not identify a specific logic error automatically",
            "hint": "Trace through your code manually with the failed test input step by step.",
        }

    return result
