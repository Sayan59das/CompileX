"""Python source -> IR, using the standard `ast` module."""

from __future__ import annotations

import ast
from typing import Any, List

from . import ir

# modules whose functions are called as `heapq.heappush(...)`: the module name carries no information for costing
_MODULES = {
    "math", "heapq", "bisect", "itertools", "collections", "functools", "sys", "random", "string", "operator",
    "copy", "re", "statistics", "np", "numpy", "os", "time", "json", "decimal", "fractions",
}

_BINOPS = {
    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
    ast.LShift: "<<", ast.RShift: ">>", ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^", ast.MatMult: "*",
}
_CMPOPS = {
    ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=",
    ast.In: "in", ast.NotIn: "notin", ast.Is: "==", ast.IsNot: "!=",
}


def parse(code: str) -> ir.Module:
    tree = ast.parse(code)
    return ir.Module(body=_stmts(tree.body), language="python")


def _line(node) -> int:
    return getattr(node, "lineno", 0) or 0


def _stmts(nodes) -> List[Any]:
    out: List[Any] = []
    for n in nodes:
        out.extend(_stmt(n))
    return out


def _stmt(n) -> List[Any]:
    ln = _line(n)
    if isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef):
        params = [(a.arg, ast.unparse(a.annotation) if a.annotation is not None else None) for a in n.args.args if a.arg != "self"]
        params += [(a.arg, ast.unparse(a.annotation) if a.annotation is not None else None) for a in n.args.kwonlyargs]
        decos = []
        for d in n.decorator_list:
            target = d.func if isinstance(d, ast.Call) else d
            decos.append(ast.unparse(target).split(".")[-1])
        return [ir.FuncDef(line=ln, name=n.name, params=params, body=_stmts(n.body), decorators=decos)]
    if isinstance(n, ast.ClassDef):
        return _stmts(n.body)
    if isinstance(n, ast.Assign):
        return [ir.Assign(line=ln, targets=[_target(t) for t in n.targets], value=_expr(n.value))]
    if isinstance(n, ast.AugAssign):
        return [ir.Assign(line=ln, targets=[_target(n.target)], value=_expr(n.value), op=_BINOPS.get(type(n.op), "+"))]
    if isinstance(n, ast.AnnAssign):
        if n.value is None:
            return []
        return [ir.Assign(line=ln, targets=[_target(n.target)], value=_expr(n.value), decl_type=ast.unparse(n.annotation))]
    if isinstance(n, ast.Expr):
        return [ir.ExprStmt(line=ln, expr=_expr(n.value))]
    if isinstance(n, ast.If):
        return [ir.If(line=ln, test=_expr(n.test), body=_stmts(n.body), orelse=_stmts(n.orelse))]
    if isinstance(n, ast.While):
        return [ir.While(line=ln, test=_expr(n.test), body=_stmts(n.body))]
    if isinstance(n, (ast.For, ast.AsyncFor)):
        var = _target(n.target)
        it = n.iter
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range" and 1 <= len(it.args) <= 3:
            args = [_expr(a) for a in it.args]
            if len(args) == 1:
                start, stop, step = ir.Const(value=0), args[0], ir.Const(value=1)
            elif len(args) == 2:
                start, stop, step = args[0], args[1], ir.Const(value=1)
            else:
                start, stop, step = args
            return [ir.ForRange(line=ln, var=var, start=start, stop=stop, step=step, body=_stmts(n.body))]
        return [ir.ForEach(line=ln, var=var, iter=_expr(it), body=_stmts(n.body))]
    if isinstance(n, ast.Return):
        return [ir.Return(line=ln, value=_expr(n.value) if n.value is not None else None)]
    if isinstance(n, ast.Break):
        return [ir.Break(line=ln)]
    if isinstance(n, ast.Continue):
        return [ir.Continue(line=ln)]
    if isinstance(n, ast.Raise):
        return [ir.Return(line=ln)]
    if isinstance(n, (ast.With, ast.AsyncWith)):
        return _stmts(n.body)
    if isinstance(n, ast.Try):
        out = _stmts(n.body)
        for h in n.handlers:
            out.extend(_stmts(h.body))
        out.extend(_stmts(n.orelse))
        out.extend(_stmts(n.finalbody))
        return out
    if isinstance(n, ast.Assert):
        return [ir.ExprStmt(line=ln, expr=_expr(n.test))]
    return []


def _target(t) -> Any:
    if isinstance(t, (ast.Tuple, ast.List)):
        return ir.Lit(line=_line(t), kind="tuple", elts=[_target(e) for e in t.elts])
    if isinstance(t, ast.Starred):
        return _target(t.value)
    return _expr(t)


def _expr(e) -> Any:
    if e is None:
        return ir.Const(value=None, kind="none")
    ln = _line(e)
    if isinstance(e, ast.Constant):
        v = e.value
        if isinstance(v, bool):
            return ir.Const(line=ln, value=v, kind="bool")
        if isinstance(v, int):
            return ir.Const(line=ln, value=v, kind="int")
        if isinstance(v, float):
            return ir.Const(line=ln, value=v, kind="float")
        if isinstance(v, (str, bytes)):
            return ir.Const(line=ln, value=v, kind="str")
        return ir.Const(line=ln, value=None, kind="none")
    if isinstance(e, ast.Name):
        return ir.Name(line=ln, id=e.id)
    if isinstance(e, ast.BinOp):
        return ir.BinOp(line=ln, op=_BINOPS.get(type(e.op), "+"), left=_expr(e.left), right=_expr(e.right))
    if isinstance(e, ast.BoolOp):
        op = "and" if isinstance(e.op, ast.And) else "or"
        out = _expr(e.values[0])
        for v in e.values[1:]:
            out = ir.BinOp(line=ln, op=op, left=out, right=_expr(v))
        return out
    if isinstance(e, ast.UnaryOp):
        op = {ast.Not: "not", ast.USub: "-", ast.UAdd: "+", ast.Invert: "~"}.get(type(e.op), "-")
        return ir.UnOp(line=ln, op=op, operand=_expr(e.operand))
    if isinstance(e, ast.Compare):
        parts, left = [], e.left
        for op, right in zip(e.ops, e.comparators):
            parts.append(ir.BinOp(line=ln, op=_CMPOPS.get(type(op), "=="), left=_expr(left), right=_expr(right)))
            left = right
        out = parts[0]
        for p in parts[1:]:
            out = ir.BinOp(line=ln, op="and", left=out, right=p)
        return out
    if isinstance(e, ast.Call):
        args = [_expr(a.value if isinstance(a, ast.Starred) else a) for a in e.args]
        kwargs = {k.arg: _expr(k.value) for k in e.keywords if k.arg}
        f = e.func
        if isinstance(f, ast.Name):
            return ir.Call(line=ln, fn=f.id, args=args, kwargs=kwargs)
        if isinstance(f, ast.Attribute):
            root = f.value
            if isinstance(root, ast.Name) and root.id in _MODULES:
                return ir.Call(line=ln, fn=f.attr, args=args, kwargs=kwargs)
            if isinstance(root, ast.Attribute) and isinstance(root.value, ast.Name) and root.value.id in _MODULES:
                return ir.Call(line=ln, fn=f.attr, args=args, kwargs=kwargs)       # sys.stdin.readline()
            return ir.Call(line=ln, fn=f.attr, recv=_expr(root), args=args, kwargs=kwargs)
        return ir.Call(line=ln, fn="<call>", recv=_expr(f), args=args, kwargs=kwargs)
    if isinstance(e, ast.Subscript):
        sl = e.slice
        if isinstance(sl, ast.Slice):
            return ir.Slice(line=ln, base=_expr(e.value), lo=_expr(sl.lower) if sl.lower else None,
                            hi=_expr(sl.upper) if sl.upper else None)
        return ir.Index(line=ln, base=_expr(e.value), index=_expr(sl))
    if isinstance(e, ast.Attribute):
        return ir.Attr(line=ln, base=_expr(e.value), name=e.attr)
    if isinstance(e, (ast.List, ast.Tuple, ast.Set)):
        kind = "list" if isinstance(e, ast.List) else "tuple" if isinstance(e, ast.Tuple) else "set"
        return ir.Lit(line=ln, kind=kind, elts=[_expr(x.value if isinstance(x, ast.Starred) else x) for x in e.elts])
    if isinstance(e, ast.Dict):
        return ir.Lit(line=ln, kind="dict", elts=[_expr(v) for v in e.values])
    if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        kind = {ast.ListComp: "list", ast.SetComp: "set", ast.GeneratorExp: "gen", ast.DictComp: "dict"}[type(e)]
        gens = [ir.Gen(line=ln, var=_target(g.target), iter=_expr(g.iter), conds=[_expr(c) for c in g.ifs]) for g in e.generators]
        elt = _expr(e.value if isinstance(e, ast.DictComp) else e.elt)
        return ir.Comp(line=ln, kind=kind, elt=elt, gens=gens)
    if isinstance(e, ast.IfExp):
        return ir.Cond(line=ln, test=_expr(e.test), a=_expr(e.body), b=_expr(e.orelse))
    if isinstance(e, ast.Lambda):
        return ir.Lambda(line=ln, params=[a.arg for a in e.args.args], body=[ir.Return(line=ln, value=_expr(e.body))])
    if isinstance(e, ast.NamedExpr):
        return _expr(e.value)
    if isinstance(e, ast.Starred):
        return _expr(e.value)
    if isinstance(e, (ast.JoinedStr, ast.FormattedValue)):
        return ir.Const(line=ln, value="", kind="str")
    return ir.Unknown(line=ln, text=type(e).__name__)
