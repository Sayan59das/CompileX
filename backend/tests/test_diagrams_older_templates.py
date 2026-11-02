"""The question service can still serve its older, template-made graph and tree questions (when a topic's reviewed questions are
used up). Each of the ten templates is drawn here, over many random seeds, and the structure that is drawn must give the
template's own sample output.

Run from the backend folder:  python -m pytest tests/test_diagrams_older_templates.py -q
"""

import collections
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "question-service"))

import pytest

from app.services import diagram_generator as D
from app.services.diagram_generator import diagram_generator as dg
from test_diagrams import decode, draw_and_inspect, has_colour, mark, rgb

try:
    from model import dynamic_generator as G
except Exception:  # the question service is not in this checkout, or its imports are missing
    G = None

pytestmark = pytest.mark.skipif(G is None, reason="the question service's templates are not importable here")

NAMES = ["_graph_bfs_shortest_path", "_graph_number_of_islands", "_graph_detect_cycle", "_graph_topological_sort", "_graph_dijkstra",
         "_tree_inorder", "_tree_max_depth", "_tree_level_order", "_tree_diameter", "_tree_lowest_common_ancestor"]


def question(name, seed):
    q = getattr(G, name)(random.Random(seed))
    topic = "graphs" if name.startswith("_graph") else "trees"
    return q, {"title": q["title"], "topic": topic, "problem_statement": q["problem_statement"], "input_format": q.get("input_format", ""),
               "sample_input": q.get("sample_input", "")}


# ── answers recomputed from what is drawn ───────────────────────────────────────────────────────────────────────────────

def undirected(m):
    adj = {v: set() for v in m.nodes}
    for a, b, _ in m.edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def hops(m, s, t):
    adj, dist, queue = undirected(m), {s: 0}, collections.deque([s])
    while queue:
        v = queue.popleft()
        for w in adj[v]:
            if w not in dist:
                dist[w] = dist[v] + 1
                queue.append(w)
    return dist.get(t, -1)


def islands(m):
    seen, count = set(), 0
    rows, cols = len(m.grid), len(m.grid[0])
    for r in range(rows):
        for c in range(cols):
            if m.grid[r][c] == 1 and (r, c) not in seen:
                count += 1
                stack = [(r, c)]
                while stack:
                    y, x = stack.pop()
                    if (y, x) in seen or not (0 <= y < rows and 0 <= x < cols) or m.grid[y][x] != 1:
                        continue
                    seen.add((y, x))
                    stack.extend([(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)])
    return count


def has_cycle(m):
    parent = {v: v for v in m.nodes}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for a, b, _ in m.edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            return True
        parent[ra] = rb
    return False


def dijkstra_all(m, src):
    import heapq
    adj = collections.defaultdict(list)
    for a, b, w in m.edges:
        adj[a].append((b, w))
        adj[b].append((a, w))
    best, heap = {src: 0}, [(0, src)]
    while heap:
        cost, v = heapq.heappop(heap)
        if cost > best.get(v, float("inf")):
            continue
        for w, c in adj[v]:
            if cost + c < best.get(w, float("inf")):
                best[w] = cost + c
                heapq.heappush(heap, (cost + c, w))
    return [best.get(v, -1) for v in sorted(m.nodes)]


def bst_walk(m):
    left = {a: b for a, b, _ in m.edges if m.sides[b] == "L"}
    right = {a: b for a, b, _ in m.edges if m.sides[b] == "R"}
    return left, right


def inorder(m):
    left, right = bst_walk(m)
    out = []

    def walk(v):
        if v in left:
            walk(left[v])
        out.append(int(m.label(v)))
        if v in right:
            walk(right[v])

    walk(m.roots[0])
    return out


def levels(m):
    left, right = bst_walk(m)
    rows, level = [], [m.roots[0]]
    while level:
        rows.append([int(m.label(v)) for v in level])
        level = [c for v in level for c in (left.get(v), right.get(v)) if c is not None]
    return rows


def diameter_edges(m):
    adj = undirected(m)

    def far(start):
        dist, queue = {start: 0}, collections.deque([start])
        while queue:
            v = queue.popleft()
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
        return max(dist.items(), key=lambda t: t[1])

    a, _ = far(m.nodes[0])
    return far(a)[1]


def common_ancestor(m, p, q):
    parent = {b: a for a, b, _ in m.edges}
    chain, v = [], p
    while True:
        chain.append(v)
        if v not in parent:
            break
        v = parent[v]
    v = q
    while v not in chain:
        v = parent[v]
    return int(m.label(v))


def topological_order_is_valid(m, order):
    where = {v: i for i, v in enumerate(order)}
    return sorted(order) == sorted(m.nodes) and all(where[a] < where[b] for a, b, _ in m.edges)


def label_vertex(m, tag):
    return next(v for v, tags in m.marks.items() if tag in tags)


def answer_from_drawing(name, m, q):
    if name == "_graph_bfs_shortest_path":
        return str(hops(m, label_vertex(m, "src"), label_vertex(m, "dst")))
    if name == "_graph_number_of_islands":
        return str(islands(m))
    if name == "_graph_detect_cycle":
        return "true" if has_cycle(m) else "false"
    if name == "_graph_dijkstra":
        return " ".join(map(str, dijkstra_all(m, label_vertex(m, "src"))))
    if name == "_tree_inorder":
        return " ".join(map(str, inorder(m)))
    if name == "_tree_max_depth":
        return str(len(levels(m)))
    if name == "_tree_level_order":
        return "\n".join(" ".join(map(str, row)) for row in levels(m))
    if name == "_tree_diameter":
        return str(diameter_edges(m))
    if name == "_tree_lowest_common_ancestor":
        return str(common_ancestor(m, label_vertex(m, "p"), label_vertex(m, "q")))
    raise AssertionError(name)


@pytest.mark.parametrize("seed", range(14))
@pytest.mark.parametrize("name", NAMES)
def test_the_structure_drawn_for_an_older_template_gives_its_sample_output(name, seed):
    q, as_q = question(name, seed)
    m = dg.plan(as_q)
    assert m is not None, f"{name} seed {seed}: no diagram for {q['sample_input']!r}"
    if name == "_graph_topological_sort":
        order = [int(x) for x in q["sample_output"].split()]
        assert m.directed and topological_order_is_valid(m, order)
        return
    assert answer_from_drawing(name, m, q) == q["sample_output"].strip()


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("name", [n for n in NAMES if n != "_graph_number_of_islands"])
def test_the_picture_of_an_older_template_agrees_with_its_model(name, seed):
    q, as_q = question(name, seed)
    model, url, info, problems = draw_and_inspect(as_q)
    assert problems == []


@pytest.mark.parametrize("seed", range(8))
def test_a_grid_is_drawn_cell_for_cell(seed):
    q, as_q = question("_graph_number_of_islands", seed)
    m = dg.plan(as_q)
    assert m.kind == "grid" and m.grid == [[int(x) for x in row.split()] for row in q["sample_input"].splitlines()]
    url, info = dg.render(m)
    img = decode(url)
    assert len(info["cells"]) == len(m.grid) * len(m.grid[0])
    for cell in info["cells"]:
        cx, cy = cell["centre_px"]
        want = D.LAND if cell["value"] else D.WATER
        assert has_colour(img, cx - 20, cy - 20, want, win=2, tol=14), cell
        assert not has_colour(img, cx - 20, cy - 20, D.WATER if cell["value"] else D.LAND, win=0, tol=14), cell


def test_named_vertices_of_an_older_template_are_marked_by_their_own_names():
    q, as_q = question("_graph_bfs_shortest_path", 3)
    m = dg.plan(as_q)
    src, dst = [int(x) for x in q["sample_input"].splitlines()[-1].split()]
    assert m.marks[src] == ["src"] and m.marks[dst] == ["dst"] or src == dst
    q, as_q = question("_tree_lowest_common_ancestor", 3)
    m = dg.plan(as_q)
    p, qq = [int(x) for x in q["sample_input"].splitlines()[-1].split()]
    assert m.label(label_vertex(m, "p")) == str(p) and m.label(label_vertex(m, "q")) == str(qq)


def test_an_older_format_that_is_not_recognised_gets_no_diagram():
    as_q = {"title": "T", "topic": "graphs", "problem_statement": "A graph question.", "input_format": "Some free text.", "sample_input": "5 3 9\n1 2\n3 4"}
    assert dg.plan(as_q) is None
    as_q = {"title": "T", "topic": "trees", "problem_statement": "A BST question.", "input_format": "Free text.", "sample_input": "5 3 9"}
    assert dg.plan(as_q) is None


def test_a_grid_that_is_not_zeros_and_ones_is_not_drawn():
    as_q = {"title": "T", "topic": "graphs", "problem_statement": "A grid of costs.", "input_format": "The grid: 2 rows of 2 integers.", "sample_input": "1 5\n3 0"}
    assert dg.plan(as_q) is None
