"""Input/output schemas and starter-code generation, so players write only the logic.

A generated question declares its input structure in a tiny notation, one entry per input line:

    n:int                    one integer on its own line
    n:int q:int              several integers on one line
    s:str                    one string (the whole line)
    arr:int[n]               n integers on one line        (str[n]: n words on one line)
    queries:int[q]/lines     q lines, one integer each     (str[k]/lines: k lines of text)
    grid:int[r][c]           r lines of c integers each

and its output as one of:  int | str | int[] | int[]/lines | str[]/lines

From that, starter code (function stub plus a main that reads stdin and prints the answer) is
generated for python, cpp, java, javascript and c, and the same schema parses test inputs when
verifying a question, so the code players run is the code that was checked.

Every starter has the same shape, which the editor relies on to lock it:

    <imports>
    <the function signature line>          locked
        // Write your logic here           the only part a player edits (plus helpers above the marker)
    <closing of the function>

    // ===== Reads the input and prints the answer. You do not need to edit below. =====   locked from here on
    <the reader, the call of the function with the parsed arguments, and the printing of its result>

This is the public copy used by the running service. qgen/scaffold.py is the private one used when questions are
built; keep the four older languages identical in both.
"""

import keyword
import re
from dataclasses import dataclass

MAX_VARIABLES = 8
RESERVED = set(keyword.kwlist) | {
    "int", "long", "double", "float", "char", "string", "str", "list", "new", "class", "public", "static",
    "void", "var", "let", "const", "function", "result", "lines", "idx", "main", "input", "print", "len",
    "min", "max", "sum", "vector", "return", "this", "default", "switch", "case", "do", "bool", "true", "false",
    # C keywords that Python's keyword list does not already cover
    "short", "unsigned", "signed", "goto", "sizeof", "struct", "union", "enum", "typedef", "extern", "register",
    "auto", "volatile", "inline", "restrict",
}
_TOKEN = re.compile(r"^([a-z][a-z0-9_]{0,15}):(int|str)(?:\[(\w+)\](?:\[(\w+)\])?(/lines)?)?$")
_OUTPUT = re.compile(r"^(int|str)(\[\](/lines)?)?$")
LANGUAGES = ("python", "cpp", "java", "javascript", "c")
MARKER_TEXT = "===== Reads the input and prints the answer. You do not need to edit below. ====="
C_RESULT_CAPACITY = 1 << 20   # how many values (or characters) the result buffer of a C starter holds


@dataclass
class Var:
    name: str
    base: str            # "int" or "str"
    kind: str            # "scalar", "array", "lines" or "matrix"
    length: str | None   # count of lines for "lines"/"matrix": an earlier int variable or a literal


@dataclass
class Output:
    base: str            # "int" or "str"
    kind: str            # "scalar", "array" (space separated) or "lines" (one per line)


def parse_input_schema(text: str) -> list[list[Var]]:
    schema: list[list[Var]] = []
    known: dict[str, Var] = {}
    for raw in text.strip().splitlines():
        line = []
        for token in raw.split():
            match = _TOKEN.match(token)
            if not match:
                raise ValueError(f"bad schema token '{token}'")
            name, base, length, cols, per_line = match.groups()
            if name in RESERVED or name in known:
                raise ValueError(f"variable name '{name}' is reserved or repeated")
            if length is None:
                var = Var(name, base, "scalar", None)
            elif cols is not None:
                if base != "int" or per_line:
                    raise ValueError("a matrix must be written int[rows][cols]")
                var = Var(name, base, "matrix", length)
            elif per_line:
                var = Var(name, base, "lines", length)
            else:
                var = Var(name, base, "array", length)
            if var.length is not None and not (
                var.length.isdigit() or (var.length in known and known[var.length].kind == "scalar" and known[var.length].base == "int")
            ):
                raise ValueError(
                    f"'{name}' needs its count to be an earlier int variable or a number: declare `{var.length}:int` on an "
                    f"earlier line before `{token}`"
                )
            known[name] = var
            line.append(var)
        if len(line) > 1 and any(v.kind != "scalar" for v in line):
            raise ValueError("only single values may share a line")
        if line:
            schema.append(line)
    if not schema or len(known) > MAX_VARIABLES:
        raise ValueError(f"schema must declare 1 to {MAX_VARIABLES} variables")
    return schema


def parse_output_schema(text: str) -> Output:
    match = _OUTPUT.match(text.strip())
    if not match:
        raise ValueError(f"bad output type '{text.strip()}'")
    base, brackets, per_line = match.groups()
    return Output(base, "scalar" if not brackets else ("lines" if per_line else "array"))


def variables(schema: list[list[Var]]) -> list[Var]:
    return [v for line in schema for v in line]


def _count(length: str, env: dict) -> int:
    return int(length) if length.isdigit() else env[length]


def parse_input_text(schema: list[list[Var]], text: str) -> list:
    """Parse an input text into the argument list, strictly: every line must be accounted for."""
    lines = text.strip("\n").split("\n")
    idx, env, args = 0, {}, []

    def take(n=1):
        nonlocal idx
        if idx + n > len(lines):
            raise ValueError("input has fewer lines than the schema")
        chunk = lines[idx:idx + n]
        idx += n
        return chunk

    def convert(token, base):
        return int(token) if base == "int" else token

    for line in schema:
        if len(line) > 1:
            tokens = take()[0].split()
            if len(tokens) != len(line):
                raise ValueError("wrong number of values on a line")
            values = [convert(t, v.base) for t, v in zip(tokens, line)]
        else:
            v = line[0]
            if v.kind == "scalar":
                values = [convert(take()[0].strip(), v.base)]
            elif v.kind == "array":
                values = [[convert(t, v.base) for t in take()[0].split()]]
            elif v.kind == "lines":
                values = [[convert(s.strip(), v.base) for s in take(_count(v.length, env))]]
            else:
                values = [[[int(t) for t in row.split()] for row in take(_count(v.length, env))]]
        for v, value in zip(line, values):
            env[v.name] = value
            args.append(value)
    if any(rest.strip() for rest in lines[idx:]):
        raise ValueError("input has more lines than the schema")
    return args


def render_output(out: Output, value) -> str:
    if out.kind == "scalar":
        if out.base == "int" and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError("expected an int")
        if out.base == "str" and not isinstance(value, str):
            raise ValueError("expected a str")
        return str(value)
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected a list")
    if out.base == "int" and not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        raise ValueError("expected a list of ints")
    if out.base == "str" and not all(isinstance(x, str) for x in value):
        raise ValueError("expected a list of strs")
    return ("\n" if out.kind == "lines" else " ").join(str(x) for x in value)


def type_name(v: Var | Output) -> str:
    kind = v.kind
    inner = "int" if v.base == "int" else "str"
    if kind == "scalar":
        return inner
    if kind == "matrix":
        return "List[List[int]]"
    return f"List[{inner}]"


def parameters(schema: list[list[Var]], sample_args: list) -> list[dict]:
    notes = {"scalar": "A value", "array": "A list of values", "lines": "A list of values, one per input line", "matrix": "A grid of integers"}
    return [
        {"name": v.name, "type": type_name(v), "description": notes[v.kind], "example": repr(value)}
        for v, value in zip(variables(schema), sample_args)
    ]


# ───────────────────────────── starter code ─────────────────────────────

def _py_parse(schema):
    out = ["lines = sys.stdin.read().split('\\n')", "idx = 0"]
    for line in schema:
        if len(line) > 1:
            out.append("tokens = lines[idx].split(); idx += 1")
            for i, v in enumerate(line):
                out.append(f"{v.name} = {'int(tokens[%d])' % i if v.base == 'int' else 'tokens[%d]' % i}")
            continue
        v = line[0]
        conv = "int" if v.base == "int" else "str"
        if v.kind == "scalar":
            out.append(f"{v.name} = {conv}(lines[idx].strip()); idx += 1")
        elif v.kind == "array":
            out.append(f"{v.name} = [{conv}(t) for t in lines[idx].split()]; idx += 1")
        elif v.kind == "lines":
            out.append(f"{v.name} = [{conv}(lines[idx + i].strip()) for i in range({v.length})]; idx += {v.length}")
        else:
            out.append(f"{v.name} = [[int(t) for t in lines[idx + i].split()] for i in range({v.length})]; idx += {v.length}")
    return out


def _py_print(out):
    if out.kind == "scalar":
        return "print(result)"
    sep = "'\\n'" if out.kind == "lines" else "' '"
    return f"print({sep}.join(str(x) for x in result))"


def python_code(schema, out, fn, stub=None):
    params = ", ".join(v.name for v in variables(schema))
    # an untouched stub for a list result returns an empty list, so running it before writing anything is a wrong answer, not a crash
    stub = stub or f"def {fn}({params}):\n    # Write your logic here\n    {'pass' if out.kind == 'scalar' else 'return []'}\n"
    body = "\n".join("    " + s for s in _py_parse(schema))
    call = f"    result = {fn}({params})\n    {_py_print(out)}\n"
    return (
        f"import sys\n\n\n{stub.rstrip()}\n\n\n"
        f"# ===== Reads the input and prints the answer. You do not need to edit below. =====\n"
        f"def main():\n{body}\n{call}\n\nif __name__ == '__main__':\n    main()\n"
    )


def _js_parse(schema):
    out = ["const lines = require('fs').readFileSync(0, 'utf8').split('\\n');", "let idx = 0;"]
    for line in schema:
        if len(line) > 1:
            tmp = f"_t{len(out)}"
            out.append(f"const {tmp} = lines[idx++].trim().split(/\\s+/);")
            for i, v in enumerate(line):
                out.append(f"const {v.name} = {'Number(%s[%d])' % (tmp, i) if v.base == 'int' else '%s[%d]' % (tmp, i)};")
            continue
        v = line[0]
        conv = "Number" if v.base == "int" else "String"
        if v.kind == "scalar":
            out.append(f"const {v.name} = {conv}(lines[idx++].trim());")
        elif v.kind == "array":
            out.append(f"const {v.name} = lines[idx++].trim().split(/\\s+/).filter(x => x.length).map({conv});")
        elif v.kind == "lines":
            out.append(f"const {v.name} = []; for (let i = 0; i < {v.length}; i++) {v.name}.push({conv}(lines[idx++].trim()));")
        else:
            out.append(f"const {v.name} = []; for (let i = 0; i < {v.length}; i++) {v.name}.push(lines[idx++].trim().split(/\\s+/).map(Number));")
    return out


def javascript_code(schema, out, fn, stub=None):
    params = ", ".join(v.name for v in variables(schema))
    stub = stub or f"function {fn}({params}) {{\n    // Write your logic here\n{'' if out.kind == 'scalar' else '    return [];' + chr(10)}}}\n"
    parse = "\n".join(_js_parse(schema))
    sep = "'\\n'" if out.kind == "lines" else "' '"
    show = "console.log(String(result));" if out.kind == "scalar" else f"console.log(result.join({sep}));"
    return (
        f"{stub.rstrip()}\n\n// ===== Reads the input and prints the answer. You do not need to edit below. =====\n"
        f"{parse}\nconst result = {fn}({params});\n{show}\n"
    )


_CPP_TYPE = {("int", "scalar"): "long long", ("str", "scalar"): "string", ("int", "array"): "vector<long long>",
             ("str", "array"): "vector<string>", ("int", "lines"): "vector<long long>", ("str", "lines"): "vector<string>",
             ("int", "matrix"): "vector<vector<long long>>"}
_CPP_DEFAULT = {"scalar": {"int": "0", "str": '""'}}


def _cpp_param(v):
    t = _CPP_TYPE[(v.base, v.kind)]
    return f"{t} {v.name}" if v.kind == "scalar" else f"const {t}& {v.name}"


def cpp_code(schema, out, fn, stub=None):
    ret = _CPP_TYPE[(out.base, "scalar" if out.kind == "scalar" else "array")]
    stub = stub or (
        f"{ret} {fn}({', '.join(_cpp_param(v) for v in variables(schema))}) {{\n    // Write your logic here\n"
        f"    return {_CPP_DEFAULT['scalar'][out.base] if out.kind == 'scalar' else '{}'};\n}}\n"
    )
    body = []
    for line in schema:
        if len(line) > 1:
            tmp = f"t{len(body)}"
            for v in line:
                body.append(f"{_CPP_TYPE[(v.base, 'scalar')]} {v.name};")
            body.append(f"{{ auto {tmp} = _words(lines[idx++]);")
            for i, v in enumerate(line):
                body.append(f"  {v.name} = {'stoll(%s[%d])' % (tmp, i) if v.base == 'int' else '%s[%d]' % (tmp, i)};")
            body.append("}")
            continue
        v = line[0]
        t = _CPP_TYPE[(v.base, v.kind)]
        if v.kind == "scalar":
            body.append(f"{t} {v.name} = {'stoll(_trim(lines[idx++]))' if v.base == 'int' else '_trim(lines[idx++])'};")
        elif v.kind == "array":
            body.append(f"{t} {v.name} = {'_ints' if v.base == 'int' else '_words'}(lines[idx++]);")
        elif v.kind == "lines":
            item = "stoll(_trim(lines[idx++]))" if v.base == "int" else "_trim(lines[idx++])"
            body.append(f"{t} {v.name}; for (long long i = 0; i < (long long){v.length}; i++) {v.name}.push_back({item});")
        else:
            body.append(f"{t} {v.name}; for (long long i = 0; i < (long long){v.length}; i++) {v.name}.push_back(_ints(lines[idx++]));")
    args = ", ".join(v.name for v in variables(schema))
    if out.kind == "scalar":
        show = 'cout << result << "\\n";'
    else:
        sep = '"\\n"' if out.kind == "lines" else '" "'
        show = f'for (size_t i = 0; i < result.size(); i++) {{ if (i) cout << {sep}; cout << result[i]; }} cout << "\\n";'
    parse = "\n    ".join(body)
    return (
        "#include <bits/stdc++.h>\nusing namespace std;\n\n"
        f"{stub.rstrip()}\n\n// ===== Reads the input and prints the answer. You do not need to edit below. =====\n"
        "int main() {\n    ios_base::sync_with_stdio(false);\n    cin.tie(NULL);\n"
        "    vector<string> lines;\n    string line;\n"
        "    while (getline(cin, line)) {\n        if (!line.empty() && line.back() == '\\r') line.pop_back();\n        lines.push_back(line);\n    }\n"
        "    size_t idx = 0;\n"
        "    auto _ints = [](const string& s) { vector<long long> v; istringstream is(s); long long x; while (is >> x) v.push_back(x); return v; };\n"
        "    auto _words = [](const string& s) { vector<string> v; istringstream is(s); string x; while (is >> x) v.push_back(x); return v; };\n"
        "    auto _trim = [](const string& s) { size_t a = s.find_first_not_of(\" \\t\"); if (a == string::npos) return string(); size_t b = s.find_last_not_of(\" \\t\"); return s.substr(a, b - a + 1); };\n"
        f"    {parse}\n    auto result = {fn}({args});\n    {show}\n    return 0;\n}}\n"
    )


_JAVA_TYPE = {("int", "scalar"): "long", ("str", "scalar"): "String", ("int", "array"): "long[]", ("str", "array"): "String[]",
              ("int", "lines"): "long[]", ("str", "lines"): "String[]", ("int", "matrix"): "long[][]"}


def java_code(schema, out, fn, stub=None):
    ret = _JAVA_TYPE[(out.base, "scalar" if out.kind == "scalar" else "array")]
    default = ("0" if out.base == "int" else '""') if out.kind == "scalar" else f"new {ret[:-2]}[0]"
    params = ", ".join(f"{_JAVA_TYPE[(v.base, v.kind)]} {v.name}" for v in variables(schema))
    stub = stub or f"    static {ret} {fn}({params}) {{\n        // Write your logic here\n        return {default};\n    }}\n"
    body = []
    for line in schema:
        if len(line) > 1:
            tmp = f"t{len(body)}"
            body.append(f"String[] {tmp} = lines.get(idx++).trim().split(\"\\\\s+\");")
            for i, v in enumerate(line):
                body.append(
                    f"{_JAVA_TYPE[(v.base, 'scalar')]} {v.name} = "
                    f"{'Long.parseLong(%s[%d])' % (tmp, i) if v.base == 'int' else '%s[%d]' % (tmp, i)};"
                )
            continue
        v = line[0]
        t = _JAVA_TYPE[(v.base, v.kind)]
        if v.kind == "scalar":
            body.append(f"{t} {v.name} = {'Long.parseLong(lines.get(idx++).trim())' if v.base == 'int' else 'lines.get(idx++).trim()'};")
        elif v.kind == "array":
            if v.base == "int":
                body.append(f"long[] {v.name} = Arrays.stream(lines.get(idx++).trim().split(\"\\\\s+\")).filter(_s -> !_s.isEmpty()).mapToLong(Long::parseLong).toArray();")
            else:
                body.append(f"String[] {v.name} = Arrays.stream(lines.get(idx++).trim().split(\"\\\\s+\")).filter(_s -> !_s.isEmpty()).toArray(String[]::new);")
        elif v.kind == "lines":
            item = "Long.parseLong(lines.get(idx++).trim())" if v.base == "int" else "lines.get(idx++).trim()"
            body.append(f"{t} {v.name} = new {t[:-2]}[(int) {v.length}]; for (int i = 0; i < {v.name}.length; i++) {v.name}[i] = {item};")
        else:
            body.append(f"long[][] {v.name} = new long[(int) {v.length}][]; for (int i = 0; i < {v.name}.length; i++) {v.name}[i] = Arrays.stream(lines.get(idx++).trim().split(\"\\\\s+\")).mapToLong(Long::parseLong).toArray();")
    args = ", ".join(v.name for v in variables(schema))
    if out.kind == "scalar":
        show = "System.out.println(result);"
    else:
        sep = '"\\n"' if out.kind == "lines" else '" "'
        elems = "Arrays.stream(result).mapToObj(String::valueOf)" if out.base == "int" else "Arrays.stream(result)"
        show = f"System.out.println({elems}.collect(Collectors.joining({sep})));"
    parse = "\n        ".join(body)
    return (
        "import java.util.*;\nimport java.util.stream.*;\nimport java.io.*;\n\npublic class Solution {\n"
        f"{stub.rstrip()}\n\n    // ===== Reads the input and prints the answer. You do not need to edit below. =====\n"
        "    public static void main(String[] args) throws IOException {\n"
        "        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
        "        List<String> lines = new ArrayList<>();\n        String ln;\n        while ((ln = br.readLine()) != null) lines.add(ln);\n"
        f"        int idx = 0;\n        {parse}\n        {ret} result = {fn}({args});\n        {show}\n    }}\n}}\n"
    )


# C has no vectors and no strings, so the function gets each array together with its length (`arr`, `arr_len`), a grid
# together with the length of every row (`grid`, `grid_cols`, `grid_len`), and a list result is written into a buffer the
# harness provides (`result`, room for C_RESULT_CAPACITY values) while the function returns how many values it wrote.
# `getline` and `strndup` need _POSIX_C_SOURCE because the sandbox compiles with -std=c17.

_C_HELPERS = r"""static char** _lines;
static long long _line_count;

static const char* _next(long long* idx) {
    long long i = (*idx)++;
    return i < _line_count ? _lines[i] : "";
}

static const char* _at(char** t, long long count, long long i) {
    return i < count ? t[i] : "";
}

static char* _trim(const char* s) {
    while (*s == ' ' || *s == '\t') s++;
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t')) n--;
    return strndup(s, n);
}

static long long* _ints(const char* s, long long* count) {
    long long cap = 16, n = 0;
    long long* out = (long long*)malloc(cap * sizeof(long long));
    char* end;
    for (;;) {
        while (*s == ' ' || *s == '\t') s++;
        if (!*s) break;
        long long v = strtoll(s, &end, 10);
        if (end == s) break;
        if (n == cap) { cap *= 2; out = (long long*)realloc(out, cap * sizeof(long long)); }
        out[n++] = v;
        s = end;
    }
    *count = n;
    return out;
}

static char** _words(const char* s, long long* count) {
    long long cap = 16, n = 0;
    char** out = (char**)malloc(cap * sizeof(char*));
    for (;;) {
        while (*s == ' ' || *s == '\t') s++;
        if (!*s) break;
        const char* start = s;
        while (*s && *s != ' ' && *s != '\t') s++;
        if (n == cap) { cap *= 2; out = (char**)realloc(out, cap * sizeof(char*)); }
        out[n++] = strndup(start, (size_t)(s - start));
    }
    *count = n;
    return out;
}

"""

_C_READ_LINES = r"""    char* _buf = NULL;
    size_t _cap = 0;
    ssize_t _got;
    long long _alloc = 1024;
    _lines = (char**)malloc(_alloc * sizeof(char*));
    while ((_got = getline(&_buf, &_cap, stdin)) != -1) {
        while (_got > 0 && (_buf[_got - 1] == '\n' || _buf[_got - 1] == '\r')) _buf[--_got] = '\0';
        if (_line_count == _alloc) { _alloc *= 2; _lines = (char**)realloc(_lines, _alloc * sizeof(char*)); }
        _lines[_line_count++] = strdup(_buf);
    }
    free(_buf);
    long long idx = 0;
"""


def _c_params(schema) -> list[str]:
    parts = []
    for v in variables(schema):
        if v.kind == "scalar":
            parts.append(f"long long {v.name}" if v.base == "int" else f"const char* {v.name}")
        elif v.kind in ("array", "lines"):
            parts.append(
                f"const long long* {v.name}, long long {v.name}_len" if v.base == "int"
                else f"char* const* {v.name}, long long {v.name}_len"
            )
        else:
            parts.append(f"long long* const* {v.name}, const long long* {v.name}_cols, long long {v.name}_len")
    return parts


def _c_args(schema) -> list[str]:
    args = []
    for v in variables(schema):
        if v.kind == "scalar":
            args.append(v.name)
        elif v.kind in ("array", "lines"):
            args += [v.name, f"{v.name}_len"]
        else:
            args += [v.name, f"{v.name}_cols", f"{v.name}_len"]
    return args


def _c_parse(schema) -> list[str]:
    out = []
    for line in schema:
        if len(line) > 1:
            for v in line:
                out.append(f"long long {v.name};" if v.base == "int" else f"const char* {v.name};")
            out.append("{")
            out.append("    long long _count;")
            out.append("    char** _t = _words(_next(&idx), &_count);")
            for i, v in enumerate(line):
                out.append(
                    f"    {v.name} = strtoll(_at(_t, _count, {i}), NULL, 10);" if v.base == "int"
                    else f"    {v.name} = _at(_t, _count, {i});"
                )
            out.append("}")
            continue
        v = line[0]
        if v.kind == "scalar":
            out.append(
                f"long long {v.name} = strtoll(_next(&idx), NULL, 10);" if v.base == "int"
                else f"const char* {v.name} = _trim(_next(&idx));"
            )
        elif v.kind == "array":
            if v.base == "int":
                out.append(f"long long {v.name}_len;")
                out.append(f"long long* {v.name} = _ints(_next(&idx), &{v.name}_len);")
            else:
                out.append(f"long long {v.name}_len;")
                out.append(f"char** {v.name} = _words(_next(&idx), &{v.name}_len);")
        elif v.kind == "lines":
            out.append(f"long long {v.name}_len = (long long)({v.length});")
            if v.base == "int":
                out.append(f"long long* {v.name} = (long long*)malloc(({v.name}_len > 0 ? {v.name}_len : 1) * sizeof(long long));")
                out.append(f"for (long long _i = 0; _i < {v.name}_len; _i++) {v.name}[_i] = strtoll(_next(&idx), NULL, 10);")
            else:
                out.append(f"char** {v.name} = (char**)malloc(({v.name}_len > 0 ? {v.name}_len : 1) * sizeof(char*));")
                out.append(f"for (long long _i = 0; _i < {v.name}_len; _i++) {v.name}[_i] = _trim(_next(&idx));")
        else:
            out.append(f"long long {v.name}_len = (long long)({v.length});")
            out.append(f"long long** {v.name} = (long long**)malloc(({v.name}_len > 0 ? {v.name}_len : 1) * sizeof(long long*));")
            out.append(f"long long* {v.name}_cols = (long long*)malloc(({v.name}_len > 0 ? {v.name}_len : 1) * sizeof(long long));")
            out.append(f"for (long long _i = 0; _i < {v.name}_len; _i++) {v.name}[_i] = _ints(_next(&idx), &{v.name}_cols[_i]);")
    return out


def c_code(schema, out, fn, stub=None):
    """Raises ValueError for a shape C cannot express here (a list of strings as the result)."""
    if out.kind != "scalar" and out.base != "int":
        raise ValueError("a C starter cannot return a list of strings")
    array_out = out.kind != "scalar"
    params = _c_params(schema)
    if array_out:
        params.append("long long* result")
    ret = "long long" if array_out or out.base == "int" else "const char*"
    if stub is None:
        note = (
            "Write your logic here: put the answers in result[0], result[1], ... and return how many there are"
            if array_out else "Write your logic here"
        )
        default = "0" if ret == "long long" else '""'
        stub = f"{ret} {fn}({', '.join(params)}) {{\n    // {note}\n    return {default};\n}}\n"
    args = _c_args(schema)
    if array_out:
        sep = r'"\n"' if out.kind == "lines" else '" "'
        call = (
            f"    long long* result = (long long*)malloc({C_RESULT_CAPACITY} * sizeof(long long));\n"
            f"    long long result_len = {fn}({', '.join(args + ['result'])});\n"
            f"    for (long long _i = 0; _i < result_len; _i++) {{ if (_i) printf({sep}); printf(\"%lld\", result[_i]); }}\n"
            '    printf("\\n");\n'
        )
    elif out.base == "int":
        call = f"    long long result = {fn}({', '.join(args)});\n" + '    printf("%lld\\n", result);\n'
    else:
        call = f"    const char* result = {fn}({', '.join(args)});\n" + '    printf("%s\\n", result);\n'
    parse = "".join("    " + statement + "\n" for statement in _c_parse(schema))
    return (
        "#define _POSIX_C_SOURCE 200809L\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n"
        f"{stub.rstrip()}\n\n// {MARKER_TEXT}\n"
        f"{_C_HELPERS}int main(void) {{\n{_C_READ_LINES}{parse}{call}    return 0;\n}}\n"
    )


def starter_code(schema, out, fn) -> dict[str, str]:
    code = {
        "python": python_code(schema, out, fn),
        "cpp": cpp_code(schema, out, fn),
        "java": java_code(schema, out, fn),
        "javascript": javascript_code(schema, out, fn),
    }
    try:
        code["c"] = c_code(schema, out, fn)
    except ValueError:
        pass  # a result C cannot return (a list of strings): the editor keeps its plain C template for that question
    return code


def served_starter(question: dict):
    """The starter code as a player gets it: the stored one plus a C entry (see with_c_starter), and for a question whose result
    is a list, Python and JavaScript stubs that return an empty list instead of nothing, so running them before writing any
    logic is a wrong answer rather than a crash. Stubs that do not look the way the scaffold writes them are left alone."""
    code = with_c_starter(question)
    output = question.get("output_schema")
    if not isinstance(code, dict) or not isinstance(output, str) or not output.startswith(("int[", "str[")):
        return code
    served = dict(code)
    if isinstance(served.get("python"), str):
        served["python"] = served["python"].replace("# Write your logic here\n    pass\n", "# Write your logic here\n    return []\n", 1)
    if isinstance(served.get("javascript"), str):
        served["javascript"] = served["javascript"].replace("// Write your logic here\n}", "// Write your logic here\n    return [];\n}", 1)
    return served


def with_c_starter(question: dict):
    """The question's starter code with a C entry added when it has none and can be built from the question's own schema.

    Reviewed questions were built before C existed. Only the C entry is added; the other four are returned as stored."""
    code = question.get("starter_code")
    if not isinstance(code, dict) or code.get("c"):
        return code
    try:
        schema = parse_input_schema(question["input_schema"])
        out = parse_output_schema(question["output_schema"])
        return {**code, "c": c_code(schema, out, question["function_name"])}
    except Exception:  # an optional extra: never let it break serving a question
        return code
