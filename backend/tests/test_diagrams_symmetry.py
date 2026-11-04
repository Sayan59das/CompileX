"""Drawings are symmetric and aligned: regular figures are drawn regular, a graph that has a mirror symmetry is drawn as an exact mirror
image of itself, rows and columns line up exactly, and the vertices sit in the middle of the frame.

Run from the backend folder:  python -m pytest tests/test_diagrams_symmetry.py -q
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import diagram_generator as D
from app.services.diagram_generator import diagram_generator as dg
from test_diagrams import draw_and_inspect, graph_q

UND = "A country has n cities numbered 1 to n and m two-way roads."
DIR = "A system has n tasks numbered 1 to n and m one-way links."


def question(pairs, n, text=UND):
    body = "\n".join(" ".join(map(str, p)) for p in pairs)
    return graph_q(f"{n} {len(pairs)}\n{body}", "n:int m:int\nroads:int[m][2]", text=text)


def positions(pairs, n, text=UND):
    model = dg.plan(question(pairs, n, text))
    assert model is not None
    return model, dg._layout(model)


def cycle_pairs(n):
    return [(i, i % n + 1) for i in range(1, n + 1)]


def centroid(pts):
    return (sum(p[0] for p in pts.values()) / len(pts), sum(p[1] for p in pts.values()) / len(pts))


def assert_regular(pts, order):
    """The vertices, taken in this order, are the corners of a regular polygon."""
    cx, cy = centroid(pts)
    radii = [math.dist(pts[v], (cx, cy)) for v in order]
    assert max(radii) - min(radii) < 1e-6, radii
    sides = [math.dist(pts[order[i]], pts[order[(i + 1) % len(order)]]) for i in range(len(order))]
    assert max(sides) - min(sides) < 1e-6, sides


# ── regular figures ─────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("n", range(4, 13))
@pytest.mark.parametrize("text", [UND, DIR], ids=["undirected", "directed"])
def test_a_cycle_is_a_regular_polygon_in_cycle_order(n, text):
    model, pts = positions(cycle_pairs(n), n, text)
    assert_regular(pts, list(range(1, n + 1)))
    assert dg.render(model)[1]["size"][0] > 0


@pytest.mark.parametrize("n", range(4, 9))
def test_a_complete_graph_is_a_regular_polygon(n):
    pairs = [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]
    _, pts = positions(pairs, n)
    assert_regular(pts, list(range(1, n + 1)))


@pytest.mark.parametrize("leaves", range(3, 9))
def test_a_star_has_its_leaves_evenly_round_the_hub(leaves):
    pairs = [(1, v) for v in range(2, leaves + 2)]
    _, pts = positions(pairs, leaves + 1)
    assert pts[1] == pytest.approx(centroid({v: pts[v] for v in range(2, leaves + 2)}), abs=1e-6)
    assert_regular({v: pts[v] for v in range(2, leaves + 2)}, list(range(2, leaves + 2)))


@pytest.mark.parametrize("n", range(4, 8))
def test_a_short_path_is_a_straight_horizontal_line_with_equal_steps(n):
    _, pts = positions([(i, i + 1) for i in range(1, n)], n)
    ys = {round(pts[v][1], 9) for v in pts}
    xs = [pts[v][0] for v in range(1, n + 1)]
    assert len(ys) == 1
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert max(steps) - min(steps) < 1e-9 and min(steps) > 0


@pytest.mark.parametrize("n", range(5, 11))
def test_a_wheel_has_its_hub_in_the_middle_of_a_regular_rim(n):
    rim = list(range(2, n + 1))
    pairs = [(1, v) for v in rim] + [(rim[i], rim[(i + 1) % len(rim)]) for i in range(len(rim))]
    _, pts = positions(pairs, n)
    assert pts[1] == pytest.approx(centroid({v: pts[v] for v in rim}), abs=1e-6)
    assert_regular({v: pts[v] for v in rim}, rim)


@pytest.mark.parametrize("a, b", [(2, 3), (2, 4), (3, 3), (3, 4)])
def test_a_complete_bipartite_graph_is_two_centred_rows(a, b):
    left, right = list(range(1, a + 1)), list(range(a + 1, a + b + 1))
    _, pts = positions([(u, v) for u in left for v in right], a + b)
    rows = {}
    for v, (x, y) in pts.items():
        rows.setdefault(round(y, 9), []).append(x)
    assert len(rows) == 2
    centres = [(min(xs) + max(xs)) / 2 for xs in rows.values()]
    assert centres[0] == pytest.approx(centres[1], abs=1e-9), "the two rows are not centred on one axis"
    for xs in rows.values():
        steps = [b - a for a, b in zip(sorted(xs), sorted(xs)[1:])]
        assert max(steps) - min(steps) < 1e-9, "uneven spacing within a row"


# ── mirror symmetry and alignment ───────────────────────────────────────────────────────────────────────────────────────

def mirror_images(pts, axis):
    c = centroid(pts)[axis]
    flipped = [((2 * c - x, y) if axis == 0 else (x, 2 * c - y)) for x, y in pts.values()]
    return all(any(math.dist(f, p) < 1e-6 for p in pts.values()) for f in flipped)


SYMMETRIC = {
    "diamond": ([(1, 2), (1, 3), (2, 4), (3, 4), (2, 3)], 4),
    "ladder 2x3": ([(1, 2), (2, 3), (4, 5), (5, 6), (1, 4), (2, 5), (3, 6)], 6),
    "ladder 2x4": ([(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (1, 5), (2, 6), (3, 7), (4, 8)], 8),
    "K2,3": ([(a, b) for a in (1, 2) for b in (3, 4, 5)], 5),
    "bow tie": ([(1, 2), (2, 3), (3, 1), (3, 4), (4, 5), (5, 3)], 5),
    "H": ([(1, 3), (2, 3), (3, 4), (4, 5), (4, 6)], 6),
    "square with a diagonal-free centre": ([(1, 2), (2, 3), (3, 4), (4, 1), (1, 5), (2, 5), (3, 5), (4, 5)], 5),
}


@pytest.mark.parametrize("name", SYMMETRIC)
def test_a_graph_with_a_mirror_symmetry_is_drawn_as_its_own_mirror_image(name):
    pairs, n = SYMMETRIC[name]
    model, pts = positions(pairs, n)
    assert mirror_images(pts, 0) or mirror_images(pts, 1), f"{name} is not drawn symmetrically"
    draw_and_inspect(question(pairs, n))  # and it is still clear of overlaps


def test_the_rows_and_columns_of_a_ladder_line_up_exactly():
    pairs, n = SYMMETRIC["ladder 2x4"]
    _, pts = positions(pairs, n)
    assert len({round(pts[v][1], 9) for v in (1, 2, 3, 4)}) == 1
    assert len({round(pts[v][1], 9) for v in (5, 6, 7, 8)}) == 1
    for top, bottom in ((1, 5), (2, 6), (3, 7), (4, 8)):
        assert pts[top][0] == pytest.approx(pts[bottom][0], abs=1e-9)


def test_a_dag_with_edges_that_skip_a_layer_is_balanced_about_its_axis():
    model, pts = positions([(1, 2), (1, 3), (2, 3), (2, 4), (3, 4)], 4, DIR)
    xs = [pts[v][0] for v in (1, 2, 3, 4)]
    assert xs[1] != xs[2], "the two middle vertices must sit on opposite sides of the axis"
    assert pts[1][0] == pytest.approx(pts[4][0], abs=1e-6)
    assert (xs[1] + xs[2]) / 2 == pytest.approx(xs[0], abs=1e-6)


# ── the frame ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def random_graph(rng):
    n = rng.randint(3, 14)
    allp = [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]
    pairs = rng.sample(allp, rng.randint(n - 1, min(len(allp), 2 * n)))
    directed = rng.random() < 0.4
    if directed:
        pairs = [(a, b) if rng.random() < 0.5 else (b, a) for a, b in pairs]
    return pairs, n, (DIR if directed else UND)


@pytest.mark.parametrize("seed", range(60))
def test_the_vertices_sit_in_the_middle_of_the_image(seed):
    pairs, n, text = random_graph(random.Random(seed))
    model, url, info, problems = draw_and_inspect(question(pairs, n, text))
    assert problems == []
    w, h = info["size"]
    xs = [info["node_px"][v][0] for v in model.nodes]
    ys = [info["node_px"][v][1] for v in model.nodes]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(w / 2, abs=2.5), "not centred left to right"
    band = D.CAPTION_BAND * info["unit_px"]
    above = min(ys)
    below = h - band - max(ys)
    assert above == pytest.approx(below, abs=2.5), "not centred top to bottom (the caption's strip aside)"


def test_the_caption_is_centred_under_the_drawing():
    model, url, info, _ = draw_and_inspect(question(cycle_pairs(5), 5))
    import numpy as np
    from test_diagrams import decode
    img = np.asarray(decode(url)).astype(int)
    bottom = img[int(info["size"][1] * 0.9):, :, :]
    lit = np.where(np.abs(bottom - np.array(D_rgb(D.BG))).max(axis=2) > 25)
    assert lit[1].size > 0
    assert (lit[1].min() + lit[1].max()) / 2 == pytest.approx(info["size"][0] / 2, abs=6)


def D_rgb(hexcolour):
    return tuple(int(hexcolour[i:i + 2], 16) for i in (1, 3, 5))
