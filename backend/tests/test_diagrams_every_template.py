"""Every template the question service can generate: nothing it draws goes unchecked.

The other template files name the templates they know. A template added tomorrow is in none of them, so nothing would check its
picture. This file names no template to test. It reads the service's own registries (the topic registry of dynamic_generator and the
difficulty registry of difficulty_templates), asks the diagram generator about EVERY template under every topic it is filed under, over
many seeds, with the schema the service itself derives for the question, and then holds that:

1. a template that gets a picture has a solver below, and the solver, run on the DRAWN structure, reproduces the template's own sample
   output on every seed (a template drawn without a solver fails here: add the solver, do not silence the test),
2. a template whose text talks about graphs or trees but gets no picture is listed in NO_PICTURE with the reason (so somebody has
   looked at it), and every list entry still describes a template that exists and behaves that way,
3. a template that is drawn is never refused for one of its wordings once the service can type it (that is a statement that does not
   say what the picture needs to know, such as whether the edges are directed),
4. what the service really serves, through generate_dynamic with its difficulty text and title variants, for each template alone at
   each difficulty, draws exactly the same templates and agrees with the same solvers.

The guard checks itself: the last tests hand it deliberately broken templates and require it to complain.

Run from the backend folder:  python -m pytest tests/test_diagrams_every_template.py -q
"""

import collections
import contextlib
import copy
import io
import itertools
import os
import random
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "question-service"))

import pytest

from app.services.diagram_generator import diagram_generator as dg
from test_diagrams import draw_and_inspect
from test_diagrams_hard_templates import bellman_ford, floyd_warshall, path_sum, strongly_connected_components
from test_diagrams_older_templates import answer_from_drawing, bst_walk, hops

try:
    from model import difficulty_templates as T
    from model import dynamic_generator as G
    from model import legacy_typing
    from model.legacy_typing import type_question
    from model.stdio import to_stdin, to_stdout
except Exception:  # the question service is not in this checkout, or its imports are missing
    if os.environ.get("CI"):
        raise  # in CI a guard that cannot run must fail, not skip
    G = None

pytestmark = pytest.mark.skipif(G is None, reason="the question service's templates are not importable here")

SEEDS = 30
SERVED_SEEDS = 6
PIXEL_SEEDS = 2
DIFFICULTIES = ("easy", "medium", "hard")
GRAPH_WORDS = re.compile(r"\b(graph|tree|node|nodes|vertex|vertices|edge|edges|bfs|dfs|root|parent|child|children|ancestor|adjacen|path|cycle|island|grid|network|route|city|cities)\b", re.I)


# ── solvers on the drawn structure: (drawn model, sample input, sample output) -> a complaint, or None when they agree ─────────

def agree(got, want):
    got, want = str(got).strip(), str(want).strip()
    return None if got == want else f"the drawing gives {got!r}, the question's own sample output is {want!r}"


def older(name):
    return lambda m, sample_in, sample_out: agree(answer_from_drawing(name, m, None), sample_out)


def topological_sort(m, sample_in, sample_out):
    """Kahn's algorithm as the template runs it (zero in-degree nodes in index order, neighbours in input order) on the DRAWN graph. Any
    valid order would pass a missing edge, since fewer constraints keep an order valid; reproducing the exact order does not."""
    if not m.directed:
        return "the graph was drawn undirected"
    indegree, neighbours = {v: 0 for v in m.nodes}, {v: [] for v in m.nodes}
    for a, b, _ in m.edges:
        neighbours[a].append(b)
        indegree[b] += 1
    queue, order = collections.deque(v for v in sorted(m.nodes) if indegree[v] == 0), []
    while queue:
        v = queue.popleft()
        order.append(v)
        for w in neighbours[v]:
            indegree[w] -= 1
            if indegree[w] == 0:
                queue.append(w)
    return agree(" ".join(map(str, order if len(order) == len(m.nodes) else [])), sample_out)


def bellman_ford_distances(m, sample_in, sample_out):
    if bellman_ford(m, passes=len(m.nodes)) != bellman_ford(m):
        return "the drawn graph has a negative cycle, which the statement rules out"
    return agree(" ".join(map(str, bellman_ford(m))), sample_out)


def components(m, sample_in, sample_out):
    return agree(strongly_connected_components(m), sample_out) if m.directed else "the graph was drawn undirected"


def all_pairs(m, sample_in, sample_out):
    return agree(floyd_warshall(m), sample_out)


def root_to_leaf_sum(m, sample_in, sample_out):
    target = int(sample_in.split("\n")[0].split()[1])
    return agree(str(path_sum(m, target)).lower(), sample_out.lower())


def preorder(m, sample_in, sample_out):
    left, right = bst_walk(m)
    out = []

    def walk(v):
        out.append(int(m.label(v)))
        if v in left:
            walk(left[v])
        if v in right:
            walk(right[v])

    walk(m.roots[0])
    return agree(" ".join(map(str, out)), sample_out)


def hop_counts(m, sample_in, sample_out):
    src = [v for v, tags in m.marks.items() if "src" in tags]
    if len(src) != 1:
        return "the source node is not marked in the picture"
    return agree(" ".join(str(hops(m, src[0], v)) for v in sorted(m.nodes)), sample_out)


ANSWERS = {
    "_graph_bfs_shortest_path": older("_graph_bfs_shortest_path"),
    "_graph_number_of_islands": older("_graph_number_of_islands"),
    "_graph_detect_cycle": older("_graph_detect_cycle"),
    "_graph_dijkstra": older("_graph_dijkstra"),
    "_graph_topological_sort": topological_sort,
    "_tree_inorder": older("_tree_inorder"),
    "_tree_max_depth": older("_tree_max_depth"),
    "_tree_level_order": older("_tree_level_order"),
    "_tree_diameter": older("_tree_diameter"),
    "_tree_lowest_common_ancestor": older("_tree_lowest_common_ancestor"),
    "_hard_graph_bellman_ford": bellman_ford_distances,
    "_hard_graph_strongly_connected": components,
    "_hard_graph_floyd_warshall": all_pairs,
    "_hard_tree_path_sum": root_to_leaf_sum,
    "_hard_tree_serialize_deserialize": preorder,  # the template is titled "BST Preorder Traversal"
    "_queue_bfs_level_order": hop_counts,
}


# ── the drawn structure against the question's own input, read again here from the sample text alone ──────────────────────────
# An answer is a weak witness: a true/false, a count or a distance rarely changes when one edge, one vertex, one value or one side is
# wrong. So every template's picture is ALSO compared with the structure its sample input describes.

def header_and_rows(sample_in):
    """(n, the m rows after the first line) for the inputs that are 'n m [src]' and then m rows."""
    lines = sample_in.strip().split("\n")
    n, m = (int(x) for x in lines[0].split()[:2])
    return n, [tuple(int(x) for x in line.split()) for line in lines[1:1 + m]]


def differences(drawn, wanted, what):
    if drawn == wanted:
        return None
    return f"the {what} drawn differ from the input's: missing {sorted((wanted - drawn).elements())[:3]}, extra {sorted((drawn - wanted).elements())[:3]}"


def graph_edges(directed):
    def check(m, sample_in):
        n, rows = header_and_rows(sample_in)
        if m.directed != directed:
            return f"drawn {'directed' if m.directed else 'undirected'}, but its edges are {'directed' if directed else 'undirected'}"
        if sorted(m.nodes) != list(range(n)):
            return f"the vertices drawn are {sorted(m.nodes)}, the input has {n} numbered from 0"
        key = (lambda r: r) if directed else (lambda r: (min(r[0], r[1]), max(r[0], r[1])) + tuple(r[2:]))
        drawn = collections.Counter(key((a, b) + (() if w is None else (w,))) for a, b, w in m.edges)
        return differences(drawn, collections.Counter(key(r) for r in rows), "edges")
    return check


def search_tree(values_line):
    """The BST that inserting the values of that line in order builds: every (parent value, child value, side), and the root."""
    def check(m, sample_in):
        values = [int(x) for x in sample_in.strip().split("\n")[values_line].split()]
        child_of, wanted = {}, collections.Counter()
        for v in values[1:]:
            current = values[0]
            while True:
                side = "L" if v < current else "R"
                if (current, side) in child_of:
                    current = child_of[(current, side)]
                    continue
                child_of[(current, side)] = v
                wanted[(current, v, side)] += 1
                break
        if sorted(int(m.label(v)) for v in m.nodes) != sorted(values):
            return f"the values drawn are {sorted(int(m.label(v)) for v in m.nodes)}, the input has {sorted(values)}"
        if int(m.label(m.roots[0])) != values[0]:
            return f"the root drawn is {m.label(m.roots[0])}, the first value inserted is {values[0]}"
        return differences(collections.Counter((int(m.label(a)), int(m.label(b)), m.sides[b]) for a, b, _ in m.edges), wanted, "tree edges")
    return check


def level_order_tree(m, sample_in):
    """'N target' then N values in level order: the node at index i has its children at 2i+1 (left) and 2i+2 (right)."""
    values = [int(x) for x in sample_in.strip().split("\n")[1].split()]
    wanted = collections.Counter((values[(i - 1) // 2], values[i], "L" if i % 2 else "R") for i in range(1, len(values)))
    if sorted(int(m.label(v)) for v in m.nodes) != sorted(values):
        return f"the values drawn are {sorted(int(m.label(v)) for v in m.nodes)}, the input has {sorted(values)}"
    return differences(collections.Counter((int(m.label(a)), int(m.label(b)), m.sides[b]) for a, b, _ in m.edges), wanted, "tree edges")


def adjacency_matrix(m, sample_in):
    lines = sample_in.strip().split("\n")
    n = int(lines[0])
    matrix = [[int(x) for x in line.split()] for line in lines[1:1 + n]]
    if not m.directed or sorted(m.nodes) != list(range(n)):
        return "the matrix is a directed graph on the vertices 0..n-1"
    wanted = collections.Counter((i, j, matrix[i][j]) for i in range(n) for j in range(n) if i != j and matrix[i][j] != -1)
    return differences(collections.Counter(m.edges), wanted, "edges")


def land_and_water(m, sample_in):
    rows = [[int(x) for x in line.split()] for line in sample_in.strip().split("\n")]
    return None if m.kind == "grid" and m.grid == rows else "the grid drawn is not the sample's grid"


STRUCTURES = {
    "_graph_bfs_shortest_path": graph_edges(False),
    "_graph_detect_cycle": graph_edges(False),
    "_graph_dijkstra": graph_edges(False),
    "_graph_topological_sort": graph_edges(True),
    "_hard_graph_bellman_ford": graph_edges(True),
    "_hard_graph_strongly_connected": graph_edges(True),
    "_queue_bfs_level_order": graph_edges(False),
    "_hard_graph_floyd_warshall": adjacency_matrix,
    "_graph_number_of_islands": land_and_water,
    "_tree_inorder": search_tree(0),
    "_tree_max_depth": search_tree(0),
    "_tree_level_order": search_tree(0),
    "_tree_diameter": search_tree(0),
    "_tree_lowest_common_ancestor": search_tree(0),   # line 2 is 'p q'
    "_hard_tree_serialize_deserialize": search_tree(1),   # line 1 is N
    "_hard_tree_path_sum": level_order_tree,
}
assert set(ANSWERS) == set(STRUCTURES), f"each template needs both an answer solver and a structure check: {sorted(set(ANSWERS) ^ set(STRUCTURES))}"


def both(name):
    answer, structure = ANSWERS[name], STRUCTURES[name]
    return lambda m, sample_in, sample_out: structure(m, sample_in) or answer(m, sample_in, sample_out)


ORACLES = {name: both(name) for name in ANSWERS}   # what the audit runs on every drawn picture

# Templates whose text talks about graphs or trees but that are deliberately not drawn, and why.
NO_PICTURE = {
    "_backtracking_word_search": "a grid of letters and a word to find in it: the grid holds letters, not a graph or a land and water map",
    "_hard_dp_bitmask_tsp": "a distance matrix between cities in a dynamic-programming question: no graph is drawn from it",
    "_hard_tree_kth_smallest_bst": "the BST is given as sorted values, which do not fix the shape of the tree",
    "_ll_detect_cycle": "a linked list, not a graph",
    "_ll_nth_from_end": "a linked list, not a graph",
    "_searching_sqrt_integer": "a square root, not a tree",
}


# ── the service's templates, built into questions the way the service builds them ───────────────────────────────────────────

def registered_templates():
    """{name: (function, {topics})} for every template of both registries."""
    found = {}

    def add(fn, topic):
        known = found.setdefault(fn.__name__, (fn, set()))
        assert known[0] is fn, f"two different templates are both called {fn.__name__}"
        known[1].add(topic)

    for topic, fns in G.TOPIC_TEMPLATES.items():
        for fn in fns:
            add(fn, topic)
    for (topic, _difficulty), fns in T._get_difficulty_templates().items():
        for fn in fns:
            add(fn, topic)
    return found


def as_served(result, topic):
    """(the question the diagram generator is given, sample input, sample output, whether the service can type it).

    The service turns every test case into stdin / stdout text and derives the question's input schema from them (main_dynamic.py);
    the input format it then serves is the one generated from that schema, which replaces the template's own wording. A question it
    cannot type is not served at all, but it is still checked here, as it would be drawn if it were."""
    tests = [(to_stdin(tc["input"]), to_stdout(tc["output"])) for tc in result["test_cases"]]
    sample_in, sample_out = to_stdin(result["sample_input"]), to_stdout(result["sample_output"])
    typed = type_question(tests, sample_in, sample_out, input_format=str(result.get("input_format") or ""))
    question = {"title": result["title"], "topic": topic, "problem_statement": result["problem_statement"],
                "input_format": (typed or {}).get("input_format") or result.get("input_format", ""),
                "input_schema": (typed or {}).get("input_schema"), "sample_input": sample_in}
    return question, sample_in, sample_out, typed is not None


def plan_quietly(question):
    """(the model, or None; the reason the generator gave for refusing)."""
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        model = dg.plan(question)
    why = re.findall(r"no diagram: (.*)", log.getvalue())
    return model, (why[0] if why else "the topic is not a graph or tree topic and the text names none")


def judge(oracle, model, sample_in, sample_out):
    try:
        return oracle(model, sample_in, sample_out)
    except Exception as exc:  # a solver that cannot even read the drawing found something wrong with it
        return f"the solver could not read the drawing: {type(exc).__name__}: {exc}"


def check_pixels(question, model, sample_in):
    if model.kind == "grid":
        return None if model.grid == [[int(x) for x in row.split()] for row in sample_in.splitlines()] else "the grid drawn is not the sample's grid"
    _, _, _, problems = draw_and_inspect(question)
    return "; ".join(problems) if problems else None


def directly_drawn(templates=None, seeds=SEEDS):
    """The names of the templates that get a picture on at least one seed under at least one of their topics."""
    templates = registered_templates() if templates is None else templates
    return {name for name, (fn, topics) in templates.items()
            if any(plan_quietly(as_served(fn(random.Random(seed)), topic)[0])[0] is not None for topic in topics for seed in range(seeds))}


def audit(templates=None, oracles=None, no_picture=None, seeds=SEEDS, pixels=True):
    """Every way the service's templates and the pictures made from them can go unchecked or wrong, as readable sentences."""
    templates = registered_templates() if templates is None else templates
    oracles = ORACLES if oracles is None else oracles
    no_picture = NO_PICTURE if no_picture is None else no_picture
    problems = []
    for name, (fn, topics) in sorted(templates.items()):
        drawn_at, refused_while_typed, looks_like_graph, pixel_checked = [], [], False, 0
        for topic in sorted(topics):
            for seed in range(seeds):
                result = fn(random.Random(seed))
                question, sample_in, sample_out, typed = as_served(result, topic)
                looks_like_graph = looks_like_graph or bool(GRAPH_WORDS.search(f"{result['title']} {result['problem_statement']} {result.get('input_format', '')}"))
                model, why = plan_quietly(question)
                if model is None:
                    if typed:
                        refused_while_typed.append((topic, seed, why, result["problem_statement"][:110]))
                    continue
                drawn_at.append((topic, seed))
                if name not in oracles:
                    continue
                complaint = judge(oracles[name], model, sample_in, sample_out)
                if complaint:
                    problems.append(f"{name} [{topic}, seed {seed}]: {complaint}")
                if pixels and pixel_checked < PIXEL_SEEDS:
                    pixel_checked += 1
                    complaint = check_pixels(question, model, sample_in)
                    if complaint:
                        problems.append(f"{name} [{topic}, seed {seed}]: the picture disagrees with its model: {complaint}")

        if drawn_at:
            if name not in oracles:
                problems.append(f"{name} is drawn (for example {drawn_at[0]}) and no independent solver checks the picture: add one to ORACLES")
            if name in no_picture:
                problems.append(f"{name} is listed in NO_PICTURE but it is drawn: remove it from the list and give it a solver")
            for topic, seed, why, statement in refused_while_typed[:3]:
                problems.append(f"{name} [{topic}, seed {seed}] is drawn for other wordings but refused for this one ({why}): {statement!r}")
        else:
            if name in oracles:
                problems.append(f"{name} has a solver in ORACLES but is never drawn any more: remove the solver")
            if looks_like_graph and name not in no_picture:
                problems.append(f"{name} talks about graphs or trees but gets no picture: draw it (with a solver) or list it in NO_PICTURE with the reason")

    for name in sorted(set(oracles) - set(templates)):
        problems.append(f"{name} has a solver in ORACLES but the service has no such template")
    for name in sorted(set(no_picture) - set(templates)):
        problems.append(f"{name} is listed in NO_PICTURE but the service has no such template")
    return problems


@contextlib.contextmanager
def service_with_only(fn, topic, seed):
    """generate_dynamic offering `fn` as the only template of `topic`, with its random choices fixed by `seed` (the service draws a fresh
    seed for every question), so each template is served at every difficulty with the difficulty text the service appends."""
    saved = G._rng, G._seed, G.TOPIC_TEMPLATES[topic], T.get_difficulty_templates
    counter = itertools.count(seed * 1000 + 17)
    G._rng = lambda: random.Random(next(counter))
    G._seed = lambda: next(counter)
    G.TOPIC_TEMPLATES[topic] = [fn]
    T.get_difficulty_templates = lambda topic_key, difficulty: None
    G.clear_title_cache()
    try:
        yield
    finally:
        G._rng, G._seed, G.TOPIC_TEMPLATES[topic], T.get_difficulty_templates = saved
        G.clear_title_cache()


def difficulty_texts():
    """The text generate_dynamic appends to a statement that has numbers in it, at each difficulty, checked against the service itself
    (through a cheap template). It used to be a different sentence per difficulty; it is now one note that the numbers are the sample's."""
    cheap = registered_templates()["_easy_array_sum"][0]
    texts = {}
    for difficulty in DIFFICULTIES:
        with service_with_only(cheap, "arrays", 0):
            statement = G.generate_dynamic("arrays", difficulty)["problem_statement"]
        assert statement.endswith(G.SAMPLE_NOTE), "generate_dynamic no longer ends its statements with SAMPLE_NOTE: update difficulty_texts"
        texts[difficulty] = G.SAMPLE_NOTE
    return texts


def audit_served(templates=None, oracles=None, seeds=SERVED_SEEDS):
    """(problems, names drawn) for questions as the service serves them, under each topic of each template and at each difficulty.

    A template that has a solver goes through generate_dynamic itself, alone, so the title variants and the extra test cases it adds are
    included. Every other template (some, like the N-Queens counter, take seconds to top up their tests) gets the service's own difficulty
    text appended to its statement, which is the part that could make a question of another topic look like a graph question."""
    templates = registered_templates() if templates is None else templates
    oracles = ORACLES if oracles is None else oracles
    appended = difficulty_texts()
    problems, drawn = [], set()
    for name, (fn, topics) in sorted(templates.items()):
        for topic in sorted(topics):
            for difficulty in DIFFICULTIES:
                for seed in range(seeds):
                    where = f"{name} served for {topic}/{difficulty}, seed {seed}"
                    if name in oracles:
                        with service_with_only(fn, topic, seed):
                            try:
                                result = G.generate_dynamic(topic, difficulty)
                            except Exception as exc:
                                problems.append(f"{where}: generate_dynamic failed: {exc}")
                                continue
                    else:
                        result = fn(random.Random(seed))
                        if any(ch.isdigit() for ch in result["problem_statement"]):
                            result = {**result, "problem_statement": result["problem_statement"] + appended[difficulty]}
                    question, sample_in, sample_out, _ = as_served(result, topic)
                    model, _ = plan_quietly(question)
                    if model is None:
                        continue
                    drawn.add(name)
                    if name not in oracles:
                        problems.append(f"{where} is drawn and no solver is registered for it")
                        continue
                    complaint = judge(oracles[name], model, sample_in, sample_out)
                    if complaint:
                        problems.append(f"{where}: {complaint}")
    return problems, drawn


# ── the real service ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_audit_really_sees_the_services_templates():
    found = registered_templates()
    assert len(found) > 100, "the registries look empty: the audit would pass without checking anything"
    assert {"_graph_dijkstra", "_hard_graph_floyd_warshall", "_queue_bfs_level_order", "_tree_diameter"} <= set(found)
    assert directly_drawn(found) == set(ORACLES), "the templates that get a picture are not the ones that have a solver"


def test_every_template_that_is_drawn_has_a_solver_and_agrees_with_it():
    problems = audit()
    assert problems == [], "\n" + "\n".join(problems)


def test_questions_served_through_generate_dynamic_are_drawn_correctly_at_every_difficulty():
    problems, drawn = audit_served()
    assert problems == [], "\n" + "\n".join(problems)
    # the difficulty text ("complex graph algorithms") must neither hide a picture nor add one to a template that is not drawn
    assert drawn == directly_drawn(), sorted(drawn ^ directly_drawn())


def test_every_wording_of_bfs_level_order_says_the_graph_is_undirected():
    """Its fifth wording never said so, and the picture was refused for one question in five."""
    fn = registered_templates()["_queue_bfs_level_order"][0]
    wordings = {re.sub(r"\d+", "#", fn(random.Random(seed))["problem_statement"]) for seed in range(200)}
    assert len(wordings) == 5 and all("undirected" in w for w in wordings), wordings


# ── the guard checks itself: a broken or unreviewed template must make it complain ──────────────────────────────────────────

def renamed(fn, name, edit=None):
    """A copy of a real template under another name, optionally with its result edited."""
    def template(rng):
        result = fn(rng)
        return edit(result) if edit else result

    template.__name__ = name
    return template


def only(name, fn, topic):
    return {name: (fn, {topic})}


def real(name):
    return registered_templates()[name][0]


def test_a_new_template_that_is_drawn_without_a_solver_is_caught():
    brand_new = renamed(real("_graph_dijkstra"), "_graph_brand_new")
    problems = audit(only("_graph_brand_new", brand_new, "graphs"), seeds=4, pixels=False)
    assert any("_graph_brand_new is drawn" in p and "no independent solver" in p for p in problems), problems
    served_problems, _ = audit_served(only("_graph_brand_new", brand_new, "graphs"), seeds=2)
    assert any("_graph_brand_new served for graphs/hard" in p and "no solver is registered" in p for p in served_problems), served_problems


def test_a_picture_that_disagrees_with_the_templates_own_answer_is_caught():
    def wrong_answer(result):
        result["sample_output"] = "999"
        return result

    broken = renamed(real("_graph_bfs_shortest_path"), "_graph_bfs_shortest_path", wrong_answer)
    problems = audit(only("_graph_bfs_shortest_path", broken, "graphs"), seeds=4, pixels=False)
    assert any("the drawing gives" in p and "'999'" in p for p in problems), problems
    served_problems, _ = audit_served(only("_graph_bfs_shortest_path", broken, "graphs"), seeds=2)
    assert any("the drawing gives" in p and "'999'" in p for p in served_problems), served_problems


def test_a_graph_looking_template_without_a_picture_and_without_a_reason_is_caught():
    def unreadable(result):
        result["sample_input"] = "see the statement"
        return result

    undrawn = renamed(real("_graph_dijkstra"), "_graph_undrawn_newcomer", unreadable)
    templates = only("_graph_undrawn_newcomer", undrawn, "graphs")
    problems = audit(templates, seeds=4, pixels=False)
    assert any("_graph_undrawn_newcomer talks about graphs or trees but gets no picture" in p for p in problems), problems
    assert audit(templates, oracles={}, no_picture={"_graph_undrawn_newcomer": "reviewed"}, seeds=4, pixels=False) == []


def test_a_wording_that_does_not_say_whether_edges_are_directed_is_caught():
    def forget_direction(result):
        if result["problem_statement"].startswith("Perform BFS"):
            result["problem_statement"] = result["problem_statement"].replace("undirected ", "")
        return result

    vague = renamed(real("_queue_bfs_level_order"), "_queue_bfs_level_order", forget_direction)
    problems = audit(only("_queue_bfs_level_order", vague, "queues"), seeds=30, pixels=False)
    assert any("does not say whether the edges are directed" in p for p in problems), problems


def test_an_unfinished_picture_is_caught_by_the_solver():
    """The source of a BFS is part of the question: a picture that leaves it unmarked cannot be read, and the solver says so."""
    def no_source_words(result):
        result["problem_statement"] = result["problem_statement"].replace("from node", "from").replace("source", "start")
        result["input_format"] = "Line 1: n e k. Next e lines: u v."
        return result

    unmarked = renamed(real("_queue_bfs_level_order"), "_queue_bfs_level_order", no_source_words)
    problems = audit(only("_queue_bfs_level_order", unmarked, "queues"), seeds=10, pixels=False)
    assert any("source node is not marked" in p for p in problems), problems


def test_stale_entries_are_caught():
    drawn_and_listed = audit(only("_graph_dijkstra", real("_graph_dijkstra"), "graphs"), oracles={"_graph_dijkstra": ORACLES["_graph_dijkstra"]},
                             no_picture={"_graph_dijkstra": "x", "_gone": "x"}, seeds=3, pixels=False)
    assert any("_graph_dijkstra is listed in NO_PICTURE but it is drawn" in p for p in drawn_and_listed), drawn_and_listed
    assert any("_gone is listed in NO_PICTURE but the service has no such template" in p for p in drawn_and_listed), drawn_and_listed
    ghost = audit(only("_ll_nth_from_end", real("_ll_nth_from_end"), "linked-lists"), oracles={"_ll_nth_from_end": ORACLES["_graph_dijkstra"], "_vanished": ORACLES["_graph_dijkstra"]},
                  no_picture={}, seeds=3, pixels=False)
    assert any("_ll_nth_from_end has a solver in ORACLES but is never drawn any more" in p for p in ghost), ghost
    assert any("_vanished has a solver in ORACLES but the service has no such template" in p for p in ghost), ghost


# ── a check that cannot fail proves nothing: every kind of defect, in every template, is reported ───────────────────────────
# Each function takes a copy of a correct drawing and returns it with one defect, or None when the defect cannot be applied to it.

def drop_last_edge(m):
    if m.kind in ("graph", "tree", "binary_tree") and m.edges:
        m.edges = m.edges[:-1]
        return m


def flip_arrows(m):
    if m.edges and (m.directed or m.kind != "graph"):   # the direction of an undirected edge is not a thing that can be wrong
        m.edges = [(b, a, w) for a, b, w in m.edges]
        return m


def add_phantom_edge(m):
    if m.kind == "graph" and len(m.nodes) >= 3:
        joined = {(a, b) for a, b, _ in m.edges} | {(b, a) for a, b, _ in m.edges}
        for a in m.nodes:
            for b in m.nodes:
                if a < b and (a, b) not in joined:
                    m.edges = list(m.edges) + [(a, b, m.edges[0][2] if m.edges else None)]
                    return m


def drop_last_vertex(m):
    if m.kind in ("graph", "tree", "binary_tree") and len(m.nodes) >= 3:
        gone = m.nodes[-1]
        m.nodes = m.nodes[:-1]
        m.edges = [e for e in m.edges if gone not in e[:2]]
        for table in (m.labels, m.sides, m.marks, m.notes):
            table.pop(gone, None)
        return m


def drop_marks(m):
    if m.marks:
        m.marks = {}
        return m


def swap_left_and_right(m):
    if m.kind == "binary_tree" and m.sides:
        m.sides = {v: ("R" if s == "L" else "L") for v, s in m.sides.items()}
        return m


def change_a_value(m):
    if m.kind == "binary_tree" and m.labels:
        v = m.nodes[-1]
        try:
            m.labels[v] = str(int(m.labels[v]) + 1)
        except (KeyError, ValueError):
            return None
        return m


def flip_a_cell(m):
    if m.kind == "grid" and m.grid:
        m.grid[0][0] = 1 - m.grid[0][0]
        return m


DEFECTS = {f.__name__: f for f in (drop_last_edge, flip_arrows, add_phantom_edge, drop_last_vertex, drop_marks, swap_left_and_right, change_a_value, flip_a_cell)}
DEFECT_SEEDS = 12


def test_every_template_check_reports_every_kind_of_defect_every_time_it_applies():
    """The answer alone is a weak witness (a true/false or a count rarely changes when one edge or value is wrong; a mirrored tree has the same
    depth), which is why each template is also compared with the structure of its own input. If a defect slips past here, the check for that
    template can no longer fail for that kind of mistake."""
    templates = registered_templates()
    missed, applied = [], collections.Counter()
    for name, oracle in sorted(ORACLES.items()):
        fn, topics = templates[name]
        for seed in range(DEFECT_SEEDS):
            question, sample_in, sample_out, _ = as_served(fn(random.Random(seed)), sorted(topics)[0])
            model, _ = plan_quietly(question)
            if model is None:
                continue
            assert judge(oracle, model, sample_in, sample_out) is None, f"{name} seed {seed}: the unbroken drawing must pass"
            for defect_name, defect in DEFECTS.items():
                broken = defect(copy.deepcopy(model))
                if broken is None:
                    continue
                applied[defect_name] += 1
                if judge(oracle, broken, sample_in, sample_out) is None:
                    missed.append(f"{name} seed {seed}: '{defect_name}' went unnoticed")
    assert missed == [], "\n" + "\n".join(missed[:25]) + (f"\n... and {len(missed) - 25} more" if len(missed) > 25 else "")
    assert all(applied[d] >= 10 for d in DEFECTS), f"a kind of defect was hardly ever applied, so it was hardly ever tested: {dict(applied)}"


def test_every_template_with_a_solver_has_at_least_one_defect_applied_to_it():
    templates = registered_templates()
    for name in sorted(ORACLES):
        fn, topics = templates[name]
        tried = 0
        for seed in range(DEFECT_SEEDS):
            question, *_ = as_served(fn(random.Random(seed)), sorted(topics)[0])
            model, _ = plan_quietly(question)
            tried += model is not None and any(defect(copy.deepcopy(model)) is not None for defect in DEFECTS.values())
        assert tried >= 3, f"{name}: the defects could be applied to only {tried} drawings, so its check was hardly tried"


def test_the_typing_rule_for_a_last_line_is_guarded(monkeypatch):
    """The first defect this audit found: BFS Shortest Path was typed with its source and destination read from the first edge."""
    name = "_graph_bfs_shortest_path"
    alone = dict(oracles={name: ORACLES[name]}, no_picture={}, seeds=10, pixels=False)
    monkeypatch.setattr(legacy_typing, "_LAST_LINE", re.compile(r"(?!x)x"))
    assert any(name in p for p in audit(only(name, real(name), "graphs"), **alone)), "switching the rule off must be noticed"
    monkeypatch.undo()
    assert audit(only(name, real(name), "graphs"), **alone) == []
