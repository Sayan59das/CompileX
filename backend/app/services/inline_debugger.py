"""
Inline Debugger — Output-first, code-second hint engine.

Strategy:
  The ONLY reliable signal we have is:
    - the exact input that failed
    - the expected output
    - the actual output (or error message)
    - the user's code text

  We derive hints in this priority order:
    1. Syntax error          — AST parse failure (Python) or obvious brace mismatch
    2. Runtime crash         — error keywords in actual_output
    3. No output             — empty actual_output
    4. Output comparison     — diff the actual vs expected to find the exact discrepancy
    5. Code pattern scan     — look for the specific bug in the code that explains the diff
    6. Fallback              — show the exact mismatch with a trace suggestion

  Key principle: NEVER fire a hint unless the evidence actually supports it.
  A hint that says "add visited set" when the bug is an off-by-one is worse than no hint.
"""
import re
import ast
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Result builders
# ─────────────────────────────────────────────────────────────────────────────

def _hint(status: str, line: str, message: str, hint: str) -> dict:
    return {"status": status, "line": line, "message": message, "hint": hint}

def _logic(line: str, message: str, hint: str) -> dict:
    return _hint("Logic issue detected", line, message, hint)

def _runtime(line: str, message: str, hint: str) -> dict:
    return _hint("Runtime error detected", line, message, hint)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _lines(code: str) -> list:
    return code.split("\n")

def _strip_comment(line: str, lang: str) -> str:
    if lang == "python":
        return re.sub(r"#.*$", "", line).strip()
    return re.sub(r"//.*$", "", line).strip()

def _parse_nums(s: str) -> Optional[list]:
    """Parse whitespace-separated numbers. Returns None if any token is non-numeric."""
    if not s or not s.strip():
        return None
    try:
        return [float(x) for x in s.split()]
    except (ValueError, AttributeError):
        return None

def _normalize_lines(text: str) -> list:
    """Split into non-empty lines, each with collapsed whitespace."""
    result = []
    for line in text.strip().split("\n"):
        norm = " ".join(line.split())
        if norm:
            result.append(norm)
    return result

def _find_func_def_line(lines: list, lang: str) -> Optional[int]:
    """Return 1-based line number of the first function definition."""
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if lang == "python" and re.match(r"def\s+\w+", s):
            return i
        if lang in ("cpp", "c++", "c", "java", "javascript", "js"):
            if re.search(r"\b\w+\s+\w+\s*\([^)]*\)\s*\{?", s) and not s.startswith("//"):
                return i
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Syntax / compilation errors
# ─────────────────────────────────────────────────────────────────────────────

def _check_syntax(code: str, lang: str) -> Optional[dict]:
    if lang == "python":
        try:
            ast.parse(code)
        except SyntaxError as e:
            line = str(e.lineno) if e.lineno else ""
            text = e.msg or "Syntax error"
            return _hint(
                "Syntax error", line,
                f"Syntax error on line {line}: {text}",
                f"Fix the syntax on line {line}: {text}. "
                "Common causes: missing colon after `if`/`for`/`def`, "
                "unmatched brackets, or wrong indentation.",
            )
        return None

    # C / C++ / Java / JS: check for unbalanced braces
    if lang in ("cpp", "c++", "c", "java", "javascript", "js"):
        opens = code.count("{")
        closes = code.count("}")
        if opens != closes:
            diff = opens - closes
            return _hint(
                "Syntax error", "",
                f"Unbalanced braces: {opens} '{{' vs {closes} '}}'",
                f"You have {abs(diff)} {'missing' if diff > 0 else 'extra'} "
                f"closing brace(s). Check every `if`, `for`, `while`, and function body.",
            )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Runtime crash in actual output
# ─────────────────────────────────────────────────────────────────────────────

def _check_runtime_error(actual: str, lines: list, lang: str) -> Optional[dict]:
    a = actual.lower()
    crash_keywords = [
        "error", "exception", "traceback", "segfault", "segmentation fault",
        "killed", "timeout", "time limit", "tle", "mle", "runtime error",
        "compilation failed", "compile error",
    ]
    if not any(kw in a for kw in crash_keywords):
        return None

    if "time limit" in a or "tle" in a:
        return _runtime("", "Time Limit Exceeded",
            "Your solution is too slow for large inputs. "
            "Look for nested loops O(n²) that can be replaced with a hash map O(n), "
            "or a prefix sum / sliding window approach.")

    if "memory" in a or "mle" in a:
        return _runtime("", "Memory Limit Exceeded",
            "Your solution uses too much memory. "
            "Avoid storing the entire input in extra arrays when you can process it in-place.")

    if "zerodivision" in a or "division by zero" in a:
        for i, l in enumerate(lines, 1):
            if re.search(r"[/%]\s*\w+", _strip_comment(l, lang)):
                return _runtime(str(i), "Division by zero",
                    f"Line {i}: guard the division — `if denominator != 0:` before dividing.")
        return _runtime("", "Division by zero",
            "Add a guard before every division or modulo to avoid ZeroDivisionError.")

    if "index" in a and ("out of range" in a or "out of bounds" in a):
        # Find the first array access line
        for i, l in enumerate(lines, 1):
            if re.search(r"\w+\s*\[", _strip_comment(l, lang)):
                return _runtime(str(i), "Index out of bounds",
                    f"Line {i}: you're accessing an index that doesn't exist. "
                    "Check your loop bounds — use `range(len(arr))` and verify `i < len(arr)`.")
        return _runtime("", "Index out of bounds",
            "An array index exceeds the array size. Check all loop bounds.")

    if "nonetype" in a or "null pointer" in a or "attributeerror" in a or "nullpointer" in a:
        return _runtime("", "Null / None reference",
            "A variable is None/null when you try to use it. "
            "Make sure you initialize all variables before using them.")

    if "recursion" in a or "maximum recursion" in a or "stackoverflow" in a or "stack overflow" in a:
        return _runtime("", "Stack overflow / infinite recursion",
            "Your recursion never reaches its base case. "
            "Add a proper base case and make sure each recursive call moves toward it.")

    if "typeerror" in a:
        return _runtime("", "Type error",
            "You're mixing incompatible types (e.g. adding a string to an int). "
            "Convert inputs with `int()`, `float()`, or `str()` as needed.")

    if "valueerror" in a:
        return _runtime("", "Value error",
            "An invalid value was passed to a function (e.g. `int('abc')`). "
            "Validate your input before converting it.")

    if "keyerror" in a:
        return _runtime("", "Key error",
            "You're accessing a dictionary key that doesn't exist. "
            "Use `.get(key, default)` or check `if key in d` first.")

    if "compilation failed" in a or "compile error" in a:
        # Try to extract the first error line from the message
        m = re.search(r"line\s+(\d+)", actual, re.IGNORECASE)
        line = m.group(1) if m else ""
        return _hint("Compilation error", line,
            "Your code failed to compile",
            "Fix the compilation error shown above. "
            "Common causes: missing semicolons, undeclared variables, or type mismatches.")

    # Generic crash
    snippet = actual[:120].replace("\n", " ")
    return _runtime("", f"Runtime error: {snippet}",
        "Your code crashes on this input. "
        "Check for: index out of bounds, division by zero, None/null access, or type mismatches.")


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — No output produced
# ─────────────────────────────────────────────────────────────────────────────

def _check_no_output(actual: str, lines: list, lang: str) -> Optional[dict]:
    if actual.strip():
        return None

    output_kw = {
        "python": "print",
        "javascript": "console.log", "js": "console.log",
        "cpp": "cout", "c++": "cout",
        "java": "System.out",
        "c": "printf",
    }.get(lang, "print")

    has_output = any(output_kw in l for l in lines)
    if not has_output:
        return _logic("", "No output statement found",
            f"Your code never prints the result. "
            f"Add `{output_kw}(result)` at the end of your solution.")

    # Has output statement but nothing printed — likely unreachable
    for i, l in enumerate(lines, 1):
        if output_kw in l:
            return _logic(str(i), "Output statement may be unreachable",
                f"Line {i}: the `{output_kw}` exists but the code path may never reach it. "
                "Check your conditions — make sure every branch eventually prints the result.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Output comparison (the most important layer)
# Derives the hint directly from what's wrong with the output.
# ─────────────────────────────────────────────────────────────────────────────

def _check_output_diff(expected: str, actual: str) -> Optional[dict]:
    """
    Compare expected vs actual output and return a precise, factual hint.
    This fires for EVERY wrong answer — no keyword matching needed.
    """
    if not expected or not actual:
        return None
    if expected.strip() == actual.strip():
        return None  # correct — shouldn't be called, but guard anyway

    exp_norm = _normalize_lines(expected)
    act_norm = _normalize_lines(actual)

    # ── Exact match after stripping whitespace/brackets ──────────────────
    # Normalize: remove brackets/commas, collapse whitespace, then compare
    def _norm_flat(s: str) -> str:
        return re.sub(r'\s+', ' ', s.replace('[','').replace(']','').replace('(','').replace(')','').replace(',', ' ')).strip()

    exp_flat = _norm_flat(expected)
    act_flat = _norm_flat(actual)
    if exp_flat == act_flat and expected.strip() != actual.strip():
        return _logic("", "Values correct but output format wrong",
            "Your output format is wrong — the values are right but the presentation differs. "
            "Don't print lists with brackets — use `print(' '.join(map(str, result)))` "
            "instead of `print(result)`. Remove trailing spaces and extra newlines.")

    # ── Line count mismatch ───────────────────────────────────────────────
    if len(exp_norm) != len(act_norm):
        diff = len(act_norm) - len(exp_norm)
        if diff > 0:
            return _logic("", f"Too many output lines: got {len(act_norm)}, expected {len(exp_norm)}",
                f"Your code prints {diff} extra line(s). "
                "Check for duplicate print statements, an extra loop iteration, "
                "or printing inside the loop when you should print after it.")
        else:
            return _logic("", f"Too few output lines: got {len(act_norm)}, expected {len(exp_norm)}",
                f"Your code prints {abs(diff)} fewer line(s) than expected. "
                "Check for early `break`/`return` inside your loop, "
                "or a loop that doesn't iterate enough times.")

    # ── Single-value comparison ───────────────────────────────────────────
    exp_nums = _parse_nums(expected.strip())
    act_nums = _parse_nums(actual.strip())

    if exp_nums is not None and act_nums is not None and len(exp_nums) == len(act_nums) == 1:
        e, a = exp_nums[0], act_nums[0]
        diff = a - e
        if diff == 1:
            return _logic("", f"Answer is 1 too high (got {_fmt(a)}, expected {_fmt(e)})",
                "Your answer is 1 more than expected — classic off-by-one. "
                "Check: loop uses `<=` instead of `<`, or an extra `+1` in your formula.")
        if diff == -1:
            return _logic("", f"Answer is 1 too low (got {_fmt(a)}, expected {_fmt(e)})",
                "Your answer is 1 less than expected — classic off-by-one. "
                "Check: loop uses `<` instead of `<=`, or a missing `+1` in your formula.")
        if diff != 0:
            ratio = a / e if e != 0 else None
            if ratio is not None and abs(ratio - 2) < 0.001:
                return _logic("", f"Answer is exactly double (got {_fmt(a)}, expected {_fmt(e)})",
                    "Your result is 2× the expected value. "
                    "You may be counting each element twice, or forgot to divide by 2.")
            if ratio is not None and abs(ratio - 0.5) < 0.001:
                return _logic("", f"Answer is exactly half (got {_fmt(a)}, expected {_fmt(e)})",
                    "Your result is half the expected value. "
                    "Check if you're dividing when you shouldn't be, or missing a factor of 2.")
            if e != 0 and a == -e:
                return _logic("", f"Answer has wrong sign (got {_fmt(a)}, expected {_fmt(e)})",
                    "Your answer has the wrong sign — it's the negative of the expected value. "
                    "Check your subtraction order — you may have `b - a` where you need `a - b`.")
            sign = "+" if diff > 0 else ""
            return _logic("", f"Wrong answer: got {_fmt(a)}, expected {_fmt(e)}",
                f"Your answer is off by {sign}{_fmt(diff)}. "
                "Trace through your algorithm with this specific input step by step "
                "and check where the value diverges from what you expect.")

    # ── Multi-value comparison ────────────────────────────────────────────
    if exp_nums is not None and act_nums is not None and len(exp_nums) == len(act_nums) and len(exp_nums) > 1:
        n = len(exp_nums)

        # Reversed
        if act_nums == list(reversed(exp_nums)):
            return _logic("", "Output is in reverse order",
                "Your output is the exact reverse of the expected output. "
                "Check your traversal direction, or add `.reverse()` / `[::-1]` before printing.")

        # Right values, wrong order
        if sorted(act_nums) == sorted(exp_nums) and act_nums != exp_nums:
            return _logic("", "Correct values but wrong order",
                "You have all the right values but in the wrong order. "
                "Check whether you're sorting when you shouldn't be, "
                "or not preserving the original order.")

        # All off by same constant
        diffs = [a - e for a, e in zip(act_nums, exp_nums)]
        if len(set(round(d, 9) for d in diffs)) == 1 and diffs[0] != 0:
            d = diffs[0]
            if d == 1:
                return _logic("", "All values are 1 too high",
                    "Every output value is 1 more than expected. "
                    "Check: 1-based indexing where 0-based is needed, or an extra `+1`.")
            if d == -1:
                return _logic("", "All values are 1 too low",
                    "Every output value is 1 less than expected. "
                    "Check: 0-based indexing where 1-based is needed, or a missing `+1`.")
            return _logic("", f"All values are off by {d:+g}",
                f"Every output value differs from expected by {d:+g}. "
                "There's a systematic error — check your formula or initial accumulator value.")

        # All wrong sign
        if all(round(a + e, 9) == 0 for a, e in zip(act_nums, exp_nums)):
            return _logic("", "All values have the wrong sign",
                "Your values are negated. "
                "Check your subtraction order — you may have `b - a` where you need `a - b`.")

        # Find first mismatch
        for idx, (a, e) in enumerate(zip(act_nums, exp_nums)):
            if round(a - e, 9) != 0:
                return _logic("", f"First wrong value at position {idx}: got {_fmt(a)}, expected {_fmt(e)}",
                    f"Position {idx} is wrong (got {_fmt(a)}, expected {_fmt(e)}). "
                    f"Trace your algorithm at index {idx} to find where the logic diverges.")

    # ── Multi-line, non-numeric: find first differing line ────────────────
    if exp_norm and act_norm:
        for idx, (e_line, a_line) in enumerate(zip(exp_norm, act_norm)):
            if e_line != a_line:
                return _logic("", f"Line {idx + 1} of output is wrong",
                    f"Expected: `{e_line[:80]}`\n"
                    f"Got:      `{a_line[:80]}`\n"
                    "Trace your algorithm for this specific input to find where the output diverges.")

    # ── Generic mismatch ──────────────────────────────────────────────────
    e_short = expected.strip()[:60]
    a_short = actual.strip()[:60]
    return _logic("", f"Wrong output",
        f"Expected `{e_short}` but got `{a_short}`. "
        "Trace through your code with this input step by step.")


def _fmt(n: float) -> str:
    """Format a number: show as int if it's a whole number."""
    return str(int(n)) if n == int(n) else str(n)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — Code pattern scan
# Only fires when we can find a specific bug in the code that EXPLAINS the diff.
# Every check here requires evidence from both the output diff AND the code.
# ─────────────────────────────────────────────────────────────────────────────

def _check_code_patterns(code: str, lines: list, lang: str, prob: str,
                         expected: str, actual: str, inp: str) -> Optional[dict]:
    """
    Scan the code for patterns that explain the observed output difference.
    Only returns a hint when the evidence is strong.
    """
    exp_nums = _parse_nums(expected)
    act_nums = _parse_nums(actual)
    single_val_wrong = (
        exp_nums and act_nums and
        len(exp_nums) == len(act_nums) == 1 and
        exp_nums[0] != act_nums[0]
    )
    multi_val_wrong = (
        exp_nums and act_nums and
        len(exp_nums) == len(act_nums) > 1 and
        exp_nums != act_nums
    )
    off_by_one = single_val_wrong and abs(act_nums[0] - exp_nums[0]) == 1

    # ── Wrong accumulator init for product/factorial ──────────────────────
    # Evidence: expected > 0, actual == 0, code has *= or product pattern
    if act_nums and act_nums[0] == 0 and exp_nums and exp_nums[0] != 0:
        for i, raw in enumerate(lines, 1):
            l = _strip_comment(raw, lang)
            if re.search(r"\bresult\s*=\s*0\b|\bprod\s*=\s*0\b|\bans\s*=\s*0\b|\bproduct\s*=\s*0\b", l):
                return _logic(str(i), f"Accumulator initialized to 0 — multiplying by 0 gives 0",
                    f"Line {i}: change the initial value from `0` to `1`. "
                    "Multiplying by 0 always gives 0 — use 1 as the identity for multiplication.")

    # ── Off-by-one: loop boundary ─────────────────────────────────────────
    if off_by_one:
        for i, raw in enumerate(lines, 1):
            l = _strip_comment(raw, lang)
            # Python: range(1, n) skipping index 0
            if lang == "python" and re.search(r"range\s*\(\s*1\s*,", l):
                return _logic(str(i), "Loop starts at 1 — index 0 is skipped",
                    f"Line {i}: `range(1, n)` skips the first element. "
                    "Use `range(n)` to start from index 0.")
            # C-family: i <= n (should be i < n)
            if lang in ("cpp", "c++", "c", "java") and re.search(r"\bi\s*<=\s*n\b|\bi\s*<=\s*\w+\.(?:size|length)\b", l):
                return _logic(str(i), "Loop condition `<=` causes off-by-one",
                    f"Line {i}: `i <= n` accesses one element past the end. "
                    "Change to `i < n`.")

    # ── Return inside loop (exits after first iteration) ─────────────────
    # Evidence: single value wrong, code has return inside a for/while
    if single_val_wrong and lang == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and child is not node:
                            return _logic(str(child.lineno),
                                "return inside loop — exits after first iteration",
                                f"Line {child.lineno}: `return` inside the loop stops after the "
                                "first element. Move `return result` outside the loop.")
        except SyntaxError:
            pass

    # ── Wrong sort direction ──────────────────────────────────────────────
    # Evidence: multi-value output is the reverse of expected
    if multi_val_wrong and act_nums == list(reversed(exp_nums)):
        for i, raw in enumerate(lines, 1):
            l = _strip_comment(raw, lang)
            if lang == "python":
                if re.search(r"\.sort\s*\(\s*\)|sorted\s*\(", l) and "reverse" not in l:
                    return _logic(str(i), "Sorted ascending but descending is needed",
                        f"Line {i}: add `reverse=True` — use `.sort(reverse=True)` "
                        "or `sorted(..., reverse=True)`.")
                if re.search(r"reverse\s*=\s*True", l):
                    return _logic(str(i), "Sorted descending but ascending is needed",
                        f"Line {i}: remove `reverse=True` to sort in ascending order.")

    # ── Missing modulo for circular/wrap-around ───────────────────────────
    # Evidence: actual value > expected, no % in code, problem mentions rotate/circular
    if single_val_wrong and not any("%" in l for l in lines):
        if any(k in prob for k in ["circular", "rotate", "wrap", "cyclic", "ring"]):
            return _logic("", "Missing modulo for wrap-around",
                "Use `% n` to handle wrap-around indices in circular/rotation problems.")

    # ── Integer division truncating result ────────────────────────────────
    # Evidence: actual is floor of expected, code uses //
    if single_val_wrong and lang == "python":
        e, a = exp_nums[0], act_nums[0]
        if a == int(e) and e != int(e):  # expected is float, got truncated int
            for i, raw in enumerate(lines, 1):
                l = _strip_comment(raw, lang)
                if re.search(r"//", l):
                    return _logic(str(i), "Integer division `//` truncates decimal result",
                        f"Line {i}: use `/` instead of `//` to keep the decimal part.")

    # ── Missing visited set in graph traversal ────────────────────────────
    # Evidence: actual output is empty or TLE, code has graph/adj but no visited
    if any(k in prob for k in ["graph", "bfs", "dfs", "path", "connected", "component", "cycle"]):
        has_visited = any(re.search(r"\bvisited\b|\bseen\b|\bmarked\b", l, re.IGNORECASE) for l in lines)
        has_graph_code = any(re.search(r"\badj\b|\bgraph\b|\bneighbor", l, re.IGNORECASE) for l in lines)
        if has_graph_code and not has_visited:
            return _logic("", "No visited set — graph traversal will loop infinitely",
                "Add `visited = set()` and mark each node when you visit it. "
                "Without this, you'll revisit nodes and loop forever.")

    # ── BFS using stack instead of queue ─────────────────────────────────
    # Evidence: wrong output for BFS/level-order, code uses .pop() not .popleft()
    if any(k in prob for k in ["bfs", "level order", "shortest path", "level-order"]):
        has_popleft = any("popleft" in l for l in lines)
        has_pop = any(re.search(r"\.pop\(\)", l) for l in lines)
        if has_pop and not has_popleft:
            return _logic("", "Using stack (LIFO) for BFS — need a queue (FIFO)",
                "BFS requires a queue. Use `from collections import deque` "
                "and replace `.pop()` with `.popleft()`.")

    # ── Recursive DP without memoization ─────────────────────────────────
    # Evidence: TLE or wrong answer, code has recursion but no memo/cache
    if any(k in prob for k in ["fibonacci", "knapsack", "coin change", "subsequence",
                                "longest common", "edit distance", "climbing stairs"]):
        has_memo = any(re.search(r"\bmemo\b|\bdp\[|\bcache\b|@lru_cache|@cache", l, re.IGNORECASE) for l in lines)
        has_recursion = any(re.search(r"\bdef\s+\w+", l) for l in lines)
        if has_recursion and not has_memo:
            return _logic("", "Recursive solution without memoization — exponential time",
                "Add memoization to avoid recomputing subproblems. "
                "Use `@lru_cache(maxsize=None)` above your function, "
                "or a `memo = {}` dictionary.")

    # ── Wrong max/min initialization ──────────────────────────────────────
    # Evidence: actual is 0 but expected is negative (max init to 0 fails for negatives)
    if single_val_wrong:
        e, a = exp_nums[0], act_nums[0]
        if a == 0 and e < 0:
            for i, raw in enumerate(lines, 1):
                l = _strip_comment(raw, lang)
                if re.search(r"\bmax\w*\s*=\s*0\b|\blargest\s*=\s*0\b|\bbest\s*=\s*0\b", l):
                    return _logic(str(i), "Max variable initialized to 0 — fails for all-negative inputs",
                        f"Line {i}: initialize to `float('-inf')` or `arr[0]` "
                        "so it works when all values are negative.")
        if a == 0 and e > 0:
            for i, raw in enumerate(lines, 1):
                l = _strip_comment(raw, lang)
                if re.search(r"\bmin\w*\s*=\s*0\b|\bsmallest\s*=\s*0\b", l):
                    return _logic(str(i), "Min variable initialized to 0 — fails for all-positive inputs",
                        f"Line {i}: initialize to `float('inf')` or `arr[0]` "
                        "so it works when all values are positive.")

    # ── C/C++/Java integer overflow ───────────────────────────────────────
    if lang in ("cpp", "c++", "c", "java") and single_val_wrong:
        e, a = exp_nums[0], act_nums[0]
        # Overflow typically wraps to a large negative or small positive
        if abs(a) > 2**30 or (e > 0 and a < 0):
            for i, raw in enumerate(lines, 1):
                l = _strip_comment(raw, lang)
                if re.search(r"\bint\b", l) and re.search(r"\bsum\b|\btotal\b|\bprod\b|\bans\b|\bresult\b", l):
                    long_type = "long long" if lang in ("cpp", "c++", "c") else "long"
                    return _logic(str(i), "Integer overflow — `int` too small for this value",
                        f"Line {i}: use `{long_type}` instead of `int` to hold large values.")

    # ── Java String == instead of .equals() ──────────────────────────────
    if lang == "java":
        for i, raw in enumerate(lines, 1):
            l = _strip_comment(raw, lang)
            if re.search(r'[a-zA-Z_]\w*\s*==\s*"[^"]*"', l):
                return _logic(str(i), "String compared with `==` instead of `.equals()`",
                    f"Line {i}: `==` checks reference equality for Strings in Java. "
                    "Use `.equals()` for value comparison.")

    # ── Missing return / function returns None ────────────────────────────
    if lang == "python" and not actual.strip():
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    has_return = any(
                        isinstance(n, ast.Return) and n.value is not None
                        for n in ast.walk(node)
                    )
                    has_print = any("print" in l for l in lines)
                    if not has_return and not has_print:
                        return _logic(str(node.lineno),
                            f"Function `{node.name}` has no return statement",
                            f"Line {node.lineno}: add `return result` at the end of `{node.name}`. "
                            "Without a return, the function returns None and prints nothing.")
        except SyntaxError:
            pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def inline_debug_hint(
    problem_statement: str,
    user_code: str,
    language: str,
    failed_test_input: str = "",
    expected_output: str = "",
    actual_output: str = "",
) -> dict:
    """
    Analyse a failed test case and return a structured hint.
    Returns: { status, line, message, hint }
    """
    lang = language.lower().strip()
    prob = problem_statement.lower()
    lines = _lines(user_code)
    actual = (actual_output or "").strip()
    expected = (expected_output or "").strip()
    inp = (failed_test_input or "").strip()

    # Layer 1: Syntax / compilation errors
    r = _check_syntax(user_code, lang)
    if r:
        return r

    # Layer 2: Runtime crash in output
    r = _check_runtime_error(actual, lines, lang)
    if r:
        return r

    # Layer 3: No output at all
    r = _check_no_output(actual, lines, lang)
    if r:
        return r

    # Layer 4: Output comparison — derives hint from the actual diff
    r = _check_output_diff(expected, actual)
    if r:
        # Layer 5: Try to find the specific code bug that explains this diff
        code_hint = _check_code_patterns(user_code, lines, lang, prob, expected, actual, inp)
        if code_hint:
            return code_hint
        # Return the output-diff hint (always accurate, even without code evidence)
        return r

    # Fallback — outputs match (shouldn't reach here) or both empty
    return _hint(
        "No clear issue detected", "",
        "Could not identify a specific error automatically",
        "Add print statements to inspect intermediate values and find where "
        "your output diverges from the expected result.",
    )
