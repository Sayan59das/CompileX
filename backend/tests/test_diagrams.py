"""Graph and tree diagrams are drawn from the question's own data, and every drawing is checked against that data.

Four kinds of check:

* Plans: the model built for a question is compared with an independent reading of its sample input.
* Answers: the *model* (the structure that gets drawn) is used to recompute the question's expected output with an
  independent solver. A diagram that disagrees with the question cannot reproduce the answer.
* Pixels: the rendered PNG is decoded and compared with the model: every vertex ring and every edge is where the model
  says, no two vertices overlap, no vertex sits on someone else's edge, directed edges carry arrows.
* Fuzz: questions are built in every supported format with random contents, and go through the same checks.

Run from the backend folder:  python -m pytest tests/test_diagrams.py -q
"""

import asyncio
import base64
import collections
import heapq
import io
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from PIL import Image

from app.models.models import DifficultyLevel
from app.services import ai_generator as ag
from app.services import diagram_generator as D
from app.services.diagram_generator import diagram_generator as dg

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
BANK = os.path.join(ROOT, "question-service", "data", "reviewed_bank.jsonl")
LEGACY = os.path.join(ROOT, "question-service", "data", "questions.json")


def load_bank():
    if not os.path.exists(BANK):
        return []
    with open(BANK, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


BANK_ROWS = load_bank()
DIAGRAM_ROWS = [r for r in BANK_ROWS if r["topic"] in ("graphs", "trees")]
OTHER_ROWS = [r for r in BANK_ROWS if r["topic"] not in ("graphs", "trees")]


def as_question(r):
    return {"title": r["title"], "topic": r["topic"], "problem_statement": r["problem_statement"], "input_format": r["input_format"],
            "input_schema": r.get("input_schema"), "sample_input": r["sample_input"]}


def grid(sample):
    return [[int(x) for x in line.split()] for line in sample.strip().splitlines() if line.strip()]


# ── looking at the picture ──────────────────────────────────────────────────────────────────────────────────────────────

def rgb(hexcolour):
    return tuple(int(hexcolour[i:i + 2], 16) for i in (1, 3, 5))


def decode(url):
    assert url.startswith("data:image/png;base64,")
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")


def has_colour(img, cx, cy, hexcolour, win=3, tol=45):
    want = rgb(hexcolour)
    px = img.load()
    for x in range(int(cx) - win, int(cx) + win + 1):
        for y in range(int(cy) - win, int(cy) + win + 1):
            if 0 <= x < img.width and 0 <= y < img.height and all(abs(a - b) <= tol for a, b in zip(px[x, y], want)):
                return True
    return False


def seg_distance(p, a, b):
    ax, ay = a
    bx, by = b
    L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1e-9
    t = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L2))
    return math.hypot(p[0] - (ax + t * (bx - ax)), p[1] - (ay + t * (by - ay)))


def inspect_drawing(model, url, info):
    """Every way the picture can disagree with its model. An empty list means it agrees."""
    problems = []
    img = decode(url)
    if img.size != tuple(info["size"]) and max(abs(img.size[0] - info["size"][0]), abs(img.size[1] - info["size"][1])) > 1:
        problems.append(f"image is {img.size}, info says {info['size']}")
    if not (60 <= img.width <= 1500 and 60 <= img.height <= 1500):
        problems.append(f"image size {img.size}")
    lit = int((np.abs(np.asarray(img).astype(int) - np.array(rgb(D.BG))).max(axis=2) > 25).sum())
    if lit < 0.004 * img.width * img.height:
        problems.append("the image is almost blank")

    r_px, r = info["radius_px"], info["radius_units"]
    pos = info["positions"]
    if set(pos) != set(model.nodes):
        problems.append("the drawn vertices are not the model's vertices")
    ids = list(pos)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if math.dist(pos[a], pos[b]) < 2 * r + 0.2:
                problems.append(f"vertices {a} and {b} overlap")

    for n in model.nodes:
        cx, cy = info["node_px"][n]
        if not has_colour(img, cx, cy + 0.72 * r_px, D.NODE_FILL, win=1, tol=14):
            problems.append(f"vertex {n}: no fill where the model puts it")
        tags = model.marks.get(n, [])
        ring = D.MARK_COLOURS[tags[0]] if tags else (D.ROOT_RING if n in model.roots else D.NODE_RING)
        if not has_colour(img, cx + r_px, cy, ring, win=3, tol=60) and not has_colour(img, cx - r_px, cy, ring, win=3, tol=60):
            problems.append(f"vertex {n}: no {ring} ring")
        if info["labels"][n] != model.label(n):
            problems.append(f"vertex {n}: label {info['labels'][n]!r} != {model.label(n)!r}")

    if len(info["edges"]) != len(model.edges):
        problems.append(f"{len(info['edges'])} edges drawn for {len(model.edges)} in the model")
    for e in info["edges"]:
        a, b, w = model.edges[e["i"]]
        if (e["from"], e["to"]) != (a, b):
            problems.append(f"edge {e['i']} drawn between {e['from']},{e['to']} but the model says {a},{b}")
        if e["arrow"] != model.directed:
            problems.append(f"edge {e['i']}: arrow flag {e['arrow']} but directed is {model.directed}")
        mx, my = e["mid_px"]
        if w is not None:
            if not has_colour(img, mx, my, D.WEIGHT_TEXT, win=16, tol=70):
                problems.append(f"edge {a}-{b}: weight {w} not visible at its midpoint")
        elif not has_colour(img, mx, my, D.EDGE, win=3, tol=45):
            problems.append(f"edge {a}-{b}: no line at its midpoint")
        for n, p in pos.items():  # whatever the shape of the edge, no other vertex may touch it
            if n not in (a, b) and min(seg_distance(p, q0, q1) for q0, q1 in zip(e["path"], e["path"][1:])) < r + 0.03:
                problems.append(f"vertex {n} touches the edge {a}-{b}")
    return problems


def draw_and_inspect(q):
    model = dg.plan(q)
    assert model is not None, "a diagram was expected"
    url, info = dg.render(model)
    return model, url, info, inspect_drawing(model, url, info)


# ── solving from the picture's own structure ────────────────────────────────────────────────────────────────────────────

def adjacency(m, directed=None):
    directed = m.directed if directed is None else directed
    adj = {v: set() for v in m.nodes}
    for a, b, _ in m.edges:
        if a == b:
            continue
        adj[a].add(b)
        if not directed:
            adj[b].add(a)
    return adj


def components(m):
    adj = adjacency(m, directed=False)
    seen, out = set(), []
    for v in m.nodes:
        if v in seen:
            continue
        comp, stack = set(), [v]
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            stack.extend(adj[u] - comp)
        seen |= comp
        out.append(comp)
    return out


def kahn(m):
    """How many tasks can be finished: Kahn's algorithm, counting every edge (a pair of tasks may have several rules)."""
    indeg = {v: 0 for v in m.nodes}
    out = {v: [] for v in m.nodes}
    for a, b, _ in m.edges:
        indeg[b] += 1
        out[a].append(b)
    ready = [v for v in m.nodes if indeg[v] == 0]
    done = 0
    while ready:
        v = ready.pop()
        done += 1
        for w in out[v]:
            indeg[w] -= 1
            if indeg[w] == 0:
                ready.append(w)
    return done


def reachable(m, start):
    adj = adjacency(m)
    seen, stack = {start}, [start]
    while stack:
        for w in adj[stack.pop()]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen)


def dijkstra(m, s, t):
    adj = collections.defaultdict(list)
    for a, b, w in m.edges:
        adj[a].append((b, w))
        if not m.directed:
            adj[b].append((a, w))
    best, heap = {s: 0}, [(0, s)]
    while heap:
        cost, v = heapq.heappop(heap)
        if v == t:
            return cost
        if cost > best.get(v, math.inf):
            continue
        for w, c in adj[v]:
            if cost + c < best.get(w, math.inf):
                best[w] = cost + c
                heapq.heappush(heap, (cost + c, w))
    return -1


def tree_of(m):
    kids = {v: [] for v in m.nodes}
    parent = {}
    for a, b, _ in m.edges:
        kids[a].append(b)
        parent[b] = a
    return kids, parent


def depth_of(m):
    kids, _ = tree_of(m)
    depth = {}
    stack = [(r, 1) for r in m.roots]
    while stack:
        v, d = stack.pop()
        depth[v] = d
        stack.extend((c, d + 1) for c in kids[v])
    return depth


def subtree_size(m, x):
    kids, _ = tree_of(m)
    count, stack = 0, [x]
    while stack:
        v = stack.pop()
        count += 1
        stack.extend(kids[v])
    return count


def mark(m, tag):
    return next(v for v, tags in m.marks.items() if tag in tags)


def lowest_common(m, x, y):
    _, parent = tree_of(m)
    chain = [x]
    while chain[-1] in parent:
        chain.append(parent[chain[-1]])
    seen = set(chain)
    v = y
    while v not in seen:
        v = parent[v]
    return v


def tree_distance(m, x, y):
    adj = adjacency(m, directed=False)
    dist, queue = {x: 0}, collections.deque([x])
    while queue:
        v = queue.popleft()
        for w in adj[v]:
            if w not in dist:
                dist[w] = dist[v] + 1
                queue.append(w)
    return dist[y]


def triangles(m):
    adj = adjacency(m, directed=False)
    return sum(1 for a in m.nodes for b in adj[a] for c in adj[b] if a < b < c and c in adj[a])


def most_connected(m):
    adj = adjacency(m, directed=False)
    return min(m.nodes, key=lambda v: (-len(adj[v]), v))


ORACLES = {
    "Friend Groups": lambda m: len(components(m)),
    "Most Connected Person": most_connected,
    "People Without Friends": lambda m: sum(1 for v, a in adjacency(m, directed=False).items() if not a),
    "Largest Friend Group": lambda m: max(len(c) for c in components(m)),
    "Friend Triangles": triangles,
    "Extra Roads": lambda m: len(m.edges) - (len(m.nodes) - len(components(m))),
    "Tasks That Can Be Finished": kahn,
    "Who Hears the News": lambda m: reachable(m, 1),
    "Cheapest Route Between Two Cities": lambda m: dijkstra(m, mark(m, "s"), mark(m, "t")),
    "The Longest Chain of Command": lambda m: max(depth_of(m).values()),
    "People Without Reports": lambda m: sum(1 for v, k in tree_of(m)[0].items() if not k),
    "Most Crowded Generation": lambda m: max(collections.Counter(depth_of(m).values()).values()),
    "Size of a Folder": lambda m: subtree_size(m, mark(m, "x")),
    "Lowest Common Boss": lambda m: lowest_common(m, mark(m, "x"), mark(m, "y")),
    "Steps Between Two Employees": lambda m: tree_distance(m, mark(m, "x"), mark(m, "y")),
    "Heap Violations": lambda m: sum(1 for a, b, _ in m.edges if int(m.label(b)) < int(m.label(a))),
}

EXPECTED_DIRECTED = {"Tasks That Can Be Finished": True, "Who Hears the News": True}


# ── the reviewed bank ───────────────────────────────────────────────────────────────────────────────────────────────────

pytestmark = pytest.mark.skipif(not BANK_ROWS, reason="the reviewed bank is not in this checkout")


def test_the_bank_holds_graph_and_tree_questions_and_every_one_has_an_oracle():
    titles = {r["title"] for r in DIAGRAM_ROWS}
    assert len(titles) >= 16
    assert titles <= set(ORACLES), f"no oracle for {titles - set(ORACLES)}"


@pytest.mark.parametrize("row", DIAGRAM_ROWS, ids=lambda r: r["title"])
def test_the_plan_matches_the_sample_input_read_independently(row):
    model = dg.plan(as_question(row))
    assert model is not None
    g = grid(row["sample_input"])
    if row["topic"] == "graphs":
        n, body = g[0][0], g[1:]
        assert model.kind == "graph"
        assert model.nodes == list(range(1, n + 1))
        assert model.directed is EXPECTED_DIRECTED.get(row["title"], False)
        key = (lambda a, b, w: (a, b, w)) if model.directed else (lambda a, b, w: (min(a, b), max(a, b), w))
        assert collections.Counter(key(a, b, w) for a, b, w in model.edges) == collections.Counter(key(r[0], r[1], r[2] if len(r) == 3 else None) for r in body)
        assert (model.weight_name is not None) == (len(body[0]) == 3)
    elif row["title"] == "Heap Violations":
        a = g[1]
        assert model.kind == "binary_tree" and model.roots == [0]
        assert model.nodes == list(range(len(a)))
        assert sorted((p, c) for p, c, _ in model.edges) == sorted((i, c) for i in range(len(a)) for c in (2 * i + 1, 2 * i + 2) if c < len(a))
        assert [model.label(i) for i in range(len(a))] == [str(v) for v in a]
    else:
        boss = g[-1]
        assert model.kind == "tree"
        assert model.nodes == list(range(1, len(boss) + 1))
        assert model.roots == [i + 1 for i, b in enumerate(boss) if b == 0]
        assert sorted((a, b) for a, b, _ in model.edges) == sorted((b, i + 1) for i, b in enumerate(boss) if b)


@pytest.mark.parametrize("row", DIAGRAM_ROWS, ids=lambda r: r["title"])
def test_the_structure_that_is_drawn_gives_the_questions_own_answer(row):
    model = dg.plan(as_question(row))
    assert str(ORACLES[row["title"]](model)) == row["sample_output"].strip()


@pytest.mark.parametrize("row", DIAGRAM_ROWS, ids=lambda r: r["title"])
def test_the_picture_agrees_with_the_model(row):
    model, url, info, problems = draw_and_inspect(as_question(row))
    assert problems == []


def test_named_vertices_are_marked_where_the_question_names_them():
    by = {r["title"]: r for r in DIAGRAM_ROWS}
    m = dg.plan(as_question(by["Cheapest Route Between Two Cities"]))
    g = grid(by["Cheapest Route Between Two Cities"]["sample_input"])[0]
    assert m.marks == {g[2]: ["s"], g[3]: ["t"]} and m.weight_name == "toll"
    m = dg.plan(as_question(by["Lowest Common Boss"]))
    g = grid(by["Lowest Common Boss"]["sample_input"])[0]
    assert m.marks == {g[1]: ["x"], g[2]: ["y"]}
    assert dg.plan(as_question(by["Friend Groups"])).marks == {}


def test_no_other_question_in_the_bank_gets_a_diagram():
    drawn = [r["title"] for r in OTHER_ROWS if dg.plan(as_question(r)) is not None]
    assert drawn == []


def test_the_old_text_only_entry_point_cannot_invent_a_graph():
    # what the old code did with a graph question: a binary tree from the first line. Without a schema nothing is guessed.
    row = next(r for r in DIAGRAM_ROWS if r["title"] == "Friend Groups")
    out = dg.generate_diagram(row["title"], row["problem_statement"], row["sample_input"])
    assert out is None or inspect_drawing(*[(m := dg.plan({"title": row["title"], "topic": "graphs", "problem_statement": row["problem_statement"], "input_format": row["input_format"], "sample_input": row["sample_input"]})), out, dg.render(m)[1]]) == []


# ── refusing to draw what cannot be drawn with certainty ────────────────────────────────────────────────────────────────

GRAPH_FMT = "First line: two integers n and m.\nThen m lines, each with two integers u and v: a road between city u and city v."
GRAPH_TEXT = "A country has n cities numbered 1 to n and m two-way roads."


def graph_q(sample, schema="n:int m:int\nroads:int[m][2]", fmt=GRAPH_FMT, text=GRAPH_TEXT, topic="graphs", **extra):
    return {"title": "T", "topic": topic, "problem_statement": text, "input_format": fmt, "input_schema": schema, "sample_input": sample, **extra}


@pytest.mark.parametrize("why, q", [
    ("m does not match the rows", graph_q("3 2\n1 2")),
    ("a vertex outside 1..n", graph_q("3 1\n1 9")),
    ("a row with the wrong width", graph_q("3 2\n1 2\n2 3 4")),
    ("text where a number belongs", graph_q("3 1\n1 x")),
    ("no sample", graph_q("")),
    ("no schema and no shape to infer one from", graph_q("hello", schema=None)),
    ("direction not stated", graph_q("3 1\n1 2", fmt="First line: n and m.\nThen m lines: u and v.", text="A graph with n vertices.")),
    ("the third number is not described", graph_q("3 1\n1 2 5", schema="n:int m:int\nroads:int[m][3]")),
    ("a grid is not an edge list", graph_q("3 3\n1 2 3\n4 5 6\n7 8 9", schema="n:int m:int\ngrid:int[n][3]")),
    ("too many vertices", graph_q("500 1\n1 2")),
    ("the vertex count is not given", graph_q("1\n1 2", schema="m:int\nroads:int[m][2]")),
    ("another topic with intervals", graph_q("2\n1 5\n2 6", schema="n:int\nbookings:int[n][2]", topic="arrays", text="Bookings are intervals.", fmt="n then n intervals")),
    ("a topic with no graph or tree in its text", graph_q("3 1\n1 2", topic="math")),
])
def test_an_unclear_question_gets_no_diagram_and_never_a_placeholder(why, q):
    assert dg.plan(q) is None, why
    assert dg.diagram_for_question(q) is None, why


def tree_q(sample, name="boss", text="Every employee has exactly one boss, except the head, who has none. boss[i] is the boss of employee i, or 0 for the head.", schema=None, **extra):
    return {"title": "T", "topic": "trees", "problem_statement": text, "input_format": f"First line: n.\nSecond line: {name}[1] to {name}[n].",
            "input_schema": schema or f"n:int\n{name}:int[n]", "sample_input": sample, **extra}


@pytest.mark.parametrize("why, q", [
    ("a cycle of parents", tree_q("3\n2 3 1")),
    ("a parent outside 1..n", tree_q("3\n0 1 9")),
    ("a node that is its own parent", tree_q("2\n0 2")),
    ("no root at all", tree_q("2\n2 1")),
    ("an array whose meaning is not stated", tree_q("3\n0 1 1", name="a", text="You are given an array a of n numbers.")),
    ("duplicate values in a BST", tree_q("3\n5 5 7", name="a", text="The values are inserted in order into an empty binary search tree.")),
    ("a child under a missing parent", tree_q("7\n1 -1 3 4 5 6 7", name="a", text="A binary tree is stored in an array a, root at position 0, children of i at 2i + 1 and 2i + 2. -1 means no node.")),
])
def test_an_unclear_tree_gets_no_diagram(why, q):
    assert dg.plan(q) is None, why


DIRECTED_WORDS = [
    "a road from city u to city v", "person a tells person b", "task a must be finished before task b", "a one-way street from u to v",
    "a directed edge from u to v", "course a is a prerequisite of course b", "an arrow from u to v", "a message goes from a to b",
    "job a depends on job b", "u -> v",
]
UNDIRECTED_WORDS = [
    "a road between city u and city v", "person u and person v are friends", "an undirected edge between u and v", "a two-way road connecting u and v",
    "u and v are connected by a cable", "a bidirectional link between u and v", "u and v are neighbours",
]
UNCLEAR_WORDS = ["u and v", "an edge of the graph", "a pair u v"]


@pytest.mark.parametrize("line", DIRECTED_WORDS)
def test_wording_that_says_directed(line):
    assert D.classify_direction(line, line) is True


@pytest.mark.parametrize("line", UNDIRECTED_WORDS)
def test_wording_that_says_undirected(line):
    assert D.classify_direction(line, line) is False


@pytest.mark.parametrize("line", UNCLEAR_WORDS)
def test_wording_that_does_not_say(line):
    assert D.classify_direction(line, line) is None


def test_one_way_to_travel_is_not_a_one_way_road():
    assert D.classify_direction("there is at most one way to travel between two cities, using two-way roads", "a road between city u and city v") is False


def test_mixed_wording_is_refused_not_guessed():
    assert D.classify_direction("some roads are two-way and some are one-way roads", "a road between u and v") is None


def test_a_schema_is_read_exactly():
    assert D.read_sample("n:int m:int\nroads:int[m][3]", "3 2\n3 1 7\n2 3 6") == {"n": 3, "m": 2, "roads": [[3, 1, 7], [2, 3, 6]]}
    assert D.read_sample("n:int\nboss:int[n]", "3\n0 1 1\n") == {"n": 3, "boss": [0, 1, 1]}
    for bad in ("3 2\n1 2", "3 2\n1 2\n3 4\n5 6", "3 1\n1 2 3"):
        with pytest.raises(D._Reject):
            D.read_sample("n:int m:int\nroads:int[m][2]", bad)


def test_a_schema_is_inferred_only_for_shapes_that_cannot_be_mistaken():
    assert D.infer_schema("4 3\n1 2\n2 3\n3 4") == "n:int m:int\nedges:int[m][2]"
    assert D.infer_schema("4 3 1 4\n1 2 5\n2 3 6\n3 4 7") == "n:int m:int s:int t:int\nedges:int[m][3]"
    assert D.infer_schema("3\n1 2 3") == "n:int\na:int[n]"
    assert D.infer_schema("hello world") is None
    assert D.infer_schema("4 3\n1 2\n2 3") is None


# ── building questions of every kind, with random contents ──────────────────────────────────────────────────────────────

UNDIRECTED_TEMPLATES = [
    ("There are n people and m pairs of friends. Friendship is mutual.", "Then m lines, each with two integers u and v: person u and person v are friends."),
    ("A country has n cities and m two-way roads.", "Then m lines, each with two integers u and v: a road between city u and city v."),
    ("A network has n computers joined by m undirected cables.", "Then m lines, each with two integers u and v: a cable between computer u and computer v."),
]
DIRECTED_TEMPLATES = [
    ("A project has n tasks and m rules.", "Then m lines, each with two integers a and b: task a must be finished before task b."),
    ("There are n people and m one-way messages.", "Then m lines, each with two integers a and b: person a tells person b."),
    ("A city has n junctions and m one-way streets.", "Then m lines, each with two integers u and v: a one-way street from junction u to junction v."),
]
WEIGHT_NOUNS = ["toll", "cost", "distance", "time", "weight", "price"]


def random_graph_question(rng):
    n = rng.randint(2, 22)
    directed = rng.random() < 0.45
    weighted = rng.random() < 0.4
    marks = rng.random() < 0.4
    loops = directed and rng.random() < 0.2
    m = rng.randint(1, min(30, n * 2))
    rows = []
    for _ in range(m):
        u, v = rng.randint(1, n), rng.randint(1, n)
        while u == v and not loops:
            v = rng.randint(1, n)
        rows.append([u, v] + ([rng.randint(1, 99)] if weighted else []))
    statement, line = rng.choice(DIRECTED_TEMPLATES if directed else UNDIRECTED_TEMPLATES)
    noun = rng.choice(WEIGHT_NOUNS)
    if weighted:
        line = line.replace("two integers u and v", "three integers u, v and w").replace("two integers a and b", "three integers u, v and w") + f" The {noun} of using it is w."
        statement += f" Every link has its own {noun}."
    # real questions say how their vertices are numbered (the generator refuses when neither the words nor the edges settle it)
    statement += " The vertices are numbered from 1 to n."
    head = [n, m]
    names = "n:int m:int"
    if marks:
        s, t = rng.sample(range(1, n + 1), 2)
        head += [s, t]
        names += " s:int t:int"
        statement += " A traveller starts in city s and wants to reach city t."
    first = "First line: " + ("four integers n, m, s and t." if marks else "two integers n and m.")
    q = {"title": "Fuzz", "topic": "graphs", "problem_statement": statement, "input_format": first + "\n" + line,
         "input_schema": names + f"\nedges:int[m][{3 if weighted else 2}]",
         "sample_input": " ".join(map(str, head)) + "\n" + "\n".join(" ".join(map(str, r)) for r in rows)}
    return q, {"n": n, "directed": directed, "rows": rows, "weighted": weighted, "noun": noun, "marks": (head[2], head[3]) if marks else None}


def check_graph(q, want):
    model, url, info, problems = draw_and_inspect(q)
    assert model.kind == "graph" and model.directed is want["directed"] and model.nodes == list(range(1, want["n"] + 1))
    key = (lambda a, b, w: (a, b, w)) if model.directed else (lambda a, b, w: (min(a, b), max(a, b), w))
    expected = collections.Counter(key(r[0], r[1], r[2] if want["weighted"] else None) for r in want["rows"])
    assert collections.Counter(key(a, b, w) for a, b, w in model.edges) == expected
    if want["weighted"]:
        assert model.weight_name == want["noun"]
    if want["marks"]:
        s, t = want["marks"]
        assert "s" in model.marks[s] and "t" in model.marks[t]
    return problems


def random_tree_question(rng):
    n = rng.randint(1, 26)
    order = list(range(1, n + 1))
    rng.shuffle(order)
    boss = [0] * (n + 1)
    shape = rng.choice(["random", "chain", "star", "broom"])
    for i in range(1, n):
        if shape == "random":
            p = order[rng.randint(0, i - 1)]
        elif shape == "chain":
            p = order[i - 1]
        elif shape == "star":
            p = order[0]
        else:
            p = order[i - 1] if i < n // 2 else order[n // 2 - 1 if n > 1 else 0]
        boss[order[i]] = p
    name = rng.choice(["boss", "parent", "inside"])
    text = f"Every node has exactly one parent, except the oldest, who has none. {name}[i] is the number of the parent of i, or 0 for the oldest."
    marks = rng.random() < 0.4 and n >= 2
    first, schema = [n], "n:int"
    if marks:
        x, y = rng.sample(range(1, n + 1), 2)
        first += [x, y]
        schema += " x:int y:int"
        text += " Find something about x and y."
    q = {"title": "Fuzz tree", "topic": "trees", "problem_statement": text, "input_format": f"First line: n.\nSecond line: n integers, {name}[1] to {name}[n].",
         "input_schema": schema + f"\n{name}:int[n]", "sample_input": " ".join(map(str, first)) + "\n" + " ".join(map(str, boss[1:]))}
    return q, {"n": n, "boss": boss[1:], "marks": (first[1], first[2]) if marks else None}


def check_tree(q, want):
    model, url, info, problems = draw_and_inspect(q)
    n, boss = want["n"], want["boss"]
    assert model.kind == "tree" and model.nodes == list(range(1, n + 1)) and not model.directed
    assert sorted((a, b) for a, b, _ in model.edges) == sorted((b, i + 1) for i, b in enumerate(boss) if b)
    assert model.roots == [i + 1 for i, b in enumerate(boss) if b == 0]
    kids, parent = tree_of(model)
    # the drawing is a top-down tree: a child is always lower than its parent
    for a, b, _ in model.edges:
        assert info["positions"][b][1] < info["positions"][a][1]
    return problems


HEAP_TEXT = "A binary tree is stored in an array a of n numbers, with the root at position 0. The children of the node at position i are at positions 2i + 1 and 2i + 2."


def random_heap_question(rng):
    n = rng.randint(1, 31)
    a = [rng.choice([rng.randint(-999999, 999999), rng.randint(-9, 9)]) for _ in range(n)]
    q = {"title": "Fuzz heap", "topic": "trees", "problem_statement": HEAP_TEXT + " Count something.", "input_format": "First line: n.\nSecond line: the array.",
         "input_schema": "n:int\na:int[n]", "sample_input": f"{n}\n" + " ".join(map(str, a))}
    return q, a


def check_heap(q, a):
    model, url, info, problems = draw_and_inspect(q)
    assert model.kind == "binary_tree" and model.nodes == list(range(len(a))) and model.roots == [0]
    assert sorted((p, c) for p, c, _ in model.edges) == sorted((i, c) for i in range(len(a)) for c in (2 * i + 1, 2 * i + 2) if c < len(a))
    for p, c, _ in model.edges:  # a left child is left of its parent, a right child to the right
        assert (info["positions"][c][0] < info["positions"][p][0]) == (c == 2 * p + 1)
        assert info["positions"][c][1] < info["positions"][p][1]
    return problems


def random_bst_question(rng):
    n = rng.randint(1, 18)
    values = rng.sample(range(-50, 100), n)
    q = {"title": "Fuzz bst", "topic": "trees", "problem_statement": "The n values are inserted one by one, in the order given, into an empty binary search tree. Smaller values go left, larger values go right.",
         "input_format": "First line: n.\nSecond line: the values.", "input_schema": "n:int\nvalues:int[n]", "sample_input": f"{n}\n" + " ".join(map(str, values))}
    return q, values


def check_bst(q, values):
    model, url, info, problems = draw_and_inspect(q)
    assert model.kind == "binary_tree" and [model.label(i) for i in range(len(values))] == [str(v) for v in values]
    for p, c, _ in model.edges:
        assert (values[c] < values[p]) == (info["positions"][c][0] < info["positions"][p][0])
    # a BST read in order is sorted: the in-order x of the drawing must list the values in increasing order
    by_x = sorted(model.nodes, key=lambda v: info["positions"][v][0])
    assert [values[v] for v in by_x] == sorted(values)
    return problems


def random_sparse_question(rng):
    n = rng.randint(3, 21)
    a = [rng.randint(0, 99)]
    for i in range(1, n):
        a.append(rng.randint(0, 99) if a[(i - 1) // 2] != -1 and rng.random() < 0.7 else -1)
    q = {"title": "Fuzz sparse", "topic": "trees", "problem_statement": HEAP_TEXT + " The value -1 means there is no node at that position.",
         "input_format": "First line: n.\nSecond line: the array.", "input_schema": "n:int\na:int[n]", "sample_input": f"{n}\n" + " ".join(map(str, a))}
    return q, a


def check_sparse(q, a):
    model, url, info, problems = draw_and_inspect(q)
    present = [i for i, v in enumerate(a) if v != -1]
    assert model.nodes == present
    assert sorted((p, c) for p, c, _ in model.edges) == sorted((i, c) for i in present for c in (2 * i + 1, 2 * i + 2) if c < len(a) and a[c] != -1)
    return problems


FUZZ = [("graph", random_graph_question, check_graph, 70), ("tree", random_tree_question, check_tree, 45), ("heap", random_heap_question, check_heap, 25),
        ("bst", random_bst_question, check_bst, 20), ("sparse", random_sparse_question, check_sparse, 15)]


@pytest.mark.parametrize("kind, make, check, count", FUZZ, ids=[f[0] for f in FUZZ])
def test_questions_built_from_scratch_are_planned_and_drawn_correctly(kind, make, check, count):
    rng = random.Random(f"diagrams-{kind}")
    failures = []
    for i in range(count):
        q, want = make(rng)
        try:
            problems = check(q, want)
        except AssertionError as exc:
            failures.append((i, "plan", str(exc)[:200], q["sample_input"][:80]))
            continue
        if problems:
            failures.append((i, "picture", problems[:3], q["sample_input"][:80]))
    assert failures == []


def test_an_edge_list_with_no_edges_still_draws_every_vertex():
    q = graph_q("4 0", schema="n:int m:int\nroads:int[m][2]")
    model, url, info, problems = draw_and_inspect(q)
    assert model.nodes == [1, 2, 3, 4] and model.edges == [] and problems == []


def test_parallel_edges_and_opposite_directed_edges_are_all_drawn_and_apart():
    q = graph_q("3 4\n1 2\n2 1\n1 2\n2 3", fmt="First line: n and m.\nThen m lines: a one-way street from u to v.", text="A city with one-way streets.")
    model, url, info, problems = draw_and_inspect(q)
    assert model.directed and len(info["edges"]) == 4 and problems == []
    rads = [round(e["rad"], 2) for e in info["edges"] if {e["from"], e["to"]} == {1, 2}]
    assert len(set(rads)) >= 2  # they do not lie on top of each other


# ── the question service's older banks ──────────────────────────────────────────────────────────────────────────────────

def legacy_rows():
    if not os.path.exists(LEGACY):
        return []
    with open(LEGACY, encoding="utf-8") as f:
        return [q for q in json.load(f) if q.get("topic") in ("graphs", "trees")]


def test_the_older_banks_never_get_a_wrong_diagram():
    rows = legacy_rows()
    drawn = 0
    for r in rows:
        q = {"title": r["title"], "topic": r["topic"], "problem_statement": r["problem_statement"], "input_format": r.get("input_format", ""),
             "sample_input": r.get("sample_input", "")}
        model = dg.plan(q)
        if model is None:
            continue
        drawn += 1
        _, url, info, problems = draw_and_inspect(q)
        assert problems == [], r["title"]
        grid_rows = grid(q["sample_input"])
        if model.kind == "graph":
            assert len(model.edges) == grid_rows[0][1] and len(model.nodes) == grid_rows[0][0], r["title"]
    print(f"\n[legacy] {drawn} of {len(rows)} older graph/tree questions are drawn, the rest get no diagram")


# ── through the backend ─────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def image_model_must_not_be_asked(monkeypatch):
    from app.services.nvidia_image_service import nvidia_image_service

    async def forbidden(self_or_text, *a, **k):
        raise AssertionError("the image model was asked to draw a diagram")

    monkeypatch.setattr(type(nvidia_image_service), "analyze_and_generate_image", forbidden)


def build(row):
    return asyncio.run(ag._build_result(dict(row), DifficultyLevel.EASY, row["topic"]))


@pytest.mark.parametrize("row", DIAGRAM_ROWS, ids=lambda r: r["title"])
def test_a_served_graph_or_tree_question_carries_its_diagram(row, image_model_must_not_be_asked):
    out = build(row)
    assert out["diagram"] and out["diagram"].startswith("data:image/png;base64,")
    model = dg.plan(as_question(row))
    assert decode(out["diagram"]).size == tuple(dg.render(model)[1]["size"])  # the same picture the model draws


def test_a_served_question_of_another_topic_carries_none(image_model_must_not_be_asked):
    for row in OTHER_ROWS[:25]:
        assert build(row)["diagram"] is None


def test_a_question_that_cannot_be_drawn_is_served_without_a_diagram_not_a_wrong_one(image_model_must_not_be_asked):
    row = dict(next(r for r in DIAGRAM_ROWS if r["title"] == "Friend Groups"))
    row["input_schema"] = None
    row["sample_input"] = "this is not a graph"
    assert build(row)["diagram"] is None


# ── a vertex variable the statement names but the format calls something else ───────────────────────────────────────────

SRC_STATEMENT = "Given 7 nodes and weighted undirected edges (weights up to 19), determine the minimum travel cost from source `src` to all destinations."
SRC_FORMAT = "First line: the integers n, m, k.\nThen: m lines of 3 integers each, the grid grid."
SRC_SAMPLE = "7 6 4\n0 1 1\n0 2 15\n1 3 17\n1 4 18\n2 5 11\n0 6 17"


def src_q(statement=SRC_STATEMENT, fmt=SRC_FORMAT, sample=SRC_SAMPLE):
    return {"title": "Weighted Graph Distance Problem", "topic": "graphs", "problem_statement": statement, "input_format": fmt, "sample_input": sample}


def test_the_one_unexplained_number_is_the_vertex_the_statement_names():
    model = dg.plan(src_q())
    assert model.marks == {4: ["src"]}
    assert "src = 4" in model.caption


def test_nothing_is_marked_when_the_statement_names_no_vertex_variable():
    assert dg.plan(src_q(statement=SRC_STATEMENT.replace("`src`", "a source"))).marks == {}


def test_two_unexplained_numbers_are_not_guessed():
    sample = SRC_SAMPLE.replace("7 6 4", "7 6 4 2")
    model = dg.plan(src_q(fmt="First line: the integers n, m, k, q.\nThen: m lines of 3 integers each, the grid grid.", sample=sample))
    assert model is not None and model.marks == {}


def test_an_unexplained_number_that_is_not_a_vertex_is_not_marked():
    assert dg.plan(src_q(sample=SRC_SAMPLE.replace("7 6 4", "7 6 40"))).marks == {}
