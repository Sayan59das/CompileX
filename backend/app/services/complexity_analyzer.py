"""
Complexity Analyzer — AST-based accurate time & space complexity analysis.

Supports Python (via AST), C++, Java, JavaScript (via structural analysis).

Analysis strategy:
  1. Parse Python code with ast module for precise structural understanding
  2. For other languages, use regex-based structural analysis
  3. Detect: nested loops, recursion type, sorting, binary search,
     hash maps, DP tables, divide-and-conquer, sliding window, two-pointer
  4. Derive best/average/worst case from the detected pattern
  5. Generate a human-readable explanation with the reasoning
"""

import re
import ast
from typing import Dict, List, Optional, Tuple

from app.services.starter_lock import MARKER as _LOCKED_MARKER   # the line the locked harness starts at


# ─────────────────────────────────────────────────────────────────────────────
# Data classes / helpers
# ─────────────────────────────────────────────────────────────────────────────

class _Complexity:
    """Represents a detected complexity with its source explanation."""
    def __init__(self, notation: str, reason: str):
        self.notation = notation
        self.reason   = reason

    def __repr__(self):
        return f"{self.notation} ({self.reason})"


_ORDER = ["O(1)", "O(log n)", "O(sqrt n)", "O(n)", "O(n log n)",
          "O(n log² n)", "O(n sqrt n)", "O(n²)", "O(n² log n)",
          "O(n³)", "O(2^n)", "O(n!)"]

def _max_complexity(a: str, b: str) -> str:
    """Return the higher of two complexity strings."""
    ia = _ORDER.index(a) if a in _ORDER else 3   # default O(n)
    ib = _ORDER.index(b) if b in _ORDER else 3
    return _ORDER[max(ia, ib)]


def _all_recursive_calls_in_exclusive_branches(func_node: ast.AST, fname: str) -> bool:
    """
    Return True if at most ONE recursive call to `fname` can execute per
    invocation (recursive binary search pattern → O(log n)).

    Strategy: compute the max recursive calls along any single execution path.
    - Sequential statements accumulate.
    - If/elif/else: only one branch executes → take the max.
    - If an `if` body always returns (early exit), the statements that follow
      are the implicit `else` — they're mutually exclusive with the `if` body.
      So we treat them as: max(if_body_calls, remaining_calls) rather than
      if_body_calls + remaining_calls.
    """
    def _calls_in_node(node) -> int:
        return sum(
            1 for n in ast.walk(node)
            if isinstance(n, ast.Call)
            and (
                (isinstance(n.func, ast.Name) and n.func.id == fname)
                or (isinstance(n.func, ast.Attribute) and n.func.attr == fname)
            )
        )

    def _body_always_exits(stmts) -> bool:
        """Return True if every execution path through stmts ends with return/raise."""
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, (ast.Return, ast.Raise)):
            return True
        if isinstance(last, ast.If):
            # Both branches must exit
            return (
                _body_always_exits(last.body)
                and bool(last.orelse)
                and _body_always_exits(last.orelse)
            )
        return False

    def _max_calls_on_any_path(stmts) -> int:
        """
        Return the maximum number of recursive calls that can execute along
        any single execution path through `stmts`.
        """
        if not stmts:
            return 0

        stmt = stmts[0]
        rest = stmts[1:]

        if isinstance(stmt, ast.If):
            body_calls   = _max_calls_on_any_path(stmt.body)
            orelse_calls = _max_calls_on_any_path(stmt.orelse) if stmt.orelse else 0

            if _body_always_exits(stmt.body):
                # The if-body exits unconditionally (return/raise).
                # The rest of the statements only run when the condition is False.
                # So: either (if-body path) or (rest path) — take the max.
                rest_calls = _max_calls_on_any_path(rest)
                return max(body_calls, orelse_calls + rest_calls)
            else:
                # Normal if: after the if block, execution continues into rest
                branch_max = max(body_calls, orelse_calls)
                return branch_max + _max_calls_on_any_path(rest)
        else:
            # Non-if statement: calls here always execute, then continue to rest
            return _calls_in_node(stmt) + _max_calls_on_any_path(rest)

    if isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _max_calls_on_any_path(func_node.body) <= 1
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Python AST analyser
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Logarithmic loops
#
# A loop whose counter is halved, divided by a constant or doubled on every pass runs O(log n) times, not O(n):
#     while n > 0: n //= 10        for (i = 1; i < n; i *= 2)        while (e) { ...; e >>= 1; }
# They are told apart from linear loops along the nesting path, so a log loop inside a scan is O(n log n) and a lone one
# is O(log n).
# ─────────────────────────────────────────────────────────────────────────────

def _const_int(node) -> Optional[int]:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _scaled_name(value, name: str) -> Optional[str]:
    """'shrink' or 'grow' when `value` is `name <op> constant` (also inside int()/floor()/trunc()), else None."""
    while isinstance(value, ast.Call) and len(value.args) == 1 and (
        (isinstance(value.func, ast.Name) and value.func.id in ("int", "floor", "round"))
        or (isinstance(value.func, ast.Attribute) and value.func.attr in ("floor", "trunc"))
    ):
        value = value.args[0]
    if isinstance(value, ast.BinOp) and isinstance(value.left, ast.Name) and value.left.id == name:
        k = _const_int(value.right)
        if k is None:
            return None
        if isinstance(value.op, (ast.FloorDiv, ast.Div)) and k >= 2:
            return "shrink"
        if isinstance(value.op, ast.RShift) and k >= 1:
            return "shrink"
        if isinstance(value.op, ast.Mult) and k >= 2:
            return "grow"
        if isinstance(value.op, ast.LShift) and k >= 1:
            return "grow"
    return None


def _scaling_update(node) -> Optional[Tuple[str, str]]:
    """(variable, 'shrink' | 'grow') when the statement divides/shifts or multiplies a variable by a constant."""
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
        k = _const_int(node.value)
        if k is None:
            return None
        if isinstance(node.op, (ast.FloorDiv, ast.Div)) and k >= 2:
            return node.target.id, "shrink"
        if isinstance(node.op, ast.RShift) and k >= 1:
            return node.target.id, "shrink"
        if isinstance(node.op, ast.Mult) and k >= 2:
            return node.target.id, "grow"
        if isinstance(node.op, ast.LShift) and k >= 1:
            return node.target.id, "grow"
    elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        kind = _scaled_name(node.value, name) or ("shrink" if _is_remainder_by(node.value, name) else None)
        if kind:
            return name, kind
    elif (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple)
          and isinstance(node.value, ast.Tuple) and len(node.targets[0].elts) == len(node.value.elts)):
        # a, b = b, a % b  (Euclid): the variable is replaced by a remainder modulo itself, which at least halves every 2 steps
        for target, value in zip(node.targets[0].elts, node.value.elts):
            if isinstance(target, ast.Name) and _is_remainder_by(value, target.id):
                return target.id, "shrink"
    return None


def _is_remainder_by(value, name: str) -> bool:
    """`<something> % name`: the remainder modulo the very variable being assigned."""
    return (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mod)
            and isinstance(value.right, ast.Name) and value.right.id == name)


def _is_log_loop_py(node: ast.While) -> bool:
    """A while loop whose condition variable is halved (or doubled while bounded above) on every pass."""
    cond = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
    if not cond:
        return False
    bounded = set()   # names the condition keeps below a limit (i < n, i <= n, n > i): they may grow geometrically
    for cmp_ in (n for n in ast.walk(node.test) if isinstance(n, ast.Compare)):
        left = cmp_.left
        for op, right in zip(cmp_.ops, cmp_.comparators):
            if isinstance(op, (ast.Lt, ast.LtE)) and isinstance(left, ast.Name):
                bounded.add(left.id)
            if isinstance(op, (ast.Gt, ast.GtE)) and isinstance(right, ast.Name):
                bounded.add(right.id)
            left = right
    for stmt in node.body:
        for n in ast.walk(stmt):
            upd = _scaling_update(n)
            if upd and upd[0] in cond and (upd[1] == "shrink" or upd[0] in bounded):
                return True
    return False


_LOOP_HEAD = re.compile(r"\b(for|while)\s*\(")
_IF_HEAD = re.compile(r"\bif\s*\(")
_DO_BLOCK = re.compile(r"\bdo\s*\{")
_IDENT = re.compile(r"[A-Za-z_]\w*")


def _blank_comments_and_strings(code: str) -> str:
    """The code with comments and string/char literals blanked out (same length, newlines kept), so that keywords and
    brackets inside them are not mistaken for code."""
    out = list(code)
    n = len(code)
    i = 0
    while i < n:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and code[i] != "\n":
                out[i] = " "
                i += 1
        elif ch == "/" and nxt == "*":
            end = code.find("*/", i + 2)
            end = n if end < 0 else end + 2
            for k in range(i, end):
                if code[k] != "\n":
                    out[k] = " "
            i = end
        elif ch in "\"'`":
            quote = ch
            out[i] = " "
            i += 1
            while i < n and code[i] != quote:
                if code[i] == "\\" and i + 1 < n:
                    out[i] = " "
                    i += 1
                if code[i] == "\n" and quote != "`":
                    break
                if code[i] != "\n":
                    out[i] = " "
                i += 1
            if i < n and code[i] == quote:
                out[i] = " "
                i += 1
        else:
            i += 1
    return "".join(out)


def _match(code: str, i: int, open_ch: str, close_ch: str) -> int:
    """Index just past the bracket that closes the one at code[i] (len(code) when unbalanced)."""
    depth = 0
    for j in range(i, len(code)):
        if code[j] == open_ch:
            depth += 1
        elif code[j] == close_ch:
            depth -= 1
            if depth == 0:
                return j + 1
    return len(code)


def _statement_end(code: str, i: int) -> int:
    """Index just past the statement that starts at or after code[i]: a block, an if/loop with its body, or up to ';'."""
    n = len(code)
    while i < n and code[i].isspace():
        i += 1
    if i >= n:
        return n
    if code[i] == "{":
        return _match(code, i, "{", "}")
    m = _LOOP_HEAD.match(code, i) or _IF_HEAD.match(code, i)
    if m:
        end = _statement_end(code, _match(code, m.end() - 1, "(", ")"))
        if m.group(0).startswith("if"):
            j = end
            while j < n and code[j].isspace():
                j += 1
            if code.startswith("else", j) and not (j + 4 < n and (code[j + 4].isalnum() or code[j + 4] == "_")):
                return _statement_end(code, j + 4)
        return end
    depth = 0
    for j in range(i, n):
        c = code[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == ";" and depth <= 0:
            return j + 1
    return n


def _is_log_loop_text(kind: str, header: str, body: str) -> bool:
    """For brace languages: the loop's condition variable is halved/shifted down, or doubled while bounded above."""
    if kind == "for":
        parts = header.split(";")
        cond, scan = (parts[1], parts[2] + " " + body) if len(parts) == 3 else (header, body)
    else:
        cond, scan = header, body
    for v in set(_IDENT.findall(cond)):
        e = re.escape(v)
        shrink = (
            rf"\b{e}\s*(?:/=\s*(?:[2-9]|[1-9]\d+)\b|>>>?=\s*[1-9]\d*\b)"
            rf"|\b{e}\s*=[^;=]*?\b{e}\s*(?:/\s*(?:[2-9]|[1-9]\d+)\b|>>>?\s*[1-9]\d*\b)"
            rf"|\b{e}\s*=[^;=]*%\s*{e}\b"                       # b = a % b  (Euclid)
            rf"|\[[^\]=]*\b{e}\b[^\]=]*\]\s*=\s*\[[^\]]*%\s*{e}\b"   # [a, b] = [b, a % b]  (JS destructuring)
        )
        if re.search(shrink, scan):
            return True
        # t = a % b; ...; b = t   (Euclid with a temporary)
        for rem in re.finditer(rf"\b(\w+)\s*=[^;=]*%\s*{e}\b", scan):
            if re.search(rf"\b{e}\s*=\s*{re.escape(rem.group(1))}\b", scan):
                return True
        grow = (
            rf"\b{e}\s*(?:\*=\s*(?:[2-9]|[1-9]\d+)\b|<<=\s*[1-9]\d*\b)"
            rf"|\b{e}\s*=[^;=]*?\b{e}\s*(?:\*\s*(?:[2-9]|[1-9]\d+)\b|<<\s*[1-9]\d*\b)"
        )
        if re.search(grow, scan) and re.search(rf"\b{e}\s*<=?|>=?\s*\b{e}\b", cond):
            return True
    return False


def _brace_loop_profile(code: str) -> Tuple[int, int, bool]:
    """(deepest chain of non-log loops, the same over chains that contain a log loop, any log loop?) for C-like code."""
    clean = _blank_comments_and_strings(code)
    loops: List[Tuple[int, int, bool]] = []   # (start, end, is_log)
    skip = set()                              # the `while (...)` that closes a do-while is not a loop of its own

    for m in _DO_BLOCK.finditer(clean):
        body_end = _match(clean, m.end() - 1, "{", "}")
        rest = clean[body_end:]
        w = re.match(r"\s*while\s*\(", rest)
        if not w:
            continue
        open_at = body_end + w.end() - 1
        close_at = _match(clean, open_at, "(", ")")
        skip.add(body_end + len(rest) - len(rest.lstrip()))   # where that trailing `while` starts
        end = close_at
        while end < len(clean) and clean[end].isspace():
            end += 1
        if end < len(clean) and clean[end] == ";":
            end += 1
        loops.append((m.start(), end, _is_log_loop_text("while", clean[open_at + 1:close_at - 1], clean[m.start():body_end])))

    for m in _LOOP_HEAD.finditer(clean):
        if m.start() in skip:
            continue
        open_at = m.end() - 1
        close_at = _match(clean, open_at, "(", ")")
        end = _statement_end(clean, close_at)
        loops.append((m.start(), end, _is_log_loop_text(m.group(1), clean[open_at + 1:close_at - 1], clean[close_at:end])))

    loops.sort()
    stack: List[Tuple[int, int, int]] = []    # (end, non-log loops, log loops) of the chain of enclosing loops
    max_nonlog = max_with_log = 0
    has_log = False
    for start, end, is_log in loops:
        while stack and stack[-1][0] <= start:
            stack.pop()
        nonlog = (stack[-1][1] if stack else 0) + (0 if is_log else 1)
        logs = (stack[-1][2] if stack else 0) + (1 if is_log else 0)
        stack.append((end, nonlog, logs))
        max_nonlog = max(max_nonlog, nonlog)
        if logs:
            has_log = True
            max_with_log = max(max_with_log, nonlog)
    return max_nonlog, max_with_log, has_log


def _c_sized_alloc(code: str) -> bool:
    """malloc/calloc/realloc sized by a variable (not just sizeof(...)): memory that grows with the input."""
    for m in re.finditer(r"\b(?:malloc|calloc|realloc)\s*\(([^;]*)", code):
        args = re.sub(r"sizeof\s*\([^)]*\)", " ", m.group(1))
        if re.search(r"[A-Za-z_]", args):
            return True
    return False


class _PythonASTAnalyzer(ast.NodeVisitor):
    """Walk the AST and collect structural facts."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.split("\n")

        # Loop nesting
        self._loop_depth   = 0
        self.max_loop_depth = 0
        # ...split into linear loops and logarithmic ones (counter halved/doubled each pass)
        self._nonlog_depth = 0
        self._log_depth = 0
        self.max_nonlog_depth = 0
        self.max_nonlog_depth_with_log = 0
        self.has_log_loop = False

        # Recursion
        self.recursive_funcs: Dict[str, int] = {}   # fname -> call count in body
        self.func_stack: List[str] = []

        # Patterns
        self.has_sorting       = False
        self.has_binary_search = False
        self.has_hash_map      = False
        self.has_ordered_map   = False
        self.has_dp_table      = False
        self.has_heap          = False
        self.has_deque         = False
        self.has_set           = False
        self.has_2d_array      = False
        self.has_graph_adj     = False
        self.has_bfs           = False   # BFS pattern: deque + while + popleft/append
        self.allocations: List[str] = []   # variable names that grow with input

        # Try to parse
        try:
            tree = ast.parse(code)
            self.visit(tree)
            # Post-visit: detect BFS pattern (deque + while + popleft/append)
            # BFS visits each node once → O(n), not O(n²) despite nested loops
            if self.has_deque and self.max_loop_depth >= 2:
                code_lower = code.lower()
                if ("popleft" in code_lower or "appendleft" in code_lower) and \
                   "while" in code_lower and \
                   ("append" in code_lower or "add" in code_lower):
                    self.has_bfs = True
                    # BFS: the while+for combination is O(V+E) = O(n), not O(n²)
                    # Reduce effective loop depth to 1
                    self.max_loop_depth = 1
        except SyntaxError:
            # Fall back to regex scan
            self._regex_scan()

    # ── Loop tracking ────────────────────────────────────────────────────

    def _enter_loop(self, node, is_log: bool):
        self._loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self._loop_depth)
        if is_log:
            self._log_depth += 1
            self.has_log_loop = True
        else:
            self._nonlog_depth += 1
            self.max_nonlog_depth = max(self.max_nonlog_depth, self._nonlog_depth)
        if self._log_depth:
            self.max_nonlog_depth_with_log = max(self.max_nonlog_depth_with_log, self._nonlog_depth)
        self.generic_visit(node)
        self._loop_depth -= 1
        if is_log:
            self._log_depth -= 1
        else:
            self._nonlog_depth -= 1

    def visit_For(self, node):
        self._enter_loop(node, False)

    def visit_While(self, node):
        self._enter_loop(node, _is_log_loop_py(node))

    # ── Function / recursion tracking ────────────────────────────────────

    def visit_FunctionDef(self, node):
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        # Check for self-recursion
        if self.func_stack:
            fname = self.func_stack[-1]
            called = None
            if isinstance(node.func, ast.Name):
                called = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr
            if called == fname:
                self.recursive_funcs[fname] = self.recursive_funcs.get(fname, 0) + 1

        # Detect library calls
        func_str = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
        # Only flag sorting when it's a known sort function call, not a user-defined
        # function whose name happens to contain "sort" (e.g. sortArray, sortHelper).
        _SORT_CALLS = {
            "sort", "sorted", "mergesort", "heapsort", "timsort",
            # common method calls: arr.sort(), list.sort()
        }
        if isinstance(node.func, ast.Attribute):
            # method call: obj.sort() — only flag if attr is exactly "sort"
            if node.func.attr in _SORT_CALLS:
                self.has_sorting = True
        elif isinstance(node.func, ast.Name):
            # standalone call: sorted(...) — only flag exact known names
            if node.func.id in _SORT_CALLS:
                self.has_sorting = True
        if any(s in func_str for s in ["bisect", "binary_search"]):
            self.has_binary_search = True
        if any(s in func_str for s in ["heapq", "heappush", "heappop", "nlargest", "nsmallest"]):
            self.has_heap = True
        if "deque" in func_str:
            self.has_deque = True
        
        # Detect list(map(...)) or list(filter(...)) — these are O(n) operations
        if isinstance(node.func, ast.Name) and node.func.id == "list":
            if node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                    if arg.func.id in ("map", "filter", "zip"):
                        # list(map(...)) is O(n) — treat as a single loop
                        self.max_loop_depth = max(self.max_loop_depth, 1)

        self.generic_visit(node)

    # ── Assignment tracking ───────────────────────────────────────────────

    def visit_Assign(self, node):
        # Detect data structure allocations
        if isinstance(node.value, (ast.Dict, ast.DictComp)):
            self.has_hash_map = True
            if node.targets:
                self.allocations.append(ast.unparse(node.targets[0]) if hasattr(ast, "unparse") else "dict")
        if isinstance(node.value, (ast.Set, ast.SetComp)):
            self.has_set = True
        if isinstance(node.value, (ast.List, ast.ListComp)):
            val_str = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
            # 2D list: [[...] for _ in range(n)]
            if "for" in val_str and "[" in val_str:
                self.has_2d_array = True
            if node.targets:
                self.allocations.append(ast.unparse(node.targets[0]) if hasattr(ast, "unparse") else "list")
        
        # List comprehension is O(n) — treat as a single loop
        if isinstance(node.value, ast.ListComp):
            self.max_loop_depth = max(self.max_loop_depth, 1)
        # Dict/Set comprehension is also O(n)
        if isinstance(node.value, (ast.DictComp, ast.SetComp)):
            self.max_loop_depth = max(self.max_loop_depth, 1)

        # Detect dp[...] = ... pattern
        for target in node.targets:
            t_str = ast.unparse(target) if hasattr(ast, "unparse") else ""
            if re.search(r"\bdp\b|\bmemo\b|\bcache\b|\btable\b", t_str):
                self.has_dp_table = True

        # Detect binary search: mid = lo + (hi - lo) // 2  or  mid = (lo + hi) // 2
        # Require that lo/hi/left/right bounds are also present — otherwise
        # `mid = total // 2` (median calculation) is a false positive.
        for target in node.targets:
            t_str = ast.unparse(target) if hasattr(ast, "unparse") else ""
            if re.search(r"\bmid\b", t_str):
                val_str = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
                if re.search(r"//\s*2|>>\s*1", val_str):
                    # Only flag as binary search if the value expression references
                    # typical search bounds (lo, hi, left, right, low, high).
                    # A plain `total // 2` or `n // 2` is a median/midpoint, not binary search.
                    if re.search(r"\b(lo|hi|left|right|low|high)\b", val_str):
                        self.has_binary_search = True

        self.generic_visit(node)

    # ── Subscript: detect dp[i][j] ────────────────────────────────────────

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Subscript):
            self.has_2d_array = True
        self.generic_visit(node)

    # ── Regex fallback (when AST parse fails) ────────────────────────────

    def _regex_scan(self):
        code = self.code
        # Count loop depth via indentation
        depth = 0
        for line in self.lines:
            s = line.strip()
            if re.match(r"^(for|while)\b", s):
                depth += 1
                self.max_loop_depth = max(self.max_loop_depth, depth)
            elif s and not s.startswith("#"):
                indent = len(line) - len(line.lstrip())
                if indent == 0:
                    depth = 0
        # Only flag sorting for known sort function calls, not user-defined names
        # containing "sort" (e.g. sortArray). Match: .sort(, sorted(, sort(
        if re.search(r'(?<!\w)sorted\s*\(|\.sort\s*\(|(?<!\w)sort\s*\(', code):
            self.has_sorting = True
        if re.search(r"\bbisect\b|\bbinary_search\b", code):
            self.has_binary_search = True
        # Detect while-loop binary search: has mid + lo/hi/left/right bounds
        # Require bounds variable — plain `mid = total // 2` is NOT binary search
        if (re.search(r"\bmid\b", code) and
                re.search(r"\b(lo|hi|left|right|low|high)\b", code) and
                re.search(r"\bwhile\b", code)):
            self.has_binary_search = True
        if re.search(r"\bdict\b|\bdefaultdict\b|\bCounter\b|\{\}", code):
            self.has_hash_map = True
        if re.search(r"\bdp\[|\bmemo\[|\bcache\[", code):
            self.has_dp_table = True
        if re.search(r"\bheapq\b|\bheappush\b", code):
            self.has_heap = True

    # ── Recursion classification ──────────────────────────────────────────

    def classify_recursion(self) -> Optional[str]:
        """
        Returns: 'exponential', 'factorial', 'divide_conquer',
                 'linear', 'logarithmic', or None.
        If the function is memoized (@lru_cache / @cache / memo dict),
        exponential recursion is downgraded to 'memoized_exponential' which
        the caller treats as O(n) or O(n²).
        """
        if not self.recursive_funcs:
            return None

        code = self.code
        # Check for memoization decorators or memo dict at module level
        has_memo = bool(re.search(
            r'@lru_cache|@cache|@functools\.cache|@functools\.lru_cache'
            r'|\bmemo\s*=\s*\{|\bdp\s*=\s*\[|\bcache\s*=\s*\{',
            code, re.IGNORECASE
        ))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return "linear"

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            fname = node.name
            if fname not in self.recursive_funcs:
                continue

            # Check for per-function memoization decorator
            func_has_memo = has_memo or any(
                (isinstance(d, ast.Name) and d.id in ("cache", "lru_cache"))
                or (isinstance(d, ast.Attribute) and d.attr in ("cache", "lru_cache"))
                or (isinstance(d, ast.Call) and (
                    (isinstance(d.func, ast.Name) and d.func.id in ("cache", "lru_cache"))
                    or (isinstance(d.func, ast.Attribute) and d.func.attr in ("cache", "lru_cache"))
                ))
                for d in node.decorator_list
            )

            # Count recursive calls in this function body
            call_count = sum(
                1 for n in ast.walk(node)
                if isinstance(n, ast.Call)
                and (
                    (isinstance(n.func, ast.Name) and n.func.id == fname)
                    or (isinstance(n.func, ast.Attribute) and n.func.attr == fname)
                )
            )

            body_src = ast.unparse(node) if hasattr(ast, "unparse") else ""

            if call_count >= 2:
                if func_has_memo:
                    return "memoized_exponential"
                # Check if all recursive calls are in mutually exclusive if/elif/else
                # branches — this is the recursive binary search pattern where only
                # ONE branch executes per call, making it O(log n) not O(2^n).
                if _all_recursive_calls_in_exclusive_branches(node, fname):
                    return "logarithmic"
                # Check for divide-and-conquer (n//2 or n/2 in args)
                if re.search(r"//\s*2|/\s*2\b|n\s*-\s*1.*n\s*-\s*1", body_src):
                    return "divide_conquer"
                return "exponential"

            if call_count == 1:
                # Logarithmic: argument is n//2
                if re.search(r"//\s*2|/\s*2\b", body_src):
                    return "logarithmic"
                # n * f(n-1) pattern — this is linear recursion (single call per frame)
                # that computes a factorial VALUE.  It is NOT O(n!) complexity.
                # True O(n!) algorithms enumerate permutations and branch exponentially.
                return "linear"

        return "linear"


# ─────────────────────────────────────────────────────────────────────────────
# Non-Python structural analyser (C++, Java, JavaScript, C)
# ─────────────────────────────────────────────────────────────────────────────

class _StructuralAnalyzer:
    """Regex/structural analysis for non-Python languages."""

    def __init__(self, code: str, language: str):
        self.code     = code
        self.language = language.lower()
        self.lines    = code.split("\n")

        self.max_loop_depth    = 0
        self.max_nonlog_depth  = 0   # deepest chain of loops that are not halving/doubling ones
        self.max_nonlog_depth_with_log = 0
        self.has_log_loop      = False
        self.has_sorting       = False
        self.has_binary_search = False
        self.has_hash_map      = False
        self.has_ordered_map   = False
        self.has_dp_table      = False
        self.has_heap          = False
        self.has_set           = False
        self.has_2d_array      = False
        self.has_recursion     = False
        self.recursive_type    = None   # 'exponential','divide_conquer','linear','logarithmic'

        self._scan()

    def _scan(self):
        code  = self.code
        lines = self.lines

        # ── Loop depth ────────────────────────────────────────────────────
        # Strategy: scan character-by-character tracking brace depth.
        # A loop keyword opens a "pending" slot; the next '{' confirms it.
        # Single-statement loops (no braces) are handled by treating the
        # semicolon that ends the loop BODY (not the for-header) as depth+1.
        brace_depth = 0
        loop_brace_depths: list = []   # brace depth at which each loop opened
        pending_loop = False           # saw a for/while, waiting for { or body-;
        in_for_header = False          # inside the (...) of a for(;;) header
        paren_depth = 0               # tracks ( ) nesting

        i = 0
        while i < len(code):
            ch = code[i]

            # Skip line comments
            if ch == '/' and i + 1 < len(code) and code[i+1] == '/':
                while i < len(code) and code[i] != '\n':
                    i += 1
                continue

            # Skip block comments
            if ch == '/' and i + 1 < len(code) and code[i+1] == '*':
                i += 2
                while i + 1 < len(code) and not (code[i] == '*' and code[i+1] == '/'):
                    i += 1
                i += 2
                continue

            # Skip string literals (avoid matching keywords inside strings)
            if ch in ('"', "'"):
                quote = ch; i += 1
                while i < len(code) and code[i] != quote:
                    if code[i] == '\\': i += 1  # skip escape
                    i += 1
                i += 1
                continue

            if ch == '(':
                paren_depth += 1
                if pending_loop:
                    in_for_header = True

            elif ch == ')':
                paren_depth = max(0, paren_depth - 1)
                if in_for_header and paren_depth == 0:
                    in_for_header = False
                    # pending_loop stays True — waiting for { or body statement

            elif ch == '{':
                brace_depth += 1
                if pending_loop and not in_for_header:
                    loop_brace_depths.append(brace_depth - 1)
                    pending_loop = False
                self.max_loop_depth = max(self.max_loop_depth, len(loop_brace_depths))

            elif ch == '}':
                # Close any loops that were opened at or above this depth
                while loop_brace_depths and loop_brace_depths[-1] >= brace_depth - 1:
                    loop_brace_depths.pop()
                brace_depth = max(0, brace_depth - 1)
                pending_loop = False

            elif ch == ';' and pending_loop and not in_for_header:
                # Single-statement loop body (no braces): count as depth+1
                self.max_loop_depth = max(self.max_loop_depth, len(loop_brace_depths) + 1)
                pending_loop = False

            # Detect loop keywords: for( or while(
            if ch in ('f', 'w'):
                rest = code[i:]
                m = re.match(r'^(for|while)\s*\(', rest)
                if m:
                    if i == 0 or not (code[i-1].isalnum() or code[i-1] == '_'):
                        if pending_loop and not in_for_header:
                            # Outer brace-less loop's body IS this inner loop.
                            # Commit the outer loop at current depth first.
                            loop_brace_depths.append(brace_depth)
                            self.max_loop_depth = max(self.max_loop_depth, len(loop_brace_depths))
                        pending_loop = True
                        in_for_header = False

            i += 1

        # ── Logarithmic loops (counter halved/doubled each pass) ──────────────
        self.max_nonlog_depth, self.max_nonlog_depth_with_log, self.has_log_loop = _brace_loop_profile(code)

        # ── Sorting ───────────────────────────────────────────────────────
        # Use word-boundary patterns that won't match user-defined function names
        # like sortArray(), sortHelper(), etc.
        sort_patterns = [
            r"(?<!\w)sort\s*\(",                   # standalone sort(...) — not sortArray(
            r"Arrays\.sort\b",                     # Java Arrays.sort
            r"Collections\.sort\b",                # Java Collections.sort
            r"(?<!\w)sorted\s*\(",                 # Python sorted(...)
            r"\bstd::sort\b",                      # C++ std::sort
            r"\bqsort\b",                          # C qsort
            r"\.sort\s*\(",                        # method call: arr.sort(
        ]
        if any(re.search(p, code) for p in sort_patterns):
            self.has_sorting = True

        # ── Binary search ─────────────────────────────────────────────────
        # Require explicit bounds variables (lo/hi/left/right) alongside mid.
        # A plain `mid = total / 2` or `mid = n / 2` is a midpoint calculation,
        # NOT binary search.
        bs_patterns = [
            r"\bbinary_search\b",
            r"Arrays\.binarySearch\b",
            r"Collections\.binarySearch\b",
            r"\blower_bound\b|\bupper_bound\b",
            # mid assigned from bounds expression: mid = (lo + hi) / 2 or similar
            r"\bmid\s*=\s*.*\b(lo|hi|left|right|low|high)\b.*[/+].*2",
            r"\bmid\s*=\s*.*>>",                   # mid via bit shift with bounds
        ]
        # While-loop binary search: requires mid AND bounds AND while together
        has_mid    = bool(re.search(r"\bmid\b", code))
        has_bounds = bool(re.search(r"\b(lo|hi|left|right|low|high)\b", code))
        has_while  = bool(re.search(r"\bwhile\s*\(", code))
        if (has_mid and has_bounds and has_while) or any(re.search(p, code) for p in bs_patterns):
            self.has_binary_search = True

        # ── Hash map / set (O(1) operations) ─────────────────────────────────
        hash_patterns = [
            r"\bunordered_map\b|\bunordered_set\b",    # C++ O(1) hash structures
            r"\bHashMap\b|\bHashSet\b|\bLinkedHashMap\b",  # Java O(1) hash structures
            r"\bdict\b|\bdefaultdict\b|\bCounter\b",   # Python O(1) hash structures
            r"\bnew\s+Map\b|\bnew\s+Set\b",            # JS: new Map(), new Set() - O(1)
            r":\s*Map\b|:\s*Set\b",                    # TypeScript: Map<K,V>, Set<T>
            r"=\s*\{\s*\}",                            # JS/Python: freq = {} object literal
            r"\bObject\s*\.\s*create\b",               # JS: Object.create({})
        ]
        if any(re.search(p, code) for p in hash_patterns):
            self.has_hash_map = True
        
        # ── Ordered map / set (O(log n) operations) ───────────────────────
        # C++ map/set are balanced trees, not hash tables
        ordered_map_patterns = [
            r"\bmap\s*<(?!.*unordered)",               # C++ map< (but not unordered_map)
            r"\bset\s*<(?!.*unordered)",               # C++ set< (but not unordered_set)
            r"\bTreeMap\b|\bTreeSet\b",                # Java TreeMap/TreeSet
        ]
        self.has_ordered_map = any(re.search(p, code) for p in ordered_map_patterns)

        set_patterns = [
            r"\bunordered_set\b", r"\bHashSet\b", r"\bTreeSet\b",
            r"\bnew\s+Set\b", r"\bset\s*<",
        ]
        if any(re.search(p, code) for p in set_patterns):
            self.has_set = True

        # ── DP table ──────────────────────────────────────────────────────
        dp_patterns = [
            r"\bdp\s*\[|\bdp\s*=",
            r"\bmemo\s*\[|\bmemo\s*=",
            r"\btable\s*\[",
            r"int\s+dp\[|long\s+dp\[|vector.*dp",
        ]
        if any(re.search(p, code) for p in dp_patterns):
            self.has_dp_table = True

        # ── Heap / priority queue ─────────────────────────────────────────
        heap_patterns = [
            r"\bpriority_queue\b",
            r"\bPriorityQueue\b",
            r"\bheapq\b|\bheappush\b|\bheappop\b",
        ]
        if any(re.search(p, code) for p in heap_patterns):
            self.has_heap = True
        
        # ── Implicit O(n) operations ──────────────────────────────────────
        # These operations iterate through n elements but don't use explicit loops
        implicit_on_patterns = [
            r"\blist\s*\(\s*map\s*\(",           # Python: list(map(...))
            r"\blist\s*\(\s*filter\s*\(",        # Python: list(filter(...))
            r"\.map\s*\(",                        # JS/Java: arr.map(...)
            r"\.filter\s*\(",                     # JS/Java: arr.filter(...)
            r"\.forEach\s*\(",                    # JS: arr.forEach(...)
            r"\.reduce\s*\(",                     # JS: arr.reduce(...)
            r"\.stream\s*\(\s*\)",                # Java: arr.stream()
            r"\.collect\s*\(",                    # Java: stream.collect(...)
            r"\btransform\s*\(",                  # C++: transform(...)
            r"\bfor_each\s*\(",                   # C++: for_each(...)
            r"\bcopy\s*\(",                       # C++: copy(...)
            r"\[\s*\w+\s+for\s+\w+\s+in\s+",     # Python: [x for x in ...]
        ]
        if any(re.search(p, code) for p in implicit_on_patterns):
            # Treat as a single loop if no explicit loops detected yet
            self.max_loop_depth = max(self.max_loop_depth, 1)
            self.max_nonlog_depth = max(self.max_nonlog_depth, 1)

        # ── 2D array ──────────────────────────────────────────────────────
        # Use precise patterns — avoid matching two separate vector<T> params
        # as a 2D array. Require vector<vector< or arr[i][j] subscript patterns.
        if re.search(
            r'\[\s*\]\s*\[|\bint\s+\w+\s*\[.*\]\s*\[|vector\s*<\s*vector\s*<'
            r'|Array\.from\s*\(\s*\{[^}]*\}\s*,\s*\(\s*\)\s*=>\s*(?:new\s+)?Array\b'      # JS: Array.from({length: n}, () => new Array(m))
            r'|\.map\s*\(\s*\(\s*\)\s*=>\s*(?:new\s+)?Array\s*\('                          # JS: [...Array(n)].map(() => Array(m))
            r'|\b(?:malloc|calloc)\s*\(\s*\(?\s*[A-Za-z_]\w*\s*\*\s*(?!sizeof\b)[A-Za-z_]\w*',  # C: calloc(n * m, ...)
            code,
        ):
            self.has_2d_array = True

        # ── Recursion ─────────────────────────────────────────────────────
        # For each function, extract its body and check if it calls itself.
        # This avoids false positives when function A calls function B
        # (which looks like B "calls itself" when counted globally).
        self._detect_recursion_in_bodies(code)

    def _extract_function_bodies(self, code: str):
        """
        Yield (fname, body_src) for each top-level function in brace-based code.
        Uses brace matching to extract the exact body of each function.
        """
        # Match function headers: return_type fname(params) {
        if self.language in ("cpp", "c++", "c"):
            header_re = re.compile(r'\b\w[\w\s\*]*\s+(\w+)\s*\([^)]*\)\s*\{')
        elif self.language == "java":
            header_re = re.compile(
                r'(?:public|private|protected|static|final|synchronized|\s)+'
                r'\w+\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?\{'
            )
        elif self.language in ("javascript", "js"):
            header_re = re.compile(
                r'function\s+(\w+)\s*\([^)]*\)\s*\{'
                r'|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\s*)?\([^)]*\)\s*(?:=>\s*)?\{'
            )
        else:
            return

        for m in header_re.finditer(code):
            groups = m.groups()
            fname = next((g for g in groups if g), None)
            if not fname or fname in ("if", "while", "for", "switch", "else", "do"):
                continue
            # Extract body by brace matching
            start = m.end() - 1  # position of opening '{'
            depth = 0
            end = start
            for idx in range(start, len(code)):
                if code[idx] == '{':
                    depth += 1
                elif code[idx] == '}':
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
            yield fname, code[start:end]

    def _detect_recursion_in_bodies(self, code: str):
        """
        Detect recursion by checking if each function calls itself
        within its own body (not globally).
        """
        for fname, body in self._extract_function_bodies(code):
            # Count calls to fname inside its own body
            # The opening brace is the first char of body, so the definition
            # header is NOT inside body — only actual calls are counted.
            call_count = len(re.findall(rf'\b{re.escape(fname)}\s*\(', body))
            if call_count >= 1:
                self.has_recursion = True
                if call_count >= 2:
                    if re.search(r'/\s*2\b|>>\s*1\b|\bmid\b', body):
                        self.recursive_type = "divide_conquer"
                    else:
                        self.recursive_type = "exponential"
                else:
                    if re.search(r'/\s*2\b|>>\s*1\b', body):
                        self.recursive_type = "logarithmic"
                    else:
                        # Single recursive call — linear recursion regardless of
                        # whether it multiplies by n (factorial value computation
                        # is O(n), not O(n!)).
                        self.recursive_type = "linear"
                break  # use the first recursive function found


# ─────────────────────────────────────────────────────────────────────────────
# Core complexity derivation
# ─────────────────────────────────────────────────────────────────────────────

def _has_early_exit_in_loop(code: str) -> bool:
    """
    Return True if any loop body contains a return or break statement
    that can short-circuit the loop.
    Uses AST for Python; brace-depth tracking for C++/Java/JS.
    """
    # ── Python: use AST ───────────────────────────────────────────────────
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if child is node:
                        continue
                    if isinstance(child, (ast.Return, ast.Break)):
                        return True
        return False
    except SyntaxError:
        pass

    # ── Non-Python: scan for return/break inside a loop block ────────────
    # Strategy: track brace depth; when inside a loop body (depth > loop_depth),
    # a return or break keyword counts as an early exit.
    lines = code.split('\n')
    brace_depth = 0
    loop_open_depths: list = []   # brace depth at which each loop opened

    i = 0
    while i < len(code):
        ch = code[i]
        # Skip line comments
        if ch == '/' and i + 1 < len(code) and code[i+1] == '/':
            while i < len(code) and code[i] != '\n':
                i += 1
            continue
        # Skip block comments
        if ch == '/' and i + 1 < len(code) and code[i+1] == '*':
            i += 2
            while i + 1 < len(code) and not (code[i] == '*' and code[i+1] == '/'):
                i += 1
            i += 2
            continue
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            if loop_open_depths and loop_open_depths[-1] >= brace_depth - 1:
                loop_open_depths.pop()
            brace_depth = max(0, brace_depth - 1)
        # Detect loop keywords
        elif ch in ('f', 'w', 'd'):
            rest = code[i:]
            m = re.match(r'^(for|while|do)\s*[\({]', rest)
            if m and (i == 0 or not (code[i-1].isalnum() or code[i-1] == '_')):
                loop_open_depths.append(brace_depth)
        # Detect return/break inside a loop body
        elif ch in ('r', 'b') and loop_open_depths:
            rest = code[i:]
            if re.match(r'^(return|break)\b', rest):
                if brace_depth > loop_open_depths[-1]:
                    return True
        i += 1
    return False


def _derive_time_complexity(
    max_loop_depth: int,
    recursion_type: Optional[str],
    has_sorting: bool,
    has_binary_search: bool,
    has_heap: bool,
    has_dp_table: bool,
    has_hash_map: bool,
    has_ordered_map: bool,
    has_2d_array: bool,
    code_hint: str = "",
    log_factor: bool = False,
) -> Tuple[str, str, str, str]:
    """
    Returns (best, average, worst, reason).
    """

    # ── Recursion takes priority ──────────────────────────────────────────
    if recursion_type == "memoized_exponential":
        return ("O(n)", "O(n)", "O(n)",
                "Memoized recursion detected — each unique subproblem is computed once → O(n) time.")

    if recursion_type == "exponential":
        return ("O(n)", "O(2^n)", "O(2^n)",
                "Exponential recursion detected (multiple recursive calls per level). "
                "Without memoization, subproblems are recomputed repeatedly.")

    if recursion_type == "factorial":
        # n * f(n-1) is a LINEAR recursion that computes the factorial value.
        # The call stack is O(n) deep and each call does O(1) work → O(n) time.
        # True O(n!) algorithms enumerate all permutations — that's a different
        # pattern (exponential branching, not a single n-1 call).
        return ("O(n)", "O(n)", "O(n)",
                "Linear recursion computing factorial (single recursive call n * f(n-1)) → O(n) time.")
    
    if recursion_type == "divide_conquer":
        # Divide-and-conquer always follows T(n) = 2T(n/2) + O(n) → O(n log n)
        # by the Master Theorem.  The O(log n) case is handled by 'logarithmic'
        # recursion type (single recursive call that halves the input).
        return ("O(n log n)", "O(n log n)", "O(n log n)",
                "Divide-and-conquer recursion detected (problem split in half each call, "
                "two recursive branches). By the Master Theorem T(n)=2T(n/2)+O(n) → O(n log n).")

    if recursion_type == "logarithmic":
        return ("O(log n)", "O(log n)", "O(log n)",
                "Tail recursion that halves the input each call → O(log n).")

    if recursion_type == "linear":
        # Linear recursion + possible inner loops
        if max_loop_depth >= 2:
            return ("O(n²)", "O(n²)", "O(n²)",
                    "Linear recursion with nested loops inside → O(n²).")
        return ("O(n)", "O(n)", "O(n)",
                "Linear recursion (single recursive call per level, no branching) → O(n).")

    # ── No recursion — loop-based analysis ───────────────────────────────

    # Binary search (explicit or via library, or while-loop with mid pattern)
    if has_binary_search and max_loop_depth <= 1:
        if has_sorting:
            # Sort then binary search: O(n log n) for sort dominates
            return ("O(n log n)", "O(n log n)", "O(n log n)",
                    "Sort O(n log n) followed by binary search O(log n) → O(n log n) overall.")
        return ("O(log n)", "O(log n)", "O(log n)",
                "Binary search pattern detected — halves the search space each iteration → O(log n).")

    # Sorting dominates when loops are ≤ 1
    if has_sorting and max_loop_depth <= 1:
        return ("O(n log n)", "O(n log n)", "O(n log n)",
                "Built-in sort detected (Timsort / introsort) → O(n log n). "
                "The surrounding code is O(n), so sorting dominates.")

    # Sorting + one outer loop
    if has_sorting and max_loop_depth == 2:
        return ("O(n log n)", "O(n²)", "O(n²)",
                "Sort O(n log n) combined with a nested loop O(n²) → O(n²) overall.")

    # heapq.nlargest / nsmallest — O(n log k) regardless of surrounding loops
    if has_heap and bool(re.search(r'\bnlargest\b|\bnsmallest\b', code_hint)):
        return ("O(n log k)", "O(n log k)", "O(n log k)",
                "heapq.nlargest/nsmallest scans n elements maintaining a heap of size k → O(n log k).")

    # Heap operations inside a loop
    if has_heap and max_loop_depth == 1:
        return ("O(n log n)", "O(n log n)", "O(n log n)",
                "Heap/priority-queue operations (O(log n) each) inside a single loop → O(n log n).")

    # heapq.nlargest / nsmallest with no explicit loop — O(n log k)
    if has_heap and max_loop_depth == 0:
        return ("O(n log k)", "O(n log k)", "O(n log k)",
                "heapq.nlargest/nsmallest scans n elements maintaining a heap of size k → O(n log k).")
    
    # Ordered map/set operations inside a loop (C++ map/set, Java TreeMap/TreeSet)
    # Each insert/lookup is O(log n), so n operations = O(n log n)
    if has_ordered_map and max_loop_depth == 1:
        return ("O(n log n)", "O(n log n)", "O(n log n)",
                "Ordered map/set operations (O(log n) each) inside a loop → O(n log n). "
                "C++ map/set and Java TreeMap/TreeSet use balanced trees.")

    # DP table with 2D array → O(n²) or O(n*m)
    if has_dp_table and has_2d_array:
        return ("O(n²)", "O(n²)", "O(n²)",
                "2D DP table detected — filling an n×m table with constant work per cell → O(n·m).")

    # DP table with 1D array
    if has_dp_table and max_loop_depth >= 2:
        return ("O(n²)", "O(n²)", "O(n²)",
                "DP with nested loops detected → O(n²).")

    if has_dp_table and max_loop_depth == 1:
        return ("O(n)", "O(n)", "O(n)",
                "1D DP table with a single loop → O(n).")

    # A counter halved/doubled every pass (while n > 0: n //= 10) runs O(log n) times; the linear loops around it multiply.
    if log_factor:
        k = max_loop_depth
        if k == 0:
            return ("O(log n)", "O(log n)", "O(log n)",
                    "A loop whose counter is halved or doubled on every pass runs O(log n) times → O(log n).")
        t = "O(n log n)" if k == 1 else "O(n² log n)" if k == 2 else f"O(n^{k} log n)"
        return (t, t, t,
                f"{k} linear loop level(s) around a loop whose counter is halved or doubled each pass → {t}.")

    # Pure loop analysis
    if max_loop_depth == 0:
        return ("O(1)", "O(1)", "O(1)",
                "No loops or recursion detected — all operations are constant time → O(1).")

    if max_loop_depth == 1:
        # Best case O(1) only if there's a return/break INSIDE the loop body
        has_early_exit = _has_early_exit_in_loop(code_hint)
        best = "O(1)" if has_early_exit else "O(n)"
        return (best, "O(n)", "O(n)",
                "Single loop iterating over the input → O(n). "
                + ("Best case O(1) if an early exit (return/break) is hit on the first element."
                   if has_early_exit
                   else "No early exit — every element is always visited."))

    if max_loop_depth == 2:
        if has_sorting:
            return ("O(n log n)", "O(n²)", "O(n²)",
                    "Two nested loops → O(n²). Sort inside adds O(n log n) but O(n²) dominates.")
        has_early_exit = _has_early_exit_in_loop(code_hint)
        best = "O(n)" if has_early_exit else "O(n²)"
        return (best, "O(n²)", "O(n²)",
                "Two nested loops, each iterating up to n times → O(n²). "
                + ("Best case O(n) if the inner loop exits early."
                   if has_early_exit
                   else "No early exit — always O(n²)."))

    if max_loop_depth == 3:
        return ("O(n²)", "O(n³)", "O(n³)",
                "Three nested loops → O(n³). Consider reducing nesting with hash maps or DP.")

    return ("O(n^k)", f"O(n^{max_loop_depth})", f"O(n^{max_loop_depth})",
            f"{max_loop_depth} levels of nested loops → O(n^{max_loop_depth}).")


def _derive_space_complexity(
    max_loop_depth: int,
    recursion_type: Optional[str],
    has_hash_map: bool,
    has_dp_table: bool,
    has_2d_array: bool,
    has_heap: bool,
    has_set: bool,
    allocations: List[str],
    code: str,
    has_ordered_map: bool = False,
) -> Tuple[str, str, str, str]:
    """
    Returns (best, average, worst, reason).
    """

    # ── Recursion stack space ─────────────────────────────────────────────
    if recursion_type == "memoized_exponential":
        return ("O(n)", "O(n)", "O(n)",
                "Memoized recursion — memo table stores O(n) unique subproblem results.")
    if recursion_type == "exponential":
        return ("O(n)", "O(n)", "O(n)",
                "Exponential recursion — the call stack depth is O(n) at any point "
                "(even though the total call-tree nodes is O(2^n), only one path is "
                "live on the stack at a time).")
    if recursion_type == "factorial":
        return ("O(n)", "O(n)", "O(n)",
                "Linear recursion (n * f(n-1)) — call stack depth is O(n), each frame O(1) → O(n) space.")
    
    if recursion_type == "divide_conquer":
        return ("O(log n)", "O(n)", "O(n)",
                "Divide-and-conquer recursion — call stack depth O(log n), "
                "but the merge/combine step typically needs O(n) auxiliary space.")
    if recursion_type in ("linear", "logarithmic"):
        depth = "O(log n)" if recursion_type == "logarithmic" else "O(n)"
        return ("O(1)", depth, depth,
                f"Recursion call stack depth → {depth}.")

    # ── Data structure allocations ────────────────────────────────────────
    # heapq.nlargest/nsmallest: check before generic hash map — heap of size k dominates
    if has_heap and re.search(r'\bnlargest\b|\bnsmallest\b', code):
        return ("O(k)", "O(k)", "O(k)",
                "heapq.nlargest/nsmallest maintains a heap of only k elements → O(k) space.")

    if has_2d_array:
        return ("O(n²)", "O(n²)", "O(n²)",
                "2D array/matrix allocated proportional to n×m → O(n²) space.")

    if has_dp_table:
        if has_2d_array:
            return ("O(n²)", "O(n²)", "O(n²)",
                    "2D DP table → O(n²) space.")
        return ("O(n)", "O(n)", "O(n)",
                "1D DP array allocated proportional to input size → O(n) space.")

    if has_hash_map or has_set:
        return ("O(1)", "O(n)", "O(n)",
                "Hash map/set that can grow up to n entries → O(n) space. "
                "Best case O(1) if the map stays small.")

    # Ordered map/set (C++ map/set, Java TreeMap/TreeSet) also grows with input
    if has_ordered_map:
        return ("O(1)", "O(n)", "O(n)",
                "Ordered map/set (balanced tree) that can grow up to n entries → O(n) space.")

    if has_heap:
        # heapq.nlargest/nsmallest maintains a heap of size k, not n
        if re.search(r'\bnlargest\b|\bnsmallest\b', code):
            return ("O(k)", "O(k)", "O(k)",
                    "heapq.nlargest/nsmallest maintains a heap of only k elements → O(k) space.")
        return ("O(1)", "O(n)", "O(n)",
                "Heap/priority queue can hold up to n elements → O(n) space.")

    # Check for operations that build result collections (O(n) space)
    builds_result_collection = bool(re.search(
        r"\.push_back\s*\(|\.append\s*\(|\.add\s*\(|\.push\s*\("  # C++/Python/Java/JS append
        r"|\.map\s*\(|\.filter\s*\(|\.collect\s*\("                # Functional operations creating new collections
        r"|\bresult\s*=\s*\[|\bresult\s*=\s*\{|\bresult\s*=\s*new"  # Explicit result variable
        r"|\bans\s*=\s*\[|\boutput\s*=\s*\[",                       # Common result variable names
        code
    ))

    # Check for explicit list/array allocations proportional to input
    # Only flag when the allocation is clearly sized by a variable (not a literal)
    # Exclude vector<T> arr(n) which is just the input array, not an extra allocation
    # (it's only extra space if it's a result/output collection)
    has_linear_alloc = bool(re.search(
        r"\[\s*\]\s*=\s*\[|\blist\s*\(\s*\w"
        r"|\bArrayList\s*<|\bnew\s+\w+\s*\[\s*[a-zA-Z_]\w*\s*\]",
        code
    ))

    # Detect [val] * n  or  [0] * (expr)  — Python list allocation sized by input
    has_sized_alloc = bool(re.search(
        r"\[\s*\w[^]]*\]\s*\*\s*[\w(]"   # [0] * n  or  [val] * (expr)
        r"|\bnew\s+Array\s*\(\s*[a-zA-Z_]"  # JS: new Array(n)
        r"|\bnew\s+(?:int|long|boolean|double|char|byte|short|float)\s*\[\s*(?:\(\s*\w+\s*\)\s*)?\(?\s*[a-zA-Z_]"  # new int[n], new long[(int) n + 1]
        r"|\bvector\s*<[^>]+>\s*\w+\s*\(\s*[a-zA-Z_][^;{}]*\)\s*;",  # C++ declaration vector<int> dp(n); (not a function header)
        code
    ))

    has_sized_alloc = has_sized_alloc or _c_sized_alloc(code)   # C: malloc/calloc/realloc sized by a variable

    # Detect deque/queue usage (BFS/DFS) — grows with input
    has_queue_alloc = bool(re.search(
        r"\bdeque\s*\(|\bdeque\s*\[|\bQueue\b|\bArrayDeque\b|\bLinkedList\b"
        r"|\bnew\s+LinkedList|\bnew\s+ArrayDeque|\bnew\s+Queue"
        r"|\bqueue\s*<|\bstack\s*<",
        code
    ))

    if builds_result_collection or has_linear_alloc or has_sized_alloc or has_queue_alloc:
        return ("O(1)", "O(n)", "O(n)",
                "Array/list/collection that grows with input size → O(n) space.")

    # No significant allocations
    return ("O(1)", "O(1)", "O(1)",
            "No significant extra data structures — only a constant number of variables → O(1) space.")


# ─────────────────────────────────────────────────────────────────────────────
# Optimality assessment + concrete improvement hints
# ─────────────────────────────────────────────────────────────────────────────

# Complexity rank for comparison (lower index = better)
_RANK = {
    "O(1)": 0, "O(log n)": 1, "O(sqrt n)": 2, "O(n)": 3,
    "O(n log n)": 4, "O(n log² n)": 5, "O(n sqrt n)": 6,
    "O(n²)": 7, "O(n² log n)": 8, "O(n³)": 9, "O(2^n)": 10, "O(n!)": 11,
}

def _rank(c: str) -> int:
    if c in _RANK:
        return _RANK[c]
    try:
        from app.services.complexity.mag import parse_o
        m = parse_o(c)
    except Exception:
        m = None
    if m is None:
        return 3
    if m.exp:
        return 10
    by_exponent = {0: 0, 0.5: 2, 1: 3, 1.5: 6, 2: 7, 2.5: 8, 3: 9}
    a = float(m.a)
    base = max((rank for exp, rank in by_exponent.items() if exp <= a), default=0) if a < 3 else 9 + min(2, int(a) - 3)
    return base + (1 if m.b > 0 and a > 0 else 0) if a > 0 else (1 if m.b > 0 else 0)


def _is_optimal(time_worst: str, space_worst: str,
                has_hash_map: bool, has_dp_table: bool,
                has_sorting: bool, has_binary_search: bool,
                recursion_type: Optional[str],
                max_loop_depth: int,
                has_heap: bool,
                problem_statement: str) -> bool:
    """
    Return True when the solution is already at the best achievable complexity
    for its detected approach.
    """
    prob = problem_statement.lower()

    # O(1) time is always optimal
    if time_worst == "O(1)":
        return True
    # O(log n) — binary search, already optimal
    if time_worst == "O(log n)":
        return True
    # O(n) with O(1) or O(n) space — optimal linear scan
    if time_worst == "O(n)" and _rank(space_worst) <= _rank("O(n)"):
        return True
    # Memoized recursion — optimal DP
    if recursion_type == "memoized_exponential":
        return True
    # O(n log n) with sorting — only optimal if the problem actually needs ordering
    if time_worst == "O(n log n)" and has_sorting and max_loop_depth <= 1:
        # Sorting just to find max/min/sum/count is NOT optimal
        if any(k in prob for k in ["maximum", "minimum", "max", "min", "sum", "average",
                                    "count", "total", "largest", "smallest"]):
            return False
        return True
    # O(n log n) with heap — optimal for top-k / priority problems
    if time_worst == "O(n log n)" and has_heap:
        return True
    # DP with table — already memoised
    if has_dp_table and time_worst in ("O(n)", "O(n log n)", "O(n²)") and recursion_type != "exponential":
        return True
    return False


def _suggestions(
    time_worst: str,
    space_worst: str,
    has_hash_map: bool,
    has_dp_table: bool,
    has_sorting: bool,
    has_binary_search: bool,
    recursion_type: Optional[str],
    max_loop_depth: int,
    has_heap: bool,
    has_2d_array: bool,
    has_set: bool,
    problem_statement: str,
) -> Tuple[bool, List[str]]:
    """
    Returns (is_optimal, tips).
    tips are concrete, code-level instructions — not generic advice.
    """
    prob = problem_statement.lower()
    tips: List[str] = []

    optimal = _is_optimal(time_worst, space_worst, has_hash_map, has_dp_table,
                          has_sorting, has_binary_search, recursion_type, max_loop_depth,
                          has_heap, problem_statement)

    if optimal:
        tips.append("✅ Your solution is already optimal for this complexity class.")
        # Add a note about space if it can still be improved
        if _rank(space_worst) > _rank("O(1)") and not has_dp_table and not recursion_type:
            tips.append(
                "💡 Space can potentially be reduced to O(1) if you process elements "
                "in-place instead of building an extra array/map."
            )
        return True, tips

    # ── Not optimal — give exact, actionable advice ───────────────────────

    # O(n²) from nested loops — most common case
    if time_worst in ("O(n²)", "O(n³)") and max_loop_depth >= 2:
        if not has_hash_map and not has_set:
            # ── Problem-aware O(n²) advice ────────────────────────────────
            # NOTE: more specific checks first, generic last
            if any(k in prob for k in ["two sum", "pair sum", "complement", "target sum", "find two"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use a hash map for O(n):\n"
                    "  • In one pass, store each value in a dict: `seen[val] = index`.\n"
                    "  • For each element, check if `target - val` is already in `seen`.\n"
                    "  → Reduces to O(n) time, O(n) space."
                )
            elif any(k in prob for k in ["duplicate", "unique", "distinct", "frequency", "count occurrences"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use a hash map/set for O(n):\n"
                    "  • Build a frequency dict in one pass: `freq[val] += 1`.\n"
                    "  • Query counts in O(1) instead of scanning the array again.\n"
                    "  → Reduces to O(n) time, O(n) space."
                )
            elif any(k in prob for k in ["palindrome", "palindromic"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use expand-around-center for O(n):\n"
                    "  • For each index i, expand outward while s[l] == s[r].\n"
                    "  • Check both odd-length (center at i) and even-length (center at i, i+1).\n"
                    "  → Reduces to O(n) time, O(1) space."
                )
            elif any(k in prob for k in ["rotate", "rotation", "cyclic shift", "circular"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use the reverse trick for O(n) in-place rotation:\n"
                    "  • Reverse the whole array, then reverse first k, then reverse rest.\n"
                    "  • Or use slicing: `arr = arr[-k:] + arr[:-k]` in O(n).\n"
                    "  → Reduces to O(n) time, O(1) space."
                )
            elif any(k in prob for k in ["subarray", "substring", "window", "contiguous"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use a sliding window for O(n):\n"
                    "  • Maintain a window [left, right] and expand/shrink it in one pass.\n"
                    "  • Track the running sum/max/min as the window moves.\n"
                    "  → Reduces to O(n) time, O(1) space."
                )
            elif any(k in prob for k in ["sort", "sorted", "order", "arrange", "inversion"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops (e.g. bubble/insertion sort). "
                    "Use an efficient sort for O(n log n):\n"
                    "  • Python: `arr.sort()` or `sorted(arr)` — both use Timsort O(n log n).\n"
                    "  • For counting inversions, use merge sort.\n"
                    "  → Reduces to O(n log n) time."
                )
            elif any(k in prob for k in ["prefix", "suffix", "cumulative", "running sum"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use prefix sums for O(n):\n"
                    "  • Precompute `prefix[i] = prefix[i-1] + arr[i]` in one pass.\n"
                    "  • Answer range queries in O(1): `sum(l, r) = prefix[r] - prefix[l-1]`.\n"
                    "  → Reduces to O(n) time, O(n) space."
                )
            elif any(k in prob for k in ["graph", "bfs", "dfs", "path", "connected", "component", "island", "cycle"]):
                tips.append(
                    "🔴 Time: O(n²) — likely using adjacency matrix or scanning all nodes. "
                    "Use an adjacency list with BFS/DFS for O(V + E):\n"
                    "  • Build `adj = defaultdict(list)` and add edges in O(E).\n"
                    "  • BFS/DFS visits each node and edge once → O(V + E).\n"
                    "  → Reduces to O(V + E) time, O(V + E) space."
                )
            elif any(k in prob for k in ["dp", "dynamic", "knapsack", "subsequence", "edit distance", "coin", "climb"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops — expected for most DP problems. "
                    "Make sure you're not recomputing subproblems:\n"
                    "  • Use a bottom-up DP table filled in order.\n"
                    "  • If only the previous row is needed, use a 1D rolling array → O(n) space."
                )
            elif any(k in prob for k in ["anagram", "vowel", "character", "string", "reverse string", "word"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "String problems usually need only a single pass:\n"
                    "  • Use a frequency dict/Counter for character counts in O(n).\n"
                    "  • Use two pointers (left, right) for in-place reversal in O(n).\n"
                    "  → Reduces to O(n) time, O(1) or O(k) space."
                )
            elif any(k in prob for k in ["maximum", "minimum", "max", "min", "largest", "smallest"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Track the max/min in a single pass for O(n):\n"
                    "  • Initialize `best = arr[0]` then iterate once updating `best`.\n"
                    "  • No inner loop needed — each element is visited exactly once.\n"
                    "  → Reduces to O(n) time, O(1) space."
                )
            elif any(k in prob for k in ["two pointer", "three sum", "k sum", "closest"]):
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Use the two-pointer technique after sorting for O(n log n):\n"
                    "  • Sort the array once in O(n log n).\n"
                    "  • Use left/right pointers moving toward each other in O(n).\n"
                    "  → Reduces to O(n log n) time, O(1) extra space."
                )
            else:
                # Generic fallback — covers anything not matched above
                tips.append(
                    "🔴 Time: O(n²) from nested loops. "
                    "Look for a way to eliminate the inner loop:\n"
                    "  • Hash map/set: precompute values and look them up in O(1).\n"
                    "  • Two pointers: sort first, then use left/right pointers in O(n).\n"
                    "  • Sliding window: maintain a running result as you scan once.\n"
                    "  • Prefix sums: precompute cumulative values for O(1) range queries.\n"
                    "  → Target O(n) or O(n log n) time."
                )
        elif has_hash_map:
            tips.append(
                "🔴 Time: O(n²) from nested loops. "
                "You already have a hash map — make sure you're using it inside the inner loop "
                "to avoid the O(n) scan. The lookup should be O(1), not O(n)."
            )
        if max_loop_depth >= 3:
            tips.append(
                "🔴 Three nested loops → O(n³). "
                "Consider precomputing prefix sums or a 2D DP table to eliminate the innermost loop."
            )

    # O(2^n) or O(n!) from unmemorised recursion
    if time_worst in ("O(2^n)", "O(n!)"):
        if not has_dp_table:
            tips.append(
                "🔴 Time: O(2^n) — exponential recursion without memoization. "
                "Add memoization to cache subproblem results:\n"
                "  Python: add `@lru_cache(maxsize=None)` above your function, or\n"
                "  use a `memo = {}` dict and check `if args in memo: return memo[args]`.\n"
                "  → Reduces to O(n) or O(n²) time."
            )
        else:
            tips.append(
                "🔴 Time: O(2^n) — even with a DP table, the recursion branches exponentially. "
                "Convert to a bottom-up iterative DP to avoid call-stack overhead."
            )

    # O(n log n) when O(n) is achievable
    if time_worst == "O(n log n)" and has_sorting and not has_binary_search:
        if any(k in prob for k in ["maximum", "minimum", "max", "min", "sum", "average", "count"]):
            tips.append(
                "🟡 Time: O(n log n) from sorting. "
                "For max/min/sum/count problems you don't need to sort — "
                "a single linear scan O(n) is enough:\n"
                "  • Track the running max/min/sum as you iterate.\n"
                "  → Reduces to O(n) time, O(1) space."
            )
        elif any(k in prob for k in ["anagram", "frequency", "character count", "vowel", "palindrome check"]):
            tips.append(
                "🟡 Time: O(n log n) from sorting. "
                "For character frequency problems, use a Counter/dict instead:\n"
                "  • `from collections import Counter; Counter(s)` runs in O(n).\n"
                "  → Reduces to O(n) time, O(k) space (k = alphabet size)."
            )
        elif any(k in prob for k in ["two sum", "pair", "target"]):
            tips.append(
                "🟡 Time: O(n log n) from sorting. "
                "A hash map avoids sorting entirely:\n"
                "  • Store seen values in a dict and look up `target - val` in O(1).\n"
                "  → Reduces to O(n) time, O(n) space."
            )
        else:
            tips.append(
                "🟡 Time: O(n log n) from sorting. "
                "If the problem doesn't require ordered output, check whether sorting is necessary. "
                "A hash map or counting approach may achieve O(n)."
            )

    # Space improvements
    if _rank(space_worst) >= _rank("O(n²)"):
        if has_2d_array and has_dp_table:
            tips.append(
                "🟡 Space: O(n²) from 2D DP table. "
                "If each row only depends on the previous row, use two 1D arrays (current/previous) "
                "to reduce space to O(n):\n"
                "  prev = dp[i-1][:]  # keep only previous row\n"
                "  curr = [0] * n\n"
                "  → Reduces to O(n) space."
            )
        elif has_2d_array:
            tips.append(
                "🟡 Space: O(n²) from 2D array. "
                "Check if you can process the matrix in-place or use a rolling array."
            )

    if _rank(space_worst) == _rank("O(n)") and not has_dp_table and not recursion_type:
        # Extra array that might not be needed
        if any(k in prob for k in ["reverse", "rotate", "in-place", "swap"]):
            tips.append(
                "🟡 Space: O(n) from extra array. "
                "This problem can likely be solved in-place with O(1) extra space:\n"
                "  • Use two-pointer swap instead of building a reversed copy.\n"
                "  → Reduces to O(1) space."
            )

    # Recursion stack space
    if recursion_type in ("linear", "divide_conquer") and _rank(space_worst) >= _rank("O(n)"):
        tips.append(
            "🟡 Space: O(n) from recursion call stack. "
            "Convert to an iterative solution with an explicit stack to avoid stack overflow "
            "on large inputs and reduce overhead."
        )

    if not tips:
        tips.append(
            f"🟡 Current complexity: Time {time_worst}, Space {space_worst}. "
            "Review whether the algorithm can be restructured to reduce the dominant term."
        )

    return False, tips


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def _verdict(time_worst: str, space_worst: str, is_optimal: bool) -> Tuple[str, str]:
    """
    Returns (verdict_label, verdict_explanation).
    Verdict levels: 'optimal', 'acceptable', 'needs_improvement', 'poor'
    """
    t_rank = _rank(time_worst)
    s_rank = _rank(space_worst)

    if is_optimal:
        if t_rank == 0:  # O(1)
            return ("optimal", "Constant time — the best possible complexity. No improvements needed.")
        if t_rank == 1:  # O(log n)
            return ("optimal", "Logarithmic time — excellent complexity. This is optimal for search-based problems.")
        if t_rank == 3:  # O(n)
            return ("optimal", "Linear time — optimal for problems that require visiting every element at least once.")
        if t_rank == 4:  # O(n log n)
            return ("optimal", "Linearithmic time — optimal for comparison-based sorting and divide-and-conquer problems.")
        return ("optimal", f"Your solution is already at the optimal complexity class ({time_worst}).")

    if t_rank <= 3:  # O(1) to O(n)
        return ("acceptable", f"The time complexity is {time_worst}, which is acceptable. "
                "The code correctly solves the problem but may have minor style or portability issues.")

    if t_rank == 4:  # O(n log n)
        return ("acceptable", f"O(n log n) time is generally acceptable. "
                "Check if a linear O(n) approach is possible for this problem.")

    if t_rank <= 6:  # O(n sqrt n)
        return ("needs_improvement", f"Time complexity is {time_worst}. "
                "This may be too slow for large inputs. Consider a more efficient algorithm.")

    if t_rank == 7:  # O(n²)
        return ("needs_improvement", f"Quadratic time O(n²) detected. "
                "This will be slow for large inputs (n > 10,000). "
                "Look for a hash map, two-pointer, or sliding window approach.")

    # O(n³) and above
    return ("poor", f"Time complexity is {time_worst} — this will time out on large inputs. "
            "A fundamentally different algorithm is needed.")


def _tag_suggestions(tips: List[str]) -> List[Dict]:
    """
    Convert plain suggestion strings into structured dicts with priority tags.
    Returns list of { title, description, priority } dicts.
    """
    result = []
    for tip in tips:
        # Determine priority from emoji prefix
        if tip.startswith("🔴"):
            priority = "high"
        elif tip.startswith("🟡"):
            priority = "medium"
        elif tip.startswith("✅"):
            priority = "low"
        elif tip.startswith("💡"):
            priority = "low"
        else:
            priority = "medium"

        # Split into title + description
        # Remove emoji prefix
        clean = re.sub(r'^[🔴🟡✅💡⚠️]\s*', '', tip).strip()

        # Split on first ". " or ":\n" to get title vs body
        lines = clean.split('\n')
        first_line = lines[0].strip()

        # Try to extract a short title from the first sentence
        # Pattern: "Time: O(n²) from nested loops. Use a hash map..."
        # → title = "Time: O(n²) from nested loops"
        # → description = "Use a hash map..."
        dot_idx = first_line.find('. ')
        if dot_idx > 0 and dot_idx < 80:
            title = first_line[:dot_idx].strip()
            rest_of_first = first_line[dot_idx + 2:].strip()
        else:
            # Use first line as title, rest as description
            title = first_line[:60] + ('...' if len(first_line) > 60 else '')
            rest_of_first = ''

        # Build description from remaining content
        desc_parts = []
        if rest_of_first:
            desc_parts.append(rest_of_first)
        for line in lines[1:]:
            stripped = line.strip()
            if stripped:
                desc_parts.append(stripped)

        description = ' '.join(desc_parts) if desc_parts else first_line

        result.append({
            "title": title,
            "description": description,
            "priority": priority,
        })

    return result


def _players_part(code: str) -> str:
    """The code the player wrote, without the locked harness.

    Typed starters end in a harness (below the marker line) that reads the input and prints the answer. Its loops, helper
    lambdas and containers are the same for every solution, so counting them made an untouched stub look like O(n) time
    and a correct O(n) C solution like O(n^2). Code without the marker (older or custom questions) is analyzed whole."""
    lines = code.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if _LOCKED_MARKER in line:
            return "\n".join(lines[:i])
    return code


class ComplexityAnalyzer:
    """Accurate AST-based complexity analyzer."""

    async def analyze(
        self,
        code: str,
        language: str,
        problem_statement: str,
        # Optional execution stats from the last test run
        execution_time_ms: Optional[float] = None,
        memory_kb: Optional[float] = None,
        passed_tests: Optional[int] = None,
        total_tests: Optional[int] = None,
    ) -> Dict:
        lang = language.lower().strip()
        full_code = code
        code = _players_part(code)

        # ── Gather structural facts ───────────────────────────────────────
        if lang == "python":
            a = _PythonASTAnalyzer(code)
            max_loop_depth  = a.max_loop_depth
            recursion_type  = a.classify_recursion()
            has_sorting     = a.has_sorting
            has_binary_search = a.has_binary_search
            has_hash_map    = a.has_hash_map
            has_ordered_map = a.has_ordered_map
            has_dp_table    = a.has_dp_table
            has_heap        = a.has_heap
            has_set         = a.has_set
            has_2d_array    = a.has_2d_array
            allocations     = a.allocations
        else:
            a = _StructuralAnalyzer(code, lang)
            max_loop_depth  = a.max_loop_depth
            recursion_type  = a.recursive_type if a.has_recursion else None
            has_sorting     = a.has_sorting
            has_binary_search = a.has_binary_search
            has_hash_map    = a.has_hash_map
            has_ordered_map = a.has_ordered_map
            has_dp_table    = a.has_dp_table
            has_heap        = a.has_heap
            has_set         = a.has_set
            has_2d_array    = a.has_2d_array
            allocations     = []

        # ── Logarithmic loops: a counter halved/doubled each pass is O(log n), not O(n) ──
        log_factor = False
        if a.has_log_loop:
            log_factor = a.max_nonlog_depth_with_log >= a.max_nonlog_depth
            max_loop_depth = a.max_nonlog_depth

        # ── Derive complexities ───────────────────────────────────────────
        t_best, t_avg, t_worst, t_reason = _derive_time_complexity(
            max_loop_depth, recursion_type,
            has_sorting, has_binary_search, has_heap,
            has_dp_table, has_hash_map, has_ordered_map, has_2d_array,
            code_hint=code, log_factor=log_factor,
        )
        s_best, s_avg, s_worst, s_reason = _derive_space_complexity(
            max_loop_depth, recursion_type,
            has_hash_map, has_dp_table, has_2d_array,
            has_heap, has_set, allocations, code,
            has_ordered_map=has_ordered_map,
        )

        # ── The cost analysis: reads what the code does and replaces the pattern guesses above whenever it can ──
        engine_result = None
        try:
            from app.services.complexity import analyze_source
            engine_result = analyze_source(code, lang, harness_code=full_code)
        except Exception as exc:                       # the pattern rules below are the fallback; never take the endpoint down
            print(f"[ComplexityAnalyzer] cost analysis failed, using the pattern rules: {exc}")
        if engine_result is not None:
            legacy_t_best, legacy_s_best = t_best, s_best
            t_worst, s_worst = engine_result.time.fmt(), engine_result.space.fmt()
            t_avg, s_avg = t_worst, s_worst
            t_best = legacy_t_best if _rank(legacy_t_best) <= _rank(t_worst) else t_worst
            s_best = legacy_s_best if _rank(legacy_s_best) <= _rank(s_worst) else s_worst

        # ── Build explanation ─────────────────────────────────────────────
        detected = []
        if max_loop_depth > 0:
            detected.append(f"{max_loop_depth} level(s) of nested loops")
        if a.has_log_loop:
            detected.append("logarithmic loop (counter halved/doubled each pass)")
        if recursion_type:
            detected.append(f"{recursion_type.replace('_', '-')} recursion")
        if has_sorting:
            detected.append("built-in sort (O(n log n))")
        if has_binary_search:
            detected.append("binary search")
        if has_hash_map:
            detected.append("hash map/dict")
        if has_dp_table:
            detected.append("DP table")
        if has_heap:
            detected.append("heap/priority queue")
        if has_2d_array:
            detected.append("2D array")

        detected_str = ", ".join(detected) if detected else "no loops or recursion"
        analysis = (
            f"The time complexity is {t_worst} because {t_reason.lower()} "
            f"The space complexity is {s_worst} because {s_reason.lower()}"
        )
        if engine_result is not None:
            time_why = "; ".join(engine_result.notes[:5]) if engine_result.notes else (
                "there are no loops over the input and no recursion, so everything runs in constant time"
                if t_worst == "O(1)" else "it comes from the library calls on the input (sorting, searching, copying)")
            space_why = "; ".join(engine_result.space_notes) if engine_result.space_notes else \
                "only a constant number of variables is used"
            analysis = f"The time complexity is {t_worst}: {time_why}. The space complexity is {s_worst}: {space_why}."

        is_optimal, raw_tips = _suggestions(
            t_worst, s_worst,
            has_hash_map, has_dp_table,
            has_sorting, has_binary_search,
            recursion_type, max_loop_depth,
            has_heap, has_2d_array, has_set,
            problem_statement,
        )

        # ── Verdict ───────────────────────────────────────────────────────
        verdict_label, verdict_explanation = _verdict(t_worst, s_worst, is_optimal)

        # ── Structured suggestions with priority tags ─────────────────────
        structured_suggestions = _tag_suggestions(raw_tips)

        # ── Execution stats (from caller if available) ────────────────────
        exec_stats = None
        if execution_time_ms is not None or memory_kb is not None:
            exec_stats = {
                "memory_kb":        memory_kb,
                "cpu_time_ms":      execution_time_ms,
                "wall_time_ms":     execution_time_ms,  # approximation
                "passed_tests":     passed_tests,
                "total_tests":      total_tests,
            }

        # ── Try NVIDIA NIM Nemotron AI for Higher Accuracy ────────────────
        try:
            from app.core.config import get_settings
            settings = get_settings()
            api_key = getattr(settings, "COMPLEXITY_NVIDIA_API_KEY", "")
            if api_key and engine_result is None:          # the AI is only a fallback for code the cost analysis cannot read
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key,
                )
                
                prompt = (
                    f"You are an expert algorithmic complexity analyzer for competitive programming.\n"
                    f"Problem Context:\n{(problem_statement or 'Not provided')[:1200]}\n\n"
                    f"Language: {language}\n"
                    f"Code:\n```{language}\n{(code or '')[:3500]}\n```\n\n"
                    f"Initial AST heuristic scan estimates time complexity: {t_worst}, space complexity: {s_worst}.\n"
                    f"Please perform a rigorous, highly accurate Big-O algorithmic analysis (including best, average, and worst cases for time and space, closed form evaluations, recursion trees, and amortized costs).\n"
                    f"Return ONLY a valid JSON object adhering strictly to the following structure:\n"
                    f"{{\n"
                    f"  \"time_complexity\": {{ \"best\": \"O(...)\", \"average\": \"O(...)\", \"worst\": \"O(...)\" }},\n"
                    f"  \"space_complexity\": {{ \"best\": \"O(...)\", \"average\": \"O(...)\", \"worst\": \"O(...)\" }},\n"
                    f"  \"analysis\": \"Detailed professional algorithmic explanation of why the time and space complexities hold.\",\n"
                    f"  \"structured_suggestions\": [\n"
                    f"    {{ \"priority\": \"high\", \"tag\": \"optimization\", \"text\": \"Actionable advice to improve time or space efficiency.\" }}\n"
                    f"  ],\n"
                    f"  \"is_optimal\": true or false,\n"
                    f"  \"verdict\": \"optimal\" or \"suboptimal\" or \"needs_improvement\",\n"
                    f"  \"verdict_explanation\": \"Why this solution is optimal or how it can be improved.\",\n"
                    f"  \"detected_patterns\": [\"hash map\", \"nested loop\", \"recursion\"]\n"
                    f"}}"
                )
                
                completion = await client.chat.completions.create(
                    model="nvidia/nemotron-3-ultra-550b-a55b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    top_p=0.95,
                    max_tokens=4096,
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 4096},
                    stream=True,
                )
                
                content_pieces = []
                async for chunk in completion:
                    if not chunk.choices:
                        continue
                    if chunk.choices[0].delta.content is not None:
                        content_pieces.append(chunk.choices[0].delta.content)
                        
                raw_content = "".join(content_pieces).strip()
                if raw_content:
                    import json
                    clean_json = raw_content
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json:
                        clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    else:
                        start_idx = clean_json.find("{")
                        end_idx = clean_json.rfind("}")
                        if start_idx != -1 and end_idx != -1:
                            clean_json = clean_json[start_idx:end_idx+1]
                            
                    ai_data = json.loads(clean_json)
                    
                    t_comp = ai_data.get("time_complexity", {"best": t_best, "average": t_avg, "worst": t_worst})
                    s_comp = ai_data.get("space_complexity", {"best": s_best, "average": s_avg, "worst": s_worst})
                    ai_analysis = ai_data.get("analysis", analysis)
                    ai_struct_sugg = ai_data.get("structured_suggestions", structured_suggestions)
                    ai_sugg = [s.get("text", "") if isinstance(s, dict) else str(s) for s in ai_struct_sugg]
                    ai_optimal = ai_data.get("is_optimal", is_optimal)
                    ai_verdict = ai_data.get("verdict", verdict_label)
                    ai_verdict_exp = ai_data.get("verdict_explanation", verdict_explanation)
                    ai_detected = ai_data.get("detected_patterns", detected)
                    
                    return {
                        "time_complexity": t_comp,
                        "space_complexity": s_comp,
                        "analysis": ai_analysis,
                        "suggestions": ai_sugg,
                        "structured_suggestions": ai_struct_sugg,
                        "is_optimal": ai_optimal,
                        "verdict": ai_verdict,
                        "verdict_explanation": ai_verdict_exp,
                        "detected_patterns": ai_detected,
                        "execution_stats": exec_stats,
                    }
        except Exception as e:
            print(f"[ComplexityAnalyzer] NVIDIA Nemotron API error (falling back to AST): {e}")

        return {
            "time_complexity": {
                "best":    t_best,
                "average": t_avg,
                "worst":   t_worst,
            },
            "space_complexity": {
                "best":    s_best,
                "average": s_avg,
                "worst":   s_worst,
            },
            "analysis":           analysis,
            "suggestions":        raw_tips,          # kept for backward compat
            "structured_suggestions": structured_suggestions,
            "is_optimal":         is_optimal,
            "verdict":            verdict_label,
            "verdict_explanation": verdict_explanation,
            "detected_patterns":  detected,
            "execution_stats":    exec_stats,
            "engine":             "cost-model" if engine_result is not None else "pattern-rules",
            "confidence":         engine_result.confidence if engine_result is not None else "low",
            "confidence_notes":   list(engine_result.uncertain) if engine_result is not None else
                                  ["The code could not be analyzed structurally; this is a pattern-based estimate."],
            "derivation":         (list(engine_result.notes) + list(engine_result.space_notes)) if engine_result is not None else [],
        }


# Global instance
complexity_analyzer = ComplexityAnalyzer()
