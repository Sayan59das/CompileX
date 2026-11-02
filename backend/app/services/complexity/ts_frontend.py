"""C, C++, Java and JavaScript source -> IR, using tree-sitter parse trees."""

from __future__ import annotations

import re
from typing import Any, List

from . import ir
from . import library as lib

_PARSERS: dict = {}

# classes whose static functions are called as `Math.max(a, b)`: the class name carries no information for costing
_STATIC = {
    "math", "arrays", "collections", "integer", "long", "double", "float", "short", "byte", "character", "string", "objects",
    "boolean", "number", "object", "array", "stream", "intstream", "list", "map", "set", "system", "optional", "thread",
    "collectors", "comparator", "biginteger", "std", "json", "console", "date", "reflect", "symbol", "bigint",
}
# static calls that act like methods on their first argument
_AS_METHOD = {"sort", "fill", "copyof", "copyofrange", "aslist", "stream", "reverse", "shuffle", "swap", "binarysearch",
              "keys", "values", "entries", "max", "min", "frequency", "unmodifiablelist", "tostring", "equals", "hashcode",
              "deeptostring", "setall", "foreach", "isarray"}
_STD_ALGO_RANGE = {"sort", "stable_sort", "reverse", "fill", "accumulate", "iota", "unique", "min_element", "max_element",
                   "lower_bound", "upper_bound", "binary_search", "count", "find", "next_permutation", "partial_sum", "rotate",
                   "random_shuffle", "shuffle", "for_each", "transform", "copy", "equal", "is_sorted", "count_if", "find_if",
                   "all_of", "any_of", "none_of", "nth_element", "partial_sort", "inner_product", "adjacent_difference"}


def _parser(lang: str):
    if lang in _PARSERS:
        return _PARSERS[lang]
    from tree_sitter import Language, Parser
    if lang == "c":
        import tree_sitter_c as mod
    elif lang in ("cpp", "c++"):
        import tree_sitter_cpp as mod
    elif lang == "java":
        import tree_sitter_java as mod
    else:
        import tree_sitter_javascript as mod
    p = Parser(Language(mod.language()))
    _PARSERS[lang] = p
    return p


def parse(code: str, lang: str) -> ir.Module:
    lang = {"c++": "cpp", "js": "javascript"}.get(lang, lang)
    src = code.encode("utf-8")
    tree = _parser(lang).parse(src)
    conv = _Conv(src, lang)
    return ir.Module(body=conv.top(tree.root_node), language=lang)


def _num(text: str):
    t = text.replace("'", "").replace("_", "")
    t = re.sub(r"[uUlLfF]+$", "", t) if not t.lower().startswith("0x") else re.sub(r"[uUlL]+$", "", t)
    try:
        if t.lower().startswith("0x"):
            return int(t, 16), "int"
        if t.lower().startswith("0b"):
            return int(t, 2), "int"
        if re.fullmatch(r"-?\d+", t):
            return int(t), "int"
        return float(t), "float"
    except ValueError:
        return 0, "int"


_OPMAP = {"&&": "and", "||": "or", "===": "==", "!==": "!=", ">>>": ">>", "and": "and", "or": "or", "instanceof": "==", "??": "or"}


class _Conv:
    def __init__(self, src: bytes, lang: str):
        self.src = src
        self.lang = lang

    # ── helpers ────────────────────────────────────────────────────────────
    def t(self, n) -> str:
        return self.src[n.start_byte:n.end_byte].decode("utf-8", "replace") if n is not None else ""

    def line(self, n) -> int:
        return n.start_point[0] + 1

    def named(self, n) -> list:
        return [c for c in n.children if c.is_named and c.type != "comment"]

    def inner(self, d):
        """The declarator inside a pointer/reference/array declarator (a reference_declarator has no field name for it)."""
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            kids = [c for c in d.children if c.is_named and c.type != "comment"]
            nxt = kids[0] if kids else None
        return nxt

    def f(self, n, name):
        return n.child_by_field_name(name)

    def op(self, n) -> str:
        o = self.f(n, "operator")
        if o is not None:
            return self.t(o)
        for c in n.children:
            if not c.is_named and c.type not in ("(", ")", "[", "]", "{", "}", ",", ";"):
                return c.type
        return ""

    # ── top level ──────────────────────────────────────────────────────────
    def top(self, root) -> List[Any]:
        out: List[Any] = []
        for c in self.named(root):
            out.extend(self.stmt(c))
        return out

    def stmts(self, n) -> List[Any]:
        if n is None:
            return []
        if n.type in ("compound_statement", "block", "statement_block", "class_body", "declaration_list",
                      "field_declaration_list", "switch_block"):
            out: List[Any] = []
            for c in self.named(n):
                out.extend(self.stmt(c))
            return out
        return self.stmt(n)

    def effects(self, n) -> List[Any]:
        """Assignments and ++/-- hidden inside an expression (`a[i++]`, `x = y = 0`, `while (n--)`) as statements."""
        out: List[Any] = []
        if n is None:
            return out
        for c in n.children:
            if not c.is_named or c.type in ("lambda_expression", "arrow_function", "function_expression", "compound_statement",
                                            "statement_block", "block", "comment"):
                continue
            if c.type in ("update_expression", "assignment_expression", "augmented_assignment_expression"):
                out.extend(self.expr_stmts(c))
            out.extend(self.effects(c))
        return out

    # ── statements ─────────────────────────────────────────────────────────
    def stmt(self, n) -> List[Any]:
        ty = n.type
        ln = self.line(n)
        if ty in ("function_definition", "method_declaration", "function_declaration", "method_definition",
                  "generator_function_declaration", "constructor_declaration"):
            return self.funcdef(n)
        if ty in ("class_declaration", "class_specifier", "struct_specifier", "namespace_definition", "template_declaration",
                  "linkage_specification", "class_body", "declaration_list", "field_declaration_list", "enum_declaration",
                  "interface_declaration", "record_declaration", "export_statement", "access_specifier"):
            out: List[Any] = []
            for c in self.named(n):
                if c.type in ("identifier", "type_identifier", "template_parameter_list", "modifiers", "superclass",
                              "base_class_clause", "super_interfaces", "type_parameters", "access_specifier"):
                    continue
                out.extend(self.stmt(c))
            return out
        if ty in ("compound_statement", "block", "statement_block"):
            return [ir.Block(line=ln, body=self.stmts(n))]
        if ty in ("declaration", "local_variable_declaration", "lexical_declaration", "variable_declaration", "field_declaration",
                  "field_definition"):
            return self.declaration(n)
        if ty == "expression_statement":
            out = []
            for c in self.named(n):
                out.extend(self.expr_stmts(c))
                out.extend(self.effects(c))
            return out
        if ty == "if_statement":
            cond = self.cond(self.f(n, "condition"))
            pre_effects = self.effects(self.f(n, "condition"))
            body = self.stmts(self.f(n, "consequence"))
            alt = self.f(n, "alternative")
            orelse = []
            if alt is not None:
                inner = [c for c in self.named(alt)] if alt.type == "else_clause" else [alt]
                for c in inner:
                    orelse.extend(self.stmts(c))
            return pre_effects + [ir.If(line=ln, test=cond, body=body, orelse=orelse)]
        if ty == "for_statement":
            return self.for_stmt(n)
        if ty in ("for_range_loop", "enhanced_for_statement", "for_in_statement"):
            return self.foreach(n)
        if ty == "while_statement":
            return [ir.While(line=ln, test=self.cond(self.f(n, "condition")), body=self.stmts(self.f(n, "body")),
                             post=self.effects(self.f(n, "condition")))]
        if ty == "do_statement":
            return [ir.While(line=ln, test=self.cond(self.f(n, "condition")), body=self.stmts(self.f(n, "body")),
                             post=self.effects(self.f(n, "condition")), do_while=True)]
        if ty == "return_statement":
            kids = self.named(n)
            if not kids:
                return [ir.Return(line=ln)]
            k = kids[0]
            if k.type in ("assignment_expression", "augmented_assignment_expression"):      # return memo[k] = ...;
                return self.expr_stmts(k) + self.effects(k) + [ir.Return(line=ln, value=self.expr(self.f(k, "left")))]
            return self.effects(k) + [ir.Return(line=ln, value=self.expr(k))]
        if ty in ("throw_statement", "throw_expression"):
            return [ir.Return(line=ln)]
        if ty == "break_statement":
            return [ir.Break(line=ln)]
        if ty == "continue_statement":
            return [ir.Continue(line=ln)]
        if ty in ("switch_statement", "switch_expression"):
            return self.switch(n)
        if ty in ("try_statement", "try_with_resources_statement"):
            out = []
            for c in self.named(n):
                if c.type in ("compound_statement", "block", "statement_block"):
                    out.extend(self.stmts(c))
                elif c.type in ("catch_clause", "finally_clause", "catch_declaration"):
                    for cc in self.named(c):
                        if cc.type in ("compound_statement", "block", "statement_block"):
                            out.extend(self.stmts(cc))
            return out
        if ty in ("labeled_statement",):
            return [x for c in self.named(n) if c.type != "statement_identifier" and c.type != "identifier" for x in self.stmt(c)]
        return []

    def switch(self, n) -> List[Any]:
        body = self.f(n, "body") or n
        arms: List[List[Any]] = []
        for c in self.named(body):
            if c.type in ("case_statement", "switch_block_statement_group", "switch_rule", "switch_case", "switch_default"):
                inner = []
                for cc in self.named(c):
                    if cc is self.f(c, "value") or cc is self.f(c, "label"):
                        continue
                    inner.extend(self.stmt(cc))
                arms.append(inner)
        out: List[Any] = []
        for arm in reversed(arms):
            out = [ir.If(test=ir.Unknown(), body=arm, orelse=out)]
        return out

    def funcdef(self, n) -> List[Any]:
        ln = self.line(n)
        name = ""
        params: list = []
        body_node = self.f(n, "body")
        if n.type == "function_definition":                     # C / C++
            decl = self.f(n, "declarator")
            fd = decl
            while fd is not None and fd.type not in ("function_declarator",):
                fd = self.f(fd, "declarator")
            if fd is not None:
                name = self.t(self.f(fd, "declarator")).split("::")[-1]
                params = self.c_params(self.f(fd, "parameters"))
        else:                                                   # Java / JavaScript
            name = self.t(self.f(n, "name"))
            pn = self.f(n, "parameters")
            params = self.j_params(pn) if pn is not None else []
        if body_node is None:
            return []
        return [ir.FuncDef(line=ln, name=name, params=params, body=self.stmts(body_node), decorators=[])]

    def c_params(self, pl) -> list:
        out = []
        if pl is None:
            return out
        for p in self.named(pl):
            if p.type not in ("parameter_declaration", "optional_parameter_declaration"):
                continue
            decl = self.f(p, "declarator")
            tnode = self.f(p, "type")
            ttext = self.t(tnode)
            quals = " ".join(self.t(c) for c in self.named(p) if c.type == "type_qualifier")
            marks, d = "", decl
            while d is not None and d.type not in ("identifier", "field_identifier"):
                if d.type == "pointer_declarator":
                    marks += "*"
                elif d.type == "array_declarator":
                    marks += "[]"
                d = self.inner(d)
            name = self.t(d) if d is not None else ""
            if name:
                out.append((name, (quals + " " + ttext + marks).strip()))
        return out

    def j_params(self, pl) -> list:
        out = []
        for p in self.named(pl):
            if p.type == "formal_parameter" or p.type == "receiver_parameter":
                nm = self.f(p, "name")
                out.append((self.t(nm), self.t(self.f(p, "type"))))
            elif p.type == "spread_parameter":
                kids = self.named(p)
                out.append((self.t(kids[-1]) if kids else "", None))
            elif p.type == "identifier":
                out.append((self.t(p), None))
            elif p.type in ("assignment_pattern",):
                out.append((self.t(self.f(p, "left")), None))
            elif p.type in ("rest_pattern", "required_parameter", "optional_parameter"):
                kids = self.named(p)
                out.append((self.t(kids[0]) if kids else "", None))
        return out

    # ── declarations ───────────────────────────────────────────────────────
    def decl_name(self, d):
        while d is not None and d.type not in ("identifier", "field_identifier", "structured_binding_declarator", "array_pattern",
                                               "object_pattern"):
            nxt = self.f(d, "declarator") or self.f(d, "name")
            if nxt is None:
                kids = self.named(d)
                nxt = kids[0] if kids else None
            d = nxt
        return d

    def base_type(self, tnode) -> str:
        """The name of the type, without arguments: vector, unordered_map, int, String ..."""
        if tnode is None:
            return ""
        txt = self.t(tnode)
        txt = re.sub(r"\b(const|static|final|unsigned|signed|volatile|struct|register)\b", " ", txt)
        m = re.match(r"\s*([A-Za-z_][\w:\.]*)", txt)
        return (m.group(1).split("::")[-1].split(".")[-1] if m else txt.strip())

    def declaration(self, n) -> List[Any]:
        ln = self.line(n)
        tnode = self.f(n, "type")
        ttext = self.t(tnode)
        quals = " ".join(self.t(c) for c in self.named(n) if c.type == "type_qualifier")
        out: List[Any] = []
        decls = [c for c in n.children if c.is_named and (c.type in ("init_declarator", "variable_declarator", "identifier",
                                                                       "array_declarator", "pointer_declarator",
                                                                       "function_declarator", "reference_declarator",
                                                                       "structured_binding_declarator", "field_identifier",
                                                                       "assignment_expression"))]
        if n.type in ("lexical_declaration", "variable_declaration"):
            decls = [c for c in self.named(n) if c.type == "variable_declarator"]
        for d in decls:
            out.extend(self.one_declarator(d, tnode, (quals + " " + ttext).strip(), ln))
            out.extend(self.effects(d))
        return out

    def one_declarator(self, d, tnode, ttext: str, ln: int) -> List[Any]:
        base = self.base_type(tnode)
        # C++ `vector<int> dp(n);` is parsed as a function declarator whose "parameters" are the constructor arguments
        if d.type == "function_declarator":
            name = self.t(self.f(d, "declarator"))
            args = []
            for p in self.named(self.f(d, "parameters")) if self.f(d, "parameters") is not None else []:
                tn = self.f(p, "type")
                if tn is not None and self.f(p, "declarator") is None:
                    txt = self.t(tn)
                    args.append(ir.Const(value=_num(txt)[0], kind="int") if re.fullmatch(r"\d+", txt) else ir.Name(line=ln, id=txt))
            return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)], value=ir.New(line=ln, type_name=base, args=args),
                              decl_type=ttext)]
        init = self.f(d, "value")
        target = self.decl_name(d)
        if target is None:
            return []
        if target.type in ("structured_binding_declarator", "array_pattern", "object_pattern"):
            names = [ir.Name(id=self.t(c)) for c in self.named(target)]
            tgt = ir.Lit(line=ln, kind="tuple", elts=names)
            return [ir.Assign(line=ln, targets=[tgt], value=self.expr(init) if init is not None else ir.Unknown(), decl_type=None)]
        name = self.t(target)
        # arrays and pointers: the declared type needs the marks
        marks, w = "", d
        while w is not None and w is not target:
            if w.type == "pointer_declarator":
                marks += "*"
            elif w.type == "array_declarator":
                marks += "[]"
            w = self.inner(w) if w.type in ("pointer_declarator", "array_declarator", "reference_declarator", "init_declarator")                 else (self.f(w, "declarator") or self.f(w, "name"))
        if d.type == "variable_declarator":                      # Java / JS; Java also carries `int a[]`
            dims = self.f(d, "dimensions")
            if dims is not None:
                marks += "[]"
        decl_type = ttext + marks
        arr = d if d.type == "array_declarator" else (self.f(d, "declarator") if d.type == "init_declarator" else None)
        if arr is not None and arr.type == "array_declarator" and init is None:
            size = self.f(arr, "size")
            return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)],
                              value=ir.New(line=ln, type_name=base, args=[self.expr(size)] if size is not None else [ir.Const(value=1)],
                                           is_array=True), decl_type=decl_type)]
        if init is None:
            if base.lower() in lib.COLLECTION_KIND or "<" in ttext:
                return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)], value=ir.New(line=ln, type_name=base, args=[]),
                                  decl_type=decl_type)]
            return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)], value=ir.Const(value=0), decl_type=decl_type)]
        if init.type == "argument_list":                           # C++ constructor arguments
            return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)],
                              value=ir.New(line=ln, type_name=base, args=[self.expr(c) for c in self.named(init)]), decl_type=decl_type)]
        if init.type in ("arrow_function", "function_expression", "function"):
            lam = self.lambda_(init)
            return [ir.FuncDef(line=ln, name=name, params=[(p, None) for p in lam.params], body=lam.body)]
        return [ir.Assign(line=ln, targets=[ir.Name(line=ln, id=name)], value=self.expr(init), decl_type=decl_type)]

    # ── loops ──────────────────────────────────────────────────────────────
    def for_stmt(self, n) -> List[Any]:
        ln = self.line(n)
        init = self.f(n, "initializer") or self.f(n, "init")
        cond = self.f(n, "condition")
        upd = self.f(n, "update") or self.f(n, "increment")
        body = self.f(n, "body")
        pre: List[Any] = []
        if init is not None:
            if init.type in ("declaration", "local_variable_declaration", "lexical_declaration", "variable_declaration"):
                pre = self.declaration(init)
            elif init.type == "expression_statement":
                for c in self.named(init):
                    pre.extend(self.expr_stmts(c))
            else:
                pre = self.expr_stmts(init)
        c = ir.Const(value=True, kind="bool")
        if cond is not None:
            if cond.type == "expression_statement":
                kids = self.named(cond)
                c = self.expr(kids[0]) if kids else c
            else:
                c = self.cond(cond)
        post = self.expr_stmts(upd) if upd is not None else []
        if cond is not None:
            post = post + self.effects(cond)
        loop = ir.While(line=ln, test=c, body=self.stmts(body), post=post)
        return [ir.Block(line=ln, body=pre + [loop])]

    def foreach(self, n) -> List[Any]:
        ln = self.line(n)
        if n.type == "for_range_loop":
            d = self.f(n, "declarator")
            tgt = self.decl_name(d)
            if tgt is not None and tgt.type == "structured_binding_declarator":
                var = ir.Lit(line=ln, kind="tuple", elts=[ir.Name(id=self.t(c)) for c in self.named(tgt)])
            else:
                var = ir.Name(line=ln, id=self.t(tgt))
            it = self.f(n, "right")
        elif n.type == "enhanced_for_statement":
            var = ir.Name(line=ln, id=self.t(self.f(n, "name")))
            it = self.f(n, "value")
        else:                                                      # JS for...of / for...in
            left = self.f(n, "left")
            tgt = left
            if left is not None and left.type in ("lexical_declaration", "variable_declaration"):
                kids = [c for c in self.named(left) if c.type == "variable_declarator"]
                tgt = self.f(kids[0], "name") if kids else left
            if tgt is not None and tgt.type in ("array_pattern",):
                var = ir.Lit(line=ln, kind="tuple", elts=[ir.Name(id=self.t(c)) for c in self.named(tgt)])
            else:
                var = ir.Name(line=ln, id=self.t(tgt))
            it = self.f(n, "right")
        return [ir.ForEach(line=ln, var=var, iter=self.expr(it), body=self.stmts(self.f(n, "body")))]

    # ── expression statements ──────────────────────────────────────────────
    def expr_stmts(self, n) -> List[Any]:
        ty = n.type
        ln = self.line(n)
        if ty in ("comma_expression", "sequence_expression"):
            out = []
            for c in self.named(n):
                out.extend(self.expr_stmts(c))
            return out
        if ty == "parenthesized_expression":
            kids = self.named(n)
            return self.expr_stmts(kids[0]) if kids else []
        if ty == "update_expression":
            arg = self.f(n, "argument") or (self.named(n)[0] if self.named(n) else None)
            op = "-" if "--" in self.t(n) else "+"
            return [ir.Assign(line=ln, targets=[self.expr(arg)], value=ir.Const(value=1), op=op)]
        if ty in ("assignment_expression", "augmented_assignment_expression"):
            left, right = self.f(n, "left"), self.f(n, "right")
            o = self.op(n)
            if left is not None and left.type in ("array_pattern",):
                tgt = ir.Lit(line=ln, kind="tuple", elts=[self.expr(c) for c in self.named(left)])
                val = self.expr(right)
                if isinstance(val, ir.Lit):
                    val = ir.Lit(line=ln, kind="tuple", elts=val.elts)
                return [ir.Assign(line=ln, targets=[tgt], value=val)]
            tgt = self.expr(left)
            if o in ("=", ""):
                return [ir.Assign(line=ln, targets=[tgt], value=self.expr(right))]
            opn = o[:-1]
            if opn in ("||", "&&", "??"):
                return [ir.Assign(line=ln, targets=[tgt], value=self.expr(right))]
            return [ir.Assign(line=ln, targets=[tgt], value=self.expr(right), op=_OPMAP.get(opn, opn))]
        if ty in ("call_expression", "method_invocation", "await_expression", "new_expression", "object_creation_expression"):
            return [ir.ExprStmt(line=ln, expr=self.expr(n))]
        if ty in ("identifier", "number", "string", "true", "false"):
            return []
        return [ir.ExprStmt(line=ln, expr=self.expr(n))]

    # ── expressions ────────────────────────────────────────────────────────
    def cond(self, n) -> Any:
        if n is None:
            return ir.Const(value=True, kind="bool")
        if n.type in ("condition_clause", "parenthesized_expression"):
            kids = self.named(n)
            return self.expr(kids[-1]) if kids else ir.Const(value=True, kind="bool")
        return self.expr(n)

    def expr(self, n) -> Any:
        if n is None:
            return ir.Const(value=None, kind="none")
        ty = n.type
        ln = self.line(n)
        if ty in ("identifier", "this", "field_identifier", "property_identifier", "type_identifier", "namespace_identifier",
                  "shorthand_property_identifier", "statement_identifier", "undefined"):
            if ty == "undefined":
                return ir.Const(line=ln, value=None, kind="none")
            return ir.Name(line=ln, id=self.t(n))
        if ty in ("qualified_identifier", "scoped_identifier", "scoped_type_identifier"):
            return ir.Name(line=ln, id=self.t(n).split("::")[-1].split(".")[-1])
        if ty in ("number_literal", "decimal_integer_literal", "hex_integer_literal", "octal_integer_literal",
                  "binary_integer_literal", "decimal_floating_point_literal", "hex_floating_point_literal", "number",
                  "float_literal", "integer_literal"):
            v, k = _num(self.t(n))
            return ir.Const(line=ln, value=v, kind=k)
        if ty in ("string_literal", "string", "char_literal", "character_literal", "template_string", "raw_string_literal",
                  "concatenated_string", "text_block", "regex"):
            return ir.Const(line=ln, value="", kind="str")
        if ty in ("true", "false"):
            return ir.Const(line=ln, value=(ty == "true"), kind="bool")
        if ty in ("null", "nullptr", "null_literal"):
            return ir.Const(line=ln, value=None, kind="none")
        if ty == "parenthesized_expression":
            kids = self.named(n)
            return self.expr(kids[0]) if kids else ir.Unknown()
        if ty in ("cast_expression", "as_expression", "non_null_expression", "await_expression", "spread_element",
                  "type_assertion", "satisfies_expression"):
            v = self.f(n, "value")
            kids = self.named(n)
            return self.expr(v if v is not None else (kids[-1] if kids else None))
        if ty == "sizeof_expression":
            return ir.Const(line=ln, value=8, kind="int")
        if ty == "binary_expression":
            o = self.op(n)
            return ir.BinOp(line=ln, op=_OPMAP.get(o, o), left=self.expr(self.f(n, "left")), right=self.expr(self.f(n, "right")))
        if ty in ("unary_expression", "not_expression"):
            o = self.op(n)
            arg = self.f(n, "argument") or self.f(n, "operand") or (self.named(n)[-1] if self.named(n) else None)
            if o == "!":
                return ir.UnOp(line=ln, op="not", operand=self.expr(arg))
            if o in ("*", "&", "+", "typeof", "void", "delete", "await"):
                return self.expr(arg)
            return ir.UnOp(line=ln, op=o if o in ("-", "~") else "-", operand=self.expr(arg))
        if ty == "update_expression":
            arg = self.f(n, "argument") or (self.named(n)[0] if self.named(n) else None)
            return self.expr(arg)
        if ty in ("assignment_expression", "augmented_assignment_expression"):
            return self.expr(self.f(n, "right"))
        if ty in ("conditional_expression", "ternary_expression"):
            return ir.Cond(line=ln, test=self.expr(self.f(n, "condition")), a=self.expr(self.f(n, "consequence")),
                           b=self.expr(self.f(n, "alternative")))
        if ty in ("subscript_expression", "array_access"):
            base = self.f(n, "argument") or self.f(n, "object") or self.f(n, "array")
            idx = self.f(n, "index")
            if idx is None:
                ind = self.f(n, "indices")
                kids = self.named(ind) if ind is not None else []
                idx = kids[0] if kids else None
            return ir.Index(line=ln, base=self.expr(base), index=self.expr(idx))
        if ty in ("field_expression", "member_expression", "field_access", "scoped_call_expression"):
            base = self.f(n, "argument") or self.f(n, "object")
            name = self.f(n, "field") or self.f(n, "property")
            return ir.Attr(line=ln, base=self.expr(base), name=self.t(name))
        if ty in ("call_expression", "method_invocation"):
            return self.call(n)
        if ty in ("lambda_expression", "arrow_function", "function_expression", "function"):
            return self.lambda_(n)
        if ty in ("new_expression", "object_creation_expression", "array_creation_expression"):
            return self.new(n)
        if ty in ("initializer_list", "array_initializer", "array"):
            elts = self.named(n)
            if ty == "array" and len(elts) == 1 and elts[0].type == "spread_element":
                return ir.Call(line=ln, fn="list", args=[self.expr(elts[0])])
            return ir.Lit(line=ln, kind="list", elts=[self.expr(c) for c in elts])
        if ty in ("object", "dictionary"):
            return ir.Lit(line=ln, kind="dict", elts=[self.expr(self.f(c, "value")) for c in self.named(n) if c.type == "pair"])
        if ty in ("comma_expression", "sequence_expression"):
            kids = self.named(n)
            return self.expr(kids[-1]) if kids else ir.Unknown()
        if ty == "template_function":
            return ir.Name(line=ln, id=self.t(self.f(n, "name")))
        if ty == "generic_type":
            return ir.Name(line=ln, id=self.base_type(n))
        return ir.Unknown(line=ln, text=ty)

    def args(self, a) -> list:
        return [self.expr(c) for c in self.named(a)] if a is not None else []

    def call(self, n) -> Any:
        ln = self.line(n)
        if n.type == "method_invocation":                           # Java
            obj = self.f(n, "object")
            name = self.t(self.f(n, "name"))
            args = self.args(self.f(n, "arguments"))
            if obj is not None:
                o = self.expr(obj)
                if isinstance(o, ir.Name) and o.id.lower() in _STATIC and o.id[:1].isupper():
                    return self.static_call(name, o.id, args, ln)
                return ir.Call(line=ln, fn=name, recv=o, args=args)
            return ir.Call(line=ln, fn=name, args=args)
        fn = self.f(n, "function")
        args = self.args(self.f(n, "arguments"))
        if fn is None:
            return ir.Unknown(line=ln)
        if fn.type in ("identifier", "qualified_identifier", "scoped_identifier"):
            name = self.t(fn).split("::")[-1]
            if self.t(fn).startswith("std::") and name in _STD_ALGO_RANGE and args:
                return self.range_algo(name, args, ln)
            if name in _STD_ALGO_RANGE and args and self.lang in ("c", "cpp") and self.is_range_call(args):
                return self.range_algo(name, args, ln)
            if name == "Array" and self.lang == "javascript":
                return ir.New(line=ln, type_name="array", args=args)
            return ir.Call(line=ln, fn=name, args=args)
        if fn.type == "template_function":
            name = self.t(self.f(fn, "name")).split("::")[-1]
            if name in ("static_cast", "reinterpret_cast", "const_cast", "dynamic_cast"):
                return args[0] if args else ir.Unknown()
            if name.lower() in lib.COLLECTION_KIND:
                return ir.New(line=ln, type_name=name, args=args)
            return ir.Call(line=ln, fn=name, args=args)
        if fn.type in ("field_expression", "member_expression"):
            obj = self.f(fn, "argument") or self.f(fn, "object")
            name = self.t(self.f(fn, "field") or self.f(fn, "property"))
            o = self.expr(obj)
            if isinstance(o, ir.Name) and o.id.lower() in _STATIC and o.id[:1].isupper():
                return self.static_call(name, o.id, args, ln)
            return ir.Call(line=ln, fn=name, recv=o, args=args)
        return ir.Call(line=ln, fn="<call>", recv=self.expr(fn), args=args)

    def is_range_call(self, args) -> bool:
        return any(isinstance(a, ir.Call) and a.fn in ("begin", "end", "rbegin", "rend") for a in args)

    def range_algo(self, name: str, args: list, ln: int) -> Any:
        """std::sort(v.begin(), v.end(), ...): a call on the container the iterators belong to."""
        recv = None
        for a in args:
            if isinstance(a, ir.Call) and a.fn in ("begin", "end", "rbegin", "rend") and a.recv is not None:
                recv = a.recv
                break
        rest = [a for a in args if not (isinstance(a, ir.Call) and a.fn in ("begin", "end", "rbegin", "rend"))]
        if recv is None:
            return ir.Call(line=ln, fn=name, args=args)
        return ir.Call(line=ln, fn=name, recv=recv, args=rest)

    def static_call(self, name: str, cls: str, args: list, ln: int) -> Any:
        low = name.lower()
        c = cls.lower()
        if c == "array" and low == "from":
            if args and isinstance(args[0], ir.Lit) and args[0].kind == "dict":
                size = args[0].elts[0] if args[0].elts else ir.Const(value=1)
                cb = args[1] if len(args) > 1 else None
                if isinstance(cb, ir.Lambda) and cb.body and isinstance(cb.body[-1], ir.Return) and cb.body[-1].value is not None:
                    # Array.from({length: n}, () => row): n rows, each as built by the callback
                    gen = ir.Gen(line=ln, var=ir.Name(id="_"), iter=ir.Call(fn="range", args=[size]), conds=[])
                    return ir.Comp(line=ln, kind="list", elt=cb.body[-1].value, gens=[gen])
                return ir.New(line=ln, type_name="array", args=[size])
            return ir.Call(line=ln, fn="list", args=args[:1])
        if c in ("arrays", "collections", "object", "stream", "intstream", "list", "set", "map") and low in _AS_METHOD and args:
            return ir.Call(line=ln, fn=name, recv=args[0], args=args[1:])
        if c == "arrays" and low == "stream" and args:
            return ir.Call(line=ln, fn="stream", recv=args[0], args=[])
        return ir.Call(line=ln, fn=name, args=args)

    def lambda_(self, n) -> ir.Lambda:
        ln = self.line(n)
        params: List[str] = []
        pn = self.f(n, "parameters") or self.f(n, "parameter")
        if pn is not None:
            if pn.type == "identifier":
                params = [self.t(pn)]
            else:
                for p in self.named(pn):
                    if p.type == "identifier":
                        params.append(self.t(p))
                    elif p.type in ("parameter_declaration", "formal_parameter"):
                        d = self.f(p, "declarator") or self.f(p, "name")
                        d = self.decl_name(d) if d is not None else None
                        params.append(self.t(d))
                    elif p.type == "inferred_parameters":
                        params.extend(self.t(c) for c in self.named(p))
        else:
            d = self.f(n, "declarator")
            if d is not None and self.f(d, "parameters") is not None:
                params = [nm for nm, _ in self.c_params(self.f(d, "parameters"))]
        body = self.f(n, "body")
        if body is None:
            return ir.Lambda(line=ln, params=params, body=[])
        if body.type in ("compound_statement", "block", "statement_block"):
            return ir.Lambda(line=ln, params=params, body=self.stmts(body))
        return ir.Lambda(line=ln, params=params, body=[ir.Return(line=ln, value=self.expr(body))])

    def new(self, n) -> Any:
        ln = self.line(n)
        tnode = self.f(n, "type") or self.f(n, "constructor")
        name = self.base_type(tnode) if tnode is not None else ""
        if n.type == "array_creation_expression":                    # Java new int[n][m]
            dims = [self.expr(self.named(d)[0]) for d in n.children if d.type == "dimensions_expr" and self.named(d)]
            return ir.New(line=ln, type_name=name or "array", args=dims or [ir.Const(value=1)], is_array=True)
        decl = self.f(n, "declarator")                               # C++ new int[n]
        if decl is not None and decl.type == "new_declarator":
            dims = [self.expr(c) for c in self.named(decl) if c.type not in ("type_identifier", "primitive_type")]
            return ir.New(line=ln, type_name=name, args=dims or [ir.Const(value=1)], is_array=True)
        return ir.New(line=ln, type_name=name, args=self.args(self.f(n, "arguments")))
