"""Typed starter code for questions that come from the older banks.

Those banks hold a problem text, a sample and some tests, but no declared input structure, so the starter code the game
used to show for them was a guess, and often one that read the wrong lines. This module works the structure out from the
stored inputs themselves and answers only when it is certain:

* the structure is read off one stored test input (the biggest ones are tried first);
* it must then parse EVERY stored input, the sample included, with every line accounted for, every list exactly as long
  as the count it hangs on says, every grid row as wide as the first one, and every number inside 64 bits;
* the stored outputs must all fit one output type (a number, a list of numbers, or plain text).

When any check fails the answer is None and the service does not serve the question: a player must never be locked
into a reader that cannot read the question's own tests. The result uses the same schema notation and generators as
the reviewed questions (model/scaffold.py), so the code a player runs is exactly the code that was checked here.
"""

import re
from typing import Optional

from model import scaffold

FUNCTION_NAME = "solve"
_INT = re.compile(r"-?(0|[1-9][0-9]*)")   # canonical integers only: "007" or "+5" would not survive a round trip
_LIMIT = 9 * 10 ** 18                      # the starters use 64-bit integers in C, C++ and Java
_MAX_TRIES = 8                             # how many different stored inputs to try reading the structure from

_NAMES = {
    "scalar": ["n", "m", "k", "q", "a", "b", "c", "d", "e", "f"],
    "string": ["s", "t", "u", "w"],
    "array": ["arr", "arr2", "arr3", "arr4"],
    "words": ["words", "words2"],
    "grid": ["grid", "grid2"],
    "lines": ["vals", "vals2", "queries"],
    "texts": ["texts", "texts2"],
}


class _Unsupported(Exception):
    """This input has a shape the schema notation cannot express."""


class _Names:
    def __init__(self):
        self.used = {kind: 0 for kind in _NAMES}

    def take(self, kind: str) -> str:
        pool = _NAMES[kind]
        if self.used[kind] >= len(pool):
            raise _Unsupported("too many variables of one kind")
        self.used[kind] += 1
        return pool[self.used[kind] - 1]


def _is_int(token: str) -> bool:
    return bool(_INT.fullmatch(token))


def _owner(declared: dict, count: int) -> Optional[str]:
    """The first earlier int scalar whose value is `count`: the variable a list or a grid can hang its length on."""
    for name, value in declared.items():
        if value == count:
            return name
    return None


def _schema_from(text: str, bare_arrays: bool = False, extended: bool = False, trailing: bool = False):
    """(schema text, {grid name: columns}, {bare array names}) read off one input text, or None when no reading fits.

    With `bare_arrays`, a line of several numbers that no earlier count accounts for is a list in its own right (the whole
    line, any length) instead of a few separate values: many inputs are just one line of numbers, with no count line.

    With `extended` (only tried after every reading above has failed, so nothing that was typed before reads differently):
    rows that hang on a count minus one ("n", then n-1 rows, as a tree gives its edges), and a run of text lines that
    hangs on a count (n words, or q operations such as "PUSH 5" one per line).

    With `trailing`: "n m", then m edges, then "src dst" has m + 1 equal-width rows after the first line, which no count names. The
    stored tests cannot say whether the odd line comes before or after the rows (both readings fit every test), so by default the
    first is read: the line is a few values and the next m rows are the grid. `trailing` is for a question whose own format says
    "last line": the grid takes the rows the most recent earlier count names, and what follows is read on its own."""
    lines = text.strip("\n").split("\n")
    if not lines or any(not line.strip() for line in lines):
        return None   # an empty line could be an empty list or an empty string: not decidable
    rows = [line.split() for line in lines]
    names = _Names()
    declared: dict[str, int] = {}   # int scalars read so far, in order, with the value they had in this input
    entries: list[str] = []
    columns: dict[str, int] = {}
    bare: set[str] = set()
    i = 0
    while i < len(rows):
        tokens = rows[i]
        width = len(tokens)
        all_int = all(_is_int(t) for t in tokens)

        if extended and not all_int:
            run = 1   # text lines in a row (none of them only numbers): one list with a line per entry when an earlier count says how many
            while i + run < len(rows) and not all(_is_int(t) for t in rows[i + run]):
                run += 1
            owner, minus = _owner(declared, run), ""
            if not owner and run >= 2:
                owner, minus = _owner(declared, run + 1), "-1"   # n, then n-1 text rows (a tree's "parent child L" edges)
            if owner:
                entries.append(f"{names.take('texts')}:str[{owner}{minus}]/lines")
                i += run
                continue

        if width == 1:
            if not all_int:
                entries.append(f"{names.take('string')}:str")
                i += 1
                continue
            run = 1   # single-int lines in a row: one list with a line per value when an earlier count says how many
            while i + run < len(rows) and len(rows[i + run]) == 1 and _is_int(rows[i + run][0]):
                run += 1
            owner = _owner(declared, run) if run >= 2 else None
            if owner:
                entries.append(f"{names.take('lines')}:int[{owner}]/lines")
                i += run
                continue
            name = names.take("scalar")
            declared[name] = int(tokens[0])
            entries.append(f"{name}:int")
            i += 1
            continue

        if all_int:
            run = 1   # lines of the same width in a row: a grid when an earlier count says how many rows
            while i + run < len(rows) and len(rows[i + run]) == width and all(_is_int(t) for t in rows[i + run]):
                run += 1
            owner = _owner(declared, run) if run >= 2 else None
            if owner:
                name = names.take("grid")
                entries.append(f"{name}:int[{owner}][{width}]")
                columns[name] = width
                i += run
                continue
            if trailing and run >= 3:
                counts = [(name, value) for name, value in declared.items() if 2 <= value < run]
                if counts:
                    owner, rows_in_grid = counts[-1]   # the most recent count that leaves at least one line over
                    name = names.take("grid")
                    entries.append(f"{name}:int[{owner}][{width}]")
                    columns[name] = width
                    i += rows_in_grid
                    continue
            owner = _owner(declared, run + 1) if extended and run >= 2 else None
            if owner:
                name = names.take("grid")
                entries.append(f"{name}:int[{owner}-1][{width}]")
                columns[name] = width
                i += run
                continue
            owner = _owner(declared, width)
            if owner:
                entries.append(f"{names.take('array')}:int[{owner}]")
                i += 1
                continue
            if bare_arrays:
                name = names.take("array")
                entries.append(f"{name}:int[0]")   # the length is documentation only: the whole line is read
                bare.add(name)
                i += 1
                continue
            if width <= 6 and (i == 0 or width <= 4):   # a few values that belong together, e.g. "n m k" on the first line
                group = []
                for token in tokens:
                    name = names.take("scalar")
                    declared[name] = int(token)
                    group.append(f"{name}:int")
                entries.append(" ".join(group))
                i += 1
                continue
            return None

        # several tokens, not all numbers: words as many as an earlier count, otherwise the whole line is one string
        owner = _owner(declared, width) if not any(_is_int(t) for t in tokens) else None
        if owner:
            entries.append(f"{names.take('words')}:str[{owner}]")
        else:
            entries.append(f"{names.take('string')}:str")
        i += 1
    return "\n".join(entries), columns, bare


def _fits(value) -> bool:
    if isinstance(value, list):
        return all(_fits(item) for item in value)
    if isinstance(value, int):
        return abs(value) <= _LIMIT
    return True


def _verify(schema_text: str, columns: dict, bare: set, inputs: list[str]) -> bool:
    """True only when the schema reads every stored input exactly."""
    try:
        schema = scaffold.parse_input_schema(schema_text)
        declared = scaffold.variables(schema)
        for text in inputs:
            args = scaffold.parse_input_text(schema, text)
            env = {var.name: value for var, value in zip(declared, args)}
            for var in declared:
                value = env[var.name]
                if var.kind == "array" and var.name not in bare:
                    want = int(var.length) if var.length.isdigit() else env[var.length]
                    if len(value) != want:
                        return False
                if var.kind == "matrix" and any(len(row) != columns[var.name] for row in value):
                    return False
                if var.kind == "lines" and var.length and not var.length.isdigit() and len(value) != scaffold._count(var.length, env):
                    return False
                if var.kind == "matrix" and len(value) != scaffold._count(var.length, env):
                    return False
                if not _fits(value):
                    return False
        return True
    except (ValueError, KeyError, IndexError, TypeError):
        return False


def infer_input_schema(inputs: list[str], extended: bool = False, trailing: bool = False):
    """(schema text, grid columns, bare array names) that reads every given input, or None.

    The natural reading (separate values, lists that hang on a count) is tried on every candidate input first; only when
    none of them verifies is a line of numbers with no count read as a list of its own. `extended` adds the readings of
    `_schema_from` that are off by default (n-1 rows, text lines on a count); the question service never asks for them, so
    what it serves does not change, and the backend's own hand-written questions do.

    `trailing` (see `_schema_from`) is tried before all of those, and only reads a question differently when it verifies on every
    input; when it does not, the readings above are tried exactly as they are without it."""
    texts = list(dict.fromkeys(inputs))
    texts.sort(key=lambda t: (-t.strip("\n").count("\n"), -len(t)))
    for with_trailing in ((True, False) if trailing else (False,)):
        for phase_extended in ((False, True) if extended else (False,)):   # the extra readings only when none of the ordinary ones fits
            for bare_arrays in (False, True):
                for text in texts[:_MAX_TRIES]:
                    try:
                        built = _schema_from(text, bare_arrays, phase_extended, with_trailing)
                    except _Unsupported:
                        continue
                    if built and _verify(built[0], built[1], built[2], inputs):
                        return built
    return None


def _number(token: str) -> bool:
    return _is_int(token) and abs(int(token)) <= _LIMIT


def infer_output_schema(outputs: list[str], sample: Optional[str] = None) -> str:
    """The most specific output type the stored outputs fit; plain text always fits.

    The shape (one line or one per line) is read from the test outputs alone: a sample is often printed with its line
    breaks flattened. The sample only has to be made of the same kind of numbers."""
    texts = [o.strip() for o in outputs]
    sample_text = None if sample is None else sample.strip()
    if texts and all(_number(t) for t in texts) and (sample_text is None or _number(sample_text)):
        return "int"
    numbers = lambda t: bool(t) and all(_number(token) for token in t.split())
    if texts and all(numbers(t) for t in texts) and (sample_text is None or numbers(sample_text)):
        if all("\n" not in t for t in texts):
            return "int[]"
        if all(len(line.split()) == 1 for t in texts for line in t.split("\n")):
            return "int[]/lines"
    return "str"


def describe_input(schema, columns: dict, bare: set = frozenset()) -> str:
    lines = []
    for number, line in enumerate(schema, 1):
        lead = "First line" if number == 1 else "Then"
        if len(line) > 1:
            kind = "integers" if all(v.base == "int" for v in line) else "values"
            lines.append(f"{lead}: the {kind} {', '.join(v.name for v in line)}.")
            continue
        v = line[0]
        if v.kind == "scalar":
            lines.append(f"{lead}: the {'integer' if v.base == 'int' else 'string'} {v.name}.")
        elif v.kind == "array" and v.name in bare:
            lines.append(f"{lead}: one line of integers, the list {v.name}.")
        elif v.kind == "array":
            lines.append(f"{lead}: {v.length} {'integers' if v.base == 'int' else 'words'}, the list {v.name}.")
        elif v.kind == "lines":
            lines.append(f"{lead}: {v.length} lines, each with one {'integer' if v.base == 'int' else 'string'}, the list {v.name}.")
        else:
            lines.append(f"{lead}: {v.length} lines of {columns.get(v.name, 'several')} integers each, the grid {v.name}.")
    return "\n".join(lines)


_OUTPUT_TEXT = {
    "int": "One integer: the answer.",
    "int[]": "The answers on one line, separated by spaces.",
    "int[]/lines": "The answers, one per line.",
    "str": "The answer exactly as the problem asks, as text (use a line break between lines when it has several).",
}
_RETURN_TEXT = {
    "int": "The answer to the problem",
    "int[]": "The answers, in the order the problem asks for them",
    "int[]/lines": "The answers, in the order the problem asks for them",
    "str": "The text to print, exactly as the problem asks, with a line break between lines",
}


_LAST_LINE = re.compile(r"\b(?:last|final)\s+line\b", re.IGNORECASE)


def type_question(tests: list[tuple[str, str]], sample_input: str, sample_output: str, extended: bool = False, input_format: str = "") -> Optional[dict]:
    """The fields to add to an older-bank question so it carries a locked-down, correct starter, or None.

    `tests` are (stdin text, stdout text) pairs. Nothing is returned unless the structure read from the inputs parses every
    stored input and the outputs fit one type. `extended` is described at infer_input_schema.

    `input_format` is the question's own description of its input. It is read for one thing only: when it says "last line", the
    values on the last line are read after the rows above them (`trailing`, described at _schema_from), a choice the tests alone
    cannot make. It never changes a reading that does not fit every test."""
    try:
        if not tests:
            return None
        inputs = [t[0] for t in tests] + [sample_input]
        built = infer_input_schema(inputs, extended, bool(_LAST_LINE.search(input_format or "")))
        if built is None:
            return None
        schema_text, columns, bare = built
        out_text = infer_output_schema([t[1] for t in tests], sample_output)
        schema = scaffold.parse_input_schema(schema_text)
        out = scaffold.parse_output_schema(out_text)
        sample_args = scaffold.parse_input_text(schema, sample_input)
        return {
            "input_schema": schema_text,
            "output_schema": out_text,
            "function_name": FUNCTION_NAME,
            "parameters": scaffold.parameters(schema, sample_args),
            "return_type": scaffold.type_name(out),
            "return_description": _RETURN_TEXT[out_text],
            "starter_code": scaffold.starter_code(schema, out, FUNCTION_NAME),
            "input_format": describe_input(schema, columns, bare),
            "output_format": _OUTPUT_TEXT[out_text],
        }
    except (ValueError, KeyError, IndexError, TypeError, _Unsupported):
        return None
