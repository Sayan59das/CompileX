"""The question service's hard graph and tree templates are drawn, over many random seeds, and what is drawn is right.

Each template's own statement and sample go through the diagram generator (with the input shape the service's typing reads off the template's tests);
an independent solver run on the DRAWN structure must reproduce the template's own sample output:

* Bellman-Ford shortest paths (negative weights, the source marked from "source node 0"),
* strongly connected components (zero-based vertices),
* Floyd-Warshall (an adjacency matrix: the statement says the nodes are 0-indexed),
* Path Sum in a binary tree ("n target", then a level-order array),
* BST preorder traversal (the values in insertion order; the service's function is called _hard_tree_serialize_deserialize).

"Kth smallest in a BST" (sorted values: no tree is given) must get no picture.

These tests are hand-written for the templates they name. test_diagrams_every_template.py is the one that finds EVERY template of the
service by itself and fails for a new one that is drawn without a solver.

Run from the backend folder:  python -m pytest tests/test_diagrams_hard_templates.py -q
"""

import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "question-service"))

import pytest

from app.services.diagram_generator import diagram_generator as dg
from test_diagrams import draw_and_inspect

try:
    from model import difficulty_templates as T
except Exception:  # the question service is not in this checkout, or its imports are missing
    T = None

pytestmark = pytest.mark.skipif(T is None, reason="the question service's templates are not importable here")

SEEDS = list(range(20))


def question(fn, schema, seed, topic):
    t = getattr(T, fn)(random.Random(seed))
    # the service's typing writes the real width of a square matrix into the schema: "{n}" stands for the sample's first number
    schema = schema.replace("{n}", t["sample_input"].split("\n")[0].split()[0])
    return t, {"title": t["title"], "topic": topic, "problem_statement": t["problem_statement"], "input_format": t.get("input_format", ""),
               "input_schema": schema, "sample_input": t["sample_input"]}


def tags(m):
    return {t: v for v, ts in m.marks.items() for t in ts}


# ── solvers on the drawn structure ──────────────────────────────────────────────────────────────────────────────────────

def bellman_ford(m, passes=None):
    src = tags(m)["src"]
    dist = {v: float("inf") for v in m.nodes}
    dist[src] = 0
    for _ in range(len(m.nodes) - 1 if passes is None else passes):
        for a, b, w in m.edges:
            if dist[a] + w < dist[b]:
                dist[b] = dist[a] + w
    return [(-1 if dist[v] == float("inf") else dist[v]) for v in sorted(m.nodes)]


def strongly_connected_components(m):
    adj = {v: [] for v in m.nodes}
    radj = {v: [] for v in m.nodes}
    for a, b, _ in m.edges:
        adj[a].append(b)
        radj[b].append(a)
    seen, order = set(), []
    for s in m.nodes:
        if s in seen:
            continue
        stack = [(s, iter(adj[s]))]
        seen.add(s)
        while stack:
            v, it = stack[-1]
            for w in it:
                if w not in seen:
                    seen.add(w)
                    stack.append((w, iter(adj[w])))
                    break
            else:
                order.append(v)
                stack.pop()
    comp, count = set(), 0
    for s in reversed(order):
        if s in comp:
            continue
        count += 1
        stack = [s]
        comp.add(s)
        while stack:
            v = stack.pop()
            for w in radj[v]:
                if w not in comp:
                    comp.add(w)
                    stack.append(w)
    return count


def floyd_warshall(m):
    n = len(m.nodes)
    d = [[float("inf")] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0
    for a, b, w in m.edges:
        d[a][b] = min(d[a][b], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                d[i][j] = min(d[i][j], d[i][k] + d[k][j])
    return ["\n".join(" ".join(str(-1 if x == float("inf") else x) for x in row) for row in d)][0]


def path_sum(m, target):
    kids = collections.defaultdict(list)
    for a, b, _ in m.edges:
        kids[a].append(b)
    values = {v: int(m.label(v)) for v in m.nodes}
    stack = [(m.roots[0], values[m.roots[0]])]
    while stack:
        v, s = stack.pop()
        if not kids[v] and s == target:
            return True
        stack.extend((c, s + values[c]) for c in kids[v])
    return False


# ── the templates ──────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("seed", SEEDS)
def test_bellman_ford_is_drawn_with_its_source_marked_and_gives_the_templates_distances(seed):
    t, q = question("_hard_graph_bellman_ford", "n:int m:int k:int\ngrid:int[m][3]", seed, "graphs")
    model, _, _, problems = draw_and_inspect(q) if seed < 8 else (dg.plan(q), None, None, [])
    assert model is not None and problems == []
    assert model.directed and model.weight_name == "weight" and list(tags(model).values()) == [0]
    assert bellman_ford(model) == [int(x) for x in t["sample_output"].split()]
    # the question must be well posed: its statement assumes no negative cycle, so n passes and n-1 passes agree, and a reachable node is never at -1
    assert bellman_ford(model, passes=len(model.nodes)) == bellman_ford(model), "the template drew a graph with a negative cycle"
    reachable = [d for d in bellman_ford(model) if d != -1]
    assert len(reachable) == len([1 for d in t["sample_output"].split() if d != "-1"])


@pytest.mark.parametrize("seed", SEEDS)
def test_strongly_connected_components_are_drawn_zero_based_and_give_the_templates_count(seed):
    t, q = question("_hard_graph_strongly_connected", "n:int m:int\ngrid:int[m][2]", seed, "graphs")
    model, _, _, problems = draw_and_inspect(q) if seed < 8 else (dg.plan(q), None, None, [])
    assert model is not None and problems == [] and model.directed and model.nodes[0] == 0
    assert str(strongly_connected_components(model)) == t["sample_output"].strip()


@pytest.mark.parametrize("seed", SEEDS)
def test_floyd_warshall_is_drawn_from_its_matrix_and_gives_the_templates_matrix(seed):
    t, q = question("_hard_graph_floyd_warshall", "n:int\ngrid:int[n][{n}]", seed, "graphs")
    model, _, _, problems = draw_and_inspect(q) if seed < 8 else (dg.plan(q), None, None, [])
    assert model is not None and problems == [] and model.directed and model.nodes[0] == 0
    assert floyd_warshall(model) == t["sample_output"].strip()


def test_floyd_warshall_without_the_numbering_in_its_statement_gets_no_picture():
    t, q = question("_hard_graph_floyd_warshall", "n:int\ngrid:int[n][{n}]", 0, "graphs")
    q["problem_statement"] = q["problem_statement"].replace("(0-indexed: row i of the matrix is node i) ", "")
    assert "0-indexed" not in q["problem_statement"] and dg.plan(q) is None


@pytest.mark.parametrize("seed", SEEDS)
def test_path_sum_is_drawn_as_the_level_order_tree_and_gives_the_templates_answer(seed):
    t, q = question("_hard_tree_path_sum", "arr:int[0]\narr2:int[0]", seed, "trees")
    model, _, _, problems = draw_and_inspect(q) if seed < 8 else (dg.plan(q), None, None, [])
    assert model is not None and problems == [] and model.kind == "binary_tree"
    target = int(t["sample_input"].split("\n")[0].split()[1])
    assert str(path_sum(model, target)).lower() == t["sample_output"].strip().lower()


@pytest.mark.parametrize("seed", range(6))
def test_a_bst_given_as_sorted_values_gets_no_picture(seed):
    t, q = question("_hard_tree_kth_smallest_bst", "arr:int[0]\narr2:int[0]", seed, "trees")
    assert dg.plan(q) is None


def preorder(m):
    left = {a: b for a, b, _ in m.edges if m.sides[b] == "L"}
    right = {a: b for a, b, _ in m.edges if m.sides[b] == "R"}
    out = []

    def walk(v):
        out.append(int(m.label(v)))
        for child in (left.get(v), right.get(v)):
            if child is not None:
                walk(child)

    walk(m.roots[0])
    return out


@pytest.mark.parametrize("seed", SEEDS)
def test_bst_preorder_is_drawn_as_the_tree_the_insertions_build_and_gives_the_templates_preorder(seed):
    """This template is called _hard_tree_serialize_deserialize in the service but is titled 'BST Preorder Traversal': its input is the
    values in insertion order, and it has no -1 (the test that used to stand here only asserted when a -1 was present, so it never ran)."""
    t, q = question("_hard_tree_serialize_deserialize", "n:int\narr:int[n]", seed, "trees")
    assert t["title"] == "BST Preorder Traversal" and "-1" not in t["sample_input"]
    model, _, _, problems = draw_and_inspect(q) if seed < 8 else (dg.plan(q), None, None, [])
    assert model is not None and problems == [] and model.kind == "binary_tree"
    assert " ".join(map(str, preorder(model))) == t["sample_output"].strip()
