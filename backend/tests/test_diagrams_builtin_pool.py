"""The hand-written tree questions built into ai_generator.py ("N, then N-1 parent child pairs") are drawn, and what is drawn is right.

* Every stored test case of every such question is drawn, the PNG is checked against the model, and the question's own expected
  output is recomputed from the *drawn structure* with an independent solver.
* Random trees in the same two input formats ('parent child' and 'parent child L/R') are drawn and compared with the raw rows.
* Rows that cannot be a tree (two roots, two parents, a cycle, three children of a binary tree, one side used twice) get no diagram.

Run from the backend folder:  python -m pytest tests/test_diagrams_builtin_pool.py -q
"""

import ast
import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.diagram_generator import diagram_generator as dg
from test_diagrams import adjacency, depth_of, draw_and_inspect, lowest_common, mark, tree_of

AI_GENERATOR = os.path.join(os.path.dirname(__file__), "..", "app", "services", "ai_generator.py")


def pool_questions():
    tree = ast.parse(open(AI_GENERATOR, encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if {"title", "description", "input_format", "test_cases"} <= set(keys):
                try:
                    q = ast.literal_eval(node)
                except ValueError:
                    continue
                if "parent child" in q["input_format"].lower():
                    out.append(q)
    return out


POOL = pool_questions()


# ── solvers that work on the drawn structure ────────────────────────────────────────────────────────────────────────────

def height(m):
    return max(depth_of(m).values()) - 1


def leaves(m):
    kids, _ = tree_of(m)
    return sum(1 for v in m.nodes if not kids[v])


def level_order(m):
    kids, _ = tree_of(m)
    rows, level = [], list(m.roots)
    while level:
        rows.append([str(v) for v in level])
        level = [c for v in level for c in kids[v]]
    return rows


def lca(m):
    return lowest_common(m, mark(m, "U"), mark(m, "V"))


def diameter(m):
    adj = adjacency(m, directed=False)
    best = 0
    for s in m.nodes:
        dist, queue = {s: 0}, collections.deque([s])
        while queue:
            v = queue.popleft()
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
        best = max(best, max(dist.values()))
    return best


def inorder(m):
    kids, _ = tree_of(m)
    left = {p: c for p, c in ((a, b) for a, b, _ in m.edges) if m.sides[c] == "L"}
    right = {p: c for p, c in ((a, b) for a, b, _ in m.edges) if m.sides[c] == "R"}
    out = []

    def walk(v):
        if v in left:
            walk(left[v])
        out.append(v)
        if v in right:
            walk(right[v])

    walk(m.roots[0])
    return out


def same(want, got):
    if isinstance(got, list) and got and isinstance(got[0], list):
        return [r.split() for r in want.strip().splitlines()] == got
    if isinstance(got, list):
        return want.split() == [str(v) for v in got]
    return want.strip() == str(got)


SOLVERS = {"Height of Binary Tree": height, "Count Leaf Nodes": leaves, "Level Order Traversal": level_order,
           "Lowest Common Ancestor": lca, "Diameter of Binary Tree": diameter, "Inorder Traversal": inorder}


def as_question(q, sample):
    return {"title": q["title"], "topic": q.get("topic", "trees"), "problem_statement": q["description"], "input_format": q["input_format"], "sample_input": sample}


def test_the_pool_has_parent_child_questions_and_every_one_has_a_solver():
    assert len(POOL) >= 6
    missing = sorted({q["title"] for q in POOL} - set(SOLVERS))
    assert not missing, f"add a solver for {missing}"


CASES = [(q["title"], tc["input"], tc["output"], q) for q in POOL for tc in q["test_cases"] if isinstance(tc, dict) and tc["input"].split()[0] != "1"]


@pytest.mark.parametrize("title, sample, output, q", CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_each_test_case_is_drawn_and_the_drawing_gives_the_stored_answer(title, sample, output, q):
    model, _, _, problems = draw_and_inspect(as_question(q, sample))
    assert problems == []
    assert model.kind in ("tree", "binary_tree")
    got = SOLVERS[title](model)
    assert same(output, got), f"{title}: stored {output!r}, the drawn tree gives {got!r}"


def test_a_single_node_has_no_rows_to_draw_and_gets_no_diagram():
    q = next(q for q in POOL if q["title"] == "Height of Binary Tree")
    assert dg.plan(as_question(q, "1")) is None


def test_the_lca_question_marks_the_two_nodes_it_names():
    q = next(q for q in POOL if q["title"] == "Lowest Common Ancestor")
    model = dg.plan(as_question(q, "5\n1 2\n1 3\n2 4\n2 5\n4 3"))
    assert mark(model, "U") == 4 and mark(model, "V") == 3
    assert "U = 4" in model.caption and "V = 3" in model.caption


# ── random trees in the same formats ────────────────────────────────────────────────────────────────────────────────────

FMT = "First line: N.\nNext N-1 lines: parent child pairs."
FMT_SIDES = "First line: N.\nNext N-1 lines: parent child direction pairs (parent child L/R)."
BINARY = "Given a binary tree with N nodes, answer a question about it."
GENERAL = "Given a rooted tree with N nodes, answer a question about it."


def random_rows(rng, n, cap=None):
    """n-1 (parent, child) rows of a random tree with random labels; no node gets more than cap children."""
    order = list(range(1, n + 1))
    rng.shuffle(order)
    kids = collections.Counter()
    rows = []
    for i in range(1, n):
        options = [p for p in order[:i] if cap is None or kids[p] < cap]
        p = rng.choice(options)
        kids[p] += 1
        rows.append((p, order[i]))
    if rng.random() < 0.5:
        rng.shuffle(rows)
    return rows


def question(rows, n, text=BINARY, fmt=FMT, sides=None):
    body = [f"{p} {c}" + (f" {sides[(p, c)]}" if sides else "") for p, c in rows]
    return {"title": "A tree question", "topic": "trees", "problem_statement": text, "input_format": fmt, "sample_input": "\n".join([str(n), *body])}


@pytest.mark.parametrize("seed", range(40))
def test_random_parent_child_trees_are_drawn_exactly_as_given(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 34)
    binary = rng.random() < 0.6
    rows = random_rows(rng, n, cap=2 if binary else None)
    model, _, _, problems = draw_and_inspect(question(rows, n, BINARY if binary else GENERAL))
    assert problems == []
    assert [(a, b) for a, b, _ in model.edges] == rows
    assert model.roots == [next(v for v in range(1, n + 1) if v not in {c for _, c in rows})]
    assert sorted(model.nodes) == list(range(1, n + 1))
    # children are drawn left to right in the order the rows give them
    pos = dg._layout(model)
    by_parent = collections.defaultdict(list)
    for p, c in rows:
        by_parent[p].append(c)
    for p, cs in by_parent.items():
        xs = [pos[c][0] for c in cs]
        assert xs == sorted(xs) and len(set(xs)) == len(xs), f"children of {p} are not left to right in the given order"


def random_side_rows(rng, n):
    rows = random_rows(rng, n, cap=2)
    used = collections.defaultdict(set)
    sides = {}
    for p, c in rows:
        free = [s for s in "LR" if s not in used[p]]
        s = rng.choice(free)
        used[p].add(s)
        sides[(p, c)] = s
    return rows, sides


@pytest.mark.parametrize("seed", range(30))
def test_random_left_right_trees_are_drawn_on_the_sides_given(seed):
    rng = random.Random(1000 + seed)
    n = rng.randint(2, 30)
    rows, sides = random_side_rows(rng, n)
    model, _, _, problems = draw_and_inspect(question(rows, n, BINARY, FMT_SIDES, sides))
    assert problems == []
    assert model.kind == "binary_tree"
    assert {c: s for (p, c), s in sides.items()} == model.sides
    assert [(a, b) for a, b, _ in model.edges] == rows
    # the in-order walk of the drawn tree equals an independent walk of the raw rows
    left = {p: c for (p, c), s in sides.items() if s == "L"}
    right = {p: c for (p, c), s in sides.items() if s == "R"}
    root = next(v for v in range(1, n + 1) if v not in {c for _, c in rows})
    want = []

    def walk(v):
        if v in left:
            walk(left[v])
        want.append(v)
        if v in right:
            walk(right[v])

    walk(root)
    assert inorder(model) == want


# ── rows that are not a tree get no diagram ─────────────────────────────────────────────────────────────────────────────

BAD = [
    ("two roots", 4, [(1, 2), (3, 4)], BINARY, FMT),
    ("two parents", 4, [(1, 2), (1, 3), (3, 2)], BINARY, FMT),
    ("a cycle", 4, [(1, 2), (2, 3), (3, 2)], BINARY, FMT),
    ("a loop", 3, [(1, 1), (1, 2)], BINARY, FMT),
    ("three children of a binary tree", 5, [(1, 2), (1, 3), (1, 4), (4, 5)], BINARY, FMT),
    ("too few rows", 5, [(1, 2), (1, 3)], BINARY, FMT),
    ("a node outside 1..n", 3, [(1, 2), (1, 7)], BINARY, FMT),
    ("a cycle apart from the root", 5, [(1, 2), (3, 4), (4, 5), (5, 3)], BINARY, FMT),
]


@pytest.mark.parametrize("why, n, rows, text, fmt", BAD, ids=[b[0] for b in BAD])
def test_rows_that_are_not_a_tree_get_no_diagram(why, n, rows, text, fmt):
    assert dg.plan(question(rows, n, text, fmt)) is None


def test_three_children_are_fine_when_the_tree_is_not_binary():
    model = dg.plan(question([(1, 2), (1, 3), (1, 4), (4, 5)], 5, GENERAL))
    assert model is not None and model.roots == [1]


def test_one_side_used_twice_gets_no_diagram():
    rows = [(1, 2), (1, 3)]
    assert dg.plan(question(rows, 3, BINARY, FMT_SIDES, {(1, 2): "L", (1, 3): "L"})) is None


def test_a_cue_that_is_not_about_trees_does_not_draw_a_tree():
    q = question([(1, 2), (1, 3)], 3, "Given N pairs of people, count how many can be matched.", FMT)
    q["topic"] = "arrays"
    assert dg.plan(q) is None
