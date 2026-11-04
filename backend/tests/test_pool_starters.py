"""The built-in questions of ai_generator.py get a starter whose reader can read the question's own tests, in every language.

They used to get a guessed starter: the C reader took the first line of a two-line input as the whole array, and read one edge of a
list of edges, so no solution could pass. Now their structure is read off their stored tests (app/services/legacy_typing.py, with the
extended readings switched on), checked against every stored test, and the starters of all five languages come from the same
generator as the reviewed questions (app/services/scaffold.py).

* every pool question is typed, its schema parses every stored input with every line accounted for, and its starters carry the lock marker;
* the schemas read for the questions with unusual inputs are pinned;
* reference solutions check the stored answers of the questions with a shape that is new here, which is how two wrong stored answers were found;
* every C starter builds and runs, with gcc when it is installed and otherwise inside Docker's gcc:14 image (the one the app's code runner uses);
* the two vendored copies are identical to the question service's.

Run from the backend folder:  python -m pytest tests/test_pool_starters.py -q
"""

import ast
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.models import DifficultyLevel
from app.services import ai_generator as ag
from app.services import legacy_typing, scaffold

HERE = os.path.dirname(__file__)
AI_GENERATOR = os.path.join(HERE, "..", "app", "services", "ai_generator.py")

# ── compiling and running C ────────────────────────────────────────────────────────────────────────────────────────────────
# With gcc on the PATH (CI) the program is compiled and run on the machine. Without it, but with Docker and the gcc:14 image (which is
# what the app's own code runner uses), both happen inside the container, so a machine without a compiler still runs these tests.

GCC = shutil.which("gcc")


def docker_gcc_available():
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        return subprocess.run([docker, "image", "inspect", "gcc:14"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


C_RUNNER = "gcc" if GCC else ("docker" if docker_gcc_available() else None)
NO_C = pytest.mark.skipif(C_RUNNER is None, reason="neither gcc nor Docker with the gcc:14 image is available here")
COMPILE_FAILED = 97   # the exit status the container script uses when gcc fails, so a build error is told from a crash


def compile_and_run_c(source, stdin, timeout=120):
    """(built, exit status, stdout, stderr) of a C program compiled as C17 with -O1 and run on `stdin`. Bytes go in and out untouched, so
    a Windows host does not turn the input's line breaks into carriage returns."""
    data = stdin.encode("utf-8")
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "main.c")
        open(src, "w", encoding="utf-8", newline="\n").write(source)
        if C_RUNNER == "gcc":
            exe = os.path.join(d, "main")
            done = subprocess.run([GCC, "-std=c17", "-O1", "-o", exe, src], capture_output=True)
            if done.returncode != 0:
                return False, done.returncode, "", done.stderr.decode("utf-8", "replace")
            run = subprocess.run([exe], input=data, capture_output=True, timeout=timeout)
        else:
            script = f"gcc -std=c17 -O1 -o /w/main /w/main.c || exit {COMPILE_FAILED}; /w/main"
            run = subprocess.run(["docker", "run", "--rm", "-i", "-v", f"{d}:/w", "gcc:14", "sh", "-c", script], input=data, capture_output=True, timeout=timeout)
            if run.returncode == COMPILE_FAILED:
                return False, run.returncode, "", run.stderr.decode("utf-8", "replace")
        return True, run.returncode, run.stdout.decode("utf-8", "replace"), run.stderr.decode("utf-8", "replace")


def harvest():
    tree = ast.parse(open(AI_GENERATOR, encoding="utf-8").read())
    out, seen = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if {"title", "description", "input_format", "test_cases"} <= set(keys):
                try:
                    q = ast.literal_eval(node)
                except ValueError:
                    continue
                if q["title"] not in seen:
                    seen.add(q["title"])
                    out.append(q)
    return out


POOL = harvest()
BY_TITLE = {q["title"]: q for q in POOL}


def stored_tests(q):
    return [(t["input"], t["output"]) for t in q["test_cases"]]


def typed(q):
    tests = stored_tests(q)
    return legacy_typing.type_question(tests, tests[0][0], tests[0][1], extended=True)


def built(q):
    return asyncio.run(ag._build_result(dict(q), DifficultyLevel.MEDIUM, q.get("topic")))


def test_the_pool_is_found():
    assert len(POOL) >= 60


@pytest.mark.parametrize("q", POOL, ids=lambda q: q["title"])
def test_every_question_is_typed_and_its_schema_reads_every_stored_test_completely(q):
    result = typed(q)
    assert result is not None, f"{q['title']}: no reading of the stored inputs is certain, the old guess would be served"
    schema = scaffold.parse_input_schema(result["input_schema"])
    for text, _ in stored_tests(q):
        scaffold.parse_input_text(schema, text)  # raises when a line is missing, left over, or not what the schema says


@pytest.mark.parametrize("q", POOL, ids=lambda q: q["title"])
def test_the_served_starter_is_the_typed_one_in_all_five_languages_with_the_lock_marker(q):
    result = built(q)
    code = json.loads(result["starter_code"])
    for lang in scaffold.LANGUAGES:
        assert lang in code and scaffold.MARKER_TEXT in code[lang], f"{q['title']}: {lang} starter has no locked reader"
    params = json.loads(result["parameters"])
    assert params and result["function_name"] == "solve"


def fill_stub(lang, code, body):
    """The starter with a solution written into its stub, the way a player does it."""
    lines = code.split("\n")
    start = next(i for i, line in enumerate(lines) if "Write your logic here" in line)
    if lang == "python":
        end = start + 2 if lines[start + 1].strip() == "pass" else start + 1
    else:
        end = next(i for i in range(start, len(lines)) if lines[i].strip() == "}")
    return "\n".join(lines[:start] + body.split("\n") + lines[end:])


# a solution per question, run through the real starter: the answer must be the stored one. For 'N, then N numbers' the old C reader
# made the array [N] and for 'N, then N-1 rows' it read one row, so these fail without the fix.
BEHAVIOUR = {
    "Sum of Array Elements": {
        "python": "    return sum(arr)",
        "c": "    long long t = 0;\n    for (long long i = 0; i < arr_len; i++) t += arr[i];\n    return t;",
    },
    "Height of Binary Tree": {
        "python": "    par = {c: p for p, c in grid}\n    best = 0\n    for v in range(1, n + 1):\n        d, u = 0, v\n"
                  "        while u in par:\n            u, d = par[u], d + 1\n        best = max(best, d)\n    return best",
        "c": "    long long par[100001] = {0}, best = 0;\n    for (long long i = 0; i < grid_len; i++) par[grid[i][1]] = grid[i][0];\n"
             "    for (long long v = 1; v <= n; v++) { long long d = 0, u = v; while (par[u]) { u = par[u]; d++; } if (d > best) best = d; }\n    return best;",
    },
}
BEHAVIOUR_CASES = [(title, lang, text, want) for title in BEHAVIOUR for lang in BEHAVIOUR[title] for text, want in stored_tests(BY_TITLE[title])]


@pytest.mark.parametrize("title, lang, text, want", BEHAVIOUR_CASES, ids=[f"{c[0]}-{c[1]}-{i}" for i, c in enumerate(BEHAVIOUR_CASES)])
def test_a_solution_written_into_the_served_starter_gives_the_stored_answer(title, lang, text, want):
    if lang == "c" and C_RUNNER is None:
        pytest.skip(NO_C.kwargs["reason"])
    code = fill_stub(lang, json.loads(built(BY_TITLE[title])["starter_code"])[lang], BEHAVIOUR[title][lang])
    if lang == "python":
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "main.py")
            open(path, "w", encoding="utf-8", newline="\n").write(code)
            run = subprocess.run([sys.executable, path], input=(text + "\n").encode("utf-8"), capture_output=True, timeout=20)
        status, out, err = run.returncode, run.stdout.decode("utf-8", "replace"), run.stderr.decode("utf-8", "replace")
    else:
        built_ok, status, out, err = compile_and_run_c(code, text + "\n")
        assert built_ok, err[:400]
    assert status == 0, err[:300]
    assert out.split() == want.split(), f"{title} ({lang}): expected {want!r}, got {out!r} for {text!r}"


PINNED = {
    "Height of Binary Tree": "n:int\ngrid:int[n-1][2]",
    "Count Leaf Nodes": "n:int\ngrid:int[n-1][2]",
    "Level Order Traversal": "n:int\ngrid:int[n-1][2]",
    "Diameter of Binary Tree": "n:int\ngrid:int[n-1][2]",
    "Lowest Common Ancestor": "n:int\ngrid:int[n][2]",   # the n-1 parent-child rows and the last row 'U V' make n rows
    "Inorder Traversal": "n:int\ntexts:str[n-1]/lines",
    "Longest Common Prefix": "n:int\ntexts:str[n]/lines",
    "Group Anagrams": "n:int\ntexts:str[n]/lines",
    "Min Stack": "n:int\ntexts:str[n]/lines",
    "Number of Connected Components": "n:int m:int\ngrid:int[m][2]",
    "Shortest Path in Weighted Graph": "n:int m:int\ngrid:int[m][3]",
    "Sum of Array Elements": "n:int\narr:int[n]",
    "Merge Sorted Arrays": "n:int m:int\narr:int[n]\narr2:int[m]",
    "Range Minimum Query": "n:int m:int\narr:int[n]\ngrid:int[m][2]",
    "Reverse a String": "s:str",
    "Anagram Check": "s:str\nt:str",
}


@pytest.mark.parametrize("title", PINNED)
def test_the_schema_read_for_the_unusual_inputs_is_the_expected_one(title):
    assert typed(BY_TITLE[title])["input_schema"] == PINNED[title]


# ── reference solutions: the stored answers of the questions with a shape that is new here ──────────────────────────────

def lines_of(text):
    return text.strip("\n").split("\n")


def r_height(text):
    ls = lines_of(text)
    n = int(ls[0])
    par = {int(a.split()[1]): int(a.split()[0]) for a in ls[1:n]}
    best = 0
    for v in range(1, n + 1):
        d, u = 0, v
        while u in par:
            u, d = par[u], d + 1
        best = max(best, d)
    return str(best)


def r_leaves(text):
    ls = lines_of(text)
    n = int(ls[0])
    parents = {int(a.split()[0]) for a in ls[1:n]}
    return str(sum(1 for v in range(1, n + 1) if v not in parents))


def r_components(text):
    ls = lines_of(text)
    n, m = map(int, ls[0].split())
    p = list(range(n + 1))

    def find(x):
        while p[x] != x:
            x = p[x]
        return x

    comps = n
    for row in ls[1:1 + m]:
        a, b = map(find, map(int, row.split()))
        if a != b:
            p[a] = b
            comps -= 1
    return str(comps)


def r_two_sum(text):
    ls = lines_of(text)
    n, target = map(int, ls[0].split())
    arr = list(map(int, ls[1].split()))
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target:
                return f"{i} {j}"
    return ""


def r_lcp(text):
    words = lines_of(text)[1:]
    prefix = words[0]
    for w in words[1:]:
        while not w.startswith(prefix):
            prefix = prefix[:-1]
    return prefix


def r_min_stack(text):
    stack, out = [], []
    for op in lines_of(text)[1:]:
        if op.startswith("PUSH"):
            stack.append(int(op.split()[1]))
        elif op.startswith("POP"):
            stack.pop()
        else:
            out.append(str(min(stack)))
    return "\n".join(out)


def r_merge(text):
    ls = lines_of(text)
    return " ".join(map(str, sorted(list(map(int, ls[1].split())) + list(map(int, ls[2].split())))))


def r_rmq(text):
    ls = lines_of(text)
    n, q = map(int, ls[0].split())
    arr = list(map(int, ls[1].split()))
    return "\n".join(str(min(arr[int(a) - 1:int(b)])) for a, b in (r.split() for r in ls[2:2 + q]))


def r_inorder(text):
    ls = lines_of(text)
    n = int(ls[0])
    left, right, has_parent = {}, {}, set()
    for row in ls[1:n]:
        p, c, side = row.split()
        (left if side == "L" else right)[int(p)] = int(c)
        has_parent.add(int(c))
    root = next(v for v in range(1, n + 1) if v not in has_parent)
    out = []

    def walk(v):
        if v in left:
            walk(left[v])
        out.append(v)
        if v in right:
            walk(right[v])

    walk(root)
    return " ".join(map(str, out))


def r_lca(text):
    ls = lines_of(text)
    n = int(ls[0])
    par = {int(a.split()[1]): int(a.split()[0]) for a in ls[1:n]}
    u, v = map(int, ls[n].split())
    seen = set()
    while u:
        seen.add(u)
        u = par.get(u, 0)
    while v not in seen:
        v = par[v]
    return str(v)


REFERENCE = {
    "Height of Binary Tree": r_height, "Count Leaf Nodes": r_leaves, "Number of Connected Components": r_components, "Two Sum": r_two_sum,
    "Longest Common Prefix": r_lcp, "Min Stack": r_min_stack, "Merge Sorted Arrays": r_merge, "Range Minimum Query": r_rmq,
    "Inorder Traversal": r_inorder, "Lowest Common Ancestor": r_lca,
}
CASES = [(title, text, want) for title in REFERENCE for text, want in stored_tests(BY_TITLE[title])]


@pytest.mark.parametrize("title, text, want", CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_the_stored_answer_is_what_an_independent_solution_gives(title, text, want):
    assert REFERENCE[title](text).split() == want.split(), f"{title}: stored answer {want!r} for input {text!r}"


# ── the starters build ─────────────────────────────────────────────────────────────────────────────────────────────────────

@NO_C
@pytest.mark.parametrize("q", POOL, ids=lambda q: q["title"])
def test_every_c_starter_builds_and_runs_to_the_end_on_the_first_sample(q):
    c = json.loads(built(q)["starter_code"])["c"]
    built_ok, status, _, err = compile_and_run_c(c, q["test_cases"][0]["input"] + "\n")
    assert built_ok, err[:400]
    assert status == 0, err[:300]


def test_the_python_starters_are_valid_python():
    for q in POOL:
        compile(json.loads(built(q)["starter_code"])["python"], q["title"], "exec")


# ── the vendored copies ────────────────────────────────────────────────────────────────────────────────────────────────────

SERVICE = os.path.join(HERE, "..", "..", "question-service", "model")


@pytest.mark.skipif(not os.path.isdir(SERVICE), reason="the question service is not in this checkout")
@pytest.mark.parametrize("name", ["scaffold.py", "legacy_typing.py"])
def test_the_vendored_copy_is_identical_to_the_question_services(name):
    def body(path):
        text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
        text = "\n".join(line for line in text.split("\n") if not line.startswith("# VENDORED COPY") and not line.startswith("# Keep it identical"))
        return text.replace("from app.services import scaffold", "from model import scaffold")

    assert body(os.path.join(HERE, "..", "app", "services", name)) == body(os.path.join(SERVICE, name))
