"""The cost analysis: how long a piece of code runs and how much memory it needs, as a function of its input size n.

It works on the IR (see ir.py) and keeps, for every value, a coarse abstraction: what kind of thing it is and how large its
number / length is in terms of n. From that it derives

  * how often each loop runs (counting loops, loops that halve/double a counter, binary search, Euclid, sqrt loops, pointers
    and stacks that make an inner loop amortised, queue-draining loops),
  * what each library call costs on its receiver,
  * recursion: subtract-and-conquer, divide-and-conquer (master theorem), memoisation, tree/graph traversals,
  * memory: allocations, containers that grow, recursion depth.

Where it cannot tell, it assumes the worst reasonable thing and records why, so the answer comes with a confidence.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field, fields
from fractions import Fraction
from typing import Any, Dict, List, Optional, Set, Tuple

from . import ir
from . import library as lib
from .mag import EXP, LOG, N, ONE, Mag, maxm, minm, product

FUNC_TAG = -1
MAX_STEPS = 400_000


class Budget(Exception):
    """The analysis took too many steps; the caller falls back to a simpler analyzer."""


# ═══ abstract values ═══════════════════════════════════════════════════════

@dataclass
class AVal:
    kind: str = "unknown"          # num list str dict set deque heap omap oset tuple func none range unknown
    mag: Mag = ONE                 # for numbers: how large the value is
    size: Mag = ONE                # for collections and strings: how many elements
    elem: Optional["AVal"] = None  # what the elements look like
    parts: Optional[list] = None   # the members of a tuple
    fn: Any = None                 # for functions: the FuncDef / Lambda
    ragged: bool = False           # derived from the element being processed (graph[u] for the u just popped)


COLLECTIONS = {"list", "str", "dict", "set", "deque", "heap", "omap", "oset", "tuple", "range"}


def num(mag: Mag = ONE) -> AVal:
    return AVal("num", mag=mag)


def coll(kind: str, size: Mag, elem: Optional[AVal] = None) -> AVal:
    return AVal(kind, mag=ONE, size=size, elem=elem)


def unknown_n() -> AVal:
    return AVal("unknown", mag=N, size=N)


def join(a: Optional[AVal], b: Optional[AVal]) -> Optional[AVal]:
    if a is None:
        return b
    if b is None:
        return a
    if a.kind == b.kind:
        kind = a.kind
    elif a.kind == "unknown":
        kind = b.kind
    elif b.kind == "unknown":
        kind = a.kind
    else:
        kind = "unknown"
    return AVal(kind, maxm(a.mag, b.mag), maxm(a.size, b.size), join(a.elem, b.elem), a.parts, a.fn or b.fn, a.ragged and b.ragged)


def total_size(v: AVal, depth: int = 0) -> Mag:
    """How many cells a (possibly nested) collection holds."""
    if v.kind not in COLLECTIONS or depth > 3:
        return ONE
    inner = total_size(v.elem, depth + 1) if v.elem is not None and v.elem.kind in COLLECTIONS and v.elem.kind != "str" else ONE
    return v.size * inner


_NUMERIC = {"int", "long", "longlong", "short", "float", "double", "bool", "boolean", "size_t", "char", "byte", "number",
            "integer", "ll", "i32", "i64", "u32", "u64", "int64", "int32", "ssize_t", "uint", "ulong", "unsignedint", "bigint",
            "decimal", "complex", "uint64_t", "int64_t", "int32_t", "uint32_t", "auto"}


def _split_top(s: str) -> List[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "<[(":
            depth += 1
        elif ch in ">])":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def kind_for(name: str, lang: str) -> Optional[str]:
    name = name.lower()
    if name in ("map", "set", "multimap", "multiset"):
        if lang in ("c", "cpp", "c++"):
            return "omap" if "map" in name else "oset"
        return "dict" if "map" in name else "set"
    return lib.COLLECTION_KIND.get(name)


def _element(t: str, depth: int, lang: str) -> AVal:
    """An element of a list: a string in a list is a word (the list holds n of them), not a second string as long as the input."""
    v = val_from_type(t, depth, lang)
    if v.kind == "str" and v.size == N:
        return coll("str", ONE)
    return v


def val_from_type(t: Optional[str], depth: int = 0, lang: str = "python") -> AVal:
    """The abstraction of a parameter or declaration from the type as written."""
    if not t or depth > 4:
        return unknown_n()
    s = re.sub(r"\b(const|static|final|unsigned|signed|volatile|struct|mut|register|restrict)\b", " ", t).replace("&", " ")
    compact = re.sub(r"\s+", "", s)
    low = compact.lower()
    if not compact:
        return unknown_n()
    if compact.endswith("[]"):
        return coll("list", N, _element(compact[:-2], depth + 1, lang))
    if compact.endswith("*"):
        base = compact[:-1]
        if base.lower() == "char":
            return coll("str", N)
        return coll("list", N, _element(base, depth + 1, lang))
    m = re.match(r"([A-Za-z_:][\w:\.]*)<(.*)>$", compact) or re.match(r"([A-Za-z_][\w\.]*)\[(.*)\]$", compact)
    if m:
        name = m.group(1).split("::")[-1].split(".")[-1].lower()
        inner = _split_top(m.group(2))
        kind = kind_for(name, lang)
        if kind in ("list", "deque", "set", "heap", "oset"):
            return coll(kind, N, _element(inner[0], depth + 1, lang))
        if kind in ("dict", "omap"):
            return coll(kind, N, _element(inner[-1], depth + 1, lang))
        if kind:
            return coll(kind, N)
        return unknown_n()
    base = low.split("::")[-1].split(".")[-1]
    if base in ("string", "str", "string_view", "stringbuilder", "stringbuffer"):
        return coll("str", N)
    if base in _NUMERIC:
        return num(N)
    kind = kind_for(base, lang)
    if kind:
        return coll(kind, N)
    return unknown_n()


class Env:
    __slots__ = ("vars", "parent")

    def __init__(self, parent: Optional["Env"] = None, vars: Optional[dict] = None):
        self.vars = vars if vars is not None else {}
        self.parent = parent

    def get(self, name: str) -> Optional[AVal]:
        e: Optional[Env] = self
        while e is not None:
            if name in e.vars:
                return e.vars[name]
            e = e.parent
        return None

    def set(self, name: str, val: AVal) -> None:
        self.vars[name] = val

    def copy(self) -> "Env":
        return Env(self.parent, dict(self.vars))


def join_envs(base: Env, others: List[Env]) -> None:
    keys = set()
    for o in others:
        keys |= set(o.vars)
    for k in keys:
        cur = None
        for o in others:
            if k in o.vars:
                cur = join(cur, o.vars[k])
        old = base.vars.get(k)
        base.vars[k] = join(old, cur) if old is not None else cur


# ═══ IR helpers ════════════════════════════════════════════════════════════

def iter_nodes(x, skip_funcs: bool = True):
    if isinstance(x, ir.Node):
        yield x
        if skip_funcs and isinstance(x, (ir.FuncDef, ir.Lambda)):
            return
        for f in fields(x):
            if f.name == "line":
                continue
            yield from iter_nodes(getattr(x, f.name), skip_funcs)
    elif isinstance(x, (list, tuple)):
        for y in x:
            yield from iter_nodes(y, skip_funcs)
    elif isinstance(x, dict):
        for y in x.values():
            yield from iter_nodes(y, skip_funcs)


def names_in(e) -> Set[str]:
    return {n.id for n in iter_nodes(e) if isinstance(n, ir.Name)}


def const_val(e):
    if isinstance(e, ir.Const) and e.kind in ("int", "float", "bool"):
        return e.value
    if isinstance(e, ir.UnOp) and e.op == "-" and isinstance(e.operand, ir.Const) and e.operand.kind in ("int", "float"):
        return -e.operand.value
    return None


def guard_name(test) -> Optional[str]:
    """The container a test like `x not in seen`, `not seen[x]`, `seen[x] == 0` asks about."""
    for c in flatten_and(test):
        if isinstance(c, ir.BinOp) and c.op == "notin" and isinstance(c.right, ir.Name):
            return c.right.id
        if isinstance(c, ir.UnOp) and c.op == "not" and isinstance(c.operand, ir.Index) and isinstance(c.operand.base, ir.Name):
            return c.operand.base.id
        if isinstance(c, ir.BinOp) and c.op == "==" and isinstance(c.left, ir.Index) and isinstance(c.left.base, ir.Name) \
                and isinstance(c.right, ir.Const) and (c.right.kind in ("none", "bool") or const_val(c.right) in (0, -1)):
            return c.left.base.id
    return None


def kw_const(e, name: str):
    """The constant value of the keyword argument `name` of a call, if it has one."""
    a = (getattr(e, "kwargs", None) or {}).get(name)
    return const_val(a) if a is not None else None


def is_const_expr(e) -> bool:
    if isinstance(e, ir.Const):
        return True
    if isinstance(e, ir.UnOp):
        return is_const_expr(e.operand)
    if isinstance(e, ir.BinOp):
        return is_const_expr(e.left) and is_const_expr(e.right)
    return False


def is_true(e) -> bool:
    return isinstance(e, ir.Const) and e.kind in ("bool", "int") and bool(e.value)


def show(e, limit: int = 36) -> str:
    def go(x) -> str:
        if isinstance(x, ir.Name):
            return x.id
        if isinstance(x, ir.Const):
            return repr(x.value) if x.kind == "str" else str(x.value)
        if isinstance(x, ir.BinOp):
            return f"{go(x.left)} {x.op} {go(x.right)}"
        if isinstance(x, ir.UnOp):
            return f"{x.op} {go(x.operand)}"
        if isinstance(x, ir.Call):
            inner = ", ".join(go(a) for a in x.args)
            return f"{go(x.recv) + '.' if x.recv is not None else ''}{x.fn}({inner})"
        if isinstance(x, ir.Index):
            return f"{go(x.base)}[{go(x.index)}]"
        if isinstance(x, ir.Attr):
            return f"{go(x.base)}.{x.name}"
        if isinstance(x, ir.Slice):
            return f"{go(x.base)}[{go(x.lo) if x.lo is not None else ''}:{go(x.hi) if x.hi is not None else ''}]"
        return "…"
    out = go(e)
    return out if len(out) <= limit else out[: limit - 1] + "…"


_NEG = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}


def negate(e):
    if isinstance(e, ir.BinOp) and e.op in _NEG:
        return ir.BinOp(op=_NEG[e.op], left=e.left, right=e.right)
    if isinstance(e, ir.UnOp) and e.op == "not":
        return e.operand
    return ir.UnOp(op="not", operand=e)


def flatten_and(e) -> list:
    if isinstance(e, ir.BinOp) and e.op == "and":
        return flatten_and(e.left) + flatten_and(e.right)
    return [e]


def unwrap_int(e):
    while isinstance(e, ir.Call) and e.fn.lower() in ("int", "floor", "trunc", "round", "long", "ceil") and len(e.args) == 1 and e.recv is None:
        e = e.args[0]
    return e


def is_midpoint(e) -> bool:
    e = unwrap_int(e)
    if isinstance(e, ir.BinOp):
        if e.op in ("//", "/", ">>"):
            c = const_val(e.right)
            if c is not None and (c >= 1 if e.op == ">>" else c >= 2):
                return len(names_in(e.left)) >= 2
        if e.op in ("+", "-"):
            return is_midpoint(e.left) or is_midpoint(e.right)
    return False


@dataclass
class Upd:
    kind: str
    stmt: Any


def classify_update(v: str, value, op: Optional[str], mids: Set[str]) -> str:
    cv = const_val(value)
    if op:
        if op == "+" and isinstance(value, ir.Name) and value.id == v:
            return "MULT"
        if op in ("+", "-"):
            return "ADD"
        if op == "*":
            return "MULT" if cv is not None and cv >= 2 else "OTHER"
        if op in ("//", "/", ">>"):
            return "DIV" if cv is not None and (cv >= 1 if op == ">>" else cv >= 2) else "OTHER"
        if op == "<<":
            return "MULT" if cv is not None and cv >= 1 else "OTHER"
        if op == "&" and isinstance(value, ir.BinOp) and value.op == "-" and isinstance(value.left, ir.Name) and value.left.id == v:
            return "BITCLEAR"
        return "OTHER"
    value = unwrap_int(value)
    if isinstance(value, ir.Cond):
        a, b = classify_update(v, value.a, None, mids), classify_update(v, value.b, None, mids)
        return a if a == b else ("ADD" if {a, b} <= {"ADD", "OTHER"} and "ADD" in (a, b) else "OTHER")
    if isinstance(value, ir.BinOp):
        l, r = value.left, value.right
        is_l = isinstance(l, ir.Name) and l.id == v
        is_r = isinstance(r, ir.Name) and r.id == v
        if value.op == "+" and is_l and is_r:
            return "MULT"
        if value.op in ("+", "-"):
            if is_l or is_r:
                return "ADD"
            # v = 2*v + 1 : strip the additive constant and look at the rest
            if const_val(r) is not None and v in names_in(l):
                inner = classify_update(v, l, None, mids)
                if inner != "OTHER":
                    return inner
        if value.op == "*" and ((is_l and (const_val(r) or 0) >= 2) or (is_r and (const_val(l) or 0) >= 2)):
            return "MULT"
        if value.op in ("//", "/", ">>") and is_l:
            c = const_val(r)
            if c is not None and (c >= 1 if value.op == ">>" else c >= 2):
                return "DIV"
        if value.op == "<<" and is_l and const_val(r) is not None:
            return "MULT"
        if value.op == "%" and is_r:
            return "EUCLID"
        if value.op == "&" and is_l and isinstance(r, ir.BinOp) and r.op == "-" and isinstance(r.left, ir.Name) and r.left.id == v:
            return "BITCLEAR"
    if (names_in(value) & mids) or is_midpoint(value):
        return "BISECT"
    if isinstance(value, ir.Index) and v in names_in(value.index):
        return "CHASE"
    if isinstance(value, ir.Attr) and v in names_in(value.base):
        return "CHASE"
    return "OTHER"


def find_remainders(stmts) -> Dict[str, Set[str]]:
    """temp -> the names it is a remainder modulo (t = a % b)."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for n in iter_nodes(stmts):
        if isinstance(n, ir.Assign) and n.op is None and len(n.targets) == 1 and isinstance(n.targets[0], ir.Name):
            v = unwrap_int(n.value)
            if isinstance(v, ir.BinOp) and v.op == "%" and isinstance(v.right, ir.Name):
                out[n.targets[0].id].add(v.right.id)
    return out


def collect_updates(stmts, mids: Set[str]) -> Dict[str, List[Upd]]:
    out: Dict[str, List[Upd]] = defaultdict(list)
    rems = find_remainders(stmts)
    for n in iter_nodes(stmts):
        if isinstance(n, ir.Assign):
            for t in n.targets:
                if isinstance(t, ir.Name):
                    kind = classify_update(t.id, n.value, n.op, mids)
                    if kind == "OTHER" and isinstance(n.value, ir.Name) and t.id in rems.get(n.value.id, ()):
                        kind = "EUCLID"
                    out[t.id].append(Upd(kind, n))
                elif isinstance(t, ir.Lit) and t.kind == "tuple":
                    if isinstance(n.value, ir.Lit) and n.value.kind == "tuple" and len(n.value.elts) == len(t.elts):
                        for tt, vv in zip(t.elts, n.value.elts):
                            if isinstance(tt, ir.Name):
                                out[tt.id].append(Upd(classify_update(tt.id, vv, n.op, mids), n))
                    else:
                        for tt in t.elts:
                            if isinstance(tt, ir.Name):
                                out[tt.id].append(Upd("OTHER", n))
        elif isinstance(n, (ir.ForRange, ir.ForEach)):
            for nm in names_in(n.var):
                out[nm].append(Upd("OTHER", n))
    return out


def is_half(e) -> bool:
    e = unwrap_int(e)
    if isinstance(e, ir.BinOp) and e.op in ("//", "/", ">>"):
        c = const_val(e.right)
        return c is not None and (c >= 1 if e.op == ">>" else c >= 2)
    return False


def find_halves(stmts) -> Set[str]:
    out = set()
    for n in iter_nodes(stmts):
        if isinstance(n, ir.Assign) and n.op is None and is_half(n.value):
            for t in n.targets:
                if isinstance(t, ir.Name):
                    out.add(t.id)
    return out


def find_midpoints(stmts) -> Set[str]:
    mids = set()
    for n in iter_nodes(stmts):
        if isinstance(n, ir.Assign) and n.op is None and is_midpoint(n.value):
            for t in n.targets:
                if isinstance(t, ir.Name):
                    mids.add(t.id)
    return mids


def non_empty_container(e) -> Optional[str]:
    """`stack`, `len(stack) > 0`, `!q.empty()`, `q.size() != 0`, `q.length`: the container whose emptiness ends the loop."""
    if isinstance(e, ir.Name):
        return e.id
    if isinstance(e, ir.UnOp) and e.op == "not":
        inner = e.operand
        if isinstance(inner, ir.Call) and inner.fn.lower() in ("empty", "isempty") and isinstance(inner.recv, ir.Name):
            return inner.recv.id
        return None
    if isinstance(e, ir.Attr) and e.name.lower() in ("length", "size") and isinstance(e.base, ir.Name):
        return e.base.id
    if isinstance(e, ir.Call) and e.fn.lower() in ("size", "length", "len") and not e.args and isinstance(e.recv, ir.Name):
        return e.recv.id
    if isinstance(e, ir.BinOp) and e.op in (">", "!=", ">="):
        c = const_val(e.right)
        if c is not None and ((e.op == ">" and c == 0) or (e.op == "!=" and c == 0) or (e.op == ">=" and c == 1)):
            lhs = e.left
            if isinstance(lhs, ir.Call) and lhs.fn.lower() in ("len", "size", "length"):
                if lhs.recv is None and lhs.args and isinstance(lhs.args[0], ir.Name):
                    return lhs.args[0].id
                if isinstance(lhs.recv, ir.Name):
                    return lhs.recv.id
            if isinstance(lhs, ir.Attr) and lhs.name.lower() in ("length", "size") and isinstance(lhs.base, ir.Name):
                return lhs.base.id
    return None


def removal_in(stmts, c: str) -> bool:
    for n in iter_nodes(stmts):
        if isinstance(n, ir.Call) and n.fn.lower() in lib.SHRINK:
            if isinstance(n.recv, ir.Name) and n.recv.id == c:
                return True
            if n.recv is None and n.args and isinstance(n.args[0], ir.Name) and n.args[0].id == c:
                return True
    return False


def collect_grown(stmts, in_loop: bool = False, out: Optional[Set[str]] = None) -> Set[str]:
    """Names of containers the code adds to from inside a loop (their size grows with the input)."""
    if out is None:
        out = set()
    for s in stmts if isinstance(stmts, list) else [stmts]:
        if isinstance(s, (ir.ForRange, ir.ForEach, ir.While)):
            collect_grown(s.body + getattr(s, "post", []), True, out)
            continue
        if isinstance(s, ir.If):
            collect_grown(s.body, in_loop, out)
            collect_grown(s.orelse, in_loop, out)
            continue
        if isinstance(s, ir.Block):
            collect_grown(s.body, in_loop, out)
            continue
        if in_loop:
            for n in iter_nodes(s):
                if isinstance(n, ir.Call) and n.fn.lower() in lib.GROW:
                    if isinstance(n.recv, ir.Name):
                        out.add(n.recv.id)
                    elif n.recv is None and n.args and isinstance(n.args[0], ir.Name):
                        out.add(n.args[0].id)
                elif isinstance(n, ir.Assign):
                    for t in n.targets:
                        if isinstance(t, ir.Name) and n.op in ("+", "|"):
                            out.add(t.id)
                        elif isinstance(t, ir.Name) and n.op is None and isinstance(n.value, ir.BinOp) and n.value.op in ("+", "|")                                 and isinstance(n.value.left, ir.Name) and n.value.left.id == t.id:
                            out.add(t.id)                      # s = s + x, s = s | x
                        elif isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and n.op is None:
                            out.add(t.base.id)
    return out


def grows_in_loop(stmts, c: str, in_loop: bool = False) -> bool:
    """Does the function add to container c from inside some loop?"""
    for s in stmts if isinstance(stmts, list) else [stmts]:
        if isinstance(s, (ir.ForRange, ir.ForEach, ir.While)):
            if grows_in_loop(s.body + getattr(s, "post", []), c, True):
                return True
            continue
        if isinstance(s, ir.If):
            if grows_in_loop(s.body, c, in_loop) or grows_in_loop(s.orelse, c, in_loop):
                return True
            continue
        if isinstance(s, ir.Block):
            if grows_in_loop(s.body, c, in_loop):
                return True
            continue
        if in_loop:
            for n in iter_nodes(s):
                if isinstance(n, ir.Call) and n.fn.lower() in lib.GROW:
                    if isinstance(n.recv, ir.Name) and n.recv.id == c:
                        return True
                    if n.recv is None and n.args and isinstance(n.args[0], ir.Name) and n.args[0].id == c:
                        return True
                if isinstance(n, ir.Assign) and n.op == "+" and any(isinstance(t, ir.Name) and t.id == c for t in n.targets):
                    return True
    return False


# ═══ results ═══════════════════════════════════════════════════════════════

RC = Tuple[int, Mag]          # (k, m): k * m recursive calls per invocation


def rc_add(a: RC, b: RC) -> RC:
    if a[0] == 0:
        return b
    if b[0] == 0:
        return a
    if a[1] == b[1]:
        return (a[0] + b[0], a[1])
    return b if a[1] < b[1] else a


def rc_max(a: RC, b: RC) -> RC:
    if a[0] == 0:
        return b
    if b[0] == 0:
        return a
    return b if (a[1], a[0]) < (b[1], b[0]) else a


@dataclass
class Res:
    t: Mag = ONE
    tags: Dict[int, Mag] = field(default_factory=dict)
    rc: RC = (0, ONE)
    once: Mag = ONE         # work in a branch that ends the loop (`break` / `return`): it runs at most once per run of the loop


def merge_tags(a: Dict[int, Mag], b: Dict[int, Mag]) -> Dict[int, Mag]:
    out = dict(a)
    for k, v in b.items():
        out[k] = maxm(out[k], v) if k in out else v
    return out


def res_seq(a: Res, b: Res) -> Res:
    return Res(maxm(a.t, b.t), merge_tags(a.tags, b.tags), rc_add(a.rc, b.rc), maxm(a.once, b.once))


def res_alt(a: Res, b: Res) -> Res:
    return Res(maxm(a.t, b.t), merge_tags(a.tags, b.tags), rc_max(a.rc, b.rc), maxm(a.once, b.once))


@dataclass
class Bound:
    mag: Mag
    kind: str                       # pointer | drain | log | sqrt | unknown | range | each
    pv: Set[str] = field(default_factory=set)
    drain: Set[str] = field(default_factory=set)
    note: str = ""
    counters: Dict[str, Mag] = field(default_factory=dict)     # counter -> how large it gets (its own range)


@dataclass
class LoopEntry:
    id: int
    node: Any
    iters: Mag
    total: Mag = ONE
    scope: Optional[List[int]] = None     # loops this loop's total already covers (amortisation)
    vars: Set[str] = field(default_factory=set)   # the counters this loop moves


@dataclass
class FuncResult:
    time: Mag
    space: Mag
    ret: Optional[AVal]
    memo: Optional[str] = None


@dataclass
class Frame:
    fdef: Any
    params: List[str]
    entry_args: List[AVal]
    loops: List[LoopEntry] = field(default_factory=list)
    rc_acc: RC = (0, ONE)
    allocs: List[Mag] = field(default_factory=list)
    growth: Dict[str, List[Mag]] = field(default_factory=lambda: defaultdict(list))
    defdepth: Dict[str, int] = field(default_factory=dict)
    sites: List[str] = field(default_factory=list)
    memo: Optional[str] = None            # None | 'cache' | 'visit'
    popped: Set[str] = field(default_factory=set)
    rets: Optional[AVal] = None
    mids: Set[str] = field(default_factory=set)
    halves: Set[str] = field(default_factory=set)
    state_params: Set[str] = field(default_factory=set)
    once: List[Mag] = field(default_factory=list)
    grown: Optional[Set[str]] = None
    amort_fill: Dict[str, List[int]] = field(default_factory=dict)
    guards: List[str] = field(default_factory=list)   # the `seen` containers of the `if x not in seen: seen.add(x) ...` branches we are inside


@dataclass
class EngineResult:
    time: Mag
    space: Mag
    notes: List[str]
    uncertain: List[str]
    confidence: str
    space_notes: List[str] = field(default_factory=list)


# ═══ the engine ════════════════════════════════════════════════════════════

class Engine:
    def __init__(self, module: ir.Module, language: str, hints: Optional[Dict[str, List[Optional[str]]]] = None):
        self.module = module
        self.lang = language.lower()
        self.hints = hints or {}          # function name -> the type of each parameter, read from the harness
        self.funcs: Dict[str, ir.FuncDef] = {}
        self.fr: Optional[Frame] = None
        self.active: Dict[int, Frame] = {}
        self.cache: Dict[tuple, FuncResult] = {}
        self.loop_ids = 0
        self.steps = 0
        self.quiet_depth = 0
        self.notes: List[Tuple[int, str]] = []
        self.snotes: List[Tuple[Mag, int, str]] = []
        self.unc: List[str] = []
        self.line = 0

    # ── bookkeeping ───────────────────────────────────────────────────────
    def tick(self):
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise Budget()

    @property
    def quiet(self) -> bool:
        return self.quiet_depth > 0

    def note(self, line: int, text: str):
        if not self.quiet and (line, text) not in self.notes:
            self.notes.append((line, text))

    def doubt(self, line: int, text: str):
        if not self.quiet:
            msg = f"line {line}: {text}" if line else text
            if msg not in self.unc:
                self.unc.append(msg)

    def alloc(self, mag: Mag):
        if not self.quiet and self.fr is not None and not mag.is_const:
            self.fr.allocs.append(mag)
            self.snotes.append((mag, self.line, f"allocates about {mag.fmt()[2:-1]} elements"))

    def multiplicity(self, from_depth: int = 0) -> Mag:
        out = ONE
        skip: Set[int] = set()
        for entry in reversed(self.fr.loops[from_depth:]):
            if entry.id in skip:
                continue
            if entry.scope is not None:
                out = out * entry.total
                skip |= set(entry.scope)
            else:
                out = out * entry.iters
        return out

    def grow(self, key: str, inc: Mag):
        if self.quiet or self.fr is None:
            return
        for entry in self.fr.loops[self.fr.defdepth.get(key, 0):]:
            if entry.scope:
                self.fr.amort_fill[key] = list(entry.scope)         # filled by a loop whose total is bounded over the outer loop
        mult = self.multiplicity(self.fr.defdepth.get(key, 0))
        total = mult * inc
        if self.fr.guards and inc.is_const:
            seen = self.fr.guards[-1]
            if N < total:
                total = N                                           # only added for things not seen before: at most n of them
            # `seen` lives across these loops, so over all of them this container receives at most n things
            self.fr.amort_fill[key] = [e.id for e in self.fr.loops[self.fr.defdepth.get(seen, 0):]]
        self.fr.growth[key].append(total)
        if not total.is_const:
            self.snotes.append((total, self.line, f"`{key}` grows to about {total.fmt()[2:-1]} elements"))

    # ── entry ─────────────────────────────────────────────────────────────
    def run(self) -> EngineResult:
        defs = [s for s in self.module.body if isinstance(s, ir.FuncDef)]
        for d in defs:
            self.funcs[d.name] = d
        called: Set[str] = set()
        for d in defs:
            for n in iter_nodes(d.body, skip_funcs=False):
                if isinstance(n, ir.Call) and n.fn in self.funcs and n.fn != d.name:
                    called.add(n.fn)
        roots = [d for d in defs if d.name not in called] or defs
        if not defs:
            pseudo = ir.FuncDef(name="<module>", params=[], body=self.module.body)
            roots = [pseudo]
        time, space = ONE, ONE
        for d in roots:
            hint = self.hints.get(d.name) or []
            args = [val_from_type(t or (hint[i] if i < len(hint) else None), 0, self.lang) for i, (_, t) in enumerate(d.params)]
            r = self.call_function(d, args, [], Env())
            time, space = maxm(time, r.time), maxm(space, r.space)
        notes = [f"line {ln}: {txt}" for ln, txt in sorted(self.notes)]
        confidence = "high" if not self.unc else "medium" if len(self.unc) <= 2 else "low"
        seen_lines, space_notes = set(), []
        for mag, ln, txt in sorted(self.snotes, key=lambda x: x[0].key(), reverse=True):
            if ln not in seen_lines and len(space_notes) < 3:
                seen_lines.add(ln)
                space_notes.append(f"line {ln}: {txt}")
        return EngineResult(time, space, notes, self.unc, confidence, space_notes)

    # ── functions and recursion ───────────────────────────────────────────
    def call_function(self, fdef, arg_vals: List[AVal], arg_exprs: list, parent: Env) -> FuncResult:
        key = (id(fdef), tuple((a.kind, a.mag.key(), a.size.key()) for a in arg_vals))
        if key in self.cache:
            return self.cache[key]
        env = Env(parent)
        names = [p[0] for p in fdef.params]
        for i, (pname, ptype) in enumerate(fdef.params):
            if i < len(arg_vals):
                v = arg_vals[i]
                if ptype and v.kind == "unknown":
                    v = val_from_type(ptype, 0, self.lang)
            else:
                v = val_from_type(ptype, 0, self.lang)
            env.set(pname, v)
        fr = Frame(fdef=fdef, params=names, entry_args=[env.get(n) for n in names])
        fr.mids = find_midpoints(fdef.body)
        fr.halves = find_halves(fdef.body)
        fr.memo = self.detect_memo(fdef)
        if fr.memo:
            fr.state_params = set(names)
        outer, self.fr = self.fr, fr
        self.active[id(fdef)] = fr
        try:
            res = self.exec_block(fdef.body, env)
        finally:
            del self.active[id(fdef)]
            self.fr = outer
        time = maxm(res.t, res.once, *res.tags.values()) if res.tags else maxm(res.t, res.once)
        if fr.once:
            time = maxm(time, *fr.once)
        growth = [maxm(*v) for v in fr.growth.values() if v]
        space = maxm(ONE, *fr.allocs, *growth) if (fr.allocs or growth) else ONE
        if fr.sites:
            time, space = self.solve_recurrence(fr, res, time, space)
        out = FuncResult(time, space, fr.rets, fr.memo)
        if not fr.sites:
            self.cache[key] = out
        return out

    def detect_memo(self, fdef) -> Optional[str]:
        if any(d in ("lru_cache", "cache", "memoize") for d in fdef.decorators):
            return "cache"
        if not any(isinstance(n, ir.Call) and n.fn == fdef.name for n in iter_nodes(fdef.body)):
            return None
        rec_names: Set[str] = set()
        for n in iter_nodes(fdef.body):
            if isinstance(n, ir.Assign):
                if any(isinstance(m, ir.Call) and m.fn == fdef.name for m in iter_nodes(n.value)):
                    for t in n.targets:
                        rec_names |= names_in(t)

        def stored(value):
            if isinstance(value, ir.Const):
                return "visit"
            if any(isinstance(m, ir.Call) and m.fn == fdef.name for m in iter_nodes(value)):
                return "cache"
            if isinstance(value, ir.Name) and value.id in rec_names:
                return "cache"
            return None
        local_fresh: Set[str] = set()
        for n in iter_nodes(fdef.body):
            if isinstance(n, ir.Assign):
                for t in n.targets:
                    if isinstance(t, ir.Name) and isinstance(n.value, (ir.Lit, ir.Comp, ir.New)):
                        local_fresh.add(t.id)
                    elif isinstance(t, ir.Name) and isinstance(n.value, ir.Call) and n.value.fn.lower() in lib.COLLECTION_KIND:
                        local_fresh.add(t.id)
        written: Dict[str, Any] = {}
        read: Set[str] = set()
        for n in iter_nodes(fdef.body):
            if isinstance(n, ir.Assign):
                for t in n.targets:
                    if isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and t.base.id not in local_fresh and stored(n.value):
                        written[t.base.id] = n.value
                    if isinstance(t, ir.Index) and isinstance(t.base, ir.Index) and isinstance(t.base.base, ir.Name) \
                            and t.base.base.id not in local_fresh and stored(n.value):
                        written[t.base.base.id] = n.value
            if isinstance(n, ir.Call) and n.fn.lower() in ("add", "insert", "put") and isinstance(n.recv, ir.Name) \
                    and n.recv.id not in local_fresh and n.args:
                written[n.recv.id] = ir.Const(value=True, kind="bool")
            if isinstance(n, ir.Index) and isinstance(n.base, ir.Name):
                read.add(n.base.id)
            if isinstance(n, ir.Index) and isinstance(n.base, ir.Index) and isinstance(n.base.base, ir.Name):
                read.add(n.base.base.id)
            if isinstance(n, ir.BinOp) and n.op in ("in", "notin") and isinstance(n.right, ir.Name):
                read.add(n.right.id)
            if isinstance(n, ir.Call) and n.fn.lower() in ("contains", "has", "get", "count", "containskey", "find") \
                    and isinstance(n.recv, ir.Name):
                read.add(n.recv.id)
        restored = self.restored_marks(fdef)
        for name, value in written.items():
            if name in read and name not in restored:
                return stored(value)
        return None

    def restored_marks(self, fdef) -> Set[str]:
        """Containers the function marks and then un-marks (`used[c] = True` ... `used[c] = False`, `seen.add(x)` ... `seen.remove(x)`):
        that is backtracking, where every branch is explored again, not a memo that makes each state cost once."""
        out: Set[str] = set()
        initial: Dict[str, Any] = {}
        for n in iter_nodes(self.module.body, skip_funcs=False):
            if isinstance(n, ir.Assign) and n.op is None and len(n.targets) == 1 and isinstance(n.targets[0], ir.Name):
                v = n.value
                if isinstance(v, ir.BinOp) and v.op == "*":
                    v = v.left if isinstance(v.left, (ir.Lit, ir.Comp)) else v.right
                if isinstance(v, ir.Lit) and v.kind == "list" and len(v.elts) == 1 and isinstance(v.elts[0], ir.Const):
                    initial[n.targets[0].id] = v.elts[0].value
                elif isinstance(v, ir.Comp) and isinstance(v.elt, ir.Const):
                    initial[n.targets[0].id] = v.elt.value
        values: Dict[str, Set[Any]] = defaultdict(set)
        for n in iter_nodes(fdef.body):
            if isinstance(n, ir.Assign):
                for t in n.targets:
                    if isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and isinstance(n.value, ir.Const):
                        values[t.base.id].add(n.value.value)
            elif isinstance(n, ir.Call) and n.fn.lower() in ("remove", "discard", "pop", "erase") and isinstance(n.recv, ir.Name):
                out.add(n.recv.id)
        for name, vals in values.items():
            if name in initial and initial[name] in vals and len(vals) > 1:
                out.add(name)
        return out

    def site_kind(self, args: list, env: Env, fr: Frame) -> Tuple[str, List[str]]:
        kinds = []
        for i, a in enumerate(args):
            p = fr.params[i] if i < len(fr.params) else None
            kinds.append(self.arg_kind(a, p, env, fr))
        for pref in ("TREE", "SUB", "DIV", "PART"):
            if pref in kinds:
                return pref, kinds
        return "NONE", kinds

    def arg_kind(self, a, p: Optional[str], env: Env, fr: Frame) -> str:
        a = unwrap_int(a)
        if isinstance(a, ir.Const) or (isinstance(a, ir.UnOp) and a.op == "not") or (isinstance(a, ir.BinOp) and a.op in _NEG):
            return "CONST"
        if isinstance(a, ir.Name):
            if a.id == p:
                return "SAME"
            if a.id in fr.mids or a.id in fr.halves:
                return "DIV"
            v = env.get(a.id)
            if v is not None and v.ragged:
                return "TREE"
            return "OTHER"
        if isinstance(a, ir.Attr):
            root = a.base
            while isinstance(root, ir.Attr):
                root = root.base
            if isinstance(root, ir.Name) and root.id in fr.params:
                return "TREE"
            return "OTHER"
        if isinstance(a, ir.Index):
            if names_in(a.index) & fr.state_params or (isinstance(a.base, ir.Name) and a.base.id in fr.params):
                return "TREE"
            return "OTHER"
        if isinstance(a, ir.Comp) and a.kind in ("list", "gen") and a.gens and names_in(a.gens[0].iter) & set(fr.params) and a.gens[0].conds:
            return "PART"
        if isinstance(a, ir.Slice):
            if (names_in(a.hi) | names_in(a.lo)) & (fr.mids | fr.halves) or (a.hi is not None and a.lo is not None) \
                    or (a.hi is not None and isinstance(unwrap_int(a.hi), ir.BinOp) and unwrap_int(a.hi).op in ("//", "/", ">>")):
                return "DIV"
            return "SUB"
        if isinstance(a, ir.BinOp):
            if names_in(a) & (fr.mids | fr.halves):
                return "DIV"
            if a.op == "%" and isinstance(a.right, ir.Name) and a.right.id in fr.params and names_in(a.left) & set(fr.params):
                return "DIV"                      # Euclid: `gcd(y, x % y)`, the numbers at least halve every two steps
            if a.op in ("-", "+") and isinstance(a.left, ir.Name) and (a.left.id == p or a.left.id in fr.params):
                return "SUB"
            if a.op in ("//", "/", ">>") and const_val(a.right) is not None and names_in(a.left) & set(fr.params):
                return "DIV"
            if a.op in ("-", "+") and names_in(a) & set(fr.params):
                return "SUB"
        return "OTHER"

    def solve_recurrence(self, fr: Frame, res: Res, w: Mag, frame_space: Mag) -> Tuple[Mag, Mag]:
        k, m = res.rc if res.rc[0] else (max(1, len(fr.sites)), ONE)
        kinds = {k for k, _ in fr.sites}
        name = getattr(fr.fdef, "name", "the function")
        line = getattr(fr.fdef, "line", 0)
        if "TREE" in kinds or fr.memo == "visit":
            states = N
            if fr.memo is None:
                self.doubt(line, f"`{name}` recurses into the parts of its input (children/neighbours); assuming each part is visited once")
            self.note(line, f"`{name}` visits each element of its input once, doing {w.fmt()[2:-1]} work per visit → {(states * w).fmt()}")
            return states * w, maxm(N, frame_space)
        if fr.memo == "cache":
            varying = self.varying_params(fr)
            states = N.pow(varying) if varying else ONE
            self.note(line, f"`{name}` is memoised: about {states.fmt()[2:-1]} distinct states, {w.fmt()[2:-1]} work each → {(states * w).fmt()}")
            return states * w, maxm(states, N, frame_space)
        if "SUB" in kinds or kinds <= {"NONE"}:
            if "SUB" not in kinds:
                self.doubt(line, f"cannot see how `{name}`'s recursive call gets smaller; assuming it reduces the input by one each time")
            depth = N
            if k >= 2 or not m.is_const:
                self.note(line, f"`{name}` calls itself {'several' if not m.is_const else k} times per call on an input that is only slightly smaller → exponential")
                return EXP, maxm(depth, frame_space * depth if not frame_space.is_const else ONE)
            self.note(line, f"`{name}` calls itself once on an input one step smaller: depth n, {w.fmt()[2:-1]} work per level → {(depth * w).fmt()}")
            return depth * w, depth * frame_space if not frame_space.is_const else depth
        # divide and conquer
        if "PART" in kinds and "DIV" not in kinds:
            self.doubt(line, f"`{name}` recurses on parts of its input whose sizes depend on the data; assuming they split evenly (the average case)")
        a = k if m.is_const else None
        if a is None:
            self.doubt(line, f"`{name}` splits the input but makes a data-dependent number of calls")
            return N * w, N
        e = Fraction(0) if a == 1 else Fraction(str(round(__import__("math").log2(a), 3))).limit_denominator(100)
        kk, pp = w.a, w.b
        if w.exp:
            total = EXP
        elif e < kk:
            total = w
        elif e == kk:
            total = Mag(kk, pp + 1)
        else:
            total = Mag(e, 0)
        self.note(line, f"`{name}` splits the input in half and calls itself {a} time(s), with {w.fmt()[2:-1]} extra work → {total.fmt()}")
        return total, maxm(LOG, frame_space)

    def varying_params(self, fr: Frame) -> int:
        """How many parameters change between a call and its recursive calls (each can take about n values)."""
        count = 0
        for i in range(len(fr.params)):
            if any(i < len(kinds) and kinds[i] not in ("SAME", "CONST") for _, kinds in fr.sites):
                count += 1
        return count

    # ── statements ────────────────────────────────────────────────────────
    def exec_block(self, stmts: list, env: Env) -> Res:
        out = Res()
        for i, s in enumerate(stmts):
            if isinstance(s, ir.If) and not s.orelse and s.body and isinstance(s.body[-1], (ir.Return, ir.Break, ir.Continue)):
                if isinstance(s.body[-1], (ir.Return, ir.Break)):
                    head = self.exec_exit_if(s, env)
                else:
                    head = self.exec_stmt(s, env)
                rest = self.exec_block(stmts[i + 1:], env)
                alt = Res(maxm(head.t, rest.t), merge_tags(head.tags, rest.tags), rc_max(head.rc, rest.rc), maxm(head.once, rest.once))
                return res_seq(out, alt)
            out = res_seq(out, self.exec_stmt(s, env))
        return out

    def marks_what_it_tests(self, s: ir.If) -> int:
        """1 for `if x not in seen:` / `if not seen[x]:` whose body then marks `seen` (`seen.add(x)`, `seen[x] = True`)."""
        name = guard_name(s.test)
        if name is None:
            return 0
        for n in iter_nodes(s.body):
            if isinstance(n, ir.Call) and n.fn.lower() in ("add", "append", "insert", "put") and isinstance(n.recv, ir.Name) and n.recv.id == name:
                return 1
            if isinstance(n, ir.Assign):
                for t in n.targets:
                    if isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and t.base.id == name:
                        return 1
        return 0

    def exec_exit_if(self, s: ir.If, env: Env) -> Res:
        """`if test: ...; break` (or `return`): the test runs every pass, the body at most once per run of the loop."""
        self.tick()
        if getattr(s, "line", 0):
            self.line = s.line
        self.fr.rc_acc = (0, ONE)
        _, tt = self.ev(s.test, env)
        rc_test = self.fr.rc_acc
        e1 = env.copy()
        r1 = self.exec_block(s.body, e1)
        join_envs(env, [e1, env.copy()])
        return Res(tt, dict(r1.tags), rc_add(rc_test, r1.rc), maxm(r1.t, r1.once))

    def exec_stmt(self, s, env: Env) -> Res:
        self.tick()
        if getattr(s, "line", 0):
            self.line = s.line
        t = type(s)
        if t is ir.Assign:
            return self.do_assign(s, env)
        if t is ir.ExprStmt:
            self.fr.rc_acc = (0, ONE)
            _, tm = self.ev(s.expr, env)
            return Res(tm, rc=self.fr.rc_acc)
        if t is ir.If:
            self.fr.rc_acc = (0, ONE)
            _, tt = self.ev(s.test, env)
            rc_test = self.fr.rc_acc
            e1, e2 = env.copy(), env.copy()
            guarded = self.marks_what_it_tests(s)
            if guarded:
                self.fr.guards.append(guard_name(s.test))
            try:
                r1 = self.exec_block(s.body, e1)
            finally:
                if guarded:
                    self.fr.guards.pop()
            r2 = self.exec_block(s.orelse, e2)
            join_envs(env, [e1, e2])
            out = res_alt(r1, r2)
            out.t = maxm(out.t, tt)
            out.rc = rc_add(rc_test, out.rc)
            return out
        if t in (ir.While, ir.ForRange, ir.ForEach):
            return self.do_loop(s, env)
        if t is ir.Return:
            self.fr.rc_acc = (0, ONE)
            if s.value is not None:
                v, tm = self.ev(s.value, env)
                self.fr.rets = join(self.fr.rets, v)
                return Res(tm, rc=self.fr.rc_acc)
            return Res()
        if t is ir.Block:
            return self.exec_block(s.body, env)
        if t is ir.FuncDef:
            self.funcs[s.name] = s
            env.set(s.name, AVal("func", fn=s))
            return Res()
        return Res()

    def do_assign(self, s: ir.Assign, env: Env) -> Res:
        self.fr.rc_acc = (0, ONE)
        value = s.value
        op = s.op
        # `s = s + x` is treated like `s += x`
        if op is None and isinstance(value, ir.BinOp) and value.op == "+" and len(s.targets) == 1 \
                and isinstance(s.targets[0], ir.Name) and isinstance(value.left, ir.Name) and value.left.id == s.targets[0].id:
            old = env.get(s.targets[0].id)
            if old is not None and old.kind in ("str", "list"):
                op, value = "+", value.right
        if op is None and isinstance(value, ir.BinOp) and value.op == "|" and len(s.targets) == 1 \
                and isinstance(s.targets[0], ir.Name) and isinstance(value.left, ir.Name) and value.left.id == s.targets[0].id:
            old = env.get(s.targets[0].id)
            if old is not None and old.kind in ("set", "dict"):
                op, value = "|", value.right
        val, tm = self.ev(value, env)
        if s.decl_type and val.kind in ("unknown", "none"):
            declared = val_from_type(s.decl_type, 0, self.lang)
            if declared.kind in COLLECTIONS and declared.kind != "list":
                val = AVal(declared.kind, size=ONE, elem=declared.elem)
            elif declared.kind == "num":
                val = num(val.mag if val.kind == "num" else ONE)
        if op:
            tgt = s.targets[0]
            old, tt = self.ev(tgt, env) if not isinstance(tgt, ir.Lit) else (unknown_n(), ONE)
            new, tb = self.binop(op, old, val, None, value)
            tm = maxm(tm, tt, tb)
            if op == "+" and old.kind in ("list", "str", "deque"):
                inc = val.size if val.kind in COLLECTIONS else ONE
                key = self.container_key(tgt)
                if key:
                    if old.kind == "str" and self.lang == "java":
                        tm = maxm(tm, old.size)
                    self.grow(key, inc)
                new = AVal(old.kind, size=maxm(old.size, inc) if old.size.is_const else old.size, elem=old.elem)
                new.size = maxm(old.size, inc)
            if op == "|" and old.kind in ("set", "dict"):
                inc = val.size if val.kind in COLLECTIONS else ONE
                key = self.container_key(tgt)
                if key:
                    self.grow(key, inc)
                new = AVal(old.kind, size=maxm(old.size, inc), elem=old.elem or val.elem)
            val = new
        for tgt in s.targets:
            self.bind(tgt, val, env, s)
            if isinstance(tgt, ir.Name) and isinstance(value, ir.Name) and value.id in self.fr.amort_fill:
                self.fr.amort_fill[tgt.id] = self.fr.amort_fill[value.id]
            if isinstance(tgt, ir.Index):
                with self.quietly():
                    b, _ = self.ev(tgt.base, env)
                if b.kind in ("omap", "oset"):
                    tm = maxm(tm, b.size.log())
        # popped element of a queue/stack/heap, including `u = q[head++]` with a head index that only moves forward
        if isinstance(value, ir.Index) and isinstance(value.index, ir.Name) and isinstance(value.base, ir.Name):
            for entry in self.fr.loops:
                if isinstance(entry.node, ir.While) and value.index.id in entry.vars and value.base.id in names_in(entry.node.test):
                    for nm in names_in(s.targets):
                        self.fr.popped.add(nm)
        if isinstance(value, ir.Call) and value.fn.lower() in lib.SHRINK | {"front", "top"}:
            for nm in names_in(s.targets):
                self.fr.popped.add(nm)
        if isinstance(value, ir.Call) and value.fn.lower() in ("heappop", "heappushpop"):
            for nm in names_in(s.targets):
                self.fr.popped.add(nm)
        return Res(tm, rc=self.fr.rc_acc)

    def container_key(self, e) -> Optional[str]:
        if isinstance(e, ir.Name):
            return e.id
        if isinstance(e, (ir.Attr, ir.Index)):
            return show(e)
        return None

    def bind(self, target, val: AVal, env: Env, stmt=None):
        if isinstance(target, ir.Name):
            old = env.get(target.id)
            env.set(target.id, val)
            if self.fr is not None and val.kind in COLLECTIONS and (old is None or True):
                self.fr.defdepth[target.id] = len(self.fr.loops)
            return
        if isinstance(target, ir.Lit) and target.kind == "tuple":
            parts = val.parts if val.kind == "tuple" and val.parts and len(val.parts) == len(target.elts) else None
            for i, t in enumerate(target.elts):
                if parts:
                    pv = parts[i]
                elif val.kind == "tuple" or val.kind in COLLECTIONS:
                    pv = val.elem or unknown_n()
                    if val.ragged:
                        pv = AVal(pv.kind, pv.mag, pv.size, pv.elem, None, None, True)
                else:
                    pv = val
                self.bind(t, pv, env, stmt)
            return
        if isinstance(target, ir.Index):
            base, _ = self.ev(target.base, env)
            key = self.container_key(target.base)
            aug = stmt is not None and getattr(stmt, "op", None)
            if base.kind in ("dict", "omap") and key and (not aug or aug == "+"):
                self.grow(key, ONE)
            return

    # ── loops ─────────────────────────────────────────────────────────────
    def do_loop(self, s, env: Env) -> Res:
        self.fr.rc_acc = (0, ONE)
        self.loop_ids += 1
        lid = self.loop_ids
        pre = ONE
        bind_after = None
        if isinstance(s, ir.ForRange):
            start, t1 = self.ev(s.start, env)
            stop, t2 = self.ev(s.stop, env)
            pre = maxm(t1, t2)
            step_c = const_val(s.step)
            enclosing = {nm for entry in self.fr.loops if isinstance(entry.node, ir.ForRange) for nm in names_in(entry.node.var)}
            if step_c is not None and step_c < 0:
                iters = maxm(start.mag, ONE)
            elif step_c is not None:
                iters = stop.mag
            elif isinstance(s.step, ir.Name) and s.step.id in enclosing:
                iters = LOG if not stop.mag.is_const else ONE
            else:
                iters = maxm(stop.mag, start.mag) if not isinstance(s.step, ir.UnOp) else maxm(stop.mag, start.mag)
            info = Bound(iters, "range", note=f"`{show(s.var)}` runs up to {show(s.stop)}")
            elem = num(iters)
            bind_after = (s.var, elem)
        elif isinstance(s, ir.ForEach):
            it, t1 = self.ev(s.iter, env)
            pre = t1
            iters = ONE if it.ragged else it.size
            if it.kind == "range":
                iters = it.size
            info = Bound(iters, "each", note=f"goes over every element of `{show(s.iter)}`")
            e = it.elem or (num(it.size) if it.kind == "range" else unknown_n())
            if it.kind == "str":
                e = coll("str", ONE)
            if it.kind in ("dict", "omap") and it.parts is None and it.elem is None:
                e = unknown_n()
            if it.ragged:
                e = AVal(e.kind, e.mag, e.size, e.elem, e.parts, e.fn, True)
            bind_after = (s.var, e)
        else:
            info = self.while_info(s, env)
        entry = LoopEntry(lid, s, info.mag)
        entry.vars = set(info.counters) | set(info.pv) | (names_in(s.var) if isinstance(s, (ir.ForRange, ir.ForEach)) else set())
        scope = self.amort_scope(s, info) if info.kind in ("pointer", "drain") else None
        if scope is None and isinstance(s, ir.ForEach):
            src = s.iter
            while isinstance(src, ir.Call) and src.args and src.fn.lower() in ("reversed", "enumerate", "list", "sorted", "iter") and src.recv is None:
                src = src.args[0]
            if isinstance(src, ir.Name) and src.id in self.fr.amort_fill:
                live = {e.id for e in self.fr.loops}
                scope = [i for i in self.fr.amort_fill[src.id] if i in live] or None
        if scope:
            entry.scope = scope
            entry.total = info.mag
        body_env = env.copy()
        for cv, cm in info.counters.items():
            old = body_env.get(cv)
            body_env.set(cv, num(maxm(cm, old.mag if old is not None and old.kind in ("num", "unknown") else ONE)))
        if bind_after:
            self.bind(bind_after[0], bind_after[1], body_env)
        self.fr.loops.append(entry)
        try:
            body = self.exec_block(s.body + (s.post if isinstance(s, ir.While) else []), body_env)
            cond_t = ONE
            if isinstance(s, ir.While):
                with self.quietly():
                    _, cond_t = self.ev(s.test, body_env)
        finally:
            self.fr.loops.pop()
        before = {k: env.vars.get(k) for k in body_env.vars}
        join_envs(env, [body_env])
        # a container that is rebuilt every pass (`ways = following`) is the size it was made on the previous pass
        carried = [k for k, old in before.items() if old is not None and old.kind in COLLECTIONS and env.vars[k].size != old.size
                   and not env.vars[k].size.is_const]
        if carried and self.fr is not None:
            body_env = env.copy()
            for cv, cm in info.counters.items():
                oldv = body_env.get(cv)
                body_env.set(cv, num(maxm(cm, oldv.mag if oldv is not None and oldv.kind in ("num", "unknown") else ONE)))
            if bind_after:
                self.bind(bind_after[0], bind_after[1], body_env)
            self.fr.loops.append(entry)
            try:
                body = self.exec_block(s.body + (s.post if isinstance(s, ir.While) else []), body_env)
            finally:
                self.fr.loops.pop()
            join_envs(env, [body_env])
        per = maxm(body.t, cond_t)
        self.describe_loop(s, info, entry, scope)
        tags = dict(body.tags)
        total = maxm(info.mag * per, body.once)
        own = tags.pop(lid, None)
        if own is not None:
            total = maxm(total, own)
        rc = body.rc
        if rc[0]:
            rc = (rc[0], rc[1] * info.mag)
        if entry.scope:
            outer = entry.scope[-1]
            tags[outer] = maxm(tags[outer], total) if outer in tags else total
            return Res(maxm(pre, ONE), tags, rc)
        return Res(maxm(pre, total), tags, rc)

    def quietly(self):
        engine = self

        class _Q:
            def __enter__(self_):
                engine.quiet_depth += 1

            def __exit__(self_, *a):
                engine.quiet_depth -= 1
        return _Q()

    def describe_loop(self, s, info: Bound, entry: LoopEntry, scope):
        line = getattr(s, "line", 0)
        if info.kind == "unknown":
            self.note(line, f"loop {info.note}: could not tell how many times it runs, assumed n")
            return
        if info.mag.is_const:
            return
        where = ""
        if entry.scope:
            where = (" (amortised: it only ever moves forward, so over the whole outer loop it takes this many steps in total, "
                     "not this many per pass)")
        self.note(line, f"loop {info.note} → about {info.mag.fmt()[2:-1]} iterations{where}")

    def mag_of(self, name: str, env: Env) -> Mag:
        v = env.get(name)
        if v is None:
            return ONE
        return v.mag if v.kind in ("num", "unknown") else v.size

    def ev_mag(self, e, env: Env) -> Mag:
        with self.quietly():
            v, _ = self.ev(e, env)
        return v.mag if v.kind in ("num", "unknown") else v.size

    def while_info(self, L: ir.While, env: Env) -> Bound:
        body_all = L.body + L.post
        mids = self.fr.mids | find_midpoints(body_all)
        upds = collect_updates(body_all, mids)
        cond = L.test
        if is_true(cond):
            for st in L.body:
                if isinstance(st, ir.If) and any(isinstance(x, (ir.Break, ir.Return)) for x in st.body):
                    cond = negate(st.test)
                    break
            else:
                self.doubt(L.line, "this loop has no condition (`while True`) and no break test I can read; assuming it runs n times")
                return Bound(N, "unknown", note="has no readable exit")
        special = self.dsu_find(L, cond) or self.visited_guard(L, cond)
        if special is not None:
            return special
        bounds = []
        for c in flatten_and(cond):
            b = self.conjunct_bound(c, env, upds, L, mids)
            if b is not None:
                bounds.append(b)
        if bounds:
            best = bounds[0]
            for b in bounds[1:]:
                if b.mag < best.mag:
                    best = b
            return best
        # The condition depends on data, but the body moves an index forward and uses it to read a collection: the loop
        # cannot run longer than that collection is long (sliding windows, `while a[i] < x: i += 1`).
        pointer = self.index_pointer(L, upds, env)
        if pointer is not None:
            return pointer
        drained = self.body_drain(L, env)
        if drained is not None:
            return drained
        self.doubt(L.line, f"cannot tell how often the loop `while {show(cond)}` runs; assuming n times")
        return Bound(N, "unknown", note=f"`while {show(cond)}`")

    def body_drain(self, L: ir.While, env: Env) -> Optional[Bound]:
        """The test looks at a container (`window[0] <= t - w`) and the body takes elements off it: a queue that is topped up once
        per outer pass and drained here empties at most as often as it was filled."""
        body = L.body + L.post
        scan = self.fr.fdef.body if self.fr and hasattr(self.fr.fdef, "body") else []
        taken = [nm for nm in sorted(names_in(L.test)) if removal_in(body, nm)]
        if not taken:
            return None
        size0, pushes = ONE, ONE
        for nm in taken:
            val = env.get(nm)
            size0 = maxm(size0, val.size if val is not None and val.kind in COLLECTIONS else N)
            if grows_in_loop(scan, nm):
                pushes = N
        names = ", ".join(f"`{nm}`" for nm in taken)
        return Bound(maxm(size0, pushes), "drain", drain=set(taken), note=f"takes elements off {names} (each element is added once and removed once)")

    def dsu_find(self, L: ir.While, cond) -> Optional[Bound]:
        """`while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]`: the find of a union-find with path halving."""
        if not (isinstance(cond, ir.BinOp) and cond.op == "!="):
            return None
        a, b = cond.left, cond.right
        if isinstance(b, ir.Index):
            a, b = b, a
        if not (isinstance(a, ir.Index) and isinstance(a.base, ir.Name) and isinstance(a.index, ir.Name)
                and isinstance(b, ir.Name) and b.id == a.index.id):
            return None
        parent, x = a.base.id, a.index.id
        body = L.body + L.post
        follows = any(isinstance(n, ir.Assign) and any(isinstance(t, ir.Name) and t.id == x for t in n.targets)
                      and isinstance(n.value, ir.Index) and isinstance(n.value.base, ir.Name) and n.value.base.id == parent
                      for n in iter_nodes(body))
        compresses = any(isinstance(n, ir.Assign) and any(isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and t.base.id == parent
                                                          for t in n.targets) for n in iter_nodes(body))
        if not (follows and compresses):
            return None
        by_size = False
        for n in iter_nodes(self.module.body, skip_funcs=False):
            if isinstance(n, ir.BinOp) and n.op in ("<", ">", "<=", ">=") and isinstance(n.left, ir.Index) and isinstance(n.right, ir.Index) \
                    and isinstance(n.left.base, ir.Name) and isinstance(n.right.base, ir.Name) \
                    and n.left.base.id == n.right.base.id and n.left.base.id != parent:
                by_size = True
                break
        if by_size:
            return Bound(ONE, "log", note=f"finds the root of `{x}` in the union-find (path compression and union by size: nearly constant per call)")
        return Bound(LOG, "log", note=f"finds the root of `{x}` in the union-find (path compression: about log n per call, amortised)")

    def visited_guard(self, L: ir.While, cond) -> Optional[Bound]:
        """`while node != 0 and seen[node] == 0:` where the enclosing loop marks entries of `seen`: every entry is walked once."""
        if not self.fr.loops:
            return None
        outer = self.fr.loops[-1].node
        for c in flatten_and(cond):
            name = None
            if isinstance(c, ir.BinOp) and c.op == "==" and isinstance(c.left, ir.Index) and isinstance(c.left.base, ir.Name) \
                    and isinstance(c.right, ir.Const) and (c.right.kind in ("none", "bool") or const_val(c.right) in (0, -1)):
                name = c.left.base.id
            elif isinstance(c, ir.UnOp) and c.op == "not" and isinstance(c.operand, ir.Index) and isinstance(c.operand.base, ir.Name):
                name = c.operand.base.id
            elif isinstance(c, ir.BinOp) and c.op == "notin" and isinstance(c.right, ir.Name):
                name = c.right.id
            if name is None:
                continue
            body = outer.body + (outer.post if isinstance(outer, ir.While) else [])
            marks = False
            for n in iter_nodes(body):
                if isinstance(n, ir.Assign):
                    for t in n.targets:
                        if isinstance(t, ir.Index) and isinstance(t.base, ir.Name) and t.base.id == name:
                            marks = True
                        if isinstance(t, ir.Name) and t.id == name:
                            marks = False
                            break
                elif isinstance(n, ir.Call) and n.fn.lower() in ("add", "append", "insert", "push", "put") \
                        and isinstance(n.recv, ir.Name) and n.recv.id == name:
                    marks = True
            if marks:
                return Bound(N, "drain", drain={name}, note=f"only walks through entries of `{name}` that are not marked yet (each is marked once)")
        return None

    def index_pointer(self, L: ir.While, upds, env: Env) -> Optional[Bound]:
        indexed: Dict[str, Mag] = {}
        for n in iter_nodes([L.test] + L.body + L.post):
            if isinstance(n, ir.Index):
                for v in names_in(n.index):
                    if v in upds:
                        with self.quietly():
                            base, _ = self.ev(n.base, env)
                        indexed[v] = maxm(indexed.get(v, ONE), base.size if base.kind in COLLECTIONS else N)
        for v, size in indexed.items():
            if any(u.kind == "ADD" for u in upds[v]):
                return Bound(size, "pointer", pv={v}, note=f"`{v}` moves forward through the data it indexes")
        return None

    def conjunct_bound(self, c, env: Env, upds, L, mids) -> Optional[Bound]:
        if isinstance(c, ir.BinOp) and c.op == "or":
            a = self.conjunct_bound(c.left, env, upds, L, mids)
            b = self.conjunct_bound(c.right, env, upds, L, mids)
            if a and b:
                return a if b.mag < a.mag else b
            return None
        if isinstance(c, ir.UnOp) and c.op == "not" and isinstance(c.operand, ir.BinOp) and c.operand.op in _NEG:
            return self.conjunct_bound(negate(c.operand), env, upds, L, mids)
        name = non_empty_container(c)
        if name:
            val = env.get(name)
            if removal_in(L.body + L.post, name):
                size0 = val.size if val is not None and val.kind in COLLECTIONS else ONE
                scan = self.fr.fdef.body if self.fr and hasattr(self.fr.fdef, "body") else []
                pushes = N if grows_in_loop(scan, name) else ONE
                if val is None or val.kind not in COLLECTIONS:
                    size0 = N
                return Bound(maxm(size0, pushes), "drain", drain={name}, note=f"empties `{name}` (each element is added once and removed once)")
            kinds = {u.kind for u in upds.get(name, [])}
            if "CHASE" in kinds:
                return Bound(N, "pointer", pv={name}, note=f"follows `{name}` along the structure")
            if kinds & {"DIV", "EUCLID", "BITCLEAR"}:
                return Bound(self.mag_of(name, env).log(), "log", note=f"`{name}` shrinks by a constant factor each pass")
            if "ADD" in kinds:
                return Bound(self.mag_of(name, env), "pointer", pv={name}, note=f"`{name}` counts down to zero")
            return None
        if isinstance(c, ir.BinOp) and c.op in ("!=", "==") and const_val(c.right) is None and isinstance(c.right, ir.Const) \
                and c.right.kind == "none" and isinstance(c.left, (ir.Name, ir.Attr)):
            root = c.left
            while isinstance(root, ir.Attr):
                root = root.base
            if isinstance(root, ir.Name) and any(u.kind == "CHASE" for u in upds.get(root.id, [])):
                return Bound(N, "pointer", pv={root.id}, note=f"follows `{root.id}` along the structure")
        if isinstance(c, ir.BinOp) and c.op in _NEG:
            return self.compare_bound(c, env, upds, mids)
        return None

    def counter_of(self, e, P: Set[str]) -> Optional[Tuple[str, str]]:
        e = unwrap_int(e)
        if isinstance(e, ir.Name) and e.id in P:
            return e.id, "id"
        if isinstance(e, ir.BinOp):
            if e.op in ("+", "-", "//", "/", ">>") and isinstance(e.left, ir.Name) and e.left.id in P and is_const_expr(e.right):
                return e.left.id, "id"
            if e.op in ("+", "-") and isinstance(e.right, ir.Name) and e.right.id in P and is_const_expr(e.left):
                return e.right.id, "id"
            if e.op == "*":
                if isinstance(e.left, ir.Name) and isinstance(e.right, ir.Name) and e.left.id == e.right.id and e.left.id in P:
                    return e.left.id, "sq"
                if isinstance(e.left, ir.Name) and e.left.id in P and is_const_expr(e.right):
                    return e.left.id, "id"
            if e.op == "**" and isinstance(e.left, ir.Name) and e.left.id in P and const_val(e.right) == 2:
                return e.left.id, "sq"
        return None

    def compare_bound(self, c: ir.BinOp, env: Env, upds, mids) -> Optional[Bound]:
        P = set(upds)
        L, R = c.left, c.right
        pl, pr = names_in(L) & P, names_in(R) & P
        bis = [v for v in (pl | pr) if any(u.kind == "BISECT" for u in upds[v])]
        if len(bis) >= 2:
            span = maxm(*[self.mag_of(v, env) for v in names_in(c)]) if names_in(c) else ONE
            return Bound(span.log(), "log", note=f"narrows the range `{show(c)}` by half each pass (binary search)",
                         counters={v: span for v in names_in(c) if v in upds})
        cl = self.counter_of(L, P) if pl else None
        cr = self.counter_of(R, P) if pr else None
        if cl and cr and cl[0] != cr[0]:
            v1, v2 = cl[0], cr[0]
            span = maxm(self.mag_of(v1, env), self.mag_of(v2, env))
            return Bound(span, "pointer", pv={v1, v2}, note=f"two pointers `{v1}` and `{v2}` close in on each other",
                         counters={v1: span, v2: span})
        if cl and not pr:
            v, form, other, v_left = cl[0], cl[1], R, True
        elif cr and not pl:
            v, form, other, v_left = cr[0], cr[1], L, False
        else:
            return None
        # which way the condition needs v to move for the loop to end: `upper` = v must grow, `lower` = v must shrink
        if c.op in ("<", "<="):
            need = "upper" if v_left else "lower"
        elif c.op in (">", ">="):
            need = "lower" if v_left else "upper"
        else:
            need = "either"
        kinds = {u.kind for u in upds[v]}
        # a counter that the body sets back to a constant on every pass (`days, today = 1, 0`) is not what makes the loop progress
        for u in upds[v]:
            st = u.stmt
            if u.kind == "OTHER" and isinstance(st, ir.Assign) and st.op is None and not isinstance(st.value, ir.Name) and \
                    (is_const_expr(st.value) or (isinstance(st.value, ir.Lit) and all(is_const_expr(x) for x in st.value.elts))):
                return None
        other_mag = self.ev_mag(other, env)
        entry_mag = self.mag_of(v, env)
        span = maxm(other_mag, entry_mag)
        if kinds & {"EUCLID", "BITCLEAR"}:
            return Bound(entry_mag.log(), "log", note=f"`{v}` shrinks fast each pass (remainder / bit clearing)", counters={v: entry_mag})
        if "MULT" in kinds and need in ("upper", "either"):
            return Bound(span.log(), "log", note=f"`{v}` is multiplied each pass up to {show(other)}", counters={v: span})
        if "DIV" in kinds and need in ("lower", "either"):
            return Bound(span.log(), "log", note=f"`{v}` is divided each pass", counters={v: span})
        if kinds <= {"MULT", "DIV"}:
            return None                       # the update moves v away from the bound: this conjunct never ends the loop
        if "ADD" in kinds:
            if form == "sq":
                return Bound(span.sqrt(), "pointer", pv={v}, note=f"`{v}` goes up while {show(c)} (about the square root)",
                             counters={v: span.sqrt()})
            # a step that is itself an outer loop's counter (the sieve: j += i) makes this loop run about log n times on average
            enclosing = set()
            for entry in self.fr.loops:
                enclosing |= entry.vars
            for u in upds[v]:
                st = u.stmt
                if u.kind == "ADD" and isinstance(st, ir.Assign):
                    step = st.value
                    if isinstance(step, ir.BinOp) and st.op is None:
                        step = step.right if isinstance(step.left, ir.Name) and step.left.id == v else step.left
                    if isinstance(step, ir.Name) and step.id != v and step.id in enclosing and not span.is_const:
                        return Bound(LOG, "pointer", pv={v}, note=f"`{v}` steps by `{step.id}`, so over the outer loop it runs about log n times",
                                     counters={v: span})
            return Bound(span, "pointer", pv={v}, note=f"`{v}` steps towards {show(other)}", counters={v: span})
        if "CHASE" in kinds:
            return Bound(N, "pointer", pv={v}, note=f"follows `{v}` along the structure", counters={v: N})
        return None

    # ── amortisation ──────────────────────────────────────────────────────
    def amort_scope(self, L, info: Bound) -> Optional[List[int]]:
        """The enclosing loops whose iterations this loop's total already covers: its pointer/stack is never reset in them."""
        loops = self.fr.loops
        if not loops:
            return None
        scope: List[int] = []
        for entry in reversed(loops):
            if self.resets(entry.node, L, info):
                break
            scope.append(entry.id)
        return scope or None

    def lifts(self, nm: str, test, assign: ir.Assign) -> bool:
        """`if j <= i: j = i + 1`: the pointer is only ever raised, so it never moves backwards."""
        if not (isinstance(test, ir.BinOp) and test.op in ("<", "<=", ">", ">=")):
            return False
        if isinstance(test.left, ir.Name) and test.left.id == nm and test.op in ("<", "<="):
            bound = test.right
        elif isinstance(test.right, ir.Name) and test.right.id == nm and test.op in (">", ">="):
            bound = test.left
        else:
            return False
        v = unwrap_int(assign.value)
        if show(v, 99) == show(bound, 99):
            return True
        return isinstance(v, ir.BinOp) and v.op == "+" and show(v.left, 99) == show(bound, 99) and (const_val(v.right) or 0) >= 0

    def handoff(self, X, nm: str, assign: ir.Assign) -> bool:
        """`end = start` ... `start = end`: the outer pointer takes over where the inner one stopped, so together they move forward once."""
        if assign.op is not None:
            return False
        src = names_in(assign.value)
        for n in iter_nodes(X.body + (X.post if isinstance(X, ir.While) else [])):
            if isinstance(n, ir.Assign) and n.op is None and len(n.targets) == 1 and isinstance(n.targets[0], ir.Name) \
                    and n.targets[0].id in src and n.targets[0].id != nm:
                v = unwrap_int(n.value)
                if isinstance(v, ir.Name) and v.id == nm:
                    return True
                if isinstance(v, ir.BinOp) and v.op in ("+", "-") and isinstance(v.left, ir.Name) and v.left.id == nm \
                        and const_val(v.right) is not None:
                    return True
        return False

    def seeded_and_guarded(self, X, L, c: str) -> bool:
        """A worklist `c` that is started afresh for every pass of X, but only ever receives things not seen before (`if y not in seen:
        seen.add(y); c.append(y)`) and `seen` is never cleared in X: over all of X it takes at most n elements, plus its seeds."""
        if not isinstance(L, ir.While):
            return False
        pushes = [n for n in iter_nodes(L.body + L.post) if isinstance(n, ir.Call) and n.fn.lower() in lib.GROW
                  and isinstance(n.recv, ir.Name) and n.recv.id == c]
        if not pushes:
            return False
        for st in L.body + L.post:
            for n in iter_nodes(st):
                if isinstance(n, ir.If) and self.marks_what_it_tests(n):
                    seen = guard_name(n.test)
                    for p in pushes:
                        if any(p is m for m in iter_nodes(n.body)):
                            break
                    else:
                        continue
                    for st2 in X.body + (X.post if isinstance(X, ir.While) else []):
                        for m in iter_nodes(st2):
                            if isinstance(m, ir.Assign) and any(isinstance(t, ir.Name) and t.id == seen for t in m.targets):
                                return False
                    return True
        return False

    def resets(self, X, L, info: Bound) -> bool:
        names = info.pv | info.drain
        lifted: Set[int] = set()
        for st in X.body + (X.post if isinstance(X, ir.While) else []):
            for n in iter_nodes(st):
                if isinstance(n, ir.If):
                    for a in n.body:
                        if isinstance(a, ir.Assign) and a.op is None and len(a.targets) == 1 and isinstance(a.targets[0], ir.Name) \
                                and a.targets[0].id in names and self.lifts(a.targets[0].id, n.test, a):
                            lifted.add(id(a))
        for st in X.body + (X.post if isinstance(X, ir.While) else []):
            for n in iter_nodes(st):
                if n is L:
                    continue
                if isinstance(n, ir.Assign):
                    for t in n.targets:
                        for nm in names_in(t) if isinstance(t, (ir.Name, ir.Lit)) else []:
                            if nm in names and not self.monotone(nm, n) and id(n) not in lifted and not self.handoff(X, nm, n) \
                                    and not self.seeded_and_guarded(X, L, nm):
                                return True
                elif isinstance(n, (ir.ForRange, ir.ForEach)) and (names_in(n.var) & names):
                    return True
                elif isinstance(n, ir.Call) and n.fn.lower() in ("clear",) and isinstance(n.recv, ir.Name) and n.recv.id in names:
                    return True
        # a statement inside L itself does not reset it, but a sibling loop/branch inside X might: covered above
        return False

    def monotone(self, name: str, stmt: ir.Assign) -> bool:
        if stmt.op in ("+", "-"):
            return True
        v = unwrap_int(stmt.value)
        if isinstance(v, ir.BinOp) and v.op in ("+", "-") and isinstance(v.left, ir.Name) and v.left.id == name:
            return True
        if isinstance(v, ir.Call) and v.fn.lower() == "max" and any(isinstance(a, ir.Name) and a.id == name for a in v.args):
            return True                          # j = max(j, i + 1)
        return False

    # ── expressions ───────────────────────────────────────────────────────
    def ev(self, e, env: Env) -> Tuple[AVal, Mag]:
        self.tick()
        if e is None:
            return AVal("none"), ONE
        t = type(e)
        if t is ir.Const:
            if e.kind == "str":
                return coll("str", ONE), ONE
            if e.kind == "none":
                return AVal("none"), ONE
            return num(ONE), ONE
        if t is ir.Name:
            v = env.get(e.id)
            if v is not None:
                if v.kind in COLLECTIONS and v.size.is_const and self.fr is not None:
                    if self.fr.grown is None:
                        self.fr.grown = collect_grown(getattr(self.fr.fdef, "body", []))
                    if e.id in self.fr.grown:
                        v = AVal(v.kind, v.mag, N, v.elem, v.parts, v.fn, v.ragged)
                return v, ONE
            f = self.funcs.get(e.id)
            if f is not None:
                return AVal("func", fn=f), ONE
            return num(ONE), ONE
        if t is ir.BinOp:
            return self.ev_binop(e, env)
        if t is ir.UnOp:
            v, tm = self.ev(e.operand, env)
            return (num(ONE) if e.op == "not" else v), tm
        if t is ir.Call:
            return self.ev_call(e, env)
        if t is ir.Index:
            base, tb = self.ev(e.base, env)
            idx, ti = self.ev(e.index, env)
            cost = LOG if base.kind in ("omap", "oset") else ONE
            if base.kind == "str":
                res = coll("str", ONE)
            elif base.kind == "tuple" and base.parts and const_val(e.index) is not None and 0 <= int(const_val(e.index)) < len(base.parts):
                res = base.parts[int(const_val(e.index))]
            else:
                res = base.elem if base.elem is not None else unknown_n()
            ragged = isinstance(e.index, ir.Name) and (e.index.id in self.fr.popped or e.index.id in self.fr.state_params)
            if ragged and res.kind in COLLECTIONS | {"unknown"}:
                res = AVal(res.kind, res.mag, res.size, res.elem, res.parts, res.fn, True)
            return res, maxm(tb, ti, cost)
        if t is ir.Slice:
            base, tb = self.ev(e.base, env)
            lo, tl = self.ev(e.lo, env) if e.lo is not None else (num(ONE), ONE)
            hi, th = self.ev(e.hi, env) if e.hi is not None else (None, ONE)
            const_len = False
            if e.hi is not None and (e.lo is None or is_const_expr(e.lo)) and is_const_expr(e.hi):
                const_len = True
            if e.lo is not None and e.hi is not None and isinstance(e.hi, ir.BinOp) and e.hi.op == "+" \
                    and e.hi.left == e.lo and is_const_expr(e.hi.right):
                const_len = True
            size = ONE if const_len else base.size
            res = AVal(base.kind if base.kind in COLLECTIONS else "list", size=size, elem=base.elem)
            self.alloc(size)
            return res, maxm(tb, tl, th, size)
        if t is ir.Attr:
            base, tb = self.ev(e.base, env)
            nm = e.name.lower()
            if nm in ("length", "size", "count") and base.kind in COLLECTIONS:
                return num(base.size), tb
            if base.kind == "tuple" and base.parts and nm in ("first", "second"):
                return base.parts[0 if nm == "first" else min(1, len(base.parts) - 1)], tb
            res = unknown_n()
            if base.ragged:
                res = AVal("unknown", N, N, None, None, None, True)
            return res, tb
        if t is ir.Lit:
            return self.ev_lit(e, env)
        if t is ir.Comp:
            return self.ev_comp(e, env)
        if t is ir.Cond:
            _, tt = self.ev(e.test, env)
            outer = self.fr.rc_acc
            self.fr.rc_acc = (0, ONE)
            a, ta = self.ev(e.a, env)
            rca = self.fr.rc_acc
            self.fr.rc_acc = (0, ONE)
            b, tb = self.ev(e.b, env)
            rcb = self.fr.rc_acc
            self.fr.rc_acc = rc_add(outer, rc_max(rca, rcb))
            return join(a, b), maxm(tt, ta, tb)
        if t is ir.Lambda:
            return AVal("func", fn=e), ONE
        if t is ir.New:
            return self.ev_new(e, env)
        return unknown_n(), ONE

    def binop(self, op: str, l: AVal, r: AVal, lexpr, rexpr) -> Tuple[AVal, Mag]:
        if op in ("+", "-") and (l.kind in ("str", "list", "tuple") or r.kind in ("str", "list", "tuple")):
            if op == "+":
                src = l if l.kind in ("str", "list", "tuple") else r
                size = maxm(l.size if l.kind in COLLECTIONS else ONE, r.size if r.kind in COLLECTIONS else ONE)
                if not (l.size.is_const and r.size.is_const):
                    self.alloc(size)
                return AVal(src.kind, size=size, elem=src.elem or r.elem), size
        if op == "*":
            if l.kind in ("list", "str", "tuple") and r.kind not in COLLECTIONS:
                size = r.mag
                self.alloc(size)
                return AVal(l.kind, size=size, elem=l.elem), size
            if r.kind in ("list", "str", "tuple") and l.kind not in COLLECTIONS:
                size = l.mag
                self.alloc(size)
                return AVal(r.kind, size=size, elem=r.elem), size
            return num(l.mag * r.mag), ONE
        lm = l.mag if l.kind in ("num", "unknown") else ONE
        rm = r.mag if r.kind in ("num", "unknown") else ONE
        if op in ("+", "-", "&", "|", "^"):
            return num(maxm(lm, rm)), ONE
        if op in ("/", "//", ">>"):
            return num(lm), ONE
        if op == "%":
            return num(rm), ONE
        if op == "**":
            k = const_val(rexpr) if rexpr is not None else None
            if k is not None:
                if k == 0.5:
                    return num(lm.sqrt()), ONE
                if isinstance(k, (int, float)) and float(k).is_integer() and 0 < k <= 8:
                    return num(lm.pow(int(k))), ONE
                return num(lm), ONE
            return num(EXP if not rm.is_const else lm), ONE
        if op == "<<":
            return num(lm if rm.is_const else EXP), ONE
        return num(maxm(lm, rm)), ONE

    def ev_binop(self, e: ir.BinOp, env: Env) -> Tuple[AVal, Mag]:
        op = e.op
        l, tl = self.ev(e.left, env)
        r, tr = self.ev(e.right, env)
        tm = maxm(tl, tr)
        if op in ("and", "or"):
            return num(ONE), tm
        if op in ("in", "notin"):
            if r.kind in ("set", "dict"):
                c = ONE
            elif r.kind in ("omap", "oset"):
                c = LOG
            elif r.kind == "range":
                c = ONE
            else:
                c = r.size
            return num(ONE), maxm(tm, c)
        if op in ("<", "<=", ">", ">=", "==", "!="):
            c = ONE
            if l.kind == "str" and r.kind == "str" and not (l.size.is_const and r.size.is_const):
                c = minm(l.size, r.size)
            return num(ONE), maxm(tm, c)
        res, tb = self.binop(op, l, r, e.left, e.right)
        return res, maxm(tm, tb)

    def ev_lit(self, e: ir.Lit, env: Env) -> Tuple[AVal, Mag]:
        tm = ONE
        elem = None
        parts = []
        for x in e.elts:
            v, t = self.ev(x, env)
            tm = maxm(tm, t)
            elem = join(elem, v)
            parts.append(v)
        kind = {"list": "list", "tuple": "tuple", "set": "set", "dict": "dict"}[e.kind]
        out = AVal(kind, size=ONE, elem=elem)
        if kind == "tuple":
            out.parts = parts
        return out, tm

    def ev_comp(self, e: ir.Comp, env: Env) -> Tuple[AVal, Mag]:
        inner = env.copy()
        count = ONE
        # what it costs to evaluate each generator's iterable (a slice copies it): paid once per combination of the generators
        # before it, not once per element of its own loop
        iter_cost = ONE
        body_cost = ONE
        outer_rc, self.fr.rc_acc = self.fr.rc_acc, (0, ONE)
        for g in e.gens:
            it, t = self.ev(g.iter, inner)
            iter_cost = maxm(iter_cost, count * t)
            n = ONE if it.ragged else it.size
            count = count * n
            ev_ = it.elem or (num(it.size) if it.kind == "range" else unknown_n())
            self.bind(g.var, ev_, inner)
            for c in g.conds:
                _, tc = self.ev(c, inner)
                body_cost = maxm(body_cost, tc)
        elt, te = self.ev(e.elt, inner)
        body_cost = maxm(body_cost, te)
        # recursive calls made by the element expression happen once per element
        inner_rc = self.fr.rc_acc
        if inner_rc[0]:
            inner_rc = (inner_rc[0], inner_rc[1] * count)
        self.fr.rc_acc = rc_add(outer_rc, inner_rc)
        total = maxm(iter_cost, count * body_cost)
        kind = {"list": "list", "set": "set", "dict": "dict", "gen": "list"}[e.kind]
        out = AVal(kind, size=count, elem=elt)
        if e.kind != "gen":
            self.alloc(count * total_size(AVal("list", size=ONE, elem=elt)) if elt.kind in COLLECTIONS else count)
        return out, maxm(total, count)

    def ev_new(self, e: ir.New, env: Env) -> Tuple[AVal, Mag]:
        name = e.type_name.lower().split("::")[-1].split(".")[-1]
        name = re.sub(r"[<\[].*", "", name)
        kind = kind_for(name, self.lang) or ("list" if e.is_array else "unknown")
        vals = []
        tm = ONE
        for a in e.args:
            v, t = self.ev(a, env)
            vals.append(v)
            tm = maxm(tm, t)
        if kind == "unknown":
            return unknown_n(), tm
        size = ONE
        elem = None
        if e.is_array:
            dims = [v.mag if v.kind in ("num", "unknown") else v.size for v in vals] or [ONE]
            size = dims[0]
            elem = None
            for d in reversed(dims[1:]):
                elem = coll("list", d, elem)
            out = coll(kind, size, elem)
            cells = product(dims)
            self.alloc(cells)
            return out, maxm(tm, cells)
        if vals:
            first = vals[0]
            if first.kind in COLLECTIONS:
                size = first.size
                elem = first.elem
            elif first.kind in ("num", "unknown") and kind in ("list", "deque", "str"):
                size = first.mag
                if len(vals) > 1 and vals[1].kind in COLLECTIONS:
                    elem = vals[1]
        out = coll(kind, size, elem)
        cells = size * (total_size(elem) if elem is not None and elem.kind in COLLECTIONS and elem.kind != "str" else ONE)
        self.alloc(cells)
        return out, maxm(tm, cells)

    # ── calls ─────────────────────────────────────────────────────────────
    def lambda_cost(self, fn_val: AVal, elem: AVal, env: Env) -> Tuple[Mag, AVal]:
        f = fn_val.fn
        if isinstance(f, ir.Lambda):
            e2 = env.copy()
            for p in f.params:
                e2.set(p, elem)
            saved, self.fr.rets = self.fr.rets, None
            with self.quietly():
                r = self.exec_block(f.body, e2)
            ret, self.fr.rets = self.fr.rets, saved
            return maxm(r.t, r.once), (ret or unknown_n())
        return ONE, unknown_n()

    def ev_call(self, e: ir.Call, env: Env) -> Tuple[AVal, Mag]:
        fn = e.fn
        low = fn.lower()
        # user-defined function (a plain call, or a method of the same class)
        user = None
        if e.recv is None or (isinstance(e.recv, ir.Name) and e.recv.id in ("this", "self", "Solution", "solution")):
            local = env.get(fn)
            user = local.fn if local is not None and local.kind == "func" and isinstance(local.fn, ir.FuncDef) else self.funcs.get(fn)
        if user is not None:
            return self.call_user(user, e, env)
        recv, tr = (self.ev(e.recv, env) if e.recv is not None else (None, ONE))
        vals, tm = [], tr
        for a in e.args:
            v, t = self.ev(a, env)
            vals.append(v)
            tm = maxm(tm, t)
        kw = {}
        for k, a in e.kwargs.items():
            v, t = self.ev(a, env)
            kw[k] = v
            tm = maxm(tm, t)
        return self.model_call(e, low, recv, vals, kw, tm, env)

    def call_user(self, fdef: ir.FuncDef, e: ir.Call, env: Env) -> Tuple[AVal, Mag]:
        vals, tm = [], ONE
        for a in e.args:
            v, t = self.ev(a, env)
            vals.append(v)
            tm = maxm(tm, t)
        if id(fdef) in self.active:
            fr = self.active[id(fdef)]
            fr.sites.append(self.site_kind(e.args, env, fr))
            if not self.quiet:
                self.fr.rc_acc = rc_add(self.fr.rc_acc, (1, ONE))
            return unknown_n(), tm
        r = self.call_function(fdef, vals, e.args, env)
        if not self.quiet and self.fr is not None and not r.space.is_const:
            self.fr.allocs.append(r.space)
        if r.memo and self.fr is not None:
            # a memoised / visit-once function does its whole job once, however many times it is called
            if not self.quiet:
                self.fr.once.append(r.time)
            return (r.ret or unknown_n()), maxm(tm, ONE)
        return (r.ret or unknown_n()), maxm(tm, r.time)

    def model_call(self, e: ir.Call, low: str, recv: Optional[AVal], vals: List[AVal], kw: dict, tm: Mag, env: Env) -> Tuple[AVal, Mag]:
        line = e.line
        # ---- plain builtins -------------------------------------------------
        if recv is None:
            a0 = vals[0] if vals else None
            if low in ("len", "size", "length") and a0 is not None:
                return num(a0.size), tm
            if low == "range":
                if len(vals) == 1:
                    sz = vals[0].mag
                else:
                    sz = maxm(vals[0].mag, vals[1].mag) if len(vals) >= 2 else ONE
                return AVal("range", size=sz, mag=sz), tm
            if low in ("enumerate", "reversed", "iter", "sorted_view") and a0 is not None:
                inner = a0.elem or unknown_n()
                if low == "enumerate":
                    return AVal("list", size=a0.size, elem=AVal("tuple", parts=[num(a0.size), inner], elem=inner), ragged=a0.ragged), tm
                return AVal(a0.kind if a0.kind in COLLECTIONS else "list", size=a0.size, elem=a0.elem, ragged=a0.ragged), tm
            if low == "zip" and vals:
                sz = maxm(*[v.size for v in vals])
                return AVal("list", size=sz, elem=AVal("tuple", parts=[v.elem or unknown_n() for v in vals])), tm
            if low in lib.SORTS and a0 is not None and a0.kind in COLLECTIONS | {"unknown"}:
                cb = kw.get("key") or kw.get("cmp") or (vals[1] if len(vals) > 1 and vals[1].kind == "func" else None)
                per = ONE
                if cb is not None and cb.kind == "func":
                    per, _ = self.lambda_cost(cb, a0.elem or unknown_n(), env)
                n = a0.size
                cost = n * (LOG if not n.is_const else ONE) * per
                if low in ("sorted",):
                    self.alloc(n)
                    return AVal("list", size=n, elem=a0.elem), maxm(tm, cost)
                if self.lang in ("python", "javascript"):
                    self.alloc(n)
                return a0, maxm(tm, cost)
            if low in ("sort", "stable_sort", "partial_sort") and len(vals) >= 2:
                it = vals[0]
                n = it.size if it.kind in COLLECTIONS else N
                return AVal("none"), maxm(tm, n * LOG)
            if low in ("min", "max"):
                if len(vals) == 1 and vals[0].kind in COLLECTIONS | {"unknown"}:
                    cb = kw.get("key")
                    per = self.lambda_cost(cb, vals[0].elem or unknown_n(), env)[0] if cb is not None and cb.kind == "func" else ONE
                    return (vals[0].elem or num(vals[0].size)), maxm(tm, vals[0].size * per)
                best = None
                for v in vals:
                    best = join(best, v)
                return (best or num(ONE)), tm
            if low in ("sum", "any", "all", "list", "tuple", "set", "frozenset", "dict", "deque", "vector") and a0 is not None:
                if low in ("sum", "any", "all"):
                    return num(a0.elem.mag if a0.elem is not None and a0.kind in COLLECTIONS and low == "sum" else ONE), maxm(tm, a0.size)
                kind = lib.COLLECTION_KIND.get(low, "list")
                if low in ("set", "frozenset") and a0.kind == "str":
                    # the distinct characters of a string: bounded by the alphabet, not by the length
                    return AVal(kind, size=ONE, elem=coll("str", ONE)), maxm(tm, a0.size)
                if a0.kind in COLLECTIONS or a0.kind == "unknown":
                    self.alloc(a0.size)
                    return AVal(kind, size=a0.size, elem=a0.elem), maxm(tm, a0.size)
                return AVal(kind, size=a0.mag, elem=None), maxm(tm, a0.mag)
            if low in lib.COLLECTION_KIND and not vals:
                return AVal(lib.COLLECTION_KIND[low], size=ONE), tm
            if low in ("map", "filter") and len(vals) >= 2:
                it = vals[1]
                per = self.lambda_cost(vals[0], it.elem or unknown_n(), env)[0] if vals[0].kind == "func" else ONE
                return AVal("list", size=it.size, elem=it.elem or unknown_n(), ragged=it.ragged), maxm(tm, it.size * per)
            if low in ("sqrt", "isqrt", "cbrt"):
                return num((vals[0].mag if vals else ONE).sqrt()), tm
            if low in ("log", "log2", "log10", "bit_length", "ilog"):
                return num((vals[0].mag if vals else ONE).log()), tm
            if low in ("abs", "fabs", "floor", "ceil", "int", "float", "round", "trunc", "double", "long", "min2", "max2",
                       "parseint", "parselong", "valueof", "intvalue"):
                v = vals[0] if vals else num(ONE)
                c = v.size if low in ("int", "parseint", "parselong", "valueof") and v.kind == "str" else ONE
                return num(v.mag if v.kind in ("num", "unknown") else ONE), maxm(tm, c)
            if low in ("pow", "powl"):
                a, b = (vals + [num(ONE), num(ONE)])[:2]
                return num(a.mag if b.mag.is_const else EXP), tm
            if low in ("gcd", "lcm", "__gcd"):
                m_ = maxm(*[v.mag for v in vals]) if vals else ONE
                return num(m_), maxm(tm, m_.log())
            if low in ("bin", "hex", "oct", "tobinarystring", "tohexstring", "tooctalstring", "to_string") and a0 is not None \
                    and a0.kind in ("num", "unknown"):
                digits = a0.mag.log()                     # the digits of a number: about log of its size
                return coll("str", digits), maxm(tm, digits)
            if low == "format" and len(vals) >= 2 and vals[0].kind in ("num", "unknown") and vals[1].kind == "str":
                digits = vals[0].mag.log()
                return coll("str", digits), maxm(tm, digits)
            if low in ("combinations", "permutations", "product", "combinations_with_replacement") and a0 is not None:
                # itertools: choose k of n is about n^k tuples; all orderings of n is n!
                k = None
                if low in ("combinations", "permutations") and len(e.args) >= 2:
                    k = const_val(e.args[1])
                elif low == "product":
                    rep = kw_const(e, "repeat")
                    k = rep if rep is not None else len(e.args)
                    if "repeat" in (getattr(e, "kwargs", None) or {}) and rep is None:
                        k = None
                        src = N                  # repeat=<n>: a choice for each of n places, 2^n or more tuples
                elif low == "combinations_with_replacement" and len(e.args) >= 2:
                    k = const_val(e.args[1])
                src = a0.size if a0.kind in COLLECTIONS else a0.mag
                if low == "product" and "repeat" in (getattr(e, "kwargs", None) or {}) and kw_const(e, "repeat") is None:
                    src = N
                if low == "permutations" and k is None:
                    count = EXP if not src.is_const else ONE
                elif k is not None and float(k).is_integer() and 0 <= k <= 8:
                    count = src.pow(int(k))
                else:
                    count = EXP if not src.is_const else ONE
                elem = AVal("tuple", size=ONE, elem=a0.elem or unknown_n())
                self.note(line, f"`{e.fn}` produces about {count.fmt()[2:-1]} tuples")
                return AVal("list", size=count, elem=elem), maxm(tm, count)
            if low == "str" and a0 is not None:
                return coll("str", a0.mag.log() if a0.kind == "num" else a0.size), maxm(tm, a0.mag.log() if a0.kind == "num" else a0.size)
            if low in ("malloc", "calloc", "realloc", "alloca"):
                dims = [v.mag for v in vals if v.kind in ("num", "unknown")]
                cells = maxm(*dims) if len(dims) <= 1 else product(dims[:2]) if low == "calloc" else maxm(*dims)
                if low == "malloc" and dims:
                    cells = maxm(*dims)
                self.alloc(cells)
                return coll("list", cells), maxm(tm, cells)
            if low in ("strlen",) and a0 is not None:
                return num(a0.size), maxm(tm, a0.size)
            if low in ("memcpy", "memmove", "memset", "strcpy", "strncpy", "strcmp", "strncmp", "strcat", "strcasecmp"):
                sz = maxm(*[v.size for v in vals]) if vals else ONE
                sz = maxm(sz, vals[-1].mag if vals and vals[-1].kind in ("num", "unknown") else ONE)
                return AVal("none"), maxm(tm, sz)
            if low in ("accumulate", "reduce", "for_each", "count_if", "find_if", "all_of", "any_of", "none_of", "transform",
                       "fill", "iota", "copy", "reverse", "unique", "rotate", "min_element", "max_element", "count", "find",
                       "equal", "lower_bound", "upper_bound", "binary_search", "next_permutation", "shuffle", "random_shuffle",
                       "is_sorted", "partial_sum", "inner_product", "adjacent_difference", "swap_ranges", "fill_n", "copy_n"):
                n = self.range_size(e, vals)
                if low in ("lower_bound", "upper_bound", "binary_search", "equal_range"):
                    return num(n), maxm(tm, n.log())
                return unknown_n(), maxm(tm, n)
            if low in lib.LOGARITHMIC or low in ("heappush", "heappop", "heappushpop", "heapreplace", "bisect_left", "bisect_right", "bisect", "insort"):
                a = vals[0] if vals else None
                n = a.size if a is not None and a.kind in COLLECTIONS else N
                if low in ("heappush",) and e.args and isinstance(e.args[0], ir.Name):
                    self.grow(e.args[0].id, ONE)
                return (a.elem if a is not None and a.elem is not None else unknown_n()), maxm(tm, n.log())
            if low in lib.HEAPIFY and vals:
                return AVal("none"), maxm(tm, vals[0].size)
            if low in ("deepcopy", "copy") and a0 is not None:
                self.alloc(total_size(a0))
                return a0, maxm(tm, total_size(a0))
            if low in ("print", "println", "printf", "puts", "cout", "scanf", "input", "readline", "read", "swap", "exit",
                       "assert", "abort", "setrecursionlimit", "random", "randint", "time", "clock"):
                return unknown_n() if low in ("input", "readline", "read") else AVal("none"), tm
            if low in lib.CONSTANT:
                return unknown_n(), tm
            big = [v for v in vals if v.kind in COLLECTIONS and not v.size.is_const]
            if big:
                self.doubt(line, f"`{e.fn}(...)` on a sized value: assuming it takes constant time")
            return unknown_n(), tm
        # ---- methods on a receiver ------------------------------------------
        rk = recv.kind
        key = self.container_key(e.recv)
        a0 = vals[0] if vals else None
        if low in ("items", "keys", "values", "entries", "iterator", "keyset", "entryset", "chars", "stream", "boxed", "iter",
                   "begin", "end", "rbegin", "rend", "cbegin", "cend", "asindexed"):
            elem = recv.elem
            if low == "items" or low in ("entries", "entryset"):
                elem = AVal("tuple", parts=[unknown_n(), recv.elem or unknown_n()], elem=unknown_n())
            return AVal("list" if rk != "str" else "str", size=recv.size, elem=elem, ragged=recv.ragged), tm
        if low == "set" and rk in ("dict", "omap", "unknown") and key:
            self.grow(key, ONE)
            return AVal("none"), maxm(tm, recv.size.log() if rk == "omap" else ONE)
        if low in lib.GROW:
            inc = ONE
            if rk == "unknown" and not self.quiet and recv.size == N and key is None:
                pass
            if low == "insert" and rk in ("list", "str", "unknown") and len(vals) >= 2:
                tm = maxm(tm, recv.size)          # insert in the middle shifts the rest
            if low in ("push", "append", "add", "push_back", "emplace_back", "offer", "addlast", "put", "heappush") and a0 is not None \
                    and a0.kind in COLLECTIONS and not a0.size.is_const:
                inc = total_size(a0)
                self.alloc(inc)
            if key:
                self.grow(key, inc)
            if rk in ("heap", "omap", "oset"):
                tm = maxm(tm, recv.size.log())
            if low == "unshift" or (low == "add" and len(vals) == 2 and rk in ("list", "str")):
                tm = maxm(tm, recv.size)
            return AVal("none"), tm
        if low in lib.SHRINK:
            elem = recv.elem or unknown_n()
            if rk in ("heap", "omap", "oset") or (rk == "unknown" and low == "poll"):
                tm = maxm(tm, recv.size.log())
            if low in ("pop", "remove", "erase", "removeat") and rk in ("list", "str", "unknown") and vals:
                if low == "pop" and a0 is not None and a0.kind == "num" and a0.mag.is_const:
                    tm = maxm(tm, recv.size)            # pop(0): shifts everything
                elif low in ("remove", "erase", "removeat") and rk in ("list", "unknown"):
                    tm = maxm(tm, recv.size)
            if low == "shift":
                tm = maxm(tm, recv.size)
            return elem, tm
        if low in lib.SORTS:
            cb = kw.get("key") or kw.get("cmp") or (vals[0] if vals and vals[0].kind == "func" else None)
            per = self.lambda_cost(cb, recv.elem or unknown_n(), env)[0] if cb is not None and cb.kind == "func" else ONE
            n = recv.size
            if self.lang in ("python", "javascript", "java") and rk in ("list", "unknown"):
                self.alloc(n)
            return recv, maxm(tm, n * (LOG if not n.is_const else ONE) * per)
        if low in lib.CALLBACK_EACH and vals and any(v.kind == "func" for v in vals):
            fv = next(v for v in vals if v.kind == "func")
            per, ret = self.lambda_cost(fv, recv.elem or unknown_n(), env)
            out = AVal("list", size=recv.size, elem=ret if low == "map" else (recv.elem or unknown_n()), ragged=recv.ragged)
            if low in ("map", "filter", "flatmap"):
                self.alloc(recv.size * (total_size(ret) if low == "map" and ret.kind in COLLECTIONS and ret.kind != "str" else ONE))
            return out, maxm(tm, recv.size * per)
        if low in lib.LOGARITHMIC:
            return AVal("num", mag=recv.size.log()), maxm(tm, recv.size.log())
        if low in lib.MEMBERSHIP or low in ("contains", "indexof", "lastindexof", "index", "find", "count", "includes", "has"):
            if rk in ("set", "dict"):
                c = ONE
            elif rk in ("omap", "oset", "heap"):
                c = LOG if low not in ("count",) else LOG
            elif low == "has" and rk == "unknown":
                c = ONE
            else:
                c = recv.size
            return (num(ONE) if low not in ("find",) else unknown_n()), maxm(tm, c)
        if low in lib.LINEAR_ARG:
            n = a0.size if a0 is not None and a0.kind in COLLECTIONS else (a0.mag if a0 is not None else ONE)
            if key:
                self.grow(key, n)
            return AVal("none"), maxm(tm, n)
        if low in ("split", "splitlines", "tolist", "toarray", "tochararray", "chars", "aslist", "copyof", "copyofrange", "slice",
                   "clone", "copy", "concat"):
            sz = recv.size
            if low in ("slice", "copyofrange", "substring", "substr") and vals and all(is_const_expr(a) for a in e.args):
                sz = ONE
            if low == "concat" and a0 is not None:
                sz = maxm(sz, a0.size)
            self.alloc(sz)
            return AVal("list" if rk != "str" or low in ("split", "splitlines", "tolist", "toarray", "tochararray", "chars") else "str",
                        size=sz, elem=recv.elem if rk != "str" else coll("str", ONE)), maxm(tm, sz)
        if low in ("substring", "substr"):
            sz = ONE if vals and all(is_const_expr(a) for a in e.args) else recv.size
            self.alloc(sz)
            return coll("str", sz), maxm(tm, sz)
        if low in ("join",) and a0 is not None:
            n = a0.size if a0.kind in COLLECTIONS else recv.size
            self.alloc(n)
            return coll("str", n), maxm(tm, n)
        if low in ("reverse", "strip", "lstrip", "rstrip", "trim", "lower", "upper", "replace", "replaceall", "startswith",
                   "endswith", "tostring", "tostr", "capitalize", "title", "equals", "compareto", "encode", "decode", "isnumeric",
                   "format", "fill", "assign", "resize", "flatten", "flat", "unique", "distinct", "tobytes"):
            n = recv.size
            if rk in ("num",):
                n = recv.mag.log()
            if low in ("reverse", "fill", "assign", "resize") or low in ("unique", "distinct"):
                pass
            if low in ("strip", "lstrip", "rstrip", "trim", "lower", "upper", "replace", "replaceall", "tostring", "capitalize",
                       "title", "encode", "decode", "format"):
                self.alloc(n)
                return coll("str", n), maxm(tm, n)
            if low in ("startswith", "endswith", "equals", "compareto", "isnumeric"):
                n = minm(n, a0.size) if a0 is not None and a0.kind in COLLECTIONS else n
                return num(ONE), maxm(tm, n)
            return (recv if low in ("fill", "reverse", "assign") else AVal("none")), maxm(tm, n)
        if low in lib.CONSTANT or low in ("get", "set", "getordefault", "put", "peek", "top", "front", "back", "first", "last",
                                          "at", "charat", "containskey", "empty", "isempty", "size", "length", "hasnext", "next"):
            if low in ("get", "getordefault", "at", "charat", "peek", "top", "front", "back", "first", "last", "next", "getfirst",
                       "getlast", "peekfirst", "peeklast"):
                cost = recv.size.log() if rk in ("omap", "oset") and low in ("get", "getordefault") else ONE
                if rk == "str":
                    return coll("str", ONE), maxm(tm, cost)
                res = recv.elem or unknown_n()
                if low in ("get", "at") and e.args and isinstance(e.args[0], ir.Name) \
                        and (e.args[0].id in self.fr.popped or e.args[0].id in self.fr.state_params):
                    res = AVal(res.kind, res.mag, res.size, res.elem, res.parts, res.fn, True)
                return res, maxm(tm, cost)
            if low in ("size", "length", "count") and recv is not None:
                return num(recv.size), tm
            return num(ONE), tm
        if low == "set" and rk in ("list", "unknown"):
            return AVal("none"), tm
        if low in lib.LINEAR_RECV:
            n = recv.size
            if low in ("sum", "any", "all", "count"):
                return num(ONE), maxm(tm, n)
            return AVal("none"), maxm(tm, n)
        if rk in COLLECTIONS and not recv.size.is_const:
            self.doubt(line, f"`.{e.fn}(...)` on a sized value: assuming it takes constant time")
        return unknown_n(), tm

    def range_size(self, e: ir.Call, vals: List[AVal]) -> Mag:
        for v in vals:
            if v.kind in COLLECTIONS and not v.size.is_const:
                return v.size
        for a in e.args:
            if isinstance(a, ir.Call) and a.recv is not None:
                with self.quietly():
                    rv, _ = self.ev(a.recv, Env())
                    if rv.kind in COLLECTIONS:
                        return rv.size
        return N
