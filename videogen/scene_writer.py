"""Stage 2 — the Manim scene.

Claude writes a real `VoiceoverScene` subclass here, but it does not get a blank
page. It is handed the full source of `layout.py` and `theme.py` and required to
compose through those primitives, so the overlap guarantees that made this
project work are enforced by construction rather than by prompt.

Everything it returns is then checked statically before it is allowed near the
renderer. A generated scene that fails any check is regenerated with the failure
list fed back to the model, so the common failures (a missing
`run_time=tracker.duration`, a 200-line `construct`, a stray `Code` mobject)
correct themselves instead of surfacing as a broken render ten minutes later.
"""

import ast
import json
import os
import re

from llm import ClaudeUnavailable, complete

HERE = os.path.dirname(os.path.abspath(__file__))

# Generated scenes may import from these and nothing else.
ALLOWED_IMPORTS = {"manim", "manim_voiceover", "layout", "theme", "numpy", "math",
                   "itertools", "random"}

# Generated code is executed by the renderer, so the escape hatches are closed.
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input",
                   "globals", "locals"}

MIN_VOICEOVERS = 6      # a 4-6 minute lesson is many narrated beats, not three
MAX_CONSTRUCT_STMTS = 60
MIN_HELPERS = 3


def class_name(slug):
    """'hash-tables' -> 'HashTablesLesson'."""
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", slug) if p]
    stem = "".join(p[:1].upper() + p[1:] for p in parts) or "Topic"
    if stem[0].isdigit():
        stem = "Lesson" + stem
    return stem + "Lesson"


def _read(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
        return fh.read()


def system_prompt():
    """Built fresh each run so edits to the primitives reach the model."""
    return f"""You write Manim animation code for short educational programming
videos. You are given a finished lesson design — the words are already written —
and your job is to turn it into one scene that makes those words visual.

The videos should feel professionally produced: the visual reasoning of
3Blue1Brown, the clarity of Khan Academy, the diagrams of ByteByteGo, the pacing
of Fireship.

=====================================================================
THE PRIMITIVES YOU MUST BUILD ON
=====================================================================
This project owns its layout. You do not position things against the frame; you
compose these primitives, which return mobjects already fitted to the content
band. This is what makes overlapping impossible. Read them carefully — this is
the full source of the two modules you import.

--- theme.py ---
{_read("theme.py")}

--- layout.py ---
{_read("layout.py")}

=====================================================================
HARD REQUIREMENTS
=====================================================================
- Output ONE Python file and nothing else. No markdown, no code fences, no
  commentary before or after.
- Import only from: manim, manim_voiceover, layout, theme, numpy, math.
- Exactly one class. It MUST inherit from VoiceoverScene.
- In construct(), first line of setup:
      self.camera.background_color = BG
      self.set_speech_service(GTTSService(lang="en", tld="com"))
- ALL narration goes through the voiceover context manager, and every animation
  inside it MUST be synchronised with run_time=tracker.duration:

      with self.voiceover(text="...") as tracker:
          self.play(FadeIn(thing), run_time=tracker.duration)

  Do not break audio synchronisation. Do not replace the voiceover
  architecture. Where a block needs several animations, split the tracker
  duration across them or use AnimationGroup / Succession / LaggedStart so the
  total still fills tracker.duration.
- Every top-level piece of content is positioned with place(), place_top() or
  split() before it is shown. Never hand-position against frame coordinates.
- Clear the stage between acts. Nothing from one act may survive into the next.
- Do NOT use Manim's Code mobject. Render code with markup_code_block() from
  layout, which returns one MarkupText per line and is indexable: code[3] is the
  fourth line.

=====================================================================
ANIMATION STYLE
=====================================================================
The animations must feel alive. Avoid slides. Avoid static screens. Avoid walls
of text. Objects move with purpose, and the visuals explain the concept rather
than decorate it. Never leave objects static for long, and prefer motion over
narration wherever a thing can be shown instead of said.

Every idea gets an animated transition. Prefer:
    Transform, ReplacementTransform, FadeTransform, MoveAlongPath,
    AnimationGroup, LaggedStart, Succession, Create, GrowArrow, Indicate,
    Circumscribe, Flash, Write, DrawBorderThenFill

Build with animated objects, not text: Circle, Rectangle, Square, Line, Arrow,
Brace, Polygon, Dot, NumberLine, Axes, Matrix, VGroup, SurroundingRectangle,
Underline — plus this project's diagram(), nodes(), ArrayRow, Pointer,
StackFrames and VarTable.

FOR THE CODE ACT specifically — this is the part that must not be a static
listing. Animate the execution:
    - walk the listing line by line with a SurroundingRectangle that Transforms
      from one line to the next
    - show variables changing with VarTable.set_value(), which returns an
      animation
    - move pointers with Pointer.point_to() as indexes advance
    - mutate array cells with ArrayRow.set_value()
    - grow and unwind the recursion stack with StackFrames.push()/pop()
    - Indicate or Flash the value that just changed
The design's walkthrough gives you the line indexes and the variable state after
each step. Use them.

COLOUR — use it to reinforce meaning, consistently, from the theme palette:
    ACCENT   cyan    primary / the thing under discussion
    ACCENT_4 green   correct, found, success
    ACCENT_3 amber   current focus, the active line or cell
    ACCENT_2 magenta wrong, discarded, the failure case
    ACCENT_5 violet  a secondary structure
    MUTED    grey    inactive, not-yet-reached
Keep a colour meaning the same thing for the whole video.

=====================================================================
CODE QUALITY
=====================================================================
Your Manim code must be modular, well-commented and easy to maintain. Give each
act its own method — construct() orchestrates and stays short; it must not be a
long procedural block. Factor repeated animation patterns into small helpers
rather than duplicating them. Comment the intent behind a visual choice, not
what the next line obviously does.

=====================================================================
BEFORE YOU ANSWER
=====================================================================
Check your own work against every one of these, and improve the lesson before
producing final output if any is unsatisfied:
  - the lesson is engaging
  - the runtime fits 2-7 minutes
  - every important idea is animated, not stated
  - it includes the analogy
  - it builds intuition before syntax
  - it includes the solved coding example
  - the code's execution is animated, not just displayed
  - colours are used consistently
  - the narration flows naturally
  - there are no boring, text-heavy scenes
  - every self.play inside a voiceover uses run_time=tracker.duration"""


def _user_prompt(design, cls, feedback=None):
    note = ""
    if feedback:
        note = ("\n\nYour previous attempt was REJECTED by the project's static "
                "checks. Fix all of these:\n" + feedback + "\n")
    return f"""Write the Manim scene for this lesson.

The class must be named exactly: {cls}

Use the narration text verbatim — it has already been written and timed. The
"visual" field on each beat tells you what should be happening on screen while
that line is spoken.

LESSON DESIGN
{json.dumps(design, indent=2, ensure_ascii=False)}
{note}
Output the complete Python file only."""


# --- static gate -----------------------------------------------------------
def _strip_fences(text):
    """Models sometimes wrap the file in ```python despite being told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    return text.strip() + "\n"


def _root_module(name):
    return (name or "").split(".")[0]


def _stmt_count(node):
    return sum(1 for n in ast.walk(node) if isinstance(n, ast.stmt)) - 1


def _base_names(cls):
    names = []
    for base in cls.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def _narration_segments(tree):
    """Count spoken lines, not `with` blocks.

    A well-written scene funnels narration through one helper, so counting
    voiceover blocks would punish exactly the reuse we ask for. Count the
    narration strings instead: seven or more words rules out code listings and
    short labels.
    """
    count = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and len(node.value) >= 40 and len(node.value.split()) >= 7):
            count += 1
    return count


def _voiceover_blocks(tree):
    """Every `with self.voiceover(...) as tracker:` block, and its target name."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            expr = item.context_expr
            if (isinstance(expr, ast.Call)
                    and isinstance(expr.func, ast.Attribute)
                    and expr.func.attr == "voiceover"):
                target = item.optional_vars
                found.append((node, target.id if isinstance(target, ast.Name) else None))
    return found


def check(source, cls_name):
    """Every reason this scene must not be rendered. Empty list means good."""
    problems = []

    try:
        tree = ast.parse(source)
        compile(source, "<generated>", "exec")
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", "?")
        return [f"The file is not valid Python (line {line}): {exc}"]

    # -- imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _root_module(alias.name) not in ALLOWED_IMPORTS:
                    problems.append(f"Disallowed import: {alias.name}. "
                                    f"Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}.")
        elif isinstance(node, ast.ImportFrom):
            if node.level or _root_module(node.module) not in ALLOWED_IMPORTS:
                problems.append(f"Disallowed import: from {node.module}. "
                                f"Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}.")
            for alias in node.names:
                if alias.name == "Code":
                    problems.append("Imported Manim's Code mobject. Render code "
                                    "with markup_code_block() from layout instead.")

    # -- forbidden constructs
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        if (isinstance(node, ast.Attribute) and node.attr == "frame"
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "camera"):
            problems.append("Used self.camera.frame, which only exists on a "
                            "MovingCameraScene. Remove it.")
    if "Code" in calls:
        problems.append("Used Manim's Code mobject. Render code with "
                        "markup_code_block() from layout instead.")
    for bad in sorted(FORBIDDEN_CALLS & calls):
        problems.append(f"Called {bad}(), which generated scenes may not use.")

    # -- the class
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(classes) != 1:
        problems.append(f"Expected exactly one class, found {len(classes)}. "
                        f"Put every act in a method of the one scene class.")
        return problems

    cls = classes[0]
    if cls.name != cls_name:
        problems.append(f"The class must be named exactly {cls_name}, not {cls.name}.")
    if "VoiceoverScene" not in _base_names(cls):
        problems.append("The scene class must inherit from VoiceoverScene.")

    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    names = {m.name for m in methods}
    if "construct" not in names:
        problems.append("No construct() method.")
        return problems

    helpers = [m for m in methods if m.name != "construct" and not m.name.startswith("__")]
    if len(helpers) < MIN_HELPERS:
        problems.append(
            f"Only {len(helpers)} helper method(s). Give each act its own method "
            f"(at least {MIN_HELPERS}) so construct() stays an orchestrator.")

    construct = next(m for m in methods if m.name == "construct")
    stmts = _stmt_count(construct)
    if stmts > MAX_CONSTRUCT_STMTS:
        problems.append(
            f"construct() is {stmts} statements, over the {MAX_CONSTRUCT_STMTS} "
            f"limit. Move the body of each act into its own method.")

    # -- voiceover architecture
    src = source
    if "set_speech_service" not in src or "GTTSService" not in src:
        problems.append("construct() must call "
                        "self.set_speech_service(GTTSService(lang=\"en\", tld=\"com\")).")

    blocks = _voiceover_blocks(cls)
    if not blocks:
        problems.append(
            "No `with self.voiceover(...) as tracker:` block. All narration must "
            "go through the voiceover context manager.")

    spoken = _narration_segments(cls)
    if spoken < MIN_VOICEOVERS:
        problems.append(
            f"Only {spoken} narration line(s) found. A 2-7 minute lesson needs at "
            f"least {MIN_VOICEOVERS}. Speak every beat of the design; do not drop "
            f"or merge them.")

    unsynced = 0
    for node, target in blocks:
        if target is None:
            unsynced += 1
            continue
        synced = any(
            isinstance(n, ast.Attribute) and n.attr == "duration"
            and isinstance(n.value, ast.Name) and n.value.id == target
            for n in ast.walk(node)
        )
        if not synced:
            unsynced += 1
    if unsynced:
        problems.append(
            f"{unsynced} voiceover block(s) never reference tracker.duration. "
            f"Every animation under narration must use run_time=tracker.duration "
            f"so the audio stays in sync.")

    # -- layout guardrail
    if not ({"place", "place_top", "split"} & calls):
        problems.append(
            "No content was positioned with place(), place_top() or split(). "
            "Every top-level mobject must be placed through layout, not moved "
            "against frame coordinates.")

    if "markup_code_block" not in calls:
        problems.append("The code act must render its listing with "
                        "markup_code_block() from layout.")

    return problems


# --- entry point -----------------------------------------------------------
def write_scene(design, slug, model=None, effort="high", attempts=3, progress=print):
    """Generate and validate a scene module. Returns (source, class_name)."""
    cls = class_name(slug)
    system = system_prompt()
    feedback = None

    # max_tokens caps thinking *and* output together, and the system prompt here
    # carries the whole of layout.py — deep effort can burn the entire budget
    # before writing a line. If that happens, step down rather than fail.
    ladder = ["max", "xhigh", "high", "medium", "low"]
    level = effort if effort in ladder else "high"

    for attempt in range(1, attempts + 1):
        progress(f"  [scene {attempt}/{attempts}] Claude is writing {cls} "
                 f"(effort={level}) ")
        try:
            source = _strip_fences(complete(
                _user_prompt(design, cls, feedback),
                system,
                effort=level,
                max_tokens=64000,
                model=model or "claude-opus-5",
            ))
        except ClaudeUnavailable as exc:
            if "max_tokens" not in str(exc) or ladder.index(level) >= len(ladder) - 1:
                raise
            level = ladder[ladder.index(level) + 1]
            progress(f"  budget exhausted while thinking; retrying at effort={level}")
            continue
        problems = check(source, cls)
        if not problems:
            progress(f"  scene passed all checks ({len(source.splitlines())} lines)")
            return source, cls

        progress(f"  rejected, {len(problems)} problem(s):")
        for problem in problems:
            progress(f"    - {problem}")
        feedback = "\n".join(f"- {p}" for p in problems)

    raise ClaudeUnavailable(
        f"Could not get a scene past the static checks in {attempts} attempts.\n"
        f"Last failures:\n{feedback}\n"
        f"The lesson design is saved, so re-run with --reuse-plan to retry only "
        f"this stage, or use --static-scene to render with the built-in scene."
    )
