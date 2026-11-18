"""The function-style harness (questions whose code has no main of its own): the three bugs the real executor showed on 2026-11-18.

- JavaScript read a list parameter as one integer ("int" in "list[int]" matched the scalar test before the list test);
- C++ with two list parameters declared `line`, `iss` and `num` twice and did not compile;
- Java started the class `Solution`, but the harness's `main` is in `Main`.

Run from the backend folder:  python -m pytest tests/test_function_harness.py -q
(The C++ test compiles the harness when g++ is installed and skips otherwise: CI has it, the local full-test image has only gcc.)
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.code_executor import generate_test_harness

EXECUTOR = os.path.join(os.path.dirname(__file__), "..", "app", "services", "code_executor.py")


def sig(*params):
    return {"function_name": "solve", "parameters": [{"name": n, "type": t} for n, t in params], "return_type": "int"}


def test_javascript_reads_a_list_parameter_as_a_list_and_a_number_as_a_number():
    text = generate_test_harness("function solve(nums, k) {}", "javascript", sig(("nums", "list[int]"), ("k", "int")))
    assert "const nums = lines[lineIdx++].split(' ').filter(Boolean).map(Number);" in text
    assert "const k = parseInt(lines[lineIdx++]);" in text
    for kind in ("int[]", "array", "List[int]", "vector<int>"):
        assert ".map(Number)" in generate_test_harness("x", "javascript", sig(("v", kind)))


def test_cpp_with_two_list_parameters_has_no_repeated_declarations():
    text = generate_test_harness("int solve(vector<int> xs, vector<int> ys) { return 0; }", "cpp", sig(("xs", "list[int]"), ("ys", "list[int]")))
    for name in ("line_0", "line_1", "iss_0", "iss_1", "num_0", "num_1"):
        assert text.count(f" {name}") >= 1
    assert text.count("string line;") == 0 and text.count("istringstream iss(") == 0


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ is not installed here (CI has it; to run it locally use an image with g++)")
@pytest.mark.parametrize("params", [
    [("xs", "list[int]"), ("ys", "list[int]")],
    [("n", "int"), ("xs", "list[int]")],
    [("xs", "list[int]"), ("n", "int"), ("ys", "list[int]")],
])
def test_the_cpp_harness_compiles_and_reads_what_it_is_given(params):
    declared = ", ".join(("vector<int> " if t.startswith("list") else "int ") + n for n, t in params)
    body = "int s = 0;" + "".join(f" for (int v : {n}) s += v;" if t.startswith("list") else f" s += {n};" for n, t in params) + " return s;"
    code = generate_test_harness(f"int solve({declared}) {{ {body} }}", "cpp", sig(*params))
    with tempfile.TemporaryDirectory() as d:
        src, exe = os.path.join(d, "a.cpp"), os.path.join(d, "a")
        open(src, "w").write(code)
        build = subprocess.run(["g++", "-o", exe, src], capture_output=True, text=True)
        assert build.returncode == 0, build.stderr[:600]
        lines = {"xs": "1 2", "ys": "3 4", "n": "5"}
        stdin = "\n".join(lines[n] for n, _ in params) + "\n"
        expected = sum(sum(map(int, lines[n].split())) for n, _ in params)
        out = subprocess.run([exe], input=stdin, capture_output=True, text=True, timeout=10)
        assert out.stdout.strip() == str(expected), (out.stdout, expected)


def test_a_java_question_run_through_the_harness_starts_the_harness_class():
    source = open(EXECUTOR, encoding="utf-8").read()
    assert source.count('config = {**config, "classname": "Main"}') == 2, "both the Docker and the subprocess path must run Main with the harness"
    assert "class Main" in generate_test_harness("class Solution { static int solve(int a) { return a; } }", "java", sig(("a", "int")))
