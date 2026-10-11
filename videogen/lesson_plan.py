"""Stage 1 — the lesson design.

Claude is asked for a *pedagogical* artefact, not a video and not code: one
concept, taught in five acts, with the narration written out in full. The
design is schema-enforced on the way out of the API, sanitised here, and then
gated on estimated runtime before anything is rendered.

The five acts are fixed. Claude fills them; it does not get to invent the shape
of a lesson, because the shape is the part we know is right.

    Hook       an interesting question or problem. Never a definition.
    Intuition  a concrete everyday analogy, in plain language.
    Mechanism  the core idea, walked through visually.
    Trace      a real coding example, executed line by line.
    Summary    intuition, algorithm, complexity, mistakes, one challenge.

Runtime is enforced rather than hoped for: narration word count is the only
reliable predictor of video length, so a design that would render shorter than
two minutes or longer than seven is sent back with specific feedback.
"""

import ast
import re

from llm import ClaudeUnavailable, complete

# --- runtime targets -------------------------------------------------------
MIN_SECONDS = 120.0   # 2 minutes: never generate an extremely short lesson
MAX_SECONDS = 420.0   # 7 minutes: never generate an overly long one
WORDS_PER_SECOND = 2.6  # measured gTTS pace
SECONDS_PER_ACT = 2.5   # transitions, holds, the beat before each act lands

ACTS = ["hook", "intuition", "mechanism", "trace", "summary"]

ACT_GOALS = {
    "hook": "Open with an interesting question or a concrete problem that makes "
            "the viewer want the answer. Never open with a definition.",
    "intuition": "Build intuition with a relatable real-world analogy before any "
                 "technical language. Explain WHY before HOW.",
    "mechanism": "Show the core mechanism visually, step by step.",
    "trace": "Work a practical coding example, showing exactly what happens "
             "during execution.",
    "summary": "Summarise intuition, algorithm, complexity and common mistakes, "
               "then end on one challenge question.",
}

MAX_CODE_LINES = 18
MAX_CODE_WIDTH = 60


# --- response schema -------------------------------------------------------
def _obj(props, required):
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_STRS = {"type": "array", "items": _STR}

_BEAT = _obj(
    {
        "narration": _STR,
        "visual": _STR,  # what the animator should be doing while this is spoken
    },
    ["narration", "visual"],
)

_ACT = _obj(
    {
        "act": {"type": "string", "enum": ACTS},
        "heading": _STR,
        "narration": _STR,
        "beats": {"type": "array", "items": _BEAT},
    },
    ["act", "heading", "narration", "beats"],
)

_STATE = _obj({"name": _STR, "value": _STR}, ["name", "value"])

_STEP = _obj(
    {
        "lines": {"type": "array", "items": {"type": "integer"}},
        "narration": _STR,
        "state": {"type": "array", "items": _STATE},
    },
    ["lines", "narration", "state"],
)

DESIGN_SCHEMA = _obj(
    {
        "title": _STR,
        "objective": _STR,
        "analogy": _obj({"name": _STR, "mapping": _STR}, ["name", "mapping"]),
        "acts": {"type": "array", "items": _ACT},
        "code": _obj(
            {
                "lines": _STRS,
                "variables": _STRS,
                "walkthrough": {"type": "array", "items": _STEP},
            },
            ["lines", "variables", "walkthrough"],
        ),
        "complexity": _STR,
        "mistakes": _STRS,
        "challenge": _STR,
    },
    ["title", "objective", "analogy", "acts", "code", "complexity", "mistakes",
     "challenge"],
)


# --- prompt ----------------------------------------------------------------
SYSTEM = """You design short educational videos about programming concepts. Your
output is the lesson itself: the words that will be spoken and the ideas that
will be shown. You never write animation code.

The videos you design should feel like professionally produced YouTube
education — the clarity and visual reasoning of 3Blue1Brown, the patience of
Khan Academy, the systems diagrams of ByteByteGo, the pacing of Fireship, and
the analogies of Veritasium.

LESSON QUALITY — every lesson must:
- teach ONE coding concept deeply, not several shallowly
- assume a beginner-to-intermediate audience
- build intuition before syntax
- explain WHY before HOW
- avoid unnecessary jargon, and define any technical term naturally the first
  time it is used, in the flow of a sentence rather than as an aside

LEARNING OBJECTIVE
Every lesson opens with a clear objective, phrased exactly like:
"By the end of this lesson you will understand how hash maps work and know when
to use them."

STRUCTURE — exactly five acts, in this order:

1. hook
   Start with an interesting question or problem.
   For example: "How can Google search billions of pages in milliseconds?" or
   "Why is binary search impossible on an unsorted list?"
   Never start with a definition.

2. intuition
   Build intuition in simple language, using a relatable real-world analogy.
   Good analogies: a bookshelf, a library, mailboxes, a parking lot, a queue in
   a supermarket, a traffic intersection, water flowing through pipes, dominoes,
   sorting playing cards.
   Avoid abstract explanations first.

3. mechanism
   The core mechanism, explained visually. Every idea here must be something
   that can be *shown* — moving objects, changing state, highlighted paths —
   not a wall of text. Each beat's "visual" field describes what the viewer
   sees while that narration is spoken.

4. trace
   A practical coding example, executed line by line. The "code" object holds
   the program; the walkthrough holds one step per meaningful moment of
   execution, each naming the line indexes it touches and the variable state
   after it runs. Show exactly what happens during execution: variables
   changing, pointers moving, arrays mutating, the recursion stack growing and
   unwinding, items entering and leaving a queue, a tree or graph being walked.

5. summary
   Summarise the intuition, then the algorithm. Mention complexity if relevant.
   Mention common mistakes. End with one challenge question for the viewer.

DURATION
The finished video must run between 2 and 7 minutes, and should target 4 to 6.
Narration is spoken at about 2.6 words per second, so a 5-minute lesson is
roughly 780 spoken words across all narration fields. Pace it like a polished
YouTube video: never rushed, never padded.

VOICE
Friendly, energetic, conversational, confident. Occasionally humorous, and
lightly sarcastic where it earns a smile. Never childish, never robotic, never
overly formal, and never like documentation.
Narration is read aloud by a speech engine, so write plain spoken sentences:
no bullets, no markdown, no symbols. Spell things out — "O of n", not "O(n)";
"less than", not "<".

CODE RULES
- Real, runnable, self-contained Python. It must parse.
- At most 18 lines, at most 60 characters per line, 4 spaces per indent.
- Prefer one small finished function over a truncated larger one.
- "variables" lists the names worth showing in a live state panel as the code
  runs. Keep it to the two or three that actually change.
- Walkthrough "lines" are ZERO-BASED indexes into the code lines array.

Headings are short on-screen labels, at most 46 characters. Everything in a
narration field is spoken; nothing in a narration field is displayed."""


def _prompt(topic, target_seconds, feedback=None):
    words = int(target_seconds * WORDS_PER_SECOND)
    spec = "\n".join(f"- {a}: {ACT_GOALS[a]}" for a in ACTS)
    note = f"\n\nREVISION NOTE — the previous attempt was rejected:\n{feedback}\n" if feedback else ""
    return f"""Design a complete video lesson teaching this one concept: "{topic}".

Target runtime: {int(target_seconds)} seconds, which is roughly {words} spoken
words in total across every narration field. Budget those words across the five
acts deliberately; the trace and mechanism acts usually deserve the most.

The five acts, in order:
{spec}{note}

Return the lesson design as JSON."""


# --- sanitising ------------------------------------------------------------
def _text(value, limit):
    """Length-cap on a word boundary so labels never read like 'Collision Resolu'."""
    out = " ".join(str(value or "").split())
    if len(out) <= limit:
        return out
    cut = out[:limit]
    space = cut.rfind(" ")
    if space >= limit * 0.55:
        cut = cut[:space]
    return cut.rstrip(" ,;:-")


def _speech(value, fallback):
    """Narration is spoken, never displayed, so it is never truncated."""
    out = " ".join(str(value or "").split())
    return out if len(out) >= 12 else fallback


# A hook that opens by defining its subject has missed the brief. These are the
# shapes that show up when it happens.
_DEFINITION_OPENERS = (
    r"^(a|an|the)\s+\w+[\w\s]{0,40}\s+is\s+(a|an|the)\b",
    r"^\w+[\w\s]{0,30}\s+is\s+(a|an|the)\s+\w+",
    r"^(in|within)\s+(computer science|programming|software)\b",
    r"^let'?s\s+(start|begin)\s+with\s+(a\s+)?definition",
)


def _is_definition(narration):
    text = " ".join(str(narration or "").split()).lower()
    return any(re.search(p, text) for p in _DEFINITION_OPENERS)


def compiles(lines):
    """Does this listing parse as Python?

    The snippet is only ever displayed, never executed, so this is a quality
    gate rather than a safety one. It also catches the common failure where a
    model stops mid-block, since a truncated body is a SyntaxError.
    """
    try:
        ast.parse("\n".join(lines))
        return True
    except (SyntaxError, ValueError):
        return False


def _clean_code(raw):
    lines = []
    for line in (raw or [])[:MAX_CODE_LINES]:
        line = str(line or "").replace("\t", "    ").rstrip()
        if len(line) > MAX_CODE_WIDTH:
            line = line[:MAX_CODE_WIDTH]
        if not line.strip():
            continue
        lines.append(line)
    return lines or ["def example():", "    return None"]


def validate(design, topic):
    """Coerce a raw design into something both gates and renderer can rely on."""
    if not isinstance(design, dict):
        design = {}

    out = {
        "topic": topic,
        "title": _text(design.get("title"), 60) or topic.title(),
        "objective": _speech(
            design.get("objective"),
            f"By the end of this lesson you will understand how {topic} works "
            f"and know when to use it.",
        ),
        "complexity": _text(design.get("complexity"), 160),
        "challenge": _speech(design.get("challenge"), "Can you work this one out yourself?"),
    }

    analogy = design.get("analogy") if isinstance(design.get("analogy"), dict) else {}
    out["analogy"] = {
        "name": _text(analogy.get("name"), 60),
        "mapping": _speech(analogy.get("mapping"), "It maps onto the same idea."),
    }

    out["mistakes"] = [_text(m, 120) for m in (design.get("mistakes") or [])[:4] if _text(m, 120)]

    # Acts arrive as a list; index them by name so a reordered or duplicated
    # response still renders in the pedagogically correct order.
    by_name = {}
    for act in design.get("acts") or []:
        if isinstance(act, dict) and act.get("act") in ACTS and act["act"] not in by_name:
            by_name[act["act"]] = act

    out["acts"] = []
    for name in ACTS:
        act = by_name.get(name, {})
        beats = []
        for beat in (act.get("beats") or [])[:8]:
            if not isinstance(beat, dict):
                continue
            narration = _speech(beat.get("narration"), "")
            if not narration:
                continue
            beats.append({
                "narration": narration,
                "visual": _text(beat.get("visual"), 220),
            })
        out["acts"].append({
            "act": name,
            "heading": _text(act.get("heading"), 46) or name.title(),
            "narration": _speech(act.get("narration"), ACT_GOALS[name]),
            "beats": beats,
        })

    code = design.get("code") if isinstance(design.get("code"), dict) else {}
    lines = _clean_code(code.get("lines"))
    variables = [_text(v, 18) for v in (code.get("variables") or [])[:4] if _text(v, 18)]

    walkthrough = []
    for step in (code.get("walkthrough") or [])[:12]:
        if not isinstance(step, dict):
            continue
        idxs = [i for i in (step.get("lines") or [])
                if isinstance(i, int) and 0 <= i < len(lines)]
        state = [
            {"name": _text(s.get("name"), 18), "value": _text(s.get("value"), 22)}
            for s in (step.get("state") or [])[:4]
            if isinstance(s, dict) and _text(s.get("name"), 18)
        ]
        walkthrough.append({
            "lines": idxs[:4],
            "narration": _speech(step.get("narration"), "And on to the next line."),
            "state": state,
        })

    out["code"] = {
        "lines": lines,
        "variables": variables,
        "walkthrough": walkthrough or [{"lines": [0], "narration": out["objective"], "state": []}],
        "parses": compiles(lines),
    }
    return out


# --- runtime gate ----------------------------------------------------------
def _narrations(design):
    # Legacy section-based plans (rendered via --static-scene) nest their
    # narration differently. Estimating those correctly keeps the runtime the
    # CLI reports honest for older saved plans.
    if "sections" in design:
        for sec in design.get("sections", []):
            yield sec.get("narration", "")
            for key in ("points", "beats", "walkthrough"):
                for blob in sec.get(key, []):
                    if isinstance(blob, dict):
                        yield blob.get("narration", "")
        return

    yield design.get("objective", "")
    for act in design.get("acts", []):
        yield act.get("narration", "")
        for beat in act.get("beats", []):
            yield beat.get("narration", "")
    for step in design.get("code", {}).get("walkthrough", []):
        yield step.get("narration", "")
    yield design.get("challenge", "")


def estimate_seconds(design):
    """Rough runtime from narration word count, plus per-act transition time."""
    words = sum(len(str(n).split()) for n in _narrations(design))
    return words / WORDS_PER_SECOND + SECONDS_PER_ACT * len(design.get("acts", []))


def _problems(design, target):
    """Everything wrong with this design, phrased as feedback for the next try."""
    issues = []
    seconds = estimate_seconds(design)

    if seconds < MIN_SECONDS or seconds > MAX_SECONDS or abs(seconds - target) > 60:
        direction = "expand" if seconds < target else "tighten"
        issues.append(
            f"Estimated runtime is {int(seconds)} seconds; the target is "
            f"{int(target)} seconds (hard limits: {int(MIN_SECONDS)}-{int(MAX_SECONDS)}). "
            f"Please {direction} the narration. Adjust depth of explanation and "
            f"the number of beats, not the number of acts."
        )

    hook = next((a for a in design["acts"] if a["act"] == "hook"), None)
    if hook and _is_definition(hook["narration"]):
        issues.append(
            "The hook opens with a definition. Open with a question or a "
            "concrete problem the viewer wants solved instead."
        )

    if not design["analogy"]["name"]:
        issues.append("No real-world analogy was given. The intuition act needs one.")

    if not design["code"]["parses"]:
        issues.append(
            "The code snippet is not valid Python - it looks truncated or "
            "malformed. Give a smaller, complete, self-contained example."
        )

    if len(design["code"]["walkthrough"]) < 3:
        issues.append(
            "The code walkthrough has too few steps to animate an execution. "
            "Give one step per meaningful moment of execution."
        )

    thin = [a["act"] for a in design["acts"] if len(a["beats"]) < 2]
    if thin:
        issues.append(
            f"These acts have too few beats to animate: {', '.join(thin)}. "
            f"Each act needs at least two beats, each with its own visual."
        )

    if not design["mistakes"]:
        issues.append("The summary must mention common mistakes.")

    return issues


# --- entry point -----------------------------------------------------------
def build(topic, model=None, minutes=5.0, effort="high", attempts=3, progress=print):
    """Design a lesson about `topic`, regenerating until it passes the gates."""
    target = max(MIN_SECONDS, min(minutes * 60.0, MAX_SECONDS))
    feedback = None
    best = None

    for attempt in range(1, attempts + 1):
        progress(f"  [design {attempt}/{attempts}] asking Claude ", )
        raw = complete(
            _prompt(topic, target, feedback),
            SYSTEM,
            effort=effort,
            schema=DESIGN_SCHEMA,
            max_tokens=16000,
            model=model or "claude-opus-5",
        )
        design = validate(raw, topic)
        issues = _problems(design, target)
        seconds = estimate_seconds(design)
        progress(f"  estimated {int(seconds // 60)}m {int(seconds % 60)}s, "
                 f"{len(issues)} issue(s)")

        if not issues:
            return design

        for issue in issues:
            progress(f"    - {issue.splitlines()[0]}")
        best = design if best is None else best
        feedback = "\n".join(f"- {i}" for i in issues)

    # Out of attempts. A design that is merely imperfect still renders, but one
    # outside the hard runtime window is not what was asked for.
    seconds = estimate_seconds(best)
    if seconds < MIN_SECONDS or seconds > MAX_SECONDS:
        raise ClaudeUnavailable(
            f"Could not land a lesson inside the {int(MIN_SECONDS)}-{int(MAX_SECONDS)} "
            f"second window after {attempts} attempts (last: {int(seconds)}s). "
            f"Try a narrower topic, or a different --minutes target."
        )
    progress("  accepting the best of "
             f"{attempts} attempts with minor issues outstanding")
    return best
