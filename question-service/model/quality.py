"""What a stored question must not be, and what a served question must keep.

The older banks (question_db.json, questions.json, training_clean.json) were collected from contest sites and never read by a person.
The game grades a program by comparing what it prints with one stored answer, so some of those questions cannot be played fairly:

* the statement points to a picture that was not collected ("[Image]", "see the picture"): part of the problem is missing;
* the problem accepts any of several answers ("if there are multiple answers, print any"): a correct program is marked wrong
  whenever it prints a different valid answer from the stored one;
* the answer is a real number judged with a tolerance, or the problem is interactive: neither can be graded by exact match;
* a stored test has no expected output, the same input is stored with two different answers, or fewer than three different inputs.

`disqualify` names the reason and the loaders leave such a question out. Nothing here judges how good a question is, only whether a
player who solves it correctly can pass it.

A question from those banks also keeps its own words about the input. Its statement ends in sections ("-----Input-----", "-----Output-----")
that say what every number means. The service types the question from its tests and used to serve only the generated description
("Then: n integers, the list arr"), so that meaning was lost. `served_formats` puts the two together.

The templates are checked the other way round: `align_tests_with_sample` makes a template's hidden tests use the layout of the sample
its statement shows, where the template built them differently (see the function).
"""

import re
from typing import Optional

MIN_DISTINCT_TESTS = 3

_PICTURE = re.compile(
    r"\[image\]|\bsee (?:the )?(?:picture|figure|image)s?\b|\b(?:picture|figure|image)s? (?:below|above)\b|\bas shown (?:in|on) the (?:picture|figure|image)"
    r"|\b(?:picture|figure|image)s? (?:shows?|illustrates?|depicts?)\b|\blook at the (?:picture|figure|image)|\bin the (?:picture|figure) (?:below|above)",
    re.IGNORECASE)
_ANY_ANSWER = re.compile(
    r"\b(?:print|output|find|return|choose) any\b|\bany of them\b|\bif there (?:are|exist) (?:multiple|several|many|more than one)\b"
    r"|\b(?:multiple|several) (?:possible |correct |valid |optimal )?(?:answers|solutions)\b|\b(?:print|output|return)\b[^.\n]{0,80}\bin any order\b"
    r"|\bany (?:valid|suitable|correct|possible|optimal) (?:answer|solution|one)\b",
    re.IGNORECASE)
_TOLERANCE = re.compile(
    r"absolute or relative error|relative or absolute error|\berror (?:does|must|should|will) not exceed\b|\b10\s*\^\s*\{?\s*-\s*\d|\b1e-\d",
    re.IGNORECASE)
_INTERACTIVE = re.compile(r"\binteractive (?:problem|task)\b|\bflush (?:the )?(?:output|stdout)\b|\bfflush\b", re.IGNORECASE)

_SECTION = re.compile(r"-{2,}\s*(Input|Output|Examples?|Example|Note|Notes|Explanation|Constraints?|Sample Input|Sample Output|Scoring|Subtasks?)\s*-{2,}",
                      re.IGNORECASE)


_GENERIC_FORMAT = re.compile(r"as described in the problem|^\s*$", re.IGNORECASE)


def explains_input(question: dict) -> bool:
    """Whether the question says, in words, what its input is: an Input section in the statement or an input format that is more than
    a placeholder ("Read input from standard input as described in the problem.") or a copy of the sample's numbers."""
    if "input" in statement_sections(question.get("problem_statement") or ""):
        return True
    given = str(question.get("input_format") or "")
    return not _GENERIC_FORMAT.search(given) and len(re.findall(r"[A-Za-z]{3,}", given)) >= 2


def disqualify(question: dict) -> Optional[str]:
    """Why this stored question cannot be played fairly, or None."""
    statement = question.get("problem_statement") or ""
    text = f"{statement}\n{question.get('output_format') or ''}"
    letters = re.findall(r"[^\W\d_]", statement)
    if letters and sum("a" <= ch.lower() <= "z" for ch in letters) < 0.8 * len(letters):
        return "the statement is not in English"
    if not explains_input(question):
        return "the statement does not say what the input is (it is cut off before its Input section)"
    if _PICTURE.search(text):
        return "the statement refers to a picture that is not there"
    if _ANY_ANSWER.search(text):
        return "any of several answers is accepted, but only one is stored"
    if _TOLERANCE.search(text):
        return "the answer is a real number judged with a tolerance"
    if _INTERACTIVE.search(text):
        return "the problem is interactive"
    answers: dict = {}
    for case in question.get("test_cases") or []:
        if not isinstance(case, dict) or "input" not in case or "output" not in case:
            return "a test case lacks an input or an output"
        given, wanted = str(case["input"]).strip(), str(case["output"]).strip()
        if not wanted:
            return "a test has no expected output"
        if answers.setdefault(given, wanted) != wanted:
            return "the same input is stored with two different answers"
    if len(answers) < MIN_DISTINCT_TESTS:
        return f"fewer than {MIN_DISTINCT_TESTS} different test inputs"
    return None


def keep_playable(questions: list, bank: str) -> list:
    """The questions of a bank that can be played fairly; says how many were left out and why."""
    kept, reasons = [], {}
    for question in questions:
        why = disqualify(question)
        if why is None:
            kept.append(question)
        else:
            reasons[why] = reasons.get(why, 0) + 1
    if reasons:
        detail = "; ".join(f"{count} where {why}" for why, count in sorted(reasons.items(), key=lambda item: -item[1]))
        print(f"[Quality] {bank}: {len(questions) - len(kept)} of {len(questions)} questions left out ({detail})")
    return kept


def statement_sections(statement: str) -> dict:
    """{'input': ..., 'output': ...}: the text a contest statement gives under its Input and Output headings (missing ones are absent)."""
    parts = _SECTION.split(statement or "")
    found = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        key = name.strip().lower()
        if key in ("input", "output") and key not in found and body.strip():
            found[key] = re.sub(r"\n{3,}", "\n\n", body.strip())
    return found


def served_formats(statement: str, typed_input: str, typed_output: str, own_input: str = "", own_output: str = "") -> tuple:
    """(input format, output format) to serve for a question typed from its tests: how the values reach the function, then its own words
    about what they mean and what to produce, from the statement's sections or else from its own formats when those are real text."""
    sections = statement_sections(statement)
    words = lambda text: (not _GENERIC_FORMAT.search(text or "")) and len(re.findall(r"[A-Za-z]{3,}", text or "")) >= 2
    given = sections.get("input") or (own_input.strip() if words(own_input) else None)
    wanted = sections.get("output") or (own_output.strip() if words(own_output) else None)
    input_format = f"{typed_input}\n\nWhat the values mean, in the problem's own words:\n{given}" if given else typed_input
    output_format = f"{wanted}\n\n{typed_output}" if wanted else typed_output
    return input_format, output_format


# ── templates: hidden tests in the layout of the sample ─────────────────────────────────────────────────────────────────

def _ints(line: str) -> bool:
    tokens = line.split()
    return bool(tokens) and all(re.fullmatch(r"-?\d+", t) for t in tokens)


def _aligned(sample: str, test: str) -> Optional[str]:
    """`test` rewritten in the layout of `sample`, or None when they already agree or no rule applies.

    A template writes its sample by hand ("5", then the five numbers) and keeps its tests as Python values, which the service turns into
    text by a general rule (a list becomes one line, a dict one value per line). Where the two came out differently the question could not
    be typed and was never served. Only the layout changes: the values and the expected output are the template's own."""
    s, t = sample.strip("\n").split("\n"), test.strip("\n").split("\n")
    if not all(_ints(line) for line in s + t):
        return None
    width = lambda line: len(line.split())
    # "A B ..." on the first line, against A, B, ... on a line each (then, in both, the same kind of rows: none, or rows of one width)
    w = width(s[0])
    if (w >= 2 and len(t) >= w and all(width(line) == 1 for line in t[:w])
            and len({width(line) for line in s[1:]}) <= 1 and len({width(line) for line in t[w:]}) <= 1 and (len(s) > 1) == (len(t) > w)):
        return "\n".join([" ".join(t[:w])] + t[w:])
    # "N1 N2", then two lists of those lengths, against the two lists alone
    if (len(s) == 3 and len(t) == 2 and w == 2
            and [int(x) for x in s[0].split()] == [width(s[1]), width(s[2])]):
        return f"{width(t[0])} {width(t[1])}\n{t[0]}\n{t[1]}"
    return _with_counts(s, t)


def _with_counts(s: list, t: list) -> Optional[str]:
    """The sample gives a count line before a list ("N", then N numbers) or before rows ("Q", then Q lines of two numbers), and the test
    gives the same parts without their counts: the counts are put back. Anything that does not fit exactly is None."""
    width = lambda line: len(line.split())
    parts, i = [], 0
    while i < len(s):
        if width(s[i]) == 1 and i + 1 < len(s):
            k = int(s[i])
            if k >= 1 and width(s[i + 1]) == k and not (i + 2 < len(s) and width(s[i + 2]) == width(s[i + 1]) and k > 1):
                parts.append(("list", None))
                i += 2
                continue
            rows = s[i + 1:i + 1 + k]
            if k >= 1 and len(rows) == k and len({width(r) for r in rows}) == 1 and width(rows[0]) >= 2:
                parts.append(("rows", width(rows[0])))
                i += 1 + k
                continue
        parts.append(("line", width(s[i])))
        i += 1
    if not any(kind != "line" for kind, _ in parts):
        return None
    out, j = [], 0
    for kind, w in parts:
        if kind == "list":
            if j >= len(t):
                return None
            out += [str(width(t[j])), t[j]]
            j += 1
        elif kind == "rows":
            start = j
            while j < len(t) and width(t[j]) == w:
                j += 1
            out += [str(j - start)] + t[start:j]
        else:
            if j >= len(t) or width(t[j]) != w:
                return None
            out.append(t[j])
            j += 1
    return "\n".join(out) if j == len(t) else None


def align_tests_with_sample(sample_input: str, test_inputs: list) -> Optional[list]:
    """The test inputs (stdin text) rewritten in the layout of the sample, or None when nothing has to change. All or nothing: a template
    whose tests do not ALL follow one rule is left exactly as it is."""
    rewritten = [_aligned(sample_input, text) for text in test_inputs]
    return rewritten if test_inputs and all(r is not None for r in rewritten) else None
