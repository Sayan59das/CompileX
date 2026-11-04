"""Diagrams for graph and tree questions, drawn from the question's own data.

The old generator guessed the kind of picture from keywords in the text, read numbers out of the sample input without
knowing what they meant, and invented a placeholder graph whenever that failed. Every reviewed graph question was drawn as a
binary tree. This module works the other way round:

1. ``plan(question)`` builds a *model* of the structure the sample input describes: the vertices, the edges, whether they are
   directed, their weights, the roots of a tree, and the vertices the statement names (s, t, x, y). It reads the input the way
   the question's own ``input_schema`` says to, and it works out the direction and the meaning of an array from the wording of
   the input format. Anything it cannot establish for certain makes it return ``None``. It never fills a gap with a made-up
   graph.
2. ``render(model)`` draws exactly that model, with a layout that cannot put two vertices on top of each other, and reports
   where everything went so a test can check the picture against the data.

``diagram_for_question(question)`` is the one call the rest of the backend makes. No image-generation model is involved: a
diagram that a generator "paints" can show edges that are not in the question.
"""

from __future__ import annotations

import base64
import io
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

MAX_NODES = 40
EDGE_LEN = 2.7   # the length an edge is laid out at, in layout units
MIN_GAP = 2.2    # no two vertices closer than this
CLEAR = 0.95     # no vertex closer than this to an edge it is not part of (a vertex is at most 0.8 wide)
MAX_EDGES = 80

GRAPH_TOPICS = {"graph", "graphs"}
TREE_TOPICS = {"tree", "trees"}

# the palette of the site: black ground, arc cyan for structure, violet for roots, mint and amber for the named vertices
BG = "#0A0A0A"
NODE_FILL = "#10151C"
NODE_RING = "#3DE0FF"
EDGE = "#6B7787"
ROOT_RING = "#9B7BFF"
TEXT = "#F2F2F2"
MUTED = "#8C8C8C"
_MINT, _AMBER = "#35F2A0", "#FFC857"
MARK_COLOURS = {  # the first of a pair is mint, the second amber
    "src": _MINT, "source": _MINT, "start": _MINT,
    "dst": _AMBER, "dest": _AMBER, "target": _AMBER, "end": _AMBER,
}
# the two vertices a question names are tagged with the letters it uses (S and T, S and D, X and Y, U and V, A and B, P and Q, in either case)
MARK_COLOURS.update({c: _MINT for c in "sxupail"})
MARK_COLOURS.update({c: _AMBER for c in "tyvqbde"})
MARK_COLOURS.update({c.upper(): _MINT for c in "sxupail"})
MARK_COLOURS.update({c.upper(): _AMBER for c in "tyvqbde"})
LAND = "#35F2A0"
WATER = "#10202C"
WEIGHT_TEXT = "#FFC857"
CAPTION_BAND = 0.9  # the strip under a drawing that holds its caption, in layout units


class _Reject(Exception):
    """The sample cannot be turned into a picture that is certainly right."""


# ── the model ───────────────────────────────────────────────────────────────────────────────────────────────────────────

@dataclass
class Diagram:
    kind: str                                   # 'graph' | 'tree' | 'binary_tree' | 'grid'
    nodes: List[int]                            # vertex ids, as the question numbers them
    edges: List[Tuple[int, int, Optional[int]]]  # (from, to, weight); for undirected edges the order is as given
    directed: bool
    labels: Dict[int, str] = field(default_factory=dict)
    roots: List[int] = field(default_factory=list)
    marks: Dict[int, List[str]] = field(default_factory=dict)  # vertex -> tags such as 's', 't', 'x'
    weight_name: Optional[str] = None
    caption: str = ""
    layout: str = "spring"                      # 'spring' | 'tree' | 'binary'
    sides: Dict[int, str] = field(default_factory=dict)  # binary trees: child -> 'L' or 'R'
    grid: List[List[int]] = field(default_factory=list)  # kind 'grid': the cells
    notes: Dict[int, str] = field(default_factory=dict)  # vertex -> the value the question gives that vertex ('d=1'), drawn beside it

    def label(self, node: int) -> str:
        return self.labels.get(node, str(node))


# ── reading the input ───────────────────────────────────────────────────────────────────────────────────────────────────

_FIELD = re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<type>[A-Za-z_]+)(?P<dims>(?:\[\w+\])*)$")


def parse_schema(schema: str) -> List[List[Tuple[str, str, List[str]]]]:
    """'n:int m:int\\nroads:int[m][3]' -> [[('n','int',[]), ('m','int',[])], [('roads','int',['m','3'])]]."""
    lines = []
    for raw in schema.strip().splitlines():
        if not raw.strip():
            continue
        fields = []
        for token in raw.split():
            m = _FIELD.match(token)
            if not m:
                raise _Reject(f"schema token {token!r}")
            dims = re.findall(r"\[(\w+)\]", m.group("dims"))
            fields.append((m.group("name"), m.group("type"), dims))
        lines.append(fields)
    return lines


def _ints(line: str) -> List[int]:
    out = []
    for tok in line.split():
        if not re.fullmatch(r"-?\d+", tok):
            raise _Reject(f"not an integer: {tok!r}")
        out.append(int(tok))
    return out


def read_sample(schema: str, sample: str) -> dict:
    """Read the sample input as the schema describes it. Raises _Reject on any mismatch."""
    spec = parse_schema(schema)
    rows = [r.strip() for r in sample.strip().splitlines()]
    while rows and not rows[-1]:
        rows.pop()
    values: dict = {}
    at = 0

    def dim(token: str) -> int:
        if token.isdigit():
            return int(token)
        if token in values and isinstance(values[token], int):
            return values[token]
        raise _Reject(f"unknown dimension {token!r}")

    def next_row() -> str:
        nonlocal at
        if at >= len(rows):
            raise _Reject("the sample has fewer lines than the schema")
        row = rows[at]
        at += 1
        return row

    for fields in spec:
        if all(not f[2] for f in fields):
            nums = _ints(next_row())
            if len(nums) != len(fields):
                raise _Reject("scalar line has the wrong number of values")
            for (name, typ, _), v in zip(fields, nums):
                if typ != "int":
                    raise _Reject(f"type {typ}")
                values[name] = v
        elif len(fields) == 1:
            name, typ, dims = fields[0]
            if typ != "int":
                raise _Reject(f"type {typ}")
            if len(dims) == 1 and dims[0] == "0":
                # the typed schemas write "one line of integers, any length" as int[0]: the whole line is the list
                values[name] = _ints(next_row())
            elif len(dims) == 1:
                d = dim(dims[0])
                nums = _ints(next_row()) if d > 0 else []
                if len(nums) != d:
                    raise _Reject(f"{name} should hold {d} values")
                values[name] = nums
            elif len(dims) == 2:
                d1, d2 = dim(dims[0]), dim(dims[1])
                table = []
                for _ in range(d1):
                    nums = _ints(next_row())
                    if len(nums) != d2:
                        raise _Reject(f"a row of {name} should hold {d2} values")
                    table.append(nums)
                values[name] = table
            else:
                raise _Reject("arrays of more than two dimensions")
        else:
            raise _Reject("scalars and an array on one line")
    if at != len(rows):
        raise _Reject("the sample has more lines than the schema")
    return values


_NAME_OF = {"n": "n", "v": "n", "nodes": "n", "vertices": "n", "node": "n", "e": "m", "m": "m", "edges": "m", "src": "src", "source": "src", "s": "src",
            "dst": "dst", "dest": "dst", "destination": "dst", "target": "dst", "t": "dst"}


def _head_names(fmt: str, count: int) -> List[str]:
    """Names for the numbers of the first line, read from the first line of the format ('nodes edges src'), else n, m, s, t."""
    first = fmt.strip().splitlines()[0] if fmt.strip() else ""
    words = [w for w in re.findall(r"[A-Za-z_]+", first.lower()) if w in _NAME_OF]
    if len(words) >= count:
        names = [_NAME_OF[w] for w in words[:count]]
        if len(set(names)) == count and names[:2] == ["n", "m"]:
            return names
    return ["n", "m", "s", "t"][:count]


_PAIR_CUE = re.compile(r"\bparent\b[\s,/-]*(?:and\s+)?\bchild\b")
_SIDE_ROW = re.compile(r"^(\d+)\s+(\d+)\s+([LRlr])$")


def infer_schema(sample: str, input_format: str = "", statement: str = "") -> Optional[str]:
    """For a question without a schema: only the shapes that cannot be mistaken for anything else.

    'n m ...' then exactly m rows of 2 or 3 integers (and, when the format names them, a last row 'source destination')
                                                                          ->  an edge list
    'n' then one row of n integers                                        ->  an array
    one row of integers, in a format that says 'insertion order'          ->  the values a BST is built from
    rows of 0s and 1s, in a format that says 'grid'                       ->  a grid
    """
    fmt = input_format.lower()
    words = f"{fmt} {statement.lower()}"
    rows = [r.strip() for r in sample.strip().splitlines() if r.strip()]
    try:
        grid = [_ints(r) for r in rows]
    except _Reject:
        return None
    if not grid:
        return None
    head = grid[0]
    if len(head) >= 2 and len(grid) > 1 and head[1] > 0 and len(head) <= 4:
        names = _head_names(input_format, len(head))
        body = len(grid) - 1
        trailing = body == head[1] + 1 and len(grid[-1]) == 2 and re.search(r"\bsource\b|\bsrc\b", fmt) and re.search(r"destination|\bdst\b|\btarget\b", fmt)
        if body == head[1] or trailing:
            edge_rows = grid[1:-1] if trailing else grid[1:]
            widths = {len(r) for r in edge_rows}
            if len(widths) == 1 and widths.pop() in (2, 3):
                text = " ".join(f"{n}:int" for n in names) + f"\nedges:int[m][{len(edge_rows[0])}]"
                return text + ("\nsrc:int dst:int" if trailing else "")
    # 'n', then n-1 rows that the format itself calls "parent child pairs" (optionally a last row naming two nodes)  ->  a rooted tree
    if _PAIR_CUE.search(fmt) and len(head) == 1 and head[0] >= 2:
        body = grid[1:]
        k = head[0] - 1
        if len(body) == k and all(len(r) == 2 for r in body):
            return f"n:int\nedges:int[{k}][2]"
        if len(body) == k + 1 and all(len(r) == 2 for r in body):
            last = re.search(r"last line\W+([a-z])\s*(?:and|,)\s*([a-z])\b", fmt)
            if last and last.group(1) != last.group(2) and {last.group(1), last.group(2)} <= set("uvxystpq"):
                return f"n:int\nedges:int[{k}][2]\n{last.group(1)}:int {last.group(2)}:int"
        return None
    if len(head) == 1 and len(grid) == 2 and len(grid[1]) == head[0] and head[0] > 0:
        return "n:int\na:int[n]"
    if "insertion order" in fmt:
        if len(grid) == 1:
            return f"values:int[{len(head)}]"
        if len(grid) == 2 and len(grid[1]) == 2 and re.search(r"\bp\b.*\bq\b", fmt):
            return f"values:int[{len(head)}]\np:int q:int"
    if re.search(r"\bgrid\b|\bmatrix\b", words) and len(grid) >= 2 and len({len(r) for r in grid}) == 1 and len(head) >= 2 and all(v in (0, 1) for r in grid for v in r):
        return f"grid:int[{len(grid)}][{len(head)}]"
    return None


# ── what the words say ──────────────────────────────────────────────────────────────────────────────────────────────────

def _has(patterns, text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


_UNDIRECTED_STRONG = [r"\bundirected\b", r"\bnon-?directed\b", r"\bnot directed\b", r"\bindirected\b", r"\bunoriented\b", r"\btwo[- ]way\b", r"\bbidirectional\b",
                      r"\bin either direction\b", r"\bboth directions\b", r"\bboth ways\b"]
# "directed" inside "undirected", "non-directed" or "not directed" is the opposite word, so it is not matched there
_DIRECTED_STRONG = [r"\bone-way\b", r"\bone way (?:roads?|streets?|edges?|links?|routes?|paths?|messages?|connections?|flights?)\b",
                    r"(?<!un)(?<!non-)(?<!non)(?<!in)(?<!not )\bdirected\b", r"\barrows?\b"]
_UNDIRECTED_EDGE = [r"\bbetween\b", r"\bfriends?\b", r"\bfriendship", r"\bconnects?\b", r"\bconnected\b", r"\blinked?\b", r"\badjacent\b", r"\bneighbou?rs?\b", r"\bare (?:related|partners|twins)\b"]
_DIRECTED_EDGE = [
    r"\btells?\b", r"\bbefore\b", r"\bpoints? to\b", r"\bdepends? on\b", r"\bprerequisite", r"\brequires?\b",
    r"\bfrom\b[^.]{0,40}\bto\b", r"\b[a-z]\s*(?:->|→)\s*[a-z]\b", r"\bsends?\b", r"\bfollows?\b", r"\bleads? to\b", r"\bgoes? to\b",
    r"\bmust (?:be )?(?:finished|done|completed|taken|started|built)\b",
]


def classify_direction(text: str, edge_line: str) -> Optional[bool]:
    """True for directed, False for undirected, None when the words do not settle it."""
    text, edge_line = text.lower(), edge_line.lower()
    und, dire = _has(_UNDIRECTED_STRONG, text), _has(_DIRECTED_STRONG, text)
    if und != dire:
        return dire
    if und and dire:
        return None
    # the line that describes one edge row is the most exact description of an edge
    und, dire = _has(_UNDIRECTED_EDGE, edge_line), _has(_DIRECTED_EDGE, edge_line)
    if und != dire:
        return dire
    if und and dire:
        return None
    und, dire = _has(_UNDIRECTED_EDGE, text), _has(_DIRECTED_EDGE, text)
    if und != dire:
        return dire
    return None


_WEIGHT_WORDS = ["toll", "cost", "weight", "distance", "length", "time", "price", "fee", "capacity", "duration", "penalty", "risk"]


_EDGE_NOUNS = r"(?:edges?|roads?|streets?|links?|connections?|pipes?|bridges?|flights?|corridors?|tunnels?|paths?|routes?|wires?|cables?|arcs?)"


def weight_name(text: str) -> Optional[str]:
    # the sentences that talk about an edge name what it carries ("Each edge has an integer label", "the time needed to pass each road"):
    # those words win over a weight-like word that happens to appear somewhere else in the statement
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        if re.search(rf"\b{_EDGE_NOUNS}\b", sentence):
            for w in ["label"] + _WEIGHT_WORDS:
                if re.search(rf"\b{w}s?\b", sentence):
                    return w
    for w in _WEIGHT_WORDS:
        if re.search(rf"\b{w}s?\b", text):
            return w
    # an edge that "has a value": only when the statement says so about the edges themselves ("the value of an edge", "edge values")
    if re.search(r"\bvalues? of (?:an? |the |each |every )?edges?\b|\bedge values?\b|\bedges? (?:of the graph )?(?:has|have|with)\s+(?:an? |some )?values?\b|\bnodes and edges[^.]{0,40}\bvalues?\b", text):
        return "value"
    return None


_SCALAR_N = ("n", "v", "nodes", "vertices", "cities", "people", "num_nodes", "num_vertices", "node_count")
_MARKS = ("s", "t", "x", "y", "src", "source", "start", "dst", "dest", "target", "end")
_PARENT_NAMES = {"boss", "parent", "parents", "par", "inside", "father", "manager", "supervisor", "up", "prev", "owner"}


def _names_a_vertex(text: str, name: str) -> bool:
    """True when the text uses the variable as a vertex ('city s', 'from s', 'x and y'), not as some other number."""
    return bool(re.search(rf"\b(?:city|town|vertex|node|nodes|value|values|person|task|room|station|point|start|starts|source|target|destination|reach|reaches|from|to|between|of|and)\s+(?:the\s+)?['\"`]?{re.escape(name)}\b", text))


_TAG_ORDER = ("s", "src", "source", "start", "t", "dst", "dest", "target", "end", "p", "q", "x", "y", "U", "V")

# "each vertex has an integer d_i", "the nodes and edges of the graph have some values": the statement gives every vertex a value
_PER_VERTEX = re.compile(
    r"(?:each|every)\s+(?:vertex|node|city|person|town)\s+(?:has|is\s+(?:assigned|given|labell?ed)|gets|holds|contains|carries)\b"
    r"|(?:vertices|nodes)\s+(?:and\s+edges\s+)?(?:of\s+the\s+graph\s+)?have\s+(?:some\s+|an?\s+)?(?:values?|weights?|integers?|numbers?|colou?rs?|labels?)"
    r"|\bvalues?\s+(?:of|on|written\s+on)\s+(?:the\s+)?(?:vertices|nodes)\b"
    r"|(?:the\s+)?(?:i-th|\$i\$-th)\s+(?:vertex|node)\s+(?:has|is)\b")
_ORDINARY_COUNTS = {"n", "m"}

# the pairs of an input are queries, tests, forbidden or missing links, or a graph's complement: not its edge set
_NOT_THE_EDGES = re.compile(
    r"\bquer(?:y|ies)\b|\btest cases?\b|\bcomplement\b|\bnon-?edges?\b|"
    r"\bforbidden\b|\bprohibited\b|\bdislikes?\b|\benem(?:y|ies)\b|\bconflicts?\b|\bincompatible\b|\bblacklist")
# "not connected by an edge" is only worrying when the sentence is about the listed pairs ("the next m lines give pairs that are not connected");
# as the precondition of an operation ("two vertices that are not connected by an edge") it says nothing about the input
_NO_EDGE_PHRASE = re.compile(
    r"\bno edge between\b|\b(?:not|isn't|aren't|never) (?:directly (?:connected|joined|linked)|connected (?:directly|by (?:an? )?(?:edge|road|link|path))|joined by|adjacent)\b")
_ABOUT_THE_INPUT = re.compile(r"\bpairs?\b|\blines?\b|\bthe input\b|\beach of the next\b|\bthe following\b|\blisted\b|\bgiven pairs\b")


def _vertex_letters(raw: str) -> List[str]:
    """The single letters a statement uses as vertices ("from node S to node D", "Vertex S ... Vertex T"), in order of first mention.

    A letter followed by an underscore or digit ("Vertex U_i") is an edge endpoint in a formula, not a named vertex."""
    found: List[str] = []
    for m in re.finditer(r"\b(?:node|vertex|city|town|settlement|room|island|person|station|planet|village)\s+\$?([A-Za-z])\$?(?![A-Za-z0-9_])", raw, re.I):
        letter = m.group(1)
        if letter.lower() in _ORDINARY_COUNTS or letter in found:
            continue
        found.append(letter)
    return found


def _legend(marks: Dict[int, List[str]], value=lambda v: v) -> List[str]:
    """'s = 1', 't = 2': the named vertices, in the order the question names them."""
    pairs = [(t, value(v)) for v, tags in marks.items() for t in tags]
    pairs.sort(key=lambda tv: _TAG_ORDER.index(tv[0]) if tv[0] in _TAG_ORDER else len(_TAG_ORDER))
    return [f"{t} = {v}" for t, v in pairs]


def _edge_line(fmt: str) -> str:
    lines = [l for l in fmt.splitlines() if l.strip()]
    return " ".join(lines[1:]) if len(lines) > 1 else fmt


# ── planning: question -> model ─────────────────────────────────────────────────────────────────────────────────────────

class DiagramGenerator:
    """Builds and draws diagrams for graph and tree questions."""

    # ---- public API ----------------------------------------------------------------------------------------------------

    def should_generate_diagram(self, question_text: str, tags: list) -> bool:
        tags_lower = {str(t).lower().strip() for t in tags}
        if tags_lower & (GRAPH_TOPICS | TREE_TOPICS):
            return True
        return bool(re.search(r"\b(graph|vertices|binary tree|binary search tree|bst|adjacency list|adjacency matrix)\b", question_text.lower()))

    def diagram_for_question(self, question: dict) -> Optional[str]:
        """A data-URL PNG for this question, or None when it needs no diagram or one cannot be drawn with certainty."""
        try:
            model = self.plan(question)
            if model is None:
                return None
            return self.render(model)[0]
        except Exception as exc:  # a diagram is never worth failing the question for
            print(f"[Diagram] not drawn: {exc}")
            return None

    def generate_diagram(self, title: str, description: str, sample_input: Optional[str] = None) -> Optional[str]:
        """Older entry point: only the text of the question is known. Same rules, so it draws nothing it cannot verify."""
        return self.diagram_for_question({"title": title, "problem_statement": description, "sample_input": sample_input or ""})

    def plan(self, question: dict) -> Optional[Diagram]:
        try:
            return self._plan(question)
        except _Reject as why:
            print(f"[Diagram] no diagram: {why}")
            return None

    # ---- planning ------------------------------------------------------------------------------------------------------

    def _plan(self, q: dict) -> Optional[Diagram]:
        topic = str(q.get("topic") or "").lower().strip()
        title = str(q.get("title") or "")
        statement = str(q.get("problem_statement") or q.get("description") or q.get("statement") or "")
        fmt = str(q.get("input_format") or "")
        sample = str(q.get("sample_input") or "")
        raw = f"{title}\n{statement}\n{fmt}".replace("*", "")  # Markdown emphasis ("node **S**") must not hide a name from the readers below
        text = raw.lower()

        graphish = topic in GRAPH_TOPICS
        treeish = topic in TREE_TOPICS
        if not (graphish or treeish):
            # another topic draws a diagram only when its own text says it is about a graph or a tree
            if not re.search(r"\b(graph|vertices|binary tree|binary search tree|bst)\b", text):
                return None
            graphish = bool(re.search(r"\b(graph|vertices)\b", text))
            treeish = not graphish
        if not sample.strip():
            raise _Reject("no sample input")

        # 'parent child L/R' rows: a binary tree whose sides are given outright
        if _PAIR_CUE.search(fmt.lower()) and re.search(r"\bl\s*/\s*r\b|left\s*/\s*right", fmt.lower()) and not q.get("input_schema"):
            lines = [l.strip() for l in sample.strip().splitlines() if l.strip()]
            if lines and lines[0].isdigit() and len(lines) == int(lines[0]) and all(_SIDE_ROW.match(l) for l in lines[1:]):
                rows = [(int(m.group(1)), int(m.group(2)), m.group(3).upper()) for m in (_SIDE_ROW.match(l) for l in lines[1:])]
                return self._side_tree(int(lines[0]), rows, text)

        schema = q.get("input_schema") or infer_schema(sample, fmt, statement)
        if not schema:
            raise _Reject("the sample input has no schema and no recognisable shape")
        values = read_sample(schema, sample)
        dims_of = {name: dims for line in parse_schema(schema) for name, _, dims in line}

        arrays2 = {k: v for k, v in values.items() if len(dims_of.get(k, [])) == 2}
        arrays1 = {k: v for k, v in values.items() if len(dims_of.get(k, [])) == 1}
        scalars = {k: v for k, v in values.items() if isinstance(v, int)}

        grids = {k: v for k, v in arrays2.items() if all(x.isdigit() for x in dims_of[k])}
        if grids and len(grids) == 1 and re.search(r"\b(grid|matrix)\b", text):
            return self._grid(next(iter(grids.items())), text, fmt)
        if len(arrays2) == 1 and not arrays1 and re.search(r"\badjacency matrix\b", text):
            return self._adjacency(next(iter(arrays2.values())), scalars, text)
        pair_lists = [k for k, dims in dims_of.items() if k in arrays2 and len(dims) == 2 and dims[0].isdigit() and dims[1] == "2"]
        if pair_lists and len(arrays2) == 1 and (treeish or re.search(r"\b(?:binary tree|tree)\b", text)) and _PAIR_CUE.search(text):
            return self._pair_tree(arrays2[pair_lists[0]], scalars, text)
        if arrays2 and (graphish or treeish or re.search(r"\b(graph|vertices)\b", text)):
            return self._graph(arrays2, scalars, text, fmt, dims_of, arrays1, raw, statement.replace("*", "").lower())
        if len(arrays1) == 2 and not arrays2 and treeish:
            # "n target", then the tree as an array of n numbers: the first line says how long the array is
            (_, head), (name, body) = list(arrays1.items())
            if 1 < len(head) <= 3 and head[0] == len(body):
                return self._tree_array((name, body), scalars, text)
        if len(arrays1) == 1 and not arrays2 and (treeish or graphish):
            return self._tree_array(next(iter(arrays1.items())), scalars, text)
        raise _Reject("no edge list or tree array in the sample")

    def _adjacency(self, rows: List[List[int]], scalars: dict, text: str) -> Diagram:
        """A graph given as an n by n matrix, when the statement says which entry means 'no edge'."""
        n = scalars.get("n")
        if n is None or n < 1 or n > MAX_NODES or len(rows) != n or any(len(r) != n for r in rows):
            raise _Reject("the adjacency matrix is not n by n")
        none = re.search(r"(-?\d+)\s+(?:in the matrix\s+)?(?:means|denotes|indicates|represents)\s+(?:that\s+)?(?:there is\s+)?no\s+(?:direct\s+)?(?:edge|path|road|connection)", text)
        if not none:
            raise _Reject("the statement does not say which matrix entry means 'no edge'")
        absent = int(none.group(1))
        directed = classify_direction(text, "")
        if directed is None:
            raise _Reject("the wording does not say whether the edges are directed")
        # which number each row stands for is the statement's to say ("(0-indexed)", "numbered 1 to n"); a picture must not choose it
        zero = re.search(r"0-indexed|zero[- ]indexed|0-based|numbered (?:from )?0\b|\b0 to n\s*-\s*1\b", text)
        one = re.search(r"1-indexed|one[- ]indexed|1-based|numbered (?:from )?1\b|\b1 to n\b", text)
        if bool(zero) == bool(one):
            raise _Reject("the statement does not say how the vertices of the matrix are numbered")
        base = 0 if zero else 1
        weighted = bool(re.search(r"\bweighted\b|\bweights?\b|\bcosts?\b|\bdistances?\b", text))
        edges: List[Tuple[int, int, Optional[int]]] = []
        for i in range(n):
            for j in range(n):
                v = rows[i][j]
                if v == absent or (i == j and v == 0):
                    continue
                if not directed and j < i:
                    if rows[j][i] != v:
                        raise _Reject("an undirected graph with an asymmetric matrix")
                    continue
                if not weighted and v != 1:
                    raise _Reject("an unweighted matrix entry other than 1")
                edges.append((i + base, j + base, v if weighted else None))
        if len(edges) > MAX_EDGES:
            raise _Reject("too many edges to draw")
        bits = [f"n = {n}", f"adjacency matrix, vertex = row number (from {base})", "directed" if directed else "undirected"]
        if weighted:
            bits.append("edge labels: weight")
        return Diagram(kind="graph", nodes=list(range(base, base + n)), edges=edges, directed=directed, weight_name="weight" if weighted else None,
                       caption="Sample input: " + " · ".join(bits), layout="spring")

    def _graph(self, arrays2: dict, scalars: dict, text: str, fmt: str, dims_of: dict, arrays1: Optional[dict] = None, raw: str = "", statement: str = "") -> Diagram:
        if len(arrays2) != 1:
            raise _Reject("more than one edge list")
        # wording that says the listed pairs are something other than the graph's own edges. A statement like that is not drawn as that
        # graph whatever else it says, so a wording nobody has met yet cannot slip a wrong picture through on these
        not_edges = _NOT_THE_EDGES.search(statement)
        if not not_edges:
            for sentence in re.split(r"(?<=[.!?])\s+|\n", statement):
                if _NO_EDGE_PHRASE.search(sentence) and _ABOUT_THE_INPUT.search(sentence):
                    not_edges = _NO_EDGE_PHRASE.search(sentence)
                    break
        if not_edges:
            raise _Reject(f"the statement mentions {not_edges.group(0)!r}: the listed pairs may not be the graph's edges")
        name, rows = next(iter(arrays2.items()))
        dims = dims_of.get(name, [])
        # an edge list is `m` rows of a fixed 2 or 3 numbers. A grid, or a list of intervals, has another shape or another count
        if len(dims) != 2 or dims[1] not in ("2", "3") or dims[0] not in ("m", "e", "edges"):
            raise _Reject(f"{name} is not an edge list")
        width = int(dims[1])
        n = next((scalars[k] for k in _SCALAR_N if k in scalars), None)
        if n is None:
            raise _Reject("the number of vertices is not given")
        if "m" in scalars and scalars["m"] != len(rows):
            raise _Reject("m does not match the number of edge rows")
        if n < 1 or n > MAX_NODES or len(rows) > MAX_EDGES:
            raise _Reject(f"too large to draw ({n} vertices, {len(rows)} edges)")
        if re.search(r"\bcomplete graph\b|\bclique\b", text) and len(rows) != n * (n - 1) // 2:
            # the question's graph has every pair connected, so a list of fewer pairs is a property of some edges, not the edge set
            raise _Reject("a complete graph whose input lists only some of its edges")

        labels = [r[0] for r in rows] + [r[1] for r in rows]
        vertex_names = r"[uvabxy](?:_\{?\w+\}?)?(?:\s*,\s*[uvabxy](?:_\{?\w+\}?)?)*"   # "u, v" or "u_{i}, v_{i}": the endpoints, not any variable
        says_zero = bool(re.search(r"numbered (?:from )?0\b|\b0 to n\s*-\s*1\b|\bzero[- ]indexed\b|0-indexed|0-based"
                                   rf"|\b0\s*(?:≤|<=|\\le(?:q)?)\s*{vertex_names}\s*(?:<|\\lt)\s*n\b", text))
        says_one = bool(re.search(r"numbered (?:from )?1\b|\b1\s*(?:to|\.\.)\s*n\b|\bone[- ]indexed\b|1-indexed|1-based"
                                  rf"|\b1\s*(?:≤|<=|\\le(?:q)?)\s*{vertex_names}\s*(?:≤|<=|\\le(?:q)?)\s*n\b", text))
        if not (says_zero or says_one or 0 in labels or n in labels):
            # an isolated vertex 0 (vertices 0..n-1) and an isolated vertex n (vertices 1..n) fit the edges equally well, and drawing one
            # would show a vertex that does not exist and hide one that does
            raise _Reject("the vertex numbering is not stated and the edges do not settle it")
        zero_based = says_zero or (0 in labels)
        base = 0 if zero_based else 1
        nodes = list(range(base, base + n))
        if any(not (base <= v < base + n) for v in labels):
            raise _Reject("an edge names a vertex outside 1..n")

        directed = classify_direction(text, _edge_line(fmt))
        if directed is None:
            raise _Reject("the wording does not say whether the edges are directed")

        wname = None
        if width == 3:
            wname = weight_name(_edge_line(fmt).lower()) or weight_name(text)
            if wname is None:
                raise _Reject("the third number of an edge is not described")
        edges = [(r[0], r[1], r[2] if width == 3 else None) for r in rows]

        marks: Dict[int, List[str]] = {}
        used: set = set()
        for key in _MARKS:
            if key in scalars and base <= scalars[key] < base + n and key not in _SCALAR_N and key != "m" and _names_a_vertex(text, key):
                marks.setdefault(scalars[key], [])
                used.add(key)
                if key not in marks[scalars[key]]:
                    marks[scalars[key]].append(key)

        # the statement names vertex variables ("from node S to node D", "Vertex S ... Vertex T") that the input has to supply: a number the format
        # calls by the same letter is that vertex, and the numbers left unexplained ("the integers n, m, k, q") are the remaining named vertices, in
        # order, when there are exactly as many of them. A variable can also be written `src`.
        named = _vertex_letters(raw)
        if named:
            pending = [letter for letter in named if letter.lower() not in {t.lower() for ts in marks.values() for t in ts}]
            spare = [k for k in scalars if k not in _SCALAR_N and k != "m" and k not in used]
            for letter in list(pending):
                if letter.lower() in spare and base <= scalars[letter.lower()] < base + n:
                    marks.setdefault(scalars[letter.lower()], []).append(letter)
                    pending.remove(letter)
                    spare.remove(letter.lower())
            if pending and len(pending) == len(spare) and all(base <= scalars[k] < base + n for k in spare):
                for letter, key in zip(pending, spare):
                    marks.setdefault(scalars[key], []).append(letter)
            case_of = {letter.lower(): letter for letter in named}  # write every tag the way the statement writes it
            marks = {v: [case_of.get(t.lower(), t) if len(t) == 1 else t for t in ts] for v, ts in marks.items()}
        elif not marks:
            spare = [k for k in scalars if k not in _SCALAR_N and k != "m"]
            quoted = sorted(set(re.findall(r"`(src|source|start|dst|dest|target)`", text)))
            if quoted and len(quoted) == len(spare) and all(base <= scalars[k] < base + n for k in spare):
                for tag, key in zip(quoted, spare):
                    marks.setdefault(scalars[key], []).append(tag)
        if not marks:
            # two vertices the statement names by number, or as the last vertex ("find the shortest path from node 1 to node N")
            pair = re.search(r"\bfrom\s+(?:node|vertex|city)\s+(\d+)\s+to\s+(?:node|vertex|city)\s+(\d+|n)\b", text)
            if pair:
                first = int(pair.group(1))
                last = base + n - 1 if pair.group(2) == "n" else int(pair.group(2))
                if base <= first < base + n and base <= last < base + n and first != last:
                    marks[first] = ["src"]
                    marks[last] = ["dst"]
        if not marks:
            # a vertex the statement names by its number ("shortest distance from source node 0", "from node 1 to all other nodes",
            # "perform BFS from node 3")
            literal = re.search(r"\bsource\s+(?:node|vertex|city|town)?\s*(\d+)\b|\bfrom\s+(?:node|vertex|city)\s+(\d+)\s+to\s+(?:all|every|each)\b"
                                r"|\b(?:bfs|dfs)\s+(?:traversal\s+)?(?:starting\s+)?from\s+(?:node|vertex|city)\s+(\d+)\b", text)
            if literal:
                v = int(next(g for g in literal.groups() if g is not None))
                if base <= v < base + n:
                    marks[v] = ["src"]

        # a list the input gives besides the edges: one value for every vertex when the statement says each vertex has one,
        # otherwise the picture would silently leave part of the input out, so there is none
        notes: Dict[int, str] = {}
        symbol = None
        for key, values in (arrays1 or {}).items():
            cue = _PER_VERTEX.search(text)
            if len(values) == n and not notes and cue:
                # the variable the statement gives each vertex ("an integer d_{i}"), read from the words right after the cue, as an indexed name
                found = re.search(r"(?:integers?|values?|numbers?|weights?|colou?rs?)\s+\$?([A-Za-z])_\{?[a-z]\}?", raw[cue.end():cue.end() + 60])
                symbol = found.group(1) if found else None
                notes = {node: (f"{symbol}={value}" if symbol else str(value)) for node, value in zip(nodes, values)}
            else:
                raise _Reject(f"the list {key} is not tied to the vertices by the statement")

        bits = [f"n = {n}", f"m = {len(rows)}", "directed" if directed else "undirected"]
        if wname:
            bits.append(f"edge labels: {wname}")
        if notes:
            bits.append(f"beside each vertex: {symbol + '_i' if symbol else 'its value'}")
        legend = _legend(marks)
        caption = "Sample input: " + " · ".join(bits) + (("   |   " + ", ".join(legend)) if legend else "")
        return Diagram(kind="graph", nodes=nodes, edges=edges, directed=directed, marks=marks, weight_name=wname, caption=caption, layout="spring", notes=notes)

    def _side_tree(self, n: int, rows: List[Tuple[int, int, str]], text: str) -> Diagram:
        """A binary tree given as n-1 rows 'parent child L|R'."""
        if n < 2 or n > MAX_NODES or len(rows) != n - 1:
            raise _Reject("the parent-child-side rows do not match n")
        labels = [v for r in rows for v in r[:2]]
        base = 0 if (0 in labels or re.search(r"numbered (?:from )?0\b|\bzero[- ]indexed\b|0-indexed|0-based", text)) else 1
        nodes = list(range(base, base + n))
        if any(not (base <= v < base + n) for v in labels):
            raise _Reject("a row names a node outside 1..n")
        parent_of: Dict[int, int] = {}
        taken = set()
        for p, c, side in rows:
            if p == c or c in parent_of or (p, side) in taken:
                raise _Reject("a node has two parents, or a parent has two children on one side")
            parent_of[c] = p
            taken.add((p, side))
        roots = [v for v in nodes if v not in parent_of]
        if len(roots) != 1:
            raise _Reject("a tree has exactly one root")
        for v in nodes:
            seen, cur = set(), v
            while cur in parent_of:
                if cur in seen:
                    raise _Reject("the rows form a cycle")
                seen.add(cur)
                cur = parent_of[cur]
            if cur != roots[0]:
                raise _Reject("a node is not connected to the root")
        edges = [(p, c, None) for p, c, _ in rows]
        sides = {c: side for _, c, side in rows}
        caption = f"Sample input: n = {n} · root {roots[0]} · L = left child, R = right child"
        return Diagram(kind="binary_tree", nodes=nodes, edges=edges, directed=False, roots=roots, caption=caption, layout="binary", sides=sides)

    def _pair_tree(self, rows: List[List[int]], scalars: dict, text: str) -> Diagram:
        """A rooted tree given as n-1 'parent child' rows. Drawn with each parent's children left to right in the order given."""
        n = scalars.get("n")
        if n is None or n < 2 or n > MAX_NODES or len(rows) != n - 1:
            raise _Reject("the parent-child rows do not match n")
        labels = [v for r in rows for v in r]
        base = 0 if (0 in labels or re.search(r"numbered (?:from )?0\b|\bzero[- ]indexed\b|0-indexed|0-based", text)) else 1
        nodes = list(range(base, base + n))
        if any(not (base <= v < base + n) for v in labels):
            raise _Reject("a row names a node outside 1..n")
        parent_of: Dict[int, int] = {}
        for p, c in rows:
            if p == c or c in parent_of:
                raise _Reject("a node has two parents")
            parent_of[c] = p
        roots = [v for v in nodes if v not in parent_of]
        if len(roots) != 1:
            raise _Reject("a tree has exactly one root")
        for v in nodes:
            seen, cur = set(), v
            while cur in parent_of:
                if cur in seen:
                    raise _Reject("the rows form a cycle")
                seen.add(cur)
                cur = parent_of[cur]
            if cur != roots[0]:
                raise _Reject("a node is not connected to the root")
        if re.search(r"\bbinary tree\b", text):
            kids: Dict[int, int] = {}
            for p, _ in rows:
                kids[p] = kids.get(p, 0) + 1
            if any(k > 2 for k in kids.values()):
                raise _Reject("a node of a 'binary tree' has more than two children")
        # a last row such as 'U V' names two nodes of the tree; the schema gave them the letters the format uses
        marks: Dict[int, List[str]] = {}
        for name, value in scalars.items():
            if name != "n" and len(name) == 1:
                if not (base <= value < base + n):
                    raise _Reject(f"{name} is not a node of the tree")
                marks.setdefault(value, []).append(name.upper())
        legend = _legend(marks)
        caption = f"Sample input: n = {n} · root {roots[0]}" + ((" · " + ", ".join(legend)) if legend else "")
        return Diagram(kind="tree", nodes=nodes, edges=[(p, c, None) for p, c in rows], directed=False, roots=roots, marks=marks, caption=caption, layout="tree")

    def _tree_array(self, item, scalars: dict, text: str) -> Diagram:
        name, arr = item
        n = len(arr)
        if n < 1 or n > MAX_NODES:
            raise _Reject(f"too large to draw ({n} nodes)")

        array_cue = bool(re.search(r"stored in an array|root at position 0|root is at (?:index|position) 0|2\s*i\s*\+\s*1|\bheap\b", text))
        bst = bool(re.search(r"\binsert(?:ed|ing)?\b[^.]*\b(?:binary search tree|bst)\b|\b(?:binary search tree|bst)\b[^.]*\bbuilt (?:by|from)\b", text)) and not array_cue
        # "return its level-order traversal" is an output; only a level-order *input* makes the array a tree
        implicit = not bst and (array_cue or bool(re.search(
            r"level[- ]order (?:array|representation|list|input|format|serialization|sequence)|(?:given|represented|stored|provided|encoded) (?:in|as|by) (?:a )?level[- ]order", text)))
        marker = re.search(r"(-?\d+|null|none)\b[^.\n]{0,30}\b(?:means|marks|stands for|denotes|represents|indicates)\b[^.\n]{0,30}\b(?:no node|missing|absent|empty|null)", text)
        parent_cue = name.lower() in _PARENT_NAMES or bool(re.search(r"\bor 0 for\b|\b0 for the (?:head|root|oldest|top)|\b0 (?:if|means|denotes) (?:it|the node)? ?(?:has no|is the) (?:parent|root)|who has no (?:boss|parent)|\bparent\[", text))

        if bst:
            return self._bst(arr, scalars)
        if implicit:
            null = None
            if marker:
                tok = marker.group(1)
                null = int(tok) if re.fullmatch(r"-?\d+", tok) else None
            if null is None and -1 in arr and not array_cue:
                # in a level-order list -1 is very often "no node here"; drawing it as a vertex would add nodes the tree does not have,
                # and the statement does not say. (A heap stored by position 2i+1 / 2i+2 is a complete tree: -1 is just a value there.)
                raise _Reject("the array holds -1 and the statement does not say whether that is a value or a missing node")
            levelorder = bool(re.search(r"level[- ]order", text)) and null is not None and not re.search(r"2\s*i\s*\+\s*1|position", text)
            return self._implicit_binary(arr, null, levelorder)
        if parent_cue:
            neg = bool(re.search(r"-1 for\b|\bor -1\b|\bis -1\b", text)) and -1 in arr
            return self._parent_tree(arr, scalars, root_marker=-1 if neg else 0)
        raise _Reject(f"cannot tell what the array {name!r} means")

    def _parent_tree(self, parents: List[int], scalars: dict, root_marker: int) -> Diagram:
        n = len(parents)
        base = 1 if root_marker == 0 else 0
        nodes = list(range(base, base + n))
        edges, roots = [], []
        for i, p in zip(nodes, parents):
            if p == root_marker:
                roots.append(i)
            elif base <= p < base + n and p != i:
                edges.append((p, i, None))
            else:
                raise _Reject(f"node {i} has an impossible parent {p}")
        if not roots:
            raise _Reject("no root")
        # a forest: following parents from any node must end at a root
        up = {i: p for i, p in zip(nodes, parents)}
        for i in nodes:
            seen, cur = set(), i
            while up[cur] != root_marker:
                if cur in seen:
                    raise _Reject("the parents form a cycle")
                seen.add(cur)
                cur = up[cur]
        marks: Dict[int, List[str]] = {}
        for key in ("x", "y"):
            if key in scalars and base <= scalars[key] < base + n:
                marks.setdefault(scalars[key], []).append(key)
        legend = _legend(marks)
        caption = f"Sample input: n = {n} · " + ("root " + str(roots[0]) if len(roots) == 1 else "roots " + ", ".join(map(str, roots))) + ((" · " + ", ".join(legend)) if legend else "")
        return Diagram(kind="tree", nodes=nodes, edges=edges, directed=False, roots=roots, marks=marks, caption=caption, layout="tree")

    def _implicit_binary(self, arr: List[int], null: Optional[int], levelorder: bool) -> Diagram:
        """A binary tree stored in an array: children of position i at 2i+1 and 2i+2, or LeetCode-style level order."""
        n = len(arr)
        present = [v != null for v in arr]
        edges: List[Tuple[int, int, Optional[int]]] = []
        sides: Dict[int, str] = {}
        if levelorder:
            if not present[0]:
                raise _Reject("the root is missing")
            queue, nxt = [0], 1
            for parent in queue:
                for slot in range(2):
                    if nxt >= n:
                        break
                    if present[nxt]:
                        edges.append((parent, nxt, None))
                        sides[nxt] = "LR"[slot]
                        queue.append(nxt)
                    nxt += 1
            used = {0} | {v for _, v, _ in edges}
            if any(present[i] and i not in used for i in range(n)):
                raise _Reject("level-order array has nodes that belong to no parent")
        else:
            for i in range(n):
                if not present[i]:
                    continue
                if i > 0 and not present[(i - 1) // 2]:
                    raise _Reject("a node hangs under a missing parent")
                for c in (2 * i + 1, 2 * i + 2):
                    if c < n and present[c]:
                        edges.append((i, c, None))
                        sides[c] = "L" if c == 2 * i + 1 else "R"
        nodes = [i for i in range(n) if present[i]]
        if not nodes or not present[0]:
            raise _Reject("the root is missing")
        labels = {i: str(arr[i]) for i in nodes}
        caption = f"Sample input: {len(nodes)} nodes · position 0 is the root · children of i at 2i+1 and 2i+2" if not levelorder else f"Sample input: {len(nodes)} nodes · level order"
        return Diagram(kind="binary_tree", nodes=nodes, edges=edges, directed=False, labels=labels, roots=[0], caption=caption, layout="binary", sides=sides)

    def _bst(self, values: List[int], scalars: Optional[dict] = None) -> Diagram:
        if len(set(values)) != len(values):
            raise _Reject("duplicate values: the wording does not say which side they go")
        left: Dict[int, int] = {}
        right: Dict[int, int] = {}
        for i in range(1, len(values)):
            cur = 0
            while True:
                side = left if values[i] < values[cur] else right
                if cur in side:
                    cur = side[cur]
                else:
                    side[cur] = i
                    break
        edges = [(a, b, None) for a, b in list(left.items()) + list(right.items())]
        sides = {**{b: "L" for b in left.values()}, **{b: "R" for b in right.values()}}
        marks: Dict[int, List[str]] = {}
        for key in ("p", "q"):  # a query given as values: the vertex that holds that value
            if scalars and key in scalars and scalars[key] in values:
                marks.setdefault(values.index(scalars[key]), []).append(key)
        legend = _legend(marks, lambda v: values[v])
        caption = f"Sample input: binary search tree built by inserting {len(values)} values in order" + ((" · " + ", ".join(legend)) if legend else "")
        return Diagram(kind="binary_tree", nodes=list(range(len(values))), edges=edges, directed=False, labels={i: str(v) for i, v in enumerate(values)}, roots=[0],
                       marks=marks, caption=caption, layout="binary", sides=sides)

    def _grid(self, item, text: str, fmt: str) -> Diagram:
        name, rows = item
        if not rows or len(rows) > 24 or len(rows[0]) > 24:
            raise _Reject("grid too large to draw")
        if any(v not in (0, 1) for r in rows for v in r):
            raise _Reject("the grid holds values other than 0 and 1")
        legend = re.search(r"\(\s*0\s*=\s*(\w+)\s*,\s*1\s*=\s*(\w+)\s*\)", fmt.lower()) or re.search(r"0s?\s*\((\w+)\)\s*and\s*1s?\s*\((\w+)\)", text)
        words = f" · 0 = {legend.group(1)}, 1 = {legend.group(2)}" if legend else ""
        return Diagram(kind="grid", nodes=[], edges=[], directed=False, grid=[list(r) for r in rows], layout="grid",
                       caption=f"Sample input: {len(rows)} × {len(rows[0])} grid{words}")

    # ── layouts ─────────────────────────────────────────────────────────────────────────────────────────────────────────

    def _layout(self, d: Diagram) -> Dict[int, Tuple[float, float]]:
        if d.layout == "binary":
            return self._binary_layout(d)
        if d.layout == "tree":
            return self._forest_layout(d)
        return self._graph_layout(d)

    @staticmethod
    def _children(d: Diagram) -> Dict[int, List[int]]:
        kids: Dict[int, List[int]] = {n: [] for n in d.nodes}
        for a, b, _ in d.edges:
            kids[a].append(b)
        return kids

    def _binary_layout(self, d: Diagram) -> Dict[int, Tuple[float, float]]:
        """A left child is always left of its parent and a right child right of it. Two layouts, the narrower wins:
        one column per node (in-order), or the slots of a complete tree (a heap fills those slots)."""
        left = {a: b for a, b, _ in d.edges if d.sides.get(b) == "L"}
        right = {a: b for a, b, _ in d.edges if d.sides.get(b) == "R"}
        level: Dict[int, int] = {}
        slot: Dict[int, int] = {}
        rank: Dict[int, int] = {}
        counter = [0]

        def walk(node: int, depth: int, sl: int) -> None:
            level[node], slot[node] = depth, sl
            if node in left:
                walk(left[node], depth + 1, 2 * sl)
            rank[node] = counter[0]
            counter[0] += 1
            if node in right:
                walk(right[node], depth + 1, 2 * sl + 1)

        walk(d.roots[0], 0, 0)
        levels = max(level.values()) + 1
        gap, drop = 1.5, 1.9
        if 2 ** (levels - 1) - 1 <= len(rank) - 1:
            slots = 2 ** (levels - 1)
            return {n: ((slot[n] + 0.5) * (slots / 2 ** level[n]) * gap, -level[n] * drop) for n in level}
        return {n: (rank[n] * gap, -level[n] * drop) for n in level}

    def _forest_layout(self, d: Diagram) -> Dict[int, Tuple[float, float]]:
        kids = self._children(d)
        pos: Dict[int, Tuple[float, float]] = {}
        cursor = [0.0]

        def walk(node: int, depth: int) -> float:
            cs = kids[node]  # in the order the question lists them: a parent array lists them by label, 'parent child' rows as given
            if not cs:
                x = cursor[0]
                cursor[0] += 1.5
            else:
                xs = [walk(c, depth + 1) for c in cs]
                x = (xs[0] + xs[-1]) / 2
            pos[node] = (x, -depth * 1.9)
            return x

        for r in sorted(d.roots):
            walk(r, 0)
            cursor[0] += 0.8
        if min(y for _, y in pos.values()) < -8 * 1.9:  # a long chain: keep it from becoming a tower
            pos = {n: (x, y * (1.55 / 1.9)) for n, (x, y) in pos.items()}
        return pos

    # graphs: components are laid out one by one and packed, so isolated vertices never push the rest apart

    def _graph_layout(self, d: Diagram) -> Dict[int, Tuple[float, float]]:
        simple = nx.DiGraph() if d.directed else nx.Graph()
        simple.add_nodes_from(d.nodes)
        simple.add_edges_from((a, b) for a, b, _ in d.edges if a != b)
        weak = simple.to_undirected() if d.directed else simple
        comps = [sorted(c) for c in nx.connected_components(weak)]
        comps.sort(key=lambda c: (-len(c), c[0]))
        boxes = []
        singles = []
        for comp in comps:
            if len(comp) == 1:
                singles.append(comp[0])
                continue
            sub = simple.subgraph(comp)
            raw = self._layout_component(sub, d.directed)
            xs, ys = [p[0] for p in raw.values()], [p[1] for p in raw.values()]
            x0, y0 = min(xs), min(ys)
            local = {n: (p[0] - x0, p[1] - y0) for n, p in raw.items()}
            boxes.append((local, max(xs) - x0, max(ys) - y0))
        return self._pack(boxes, singles)

    def _layout_component(self, g, directed: bool) -> Dict[int, Tuple[float, float]]:
        nodes = sorted(g.nodes)
        k = len(nodes)
        if k == 2:
            return {nodes[0]: (0.0, 0.0), nodes[1]: (2.2, 0.0)}
        if directed and nx.is_directed_acyclic_graph(g):
            return self._finish(self._clear(self._layered(g), list(g.edges)), g, orient=False)
        if k == 3:
            # a path or a triangle: place it by hand so the corner is where the edges meet
            deg = sorted(g.to_undirected().degree, key=lambda t: -t[1])
            centre = deg[0][0]
            others = [n for n in nodes if n != centre]
            if g.to_undirected().number_of_edges() == 3:
                return {others[0]: (0.0, 0.0), others[1]: (2.2, 0.0), centre: (1.1, 1.9)}
            return {others[0]: (0.0, 0.0), centre: (2.2, 0.0), others[1]: (4.4, 0.0)}
        regular = self._regular(g, directed)
        if regular is not None:
            return regular
        ug = g.to_undirected()
        hops = dict(nx.all_pairs_shortest_path_length(ug))
        D = np.array([[hops[a][b] for b in nodes] for a in nodes], dtype=float) * EDGE_LEN
        starts = [nx.spring_layout(ug, seed=seed, iterations=200) for seed in range(8)] + [nx.circular_layout(ug)]
        edges = list(ug.edges)
        scored = []
        for start in starts:
            X = np.array([start[n] for n in nodes], dtype=float)
            X = X * (EDGE_LEN * math.sqrt(k) / (np.abs(X).max() or 1.0))
            X = self._stress(D, X)
            pts = self._relax({n: (float(X[i][0]), float(X[i][1])) for i, n in enumerate(nodes)}, MIN_GAP)
            scored.append((self._score(pts, edges), pts))
        scored.sort(key=lambda t: t[0])
        best, best_key = None, None
        for _, pts in scored[:6]:  # the clearance pass only for the most promising layouts
            pts = self._clear(pts, edges)
            key = (self._violations(pts, edges), self._score(pts, edges))
            if best_key is None or key < best_key:
                best, best_key = pts, key
            if key[0] == 0 and best_key[0] == 0 and len(scored) > 3 and best is not None and key == best_key:
                continue
        if best is None:
            raise _Reject("no usable layout")
        return self._finish(best, g, orient=True)

    # ── symmetry: regular shapes, a canonical orientation, exact mirror images ───────────────────────────────────────────

    def _regular(self, g, directed: bool) -> Optional[Dict[int, Tuple[float, float]]]:
        """A cycle, a complete graph, a star, a wheel, a short path or a complete bipartite graph is drawn as the regular figure it is."""
        ug = nx.Graph(g.to_undirected())
        k, m = ug.number_of_nodes(), ug.number_of_edges()
        if k < 4 or not nx.is_connected(ug):
            return None
        nodes = sorted(ug.nodes)
        deg = dict(ug.degree)
        edges = list(ug.edges)
        L = EDGE_LEN

        def ring(order, R, centre=(0.0, 0.0)):
            n = len(order)
            start = math.pi / 2 + (math.pi / n if n % 2 == 0 else 0.0)  # a vertex at the top, or a flat top for an even count
            return {v: (centre[0] + R * math.cos(start - 2 * math.pi * i / n), centre[1] + R * math.sin(start - 2 * math.pi * i / n)) for i, v in enumerate(order)}

        def accepted(make, R0):
            for f in (1.0, 1.2, 1.45, 1.8, 2.2):
                pts = make(R0 * f)
                if self._violations(pts, edges) == 0:
                    return pts
            return None

        def around(start):
            """The vertices of a cycle in order, following the direction of the edges when they have one."""
            nbrs = sorted(ug[start])
            ahead = [n for n in nbrs if g.has_edge(start, n)] if directed else []
            nxt = ahead[0] if len(ahead) == 1 else nbrs[0]
            order, prev, cur = [start], start, nxt
            while cur != start:
                order.append(cur)
                step = [n for n in ug[cur] if n != prev]
                prev, cur = cur, step[0]
                if len(order) > k:
                    return None
            return order

        if m == k * (k - 1) // 2 and k <= 12:  # complete: a regular polygon
            return accepted(lambda R: ring(nodes, R), L / (2 * math.sin(math.pi / k)))
        hubs = [v for v in nodes if deg[v] == k - 1]
        if len(hubs) == 1 and k >= 5 and m == 2 * (k - 1) and k <= 14:  # wheel: the rim as a polygon, the hub in the middle
            rim = ug.subgraph([v for v in nodes if v != hubs[0]])
            if all(d == 2 for _, d in rim.degree) and nx.is_connected(rim):
                order = self._cycle_order(rim)
                if order:
                    return accepted(lambda R: {**ring(order, R), hubs[0]: (0.0, 0.0)}, L / (2 * math.sin(math.pi / (k - 1))))
        if m == k and k <= 16 and all(d == 2 for d in deg.values()):  # cycle: a regular polygon
            order = around(nodes[0])
            if order and len(order) == k:
                return accepted(lambda R: ring(order, R), L / (2 * math.sin(math.pi / k)))
        if len(hubs) == 1 and m == k - 1 and k <= 13:  # star: leaves evenly round the hub
            leaves = [v for v in nodes if v != hubs[0]]
            return accepted(lambda R: {**ring(leaves, R), hubs[0]: (0.0, 0.0)}, max(L, L / (2 * math.sin(math.pi / len(leaves)))))
        if k <= 7 and m == k - 1 and sorted(deg.values()) == [1, 1] + [2] * (k - 2):  # a short path: a straight line
            ends = [v for v in nodes if deg[v] == 1]
            first = next((e for e in ends if directed and g.has_edge(e, next(iter(ug[e])))), ends[0])
            order, prev, cur = [first], None, first
            while len(order) < k:
                cur_next = [n for n in ug[cur] if n != prev][0]
                order.append(cur_next)
                prev, cur = cur, cur_next
            pts = {v: (i * L - (k - 1) * L / 2, 0.0) for i, v in enumerate(order)}
            return pts if self._violations(pts, edges) == 0 else None
        if k <= 12:  # complete bipartite: two rows
            try:
                top, bottom = nx.bipartite.sets(ug)
            except nx.NetworkXError:
                return None
            if len(top) >= 2 and len(bottom) >= 2 and m == len(top) * len(bottom):
                a, b = sorted(top), sorted(bottom)
                if (len(a), a[0]) > (len(b), b[0]):
                    a, b = b, a
                for gap in (3.0, 3.6, 4.4):
                    pts = {v: (i * L - (len(a) - 1) * L / 2, gap / 2) for i, v in enumerate(a)}
                    pts.update({v: (i * L - (len(b) - 1) * L / 2, -gap / 2) for i, v in enumerate(b)})
                    if self._violations(pts, edges) == 0:
                        return pts
        return None

    @staticmethod
    def _cycle_order(rim) -> Optional[List[int]]:
        start = min(rim.nodes)
        order, prev, cur = [start], None, start
        while True:
            step = [n for n in sorted(rim[cur]) if n != prev]
            nxt = step[0]
            if nxt == start:
                break
            order.append(nxt)
            prev, cur = cur, nxt
            if len(order) > rim.number_of_nodes():
                return None
        return order if len(order) == rim.number_of_nodes() else None

    def _finish(self, pts, g, orient: bool):
        """Centre the layout, lay its long axis along x, and make it an exact mirror image of itself wherever the graph is one."""
        edges = list(g.edges)
        base = self._violations(pts, edges)
        cur = dict(pts)
        if orient:
            cur = self._orient(cur, g)
        for step in range(3):  # mirror, then line up rows and columns, then mirror what the lining-up disturbed
            if step == 1:
                aligned = self._align(cur)
                if self._violations(aligned, edges) <= base:
                    cur = aligned
                continue
            for axis in (0, 1):
                mirrored = self._mirror(cur, g, axis)
                if mirrored is not None and self._violations(mirrored, edges) <= base:
                    cur = mirrored
        return cur

    @staticmethod
    def _align(pts, tol: float = 0.3):
        """Vertices whose x (or y) differ by less than tol sit in one column (or row): give them exactly the same coordinate."""
        out = {n: list(p) for n, p in pts.items()}
        for axis in (0, 1):
            order = sorted(pts, key=lambda n: pts[n][axis])
            groups, group = [], [order[0]]
            for n in order[1:]:
                if pts[n][axis] - pts[group[0]][axis] <= 2 * tol and pts[n][axis] - pts[group[-1]][axis] <= tol:
                    group.append(n)
                else:
                    groups.append(group)
                    group = [n]
            groups.append(group)
            for group in groups:
                mean = sum(pts[n][axis] for n in group) / len(group)
                for n in group:
                    out[n][axis] = mean
        return {n: (p[0], p[1]) for n, p in out.items()}

    @staticmethod
    def _orient(pts, g):
        names = sorted(pts)
        P = np.array([pts[n] for n in names], dtype=float)
        P -= P.mean(axis=0)
        if len(names) >= 3:
            w, v = np.linalg.eigh(P.T @ P)
            if w[1] > 1.15 * w[0]:  # a long axis exists: lay it along x (a round layout has none)
                ang = -math.atan2(v[1][1], v[0][1])
                c, s = math.cos(ang), math.sin(ang)
                P = P @ np.array([[c, -s], [s, c]]).T
        index = {n: i for i, n in enumerate(names)}
        if g.is_directed():
            flip_x = sum(P[index[b]][0] - P[index[a]][0] for a, b in g.edges) < -1e-9
        else:
            flip_x = P[0][0] > 1e-9  # the smallest label on the left
        if flip_x:
            P[:, 0] *= -1
        if P[0][1] < -1e-9:  # ...and in the upper half
            P[:, 1] *= -1
        return {n: (float(P[i][0]), float(P[i][1])) for n, i in index.items()}

    @staticmethod
    def _mirror(pts, g, axis: int, tol: float = 0.55):
        """Make the layout an exact mirror image across the vertical (axis 0) or horizontal (axis 1) line through its centre, but only
        when the layout is already nearly one and the mirror is a real symmetry of the graph (it maps every edge onto an edge)."""
        names = sorted(pts)
        c = sum(pts[n][axis] for n in names) / len(names)

        def reflect(p):
            return (2 * c - p[0], p[1]) if axis == 0 else (p[0], 2 * c - p[1])

        deg = dict(g.to_undirected().degree)
        sigma, used = {}, set()
        for a in names:
            if a in used:
                continue
            ra = reflect(pts[a])
            cand = sorted((math.dist(ra, pts[b]), b) for b in names if b not in used and deg[b] == deg[a])
            if not cand or cand[0][0] >= tol:
                return None
            b = cand[0][1]
            sigma[a] = b
            sigma[b] = a
            used.update((a, b))
        if any(not g.has_edge(sigma[u], sigma[v]) for u, v in g.edges):
            return None
        out = {}
        for a in names:
            b = sigma[a]
            if a == b:
                p = list(pts[a])
                p[axis] = c
                out[a] = (p[0], p[1])
            elif a < b:
                rb = reflect(pts[b])
                mid = ((pts[a][0] + rb[0]) / 2, (pts[a][1] + rb[1]) / 2)
                out[a] = mid
                out[b] = reflect(mid)
        return out

    @staticmethod
    def _violations(pts, edges) -> int:
        """Vertices closer to each other, or to an edge they are not part of, than the drawing allows."""
        bad = 0
        names = sorted(pts)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if math.dist(pts[a], pts[b]) < MIN_GAP - 1e-6:
                    bad += 1
        for a, b in edges:
            if a == b:
                continue
            for v in names:
                if v not in (a, b) and DiagramGenerator._seg(pts[v], pts[a], pts[b]) < CLEAR - 1e-6:
                    bad += 1
        return bad

    @staticmethod
    def _seg(p, a, b) -> float:
        ax, ay = a
        bx, by = b
        L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1e-9
        t = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L2))
        return math.hypot(p[0] - (ax + t * (bx - ax)), p[1] - (ay + t * (by - ay)))

    @staticmethod
    def _clear(pts, edges, rounds: int = 150):
        """Push every vertex off the edges it is not part of, then keep vertices apart; repeat until nothing moves."""
        names = sorted(pts)
        P = {n: [pts[n][0], pts[n][1]] for n in names}
        for _ in range(rounds):
            moved = False
            for a, b in edges:
                if a == b:
                    continue
                ax, ay = P[a]
                bx, by = P[b]
                L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1e-9
                for v in names:
                    if v == a or v == b:
                        continue
                    px, py = P[v]
                    t = max(0.0, min(1.0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2))
                    cx, cy = ax + t * (bx - ax), ay + t * (by - ay)
                    d = math.hypot(px - cx, py - cy)
                    if d >= CLEAR:
                        continue
                    if d < 1e-9:
                        norm = math.sqrt(L2)
                        ux, uy = -(by - ay) / norm, (bx - ax) / norm
                    else:
                        ux, uy = (px - cx) / d, (py - cy) / d
                    P[v][0] += ux * (CLEAR - d + 1e-3)
                    P[v][1] += uy * (CLEAR - d + 1e-3)
                    moved = True
            relaxed = DiagramGenerator._relax({n: (P[n][0], P[n][1]) for n in names}, MIN_GAP, rounds=6)
            for n in names:
                P[n] = list(relaxed[n])
            if not moved:
                break
        return {n: (P[n][0], P[n][1]) for n in names}

    @staticmethod
    def _stress(D, X, iters: int = 120):
        """Stress majorisation (SMACOF): positions whose distances match the graph distances, so edges come out about the same length."""
        n = len(D)
        W = np.zeros_like(D)
        off = D > 0
        W[off] = 1.0 / D[off] ** 2
        V = -W.copy()
        V[np.diag_indices(n)] = W.sum(axis=1)
        Vp = np.linalg.pinv(V)
        for _ in range(iters):
            diff = X[:, None, :] - X[None, :, :]
            dist = np.sqrt((diff ** 2).sum(axis=2))
            dist[dist < 1e-9] = 1e-9
            B = -W * D / dist
            B[np.diag_indices(n)] = 0.0
            B[np.diag_indices(n)] = -B.sum(axis=1)
            X = Vp @ B @ X
        return X

    @staticmethod
    def _relax(pts, min_d: float, rounds: int = 400):
        """Push apart any two vertices closer than min_d, so no two ever overlap."""
        names = sorted(pts)
        P = {n: [pts[n][0], pts[n][1]] for n in names}
        for r in range(rounds):
            moved = False
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    dx, dy = P[b][0] - P[a][0], P[b][1] - P[a][1]
                    d = math.hypot(dx, dy)
                    if d >= min_d - 1e-9:
                        continue
                    if d < 1e-9:
                        dx, dy, d = math.cos(a * 2.399 + b), math.sin(a * 2.399 + b), 1.0
                    push = (min_d - d) / 2 + 1e-3
                    ux, uy = dx / d, dy / d
                    P[a][0] -= ux * push
                    P[a][1] -= uy * push
                    P[b][0] += ux * push
                    P[b][1] += uy * push
                    moved = True
            if not moved:
                break
        return {n: (P[n][0], P[n][1]) for n in names}

    @staticmethod
    def _score(pts, edges) -> float:
        def side(p, q, r):
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

        crossings = 0
        for i, (a, b) in enumerate(edges):
            for c, e in edges[i + 1:]:
                if len({a, b, c, e}) < 4:
                    continue
                if side(pts[a], pts[b], pts[c]) * side(pts[a], pts[b], pts[e]) < 0 and side(pts[c], pts[e], pts[a]) * side(pts[c], pts[e], pts[b]) < 0:
                    crossings += 1
        close = 0
        for a, b in edges:
            ax, ay = pts[a]
            bx, by = pts[b]
            L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1e-9
            for n, (px, py) in pts.items():
                if n in (a, b):
                    continue
                t = max(0.0, min(1.0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2))
                if math.hypot(px - (ax + t * (bx - ax)), py - (ay + t * (by - ay))) < 0.85:
                    close += 1
        xs, ys = [p[0] for p in pts.values()], [p[1] for p in pts.values()]
        extent = max(max(xs) - min(xs), max(ys) - min(ys))
        lens = [math.dist(pts[a], pts[b]) for a, b in edges] or [1.0]
        return crossings * 1000 + close * 400 + extent * 2 + (max(lens) / min(lens)) * 3

    @staticmethod
    def _layered(g) -> Dict[int, Tuple[float, float]]:
        layer: Dict[int, int] = {}
        for n in nx.topological_sort(g):
            layer[n] = max((layer[p] + 1 for p in g.predecessors(n)), default=0)
        # an edge that skips layers reserves a slot (a virtual vertex, id < 0) in every layer it passes, so the vertices on those
        # layers are placed to its side, evenly, and not pushed aside afterwards
        pred: Dict[int, List[int]] = {n: [] for n in g.nodes}
        succ: Dict[int, List[int]] = {n: [] for n in g.nodes}
        virtual = 0
        for u, v in sorted(g.edges):
            prev = u
            for l in range(layer[u] + 1, layer[v]):
                virtual -= 1
                layer[virtual] = l
                pred[virtual], succ[virtual] = [prev], []
                succ[prev].append(virtual)
                prev = virtual
            succ[prev].append(v)
            pred[v].append(prev)
        rows: Dict[int, List[int]] = {}
        for n, l in layer.items():
            rows.setdefault(l, []).append(n)
        for l in rows:
            rows[l].sort()
        for _ in range(4):  # barycentre sweeps cut the crossings
            for l in sorted(rows)[1:]:
                idx = {n: i for i, n in enumerate(rows[l - 1])}
                rows[l].sort(key=lambda n: (sum(idx[p] for p in pred[n] if p in idx) / max(1, sum(1 for p in pred[n] if p in idx)), n))
            for l in sorted(rows, reverse=True)[1:]:
                idx = {n: i for i, n in enumerate(rows[l + 1])}
                rows[l].sort(key=lambda n: (sum(idx[s] for s in succ[n] if s in idx) / max(1, sum(1 for s in succ[n] if s in idx)), n))
        width = max(len(r) for r in rows.values())
        pos = {}
        for l, row in rows.items():
            off = (width - len(row)) * 1.1
            for i, n in enumerate(row):
                if n >= 0 or n in g.nodes:
                    pos[n] = (off + i * 2.2, -l * 2.0)
        return pos

    @staticmethod
    def _pack(boxes, singles) -> Dict[int, Tuple[float, float]]:
        gap = 2.4
        cells = [(0.0, 0.0, None, n) for n in singles]
        total = sum((w + gap) * (h + gap) for _, w, h in boxes) + sum(gap ** 2 for _ in singles)
        target = max([w for _, w, _ in boxes] + [math.sqrt(total) * 1.6, 2.0])
        items = [(w, h, loc, None) for loc, w, h in boxes] + cells
        pos: Dict[int, Tuple[float, float]] = {}
        x = y = row_h = 0.0
        for w, h, loc, single in items:
            if x > 0 and x + w > target:
                x, y, row_h = 0.0, y + row_h + gap, 0.0
            if loc is not None:
                for n, (px, py) in loc.items():
                    pos[n] = (x + px, -(y + py))
            else:
                pos[single] = (x, -y)
            x += w + gap
            row_h = max(row_h, h)
        return pos

    # ── drawing ─────────────────────────────────────────────────────────────────────────────────────────────────────────

    def _render_grid(self, d: Diagram) -> Tuple[str, dict]:
        rows, cols = len(d.grid), len(d.grid[0])
        cell = 62.0
        pad_x, pad_top, pad_bottom = 36.0, 30.0, 58.0
        W, H = int(max(cols * cell + 2 * pad_x, len(d.caption) * 6.9 + 50)), int(rows * cell + pad_top + pad_bottom)
        dpi = 100
        fig = Figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor=BG)
        canvas = FigureCanvasAgg(fig)
        width_px, height_px = canvas.get_width_height()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, width_px)
        ax.set_ylim(height_px, 0)  # image coordinates: y grows downward
        ax.axis("off")
        left = (width_px - cols * cell) / 2
        cells = []
        for r_i, row in enumerate(d.grid):
            for c_i, v in enumerate(row):
                x, y = left + c_i * cell, pad_top + r_i * cell
                ax.add_patch(Rectangle((x + 2, y + 2), cell - 4, cell - 4, facecolor=LAND if v else WATER, edgecolor=NODE_RING if v else "#1C3445", linewidth=1.6, zorder=2))
                ax.text(x + cell / 2, y + cell / 2, str(v), color="#04130C" if v else "#5B7385", fontsize=15, fontweight="bold", ha="center", va="center", zorder=3)
                cells.append({"row": r_i, "col": c_i, "value": v, "centre_px": (x + cell / 2, y + cell / 2)})
        ax.text(width_px / 2, height_px - 22, d.caption, color=MUTED, fontsize=9, ha="center", va="center")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor=BG)
        data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        return data_url, {"size": (width_px, height_px), "cells": cells, "cell_px": cell}

    def render(self, d: Diagram) -> Tuple[str, dict]:
        """(data-URL PNG, info). info says where every vertex and edge was drawn, in image pixels, so it can be checked."""
        if d.kind == "grid":
            return self._render_grid(d)
        longest = max(len(d.label(n)) for n in d.nodes)
        r = min(0.8, max(0.36, 0.17 + 0.085 * longest))
        weighted = any(w is not None for _, _, w in d.edges)
        raw = self._layout(d)
        if d.layout == "spring":
            scale = max(1.0, (2 * r + 0.7 + (0.5 if weighted else 0.0)) / 2.2)
        else:
            scale = max(1.0, (2 * r + 0.55) / 1.5)
        pos = {n: (p[0] * scale, p[1] * scale) for n, p in raw.items()}
        if set(pos) != set(d.nodes):
            raise _Reject("the layout lost a vertex")

        def quad(p0, c, p1, k=18):
            return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in (i / k for i in range(k + 1))]

        def cubic(p0, c0, c1, p1, k=18):
            out = []
            for i in range(k + 1):
                t = i / k
                u = 1 - t
                out.append((u ** 3 * p0[0] + 3 * u * u * t * c0[0] + 3 * u * t * t * c1[0] + t ** 3 * p1[0], u ** 3 * p0[1] + 3 * u * u * t * c0[1] + 3 * u * t * t * c1[1] + t ** 3 * p1[1]))
            return out

        def bowed(a: int, b: int, offset: float):
            """An arc between a and b that bulges `offset` units from the straight line (so a long edge never swings far out)."""
            p0, p1 = pos[a], pos[b]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            length = math.hypot(dx, dy) or 1.0
            rad = 2 * offset / length
            ctrl = ((p0[0] + p1[0]) / 2 + rad * dy, (p0[1] + p1[1]) / 2 - rad * dx)
            mid = ((p0[0] + p1[0]) / 2 + 0.5 * rad * dy, (p0[1] + p1[1]) / 2 - 0.5 * rad * dx)
            return rad, mid, quad(p0, ctrl, p1)

        def route(a: int, b: int, w: Optional[int], base: float):
            """The smallest bend, from the planned one, that keeps the edge and its label clear of every other vertex."""
            others = [pos[n] for n in pos if n not in (a, b)]
            if not others:
                return bowed(a, b, base)
            need, need_label = r + 0.1, r + 0.34
            best, best_margin = None, -math.inf
            for shift in (0.0, 0.2, -0.2, 0.4, -0.4, 0.7, -0.7, 1.0, -1.0):
                rad, mid, path = bowed(a, b, base + shift)
                clear = min(min(DiagramGenerator._seg(o, q0, q1) for q0, q1 in zip(path, path[1:])) for o in others) - need
                label = (min(math.dist(o, mid) for o in others) - need_label) if w is not None else math.inf
                margin = min(clear, label)
                if margin >= 0:
                    return rad, mid, path
                if margin > best_margin:
                    best, best_margin = (rad, mid, path), margin
            return best

        # step 2: the geometry of every edge
        groups: Dict[Tuple[int, int], List[int]] = {}
        for i, (a, b, _) in enumerate(d.edges):
            groups.setdefault((min(a, b), max(a, b)), []).append(i)
        geometry = {}
        for (lo, hi), idxs in groups.items():
            for j, i in enumerate(idxs):
                a, b, w = d.edges[i]
                if a == b:
                    cx, cy = pos[a][0], pos[a][1] + r * 1.55
                    top = cy + r * 0.62
                    geometry[i] = {"kind": "loop", "rad": 0.0, "centre": (cx, cy), "mid": (cx, top + (0.34 if w is not None else 0.0)),
                                   "path": [(cx + r * 0.62 * math.cos(2 * math.pi * k / 24), cy + r * 0.62 * math.sin(2 * math.pi * k / 24)) for k in range(25)]}
                elif d.layout == "tree":
                    # org-chart elbows: down from the parent to a bus halfway to the children, across, and down into the child
                    # at its own x. A boss with forty reports never has a line running through the vertex beside the one
                    # it is joined to, because every drop into a child happens at that child's own x.
                    (x0, y0), (x1, y1) = pos[a], pos[b]
                    ymid = (y0 + y1) / 2
                    verts = [(x0, y0), (x0, ymid), (x1, ymid), (x1, y1)]
                    geometry[i] = {"kind": "tree", "rad": 0.0, "verts": verts, "mid": ((x0 + x1) / 2, ymid), "path": verts}
                elif d.layout == "binary":
                    p0, p1 = pos[a], pos[b]
                    geometry[i] = {"kind": "line", "rad": 0.0, "mid": ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), "path": [p0, p1]}
                else:
                    count = len(idxs)
                    base = (j - (count - 1) / 2) * 0.7 * (-1 if a > b else 1) if count > 1 else 0.0
                    rad, mid, path = route(a, b, w, base)
                    geometry[i] = {"kind": "arc", "rad": rad, "mid": mid, "path": path}

        # step 3: the image covers every vertex, curve and label
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        xmin, xmax = min(xs) - r - 0.9, max(xs) + r + 0.9
        ymin, ymax = min(ys) - r - 1.8, max(ys) + r + 1.4  # room under for the caption, above for tags
        for g, (_, _, w) in zip((geometry[i] for i in range(len(d.edges))), d.edges):
            for x, y in g["path"]:
                xmin, xmax, ymin, ymax = min(xmin, x - 0.4), max(xmax, x + 0.4), min(ymin, y - 1.4), max(ymax, y + 0.5)
            if w is not None:
                mx, my = g["mid"]
                xmin, xmax, ymin, ymax = min(xmin, mx - 0.6), max(xmax, mx + 0.6), min(ymin, my - 1.4), max(ymax, my + 0.6)
        for node, note in d.notes.items():  # a value written beside its vertex needs room to its right and below
            x, y = pos[node]
            xmax, ymin = max(xmax, x + r * 0.95 + 0.27 * len(note) + 0.3), min(ymin, y - r * 0.85 - 0.9)
        # symmetric frame: the vertices sit in the middle, with the same room left and right, and above and below (the caption's line is extra)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half_x = max(cx - xmin, xmax - cx)
        xmin, xmax = cx - half_x, cx + half_x
        half_y = max(ymax - cy, cy - ymin - CAPTION_BAND)
        ymax, ymin = cy + half_y, cy - half_y - CAPTION_BAND
        unit = 66.0

        def size():
            return (xmax - xmin) * unit, (ymax - ymin) * unit

        W, H = size()
        if W > 1100 or H > 950:  # comfortable limit first, then a hard one
            unit = max(40.0, unit * min(1100 / W, 950 / H))
            W, H = size()
        if W > 1500 or H > 1500:
            unit = max(22.0, unit * min(1500 / W, 1500 / H))
            W, H = size()
        need = (len(d.caption) * 6.9 + 50) / unit  # the caption is one line of small text and must fit
        if xmax - xmin < need:
            mid_x = (xmin + xmax) / 2
            xmin, xmax = mid_x - need / 2, mid_x + need / 2
            W, H = size()

        # step 4: drawing
        dpi = 100
        fig = Figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor=BG)
        canvas = FigureCanvasAgg(fig)
        width_px, height_px = canvas.get_width_height()  # what the canvas really is (it truncates to whole pixels)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_aspect("auto")  # the axes fill the image exactly, so data -> pixel is exact; the scales differ by under 0.2%
        ax.axis("off")
        ax.set_facecolor(BG)

        pt_per_unit = unit * 72.0 / dpi
        r_pt = r * pt_per_unit
        diameter_px = 2 * r * unit
        font = max(6.0, min(0.55 * diameter_px, 0.78 * diameter_px / (0.62 * longest)) * 72.0 / dpi)
        w_font = max(6.5, font * 0.72)

        drawn_edges = []
        for i, (a, b, w) in enumerate(d.edges):
            g = geometry[i]
            if g["kind"] == "loop":
                ax.add_patch(Circle(g["centre"], r * 0.62, fill=False, edgecolor=EDGE, linewidth=2.0, zorder=1))
            elif g["kind"] == "tree":
                ax.add_patch(PathPatch(Path(g["verts"], [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO]), facecolor="none", edgecolor=EDGE, linewidth=2.0, joinstyle="round", zorder=1))
            else:
                ax.add_patch(FancyArrowPatch(
                    pos[a], pos[b], arrowstyle="-|>" if d.directed else "-", mutation_scale=max(12.0, r_pt * 0.62),
                    connectionstyle=f"arc3,rad={g['rad']}", color=EDGE, linewidth=2.0, shrinkA=r_pt + 1, shrinkB=r_pt + 2, zorder=1,
                ))
            drawn_edges.append({"i": i, "from": a, "to": b, "mid": g["mid"], "rad": g["rad"], "loop": g["kind"] == "loop", "arrow": d.directed, "path": g["path"]})
            if w is not None:
                # under the vertices (zorder 2 < 3): a label can never cover one
                ax.text(g["mid"][0], g["mid"][1], str(w), color=WEIGHT_TEXT, fontsize=w_font, ha="center", va="center", fontweight="bold", zorder=2,
                        bbox={"boxstyle": "round,pad=0.18", "facecolor": BG, "edgecolor": "none"})

        for n in d.nodes:
            x, y = pos[n]
            tags = d.marks.get(n, [])
            ring = MARK_COLOURS[tags[0]] if tags else (ROOT_RING if n in d.roots else NODE_RING)
            ax.add_patch(Circle((x, y), r, facecolor=NODE_FILL, edgecolor=ring, linewidth=2.6, zorder=3))
            ax.text(x, y, d.label(n), color=TEXT, fontsize=font, fontweight="bold", ha="center", va="center", zorder=5)
            if tags:
                ax.text(x + r * 0.95, y + r * 0.85, "/".join(tags), color=MARK_COLOURS[tags[0]], fontsize=max(7.0, font * 0.7), fontweight="bold", ha="left", va="bottom", zorder=5)
            if n in d.notes:
                ax.text(x + r * 0.95, y - r * 0.85, d.notes[n], color=MUTED, fontsize=max(7.0, font * 0.62), ha="left", va="top", zorder=5)

        ax.text((xmin + xmax) / 2, ymin + 0.3, d.caption, color=MUTED, fontsize=max(8.0, min(11.0, W / 90)), ha="center", va="bottom")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, facecolor=BG)
        data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        def px(p):
            return ((p[0] - xmin) / (xmax - xmin) * width_px, (ymax - p[1]) / (ymax - ymin) * height_px)

        info = {
            "size": (width_px, height_px),
            "radius_units": r,
            "radius_px": r * width_px / (xmax - xmin),
            "unit_px": unit,
            "positions": {n: pos[n] for n in d.nodes},
            "node_px": {n: px(pos[n]) for n in d.nodes},
            "edges": [dict(e, mid_px=px(e["mid"])) for e in drawn_edges],
            "labels": {n: d.label(n) for n in d.nodes},
        }
        return data_url, info


diagram_generator = DiagramGenerator()
