"""A drawing must be right according to the question, not only according to its sample input.

Found by reading every graph and tree question the service can serve against its full statement:

* "non-directed" was read as "directed";
* a complete graph whose input lists only the weight-1 edges was drawn as if the listed pairs were the whole graph;
* the vertices a statement names ("from node S to node D", "Vertex S", "source node 0") were not marked, and the values it gives each
  vertex ("each vertex has an integer d_i") were left out;
* a level-order array with -1 in it was drawn with the -1 as vertices;
* BST questions ("built by inserting ..."), "n target, then a level-order array" and adjacency matrices were not drawn at all.

Run from the backend folder:  python -m pytest tests/test_diagrams_accuracy.py -q
"""

import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.diagram_generator import classify_direction, diagram_generator as dg
from test_diagrams import draw_and_inspect

GENERIC = "First line: the integers n, m.\nThen: m lines of 2 integers each, the grid grid."


def q(statement, schema, sample, fmt=GENERIC, topic="graphs", title="A question"):
    return {"title": title, "topic": topic, "problem_statement": statement, "input_format": fmt, "input_schema": schema, "sample_input": sample}


# ── direction words ─────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("words, want", [
    ("a non-directed graph", False), ("a nondirected graph", False), ("a graph that is not directed", False), ("an undirected graph", False),
    ("a directed graph", True), ("a directed acyclic graph", True), ("one-way roads", True), ("two-way roads", False),
])
def test_the_direction_wording_is_read_the_right_way_round(words, want):
    assert classify_direction(words, "") is want


def test_a_non_directed_graph_is_drawn_undirected():
    stmt = "Vova has a non-directed graph consisting of n vertices and m edges without loops and multiple edges."
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][2]", "4 3\n1 2\n2 3\n3 4"))
    assert model is not None and model.directed is False


# ── a complete graph is not the list of the edges the input names ──────────────────────────────────────────────────────

COMPLETE = "It is an undirected graph on n vertices. It is a complete graph: each pair of vertices is connected by an edge. Exactly m edges have weight 1."


def test_a_complete_graph_whose_input_lists_only_some_edges_gets_no_diagram():
    assert dg.plan(q(COMPLETE, "n:int m:int\ngrid:int[m][2]", "4 3\n1 2\n1 3\n2 4")) is None


def test_a_complete_graph_whose_input_lists_every_pair_is_drawn():
    pairs = [(a, b) for a in range(1, 5) for b in range(a + 1, 5)]
    sample = "4 6\n" + "\n".join(f"{a} {b}" for a, b in pairs)
    model = dg.plan(q(COMPLETE, "n:int m:int\ngrid:int[m][2]", sample))
    assert model is not None and len(model.edges) == 6


# ── the vertices a statement names ──────────────────────────────────────────────────────────────────────────────────────

SD = "Consider an undirected unweighted graph with N nodes and M edges, find the shortest path from node S to node D."
SD_FMT = "First line: the integers n, m, k, q.\nThen: m lines of 2 integers each, the grid grid."
SD_SCHEMA = "n:int m:int k:int q:int\ngrid:int[m][2]"
SD_SAMPLE = "5 4 1 5\n1 2\n2 3\n3 4\n4 5"


def test_the_two_numbers_the_format_leaves_unexplained_are_the_vertices_the_statement_names_in_order():
    model = dg.plan(q(SD, SD_SCHEMA, SD_SAMPLE, SD_FMT))
    assert model.marks == {1: ["S"], 5: ["D"]}
    assert "S = 1" in model.caption and "D = 5" in model.caption
    _, _, _, problems = draw_and_inspect(q(SD, SD_SCHEMA, SD_SAMPLE, SD_FMT))
    assert problems == []


def test_a_second_line_s_t_is_marked_too():
    stmt = "We have a graph with N vertices and M edges. Takahashi departs Vertex S and Aoki departs Vertex T. The i-th edge connects Vertex U_i and Vertex V_i with time D_i, regardless of direction. Undirected."
    fmt = "First line: the integers n, m.\nThen: the integers k, q.\nThen: m lines of 3 integers each, the grid grid."
    model = dg.plan(q(stmt, "n:int m:int\nk:int q:int\ngrid:int[m][3]", "4 4\n1 3\n1 2 1\n2 3 1\n3 4 1\n4 1 1", fmt))
    assert model.marks == {1: ["S"], 3: ["T"]}


def test_edge_endpoints_in_a_formula_are_not_named_vertices():
    stmt = "An undirected graph. The i-th edge connects Vertex U_i and Vertex V_i. Count the paths."
    model = dg.plan(q(stmt, "n:int m:int k:int q:int\ngrid:int[m][2]", "5 4 1 5\n1 2\n2 3\n3 4\n4 5", SD_FMT))
    assert model.marks == {}


def test_nothing_is_marked_when_the_numbers_and_the_named_vertices_do_not_pair_up():
    stmt = "An undirected graph with n nodes. Find the shortest path from node S to the farthest node."
    model = dg.plan(q(stmt, SD_SCHEMA, SD_SAMPLE, SD_FMT))
    assert model.marks == {}


BF = "Given a directed weighted graph with 4 nodes (0-indexed) and edges that may have negative weights, find the shortest distance from source node 0 to all other nodes."


def test_a_source_the_statement_gives_by_number_is_marked():
    model = dg.plan(q(BF, "n:int m:int k:int\ngrid:int[m][3]", "4 3 0\n0 1 8\n1 3 1\n3 1 -2", "First line: the integers n, m, k.\nThen: m lines of 3 integers each, the grid grid."))
    assert model.marks == {0: ["src"]}


def test_from_node_one_to_all_other_nodes_marks_node_one():
    stmt = "Given a weighted directed graph with N nodes and M edges, find the shortest path from node 1 to all other nodes. The weights are distances."
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "3 2\n1 2 5\n2 3 1"))
    assert model.marks == {1: ["src"]}


# ── values the statement gives each vertex ──────────────────────────────────────────────────────────────────────────────

VALUES = "You are given a connected undirected graph with n vertices and m edges. Each vertex has an integer d_{i}, which can be 0, 1 or -1. Find a subset of edges."
VALUES_SCHEMA = "n:int m:int\narr:int[n]\ngrid:int[m][2]"


def test_the_value_of_each_vertex_is_written_beside_it():
    model = dg.plan(q(VALUES, VALUES_SCHEMA, "3 2\n1 0 -1\n1 2\n2 3"))
    assert model.notes == {1: "d=1", 2: "d=0", 3: "d=-1"}
    assert "d_i" in model.caption
    _, _, _, problems = draw_and_inspect(q(VALUES, VALUES_SCHEMA, "3 2\n1 0 -1\n1 2\n2 3"))
    assert problems == []


def test_a_list_the_statement_does_not_tie_to_the_vertices_means_no_diagram():
    stmt = "You are given an undirected graph with n vertices and m edges. Count the things."
    assert dg.plan(q(stmt, VALUES_SCHEMA, "3 2\n1 0 -1\n1 2\n2 3")) is None


def test_a_list_that_is_not_as_long_as_the_vertex_count_means_no_diagram():
    assert dg.plan(q(VALUES, "n:int m:int\narr:int[2]\ngrid:int[m][2]", "3 2\n1 0\n1 2\n2 3")) is None


def test_an_edge_value_the_statement_describes_labels_the_third_number():
    stmt = "The nodes and edges of an undirected graph have some values. The value of an edge is c."
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "3 2\n1 2 5\n2 3 6"))
    assert model is not None and model.weight_name == "value"


def test_a_third_number_nothing_describes_still_gets_no_diagram():
    stmt = "An undirected graph with n vertices and m edges. Each vertex has a value. Count things."
    assert dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "3 2\n1 2 5\n2 3 6")) is None


# ── BST questions whose input is one line of numbers ────────────────────────────────────────────────────────────────────

BST = "Given a BST built by inserting {n} distinct integers, find the maximum depth."


def inorder(m):
    kids = collections.defaultdict(dict)
    for a, b, _ in m.edges:
        kids[a][m.sides[b]] = b
    out = []

    def walk(v):
        if "L" in kids[v]:
            walk(kids[v]["L"])
        out.append(int(m.label(v)))
        if "R" in kids[v]:
            walk(kids[v]["R"])

    walk(m.roots[0])
    return out


def depth(m):
    kids = collections.defaultdict(list)
    for a, b, _ in m.edges:
        kids[a].append(b)
    best, stack = 0, [(m.roots[0], 1)]
    while stack:
        v, d = stack.pop()
        best = max(best, d)
        stack.extend((c, d + 1) for c in kids[v])
    return best


@pytest.mark.parametrize("seed", range(25))
def test_a_bst_built_from_a_line_of_numbers_is_drawn_with_the_tree_that_insertion_gives(seed):
    rng = random.Random(seed)
    values = rng.sample(range(1, 60), rng.randint(2, 14))
    model, _, _, problems = draw_and_inspect(q(BST.format(n=len(values)), "arr:int[0]", " ".join(map(str, values)),
                                               "First line: one line of integers, the list arr.", topic="trees"))
    assert problems == []
    assert model.kind == "binary_tree" and int(model.label(model.roots[0])) == values[0]
    assert inorder(model) == sorted(values)
    # an independent insertion
    root, left, right = values[0], {}, {}
    for v in values[1:]:
        cur = root
        while True:
            side = left if v < cur else right
            if cur in side:
                cur = side[cur]
            else:
                side[cur] = v
                break
    want_depth = 1
    stack = [(root, 1)]
    while stack:
        v, d = stack.pop()
        want_depth = max(want_depth, d)
        stack.extend((c, d + 1) for c in (left.get(v), right.get(v)) if c is not None)
    assert depth(model) == want_depth


# ── "n target", then the tree as a level-order array ────────────────────────────────────────────────────────────────────

PATH = "Given a binary tree represented as a level-order array of {n} integers and a target sum, determine if there exists a root-to-leaf path with that sum."


def test_a_level_order_array_after_a_header_line_is_drawn_as_the_complete_tree():
    model = dg.plan(q(PATH.format(n=5), "arr:int[0]\narr2:int[0]", "5 17\n4 13 17 6 9", "First line: one line of integers, the list arr.\nThen: one line of integers, the list arr2.", "trees"))
    assert model is not None and model.kind == "binary_tree"
    assert sorted((int(model.label(a)), int(model.label(b))) for a, b, _ in model.edges) == [(4, 13), (4, 17), (13, 6), (13, 9)]


def test_a_header_that_does_not_say_how_long_the_array_is_gets_no_diagram():
    assert dg.plan(q(PATH.format(n=5), "arr:int[0]\narr2:int[0]", "6 17\n4 13 17 6 9", "", "trees")) is None


# ── -1 in a level-order array ───────────────────────────────────────────────────────────────────────────────────────────

LEVEL = "Given a binary tree in level-order representation, determine if it is a valid Binary Search Tree."


def test_minus_one_that_nothing_explains_is_not_drawn_as_vertices():
    assert dg.plan(q(LEVEL, "n:int\narr:int[0]", "5\n2 1 3 -1 -1 -1 -1", "", "trees")) is None


def test_minus_one_that_the_statement_calls_a_missing_node_is_left_out():
    stmt = LEVEL + " A value of -1 means there is no node at that position."
    model = dg.plan(q(stmt, "n:int\narr:int[0]", "3\n2 1 3 -1 -1", "", "trees"))
    assert model is not None and sorted(int(model.label(v)) for v in model.nodes) == [1, 2, 3]


# ── adjacency matrices ─────────────────────────────────────────────────────────────────────────────────────────────────

FLOYD = "Given a weighted directed graph with {n} nodes (0-indexed: row i of the matrix is node i) as an adjacency matrix, find the shortest path between every pair. Input -1 in the matrix means no direct edge."


def test_an_adjacency_matrix_is_drawn_edge_for_edge():
    model = dg.plan(q(FLOYD.format(n=3), "n:int\ngrid:int[n][3]", "3\n0 -1 -1\n8 0 -1\n17 -1 0", "", "graphs"))
    assert model.directed and model.weight_name == "weight" and model.nodes == [0, 1, 2]
    assert sorted(model.edges) == [(1, 0, 8), (2, 0, 17)]


def test_an_adjacency_matrix_without_a_stated_no_edge_entry_gets_no_diagram():
    stmt = "Given a weighted directed graph with 3 nodes as an adjacency matrix, find the shortest path between every pair."
    assert dg.plan(q(stmt, "n:int\ngrid:int[n][3]", "3\n0 -1 -1\n8 0 -1\n17 -1 0", "", "graphs")) is None


def test_an_undirected_matrix_that_is_not_symmetric_gets_no_diagram():
    stmt = "Given a weighted undirected graph with 3 nodes as an adjacency matrix. Input -1 in the matrix means no direct edge."
    assert dg.plan(q(stmt, "n:int\ngrid:int[n][3]", "3\n0 2 -1\n5 0 1\n-1 1 0", "", "graphs")) is None


@pytest.mark.parametrize("seed", range(30))
def test_random_adjacency_matrices_are_drawn_exactly_as_their_entries_say(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 8)
    matrix = [[0 if i == j else (rng.randint(1, 9) if rng.random() < 0.35 else -1) for j in range(n)] for i in range(n)]
    sample = f"{n}\n" + "\n".join(" ".join(map(str, row)) for row in matrix)
    model, _, _, problems = draw_and_inspect(q(FLOYD.format(n=n), f"n:int\ngrid:int[n][{n}]", sample, "", "graphs"))
    assert problems == []
    want = sorted((i, j, matrix[i][j]) for i in range(n) for j in range(n) if i != j and matrix[i][j] != -1)
    assert sorted(model.edges) == want


def test_a_matrix_whose_numbering_the_statement_does_not_give_gets_no_diagram():
    stmt = "Given a weighted directed graph with 3 nodes as an adjacency matrix, find the shortest path between every pair. Input -1 in the matrix means no direct edge."
    assert dg.plan(q(stmt, "n:int\ngrid:int[n][3]", "3\n0 -1 -1\n8 0 -1\n17 -1 0", "", "graphs")) is None


def test_a_matrix_numbered_from_one_is_drawn_with_vertices_one_to_n():
    stmt = "Given a weighted directed graph with 3 nodes (numbered 1 to n) as an adjacency matrix. Input -1 in the matrix means no direct edge."
    model = dg.plan(q(stmt, "n:int\ngrid:int[n][3]", "3\n0 -1 -1\n8 0 -1\n17 -1 0", "", "graphs"))
    assert model.nodes == [1, 2, 3] and sorted(model.edges) == [(2, 1, 8), (3, 1, 17)]


def test_a_matrix_that_says_both_numberings_gets_no_diagram():
    stmt = "Given a weighted directed graph (0-indexed in the statement, numbered 1 to n in the figure) as an adjacency matrix. Input -1 in the matrix means no direct edge."
    assert dg.plan(q(stmt, "n:int\ngrid:int[n][3]", "3\n0 -1 -1\n8 0 -1\n17 -1 0", "", "graphs")) is None


# -- wording that says the listed pairs are not the graph's edges -------------------------------------------------------------

GRAPH_OK = "An undirected graph with n vertices and m edges is given. {extra}"


@pytest.mark.parametrize("extra", [
    "Then there are q queries, each asking about two vertices.",
    "The input has several test cases.",
    "Print the complement of the graph.",
    "Some pairs of vertices are forbidden to be joined.",
    "Two vertices that are not directly connected are enemies.",
    "The next m lines give pairs of vertices with no edge between them.",
])
def test_a_statement_that_says_the_pairs_are_not_the_edges_gets_no_diagram(extra):
    assert dg.plan(q(GRAPH_OK.format(extra=extra), "n:int m:int\ngrid:int[m][2]", "4 3\n1 2\n2 3\n3 4")) is None


def test_an_ordinary_property_of_the_graph_does_not_trigger_the_guard():
    stmt = "An undirected graph with n vertices and m edges is given. If the graph is not connected, print -1."
    assert dg.plan(q(stmt, "n:int m:int\ngrid:int[m][2]", "4 3\n1 2\n2 3\n3 4")) is not None


# -- what the third number of an edge is --------------------------------------------------------------------------------------

def test_the_sentence_about_the_edge_names_what_it_carries():
    stmt = ("Given is an undirected connected graph with N vertices and M edges numbered 1 to M. Each edge has an integer label between 1 and N. "
            "Edge i has a label c_i, and it connects Vertex u_i and v_i bidirectionally. Snuke will write a time on each vertex.")
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "3 2\n1 2 1\n2 3 2"))
    assert model.weight_name == "label"


def test_the_time_to_pass_a_road_is_a_time_even_when_the_word_weight_appears_elsewhere():
    stmt = "n settlements are connected by m bidirectional roads. The time needed to pass each road is a or b seconds. Find the minimum total weight of the remaining roads."
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "3 2\n1 2 20\n2 3 25"))
    assert model.weight_name == "time"


def test_a_name_written_in_markdown_bold_is_still_a_named_vertex():
    stmt = "Given an undirected unweighted graph with **N** nodes and **M** edges, find the shortest path from node **S** to node **D**."
    fmt = "First line: N, M, S, D.\nNext M lines: two integers u and v representing an edge."
    model = dg.plan(q(stmt, "n:int m:int s:int t:int\ngrid:int[m][2]", "5 4 1 5\n1 2\n2 3\n3 4\n4 5", fmt))
    assert model.marks == {1: ["S"], 5: ["D"]}
    assert "S = 1" in model.caption and "D = 5" in model.caption


def test_a_name_the_schema_spells_the_same_is_paired_by_name_not_by_order():
    stmt = "An undirected graph. Find the shortest path to node T from node S."
    model = dg.plan(q(stmt, "n:int m:int s:int t:int\ngrid:int[m][2]", "5 4 1 5\n1 2\n2 3\n3 4\n4 5", SD_FMT))
    assert model.marks == {1: ["S"], 5: ["T"]}


def test_from_node_one_to_node_n_marks_both_ends():
    stmt = "Given a weighted directed graph with N nodes and M edges, find the shortest path from node 1 to node N. The weights are distances."
    model = dg.plan(q(stmt, "n:int m:int\ngrid:int[m][3]", "4 3\n1 2 5\n2 3 3\n3 4 1"))
    assert model.marks == {1: ["src"], 4: ["dst"]}


def test_not_connected_by_an_edge_as_a_precondition_of_an_operation_does_not_hide_the_graph():
    stmt = ("An undirected graph with n vertices and m edges. The operation of contraction of two vertices a and b that are not connected by an edge "
            "replaces them by a new vertex. Find the longest chain.")
    assert dg.plan(q(stmt, "n:int m:int\ngrid:int[m][2]", "4 3\n1 2\n2 3\n3 4")) is not None


# ── how the vertices are numbered ───────────────────────────────────────────────────────────────────────────────────────────
# A graph can have an isolated vertex. With 7 vertices and edges among 1..6 the vertex that is not on any edge is 0 (vertices 0..6) or 7
# (vertices 1..7): drawing either shows a vertex that does not exist and hides one that does, unless the data or the words settle it.

SEVEN = "7 6\n1 3\n1 4\n2 3\n2 4\n3 6\n5 6"
SCHEMA = "n:int m:int\ngrid:int[m][2]"
STATEMENT = "You are given a 7-node unweighted undirected graph. Find a path."


def test_a_numbering_that_neither_the_edges_nor_the_words_settle_gets_no_picture():
    assert dg.plan(q(STATEMENT, SCHEMA, SEVEN)) is None


@pytest.mark.parametrize("words, first", [
    ("(0-indexed)", 0), ("The nodes are numbered from 0.", 0), ("Vertices are numbered 0 to 6.", 0), ("Each edge is u v (0 ≤ u, v < n).", 0),
    ("(1-indexed)", 1), ("The nodes are numbered from 1.", 1), ("Vertices are numbered 1 to n.", 1), ("Each edge is u v (1 ≤ u, v ≤ n).", 1),
    ("Each edge is u_{i} v_{i} (1  ≤  u_{i},  v_{i}  ≤  n).", 1),
])
def test_a_numbering_the_statement_states_is_used(words, first):
    model = dg.plan(q(f"{STATEMENT} {words}", SCHEMA, SEVEN))
    assert model is not None and model.nodes == list(range(first, first + 7))


def test_an_unrelated_bound_is_not_taken_for_the_numbering():
    """'1 ≤ k ≤ n' bounds a count, not the vertices."""
    assert dg.plan(q(f"{STATEMENT} There are k queries (1 ≤ k ≤ n).", SCHEMA, SEVEN)) is None


@pytest.mark.parametrize("sample, first", [("7 6\n0 3\n1 4\n2 3\n2 4\n3 6\n5 6", 0), ("7 6\n1 3\n1 4\n2 3\n2 4\n3 7\n5 6", 1)])
def test_a_numbering_the_edges_settle_needs_no_words(sample, first):
    """A vertex 0 on an edge means vertices 0..n-1; a vertex n on an edge means 1..n."""
    model = dg.plan(q(STATEMENT, SCHEMA, sample))
    assert model is not None and model.nodes == list(range(first, first + 7))
