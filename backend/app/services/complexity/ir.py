"""The small language every frontend (Python, C, C++, Java, JavaScript) is translated into before costing.

It keeps only what decides how much work code does: loops and their counters, calls, allocations, indexing and
assignments. Everything else (types beyond a coarse kind, exceptions, classes) is flattened away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(eq=True)
class Node:
    line: int = field(default=0, compare=False, repr=False)


# ── expressions ────────────────────────────────────────────────────────────

@dataclass(eq=True)
class Const(Node):
    value: Any = None
    kind: str = "int"                 # int | float | str | bool | none


@dataclass(eq=True)
class Name(Node):
    id: str = ""


@dataclass(eq=True)
class BinOp(Node):
    op: str = ""                      # + - * / // % ** << >> & | ^ and or < <= > >= == != in notin
    left: Any = None
    right: Any = None


@dataclass(eq=True)
class UnOp(Node):
    op: str = ""                      # not - ~
    operand: Any = None


@dataclass(eq=True)
class Call(Node):
    fn: str = ""                      # the function or method name, as written (without a receiver)
    recv: Any = None                  # the object a method is called on, if any
    args: List[Any] = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


@dataclass(eq=True)
class Index(Node):
    base: Any = None
    index: Any = None


@dataclass(eq=True)
class Slice(Node):
    base: Any = None
    lo: Any = None
    hi: Any = None


@dataclass(eq=True)
class Attr(Node):
    base: Any = None
    name: str = ""


@dataclass(eq=True)
class Gen(Node):
    var: Any = None                   # Name or Lit('tuple')
    iter: Any = None
    conds: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class Comp(Node):
    kind: str = "list"                # list | set | dict | gen
    elt: Any = None
    gens: List[Gen] = field(default_factory=list)


@dataclass(eq=True)
class Lit(Node):
    kind: str = "list"                # list | tuple | set | dict
    elts: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class Cond(Node):
    test: Any = None
    a: Any = None
    b: Any = None


@dataclass(eq=True)
class Lambda(Node):
    params: List[str] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)      # statements; an expression body is [Return(expr)]


@dataclass(eq=True)
class New(Node):
    type_name: str = ""               # list, vector, ArrayList, HashMap, int[] ...
    args: List[Any] = field(default_factory=list)
    is_array: bool = False            # new int[n]: args are the dimensions


@dataclass(eq=True)
class Unknown(Node):
    text: str = ""


# ── statements ─────────────────────────────────────────────────────────────

@dataclass(eq=True)
class Assign(Node):
    targets: List[Any] = field(default_factory=list)   # Name, Index, Attr, or Lit('tuple') for a parallel assignment
    value: Any = None
    op: Optional[str] = None                           # '+' for +=, None for a plain assignment
    decl_type: Optional[str] = None                    # the declared type, as written, when there is one


@dataclass(eq=True)
class ExprStmt(Node):
    expr: Any = None


@dataclass(eq=True)
class If(Node):
    test: Any = None
    body: List[Any] = field(default_factory=list)
    orelse: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class While(Node):
    test: Any = None
    body: List[Any] = field(default_factory=list)
    post: List[Any] = field(default_factory=list)      # the update of a C-style for loop
    do_while: bool = False


@dataclass(eq=True)
class ForRange(Node):
    var: Any = None
    start: Any = None
    stop: Any = None
    step: Any = None
    body: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class ForEach(Node):
    var: Any = None
    iter: Any = None
    body: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class Return(Node):
    value: Any = None


@dataclass(eq=True)
class Break(Node):
    pass


@dataclass(eq=True)
class Continue(Node):
    pass


@dataclass(eq=True)
class Block(Node):
    body: List[Any] = field(default_factory=list)


@dataclass(eq=True)
class FuncDef(Node):
    name: str = ""
    params: List[Any] = field(default_factory=list)    # [(name, type text or None)]
    body: List[Any] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass(eq=True)
class Module(Node):
    body: List[Any] = field(default_factory=list)
    language: str = "python"
