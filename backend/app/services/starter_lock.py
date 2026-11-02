"""The server's half of the locked starter code.

The editor stops a player from changing the harness (the code under the marker line that reads the input, calls their function
and prints its result), but that only guards against accidents: the browser is the player's. For a question the server holds
this module makes the lock real. Before graded code is run:

  * everything from the marker line to the end is replaced by the stored starter's version, so whatever the client sent there
    is ignored;
  * the function signature line (the line above the "Write your logic here" note) must still be present above the marker, so
    the arguments the harness passes in cannot be changed;
  * a submission with the marker line removed is refused, rather than run with a harness of the player's own.

Questions whose stored starter has no marker (older, guessed starters) are left exactly as they are.

What this does not do: it cannot stop code above the marker from misbehaving (that is the sandbox's job), and a question the
client created itself (a Practice question) carries whatever starter the client stored, so there is nothing for the server to
hold it to.
"""

import json
from typing import Any, Optional

MARKER = "You do not need to edit below"
LOGIC_NOTE = "Write your logic here"


class LockedHarnessError(ValueError):
    """The submitted code broke the locked part of the starter code."""


def _lines(text: str) -> list[str]:
    return (text or "").replace("\r\n", "\n").split("\n")


def _stored_starter(starter_code: Any, language: str) -> Optional[str]:
    data = starter_code
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return None
    if not isinstance(data, dict):
        return None
    text = data.get(language)
    return text if isinstance(text, str) else None


def enforce(code: str, language: str, starter_code: Any) -> str:
    """The code to run: the player's part (above the marker) followed by the stored harness.

    Raises LockedHarnessError when the signature was changed or the marker was removed."""
    stored = _stored_starter(starter_code, language)
    if not stored:
        return code
    stored_lines = _lines(stored)
    stored_marker = next((i for i, line in enumerate(stored_lines) if MARKER in line), None)
    if stored_marker is None:
        return code    # a starter without a locked harness: nothing to hold the code to

    note = next((i for i, line in enumerate(stored_lines) if LOGIC_NOTE in line and i < stored_marker), None)
    signature = stored_lines[note - 1] if note and stored_lines[note - 1].strip() else None

    sent_lines = _lines(code)
    sent_marker = next((i for i, line in enumerate(sent_lines) if MARKER in line), None)
    if sent_marker is None:
        raise LockedHarnessError(
            "The locked part of the starter code was removed. Reload the starter code and write your logic above the line "
            f"that says \"{MARKER}\"."
        )
    head = sent_lines[:sent_marker]
    if signature is not None and signature not in head:
        raise LockedHarnessError(f"The function signature was changed. It must stay exactly: {signature.strip()}")
    return "\n".join(head + stored_lines[stored_marker:])
