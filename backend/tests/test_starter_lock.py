"""The server holds the locked harness: whatever the client sends below the marker is replaced, and the signature must stay.

Run from the backend folder:  python -m pytest tests/test_starter_lock.py -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services import starter_lock as lock

MARK = "You do not need to edit below"
PYTHON = (
    "import sys\n\n\ndef solve(n, arr):\n    # Write your logic here\n    pass\n\n\n"
    f"# ===== Reads the input and prints the answer. {MARK}. =====\n"
    "def main():\n    n = int(input())\n    arr = list(map(int, input().split()))\n    print(solve(n, arr))\n\n\n"
    "if __name__ == '__main__':\n    main()\n"
)
JAVA = (
    "import java.util.*;\n\npublic class Solution {\n    static long solve(long n, long[] arr) {\n        // Write your logic here\n"
    "        return 0;\n    }\n\n"
    f"    // ===== Reads the input and prints the answer. {MARK}. =====\n"
    "    public static void main(String[] args) {\n        System.out.println(solve(1, new long[0]));\n    }\n}\n"
)
STORED = {"python": PYTHON, "java": JAVA}


def mine(text, **replace):
    for old, new in replace.items():
        text = text.replace(old, new)
    return text


def test_the_players_part_is_kept_and_the_stored_harness_follows():
    sent = PYTHON.replace("    pass\n", "    return sum(arr)\n", 1)
    assert lock.enforce(sent, "python", STORED) == sent


def test_a_changed_harness_is_replaced_by_the_stored_one():
    cheating = PYTHON.replace("print(solve(n, arr))", "print(42)")
    served = lock.enforce(cheating, "python", STORED)
    assert "print(42)" not in served and "print(solve(n, arr))" in served
    assert served == PYTHON


def test_anything_added_after_the_harness_is_dropped():
    assert lock.enforce(PYTHON + "\nimport os\nos.system('x')\n", "python", STORED) == PYTHON


def test_helpers_and_imports_above_the_signature_are_allowed():
    sent = PYTHON.replace("import sys\n", "import sys\nfrom collections import deque\n\n\ndef helper(x):\n    return x\n", 1)
    assert lock.enforce(sent, "python", STORED) == sent


def test_a_changed_signature_is_refused():
    with pytest.raises(lock.LockedHarnessError, match="signature"):
        lock.enforce(PYTHON.replace("def solve(n, arr):", "def solve(n):"), "python", STORED)
    with pytest.raises(lock.LockedHarnessError, match="signature"):
        lock.enforce(JAVA.replace("long[] arr", "int[] arr"), "java", STORED)


def test_a_removed_marker_is_refused_instead_of_run_with_the_players_own_harness():
    own = "def solve(n, arr):\n    return 1\n\nprint(solve(1, [1]))\n"
    with pytest.raises(lock.LockedHarnessError, match="locked part"):
        lock.enforce(own, "python", STORED)


def test_java_indentation_and_the_closing_braces_come_from_the_stored_harness():
    cheating = JAVA.replace("System.out.println(solve(1, new long[0]));", "System.out.println(7);")
    assert lock.enforce(cheating, "java", STORED) == JAVA


def test_windows_line_endings_from_the_client_are_fine():
    assert lock.enforce(PYTHON.replace("\n", "\r\n"), "python", STORED) == PYTHON


def test_questions_without_a_locked_starter_are_left_alone():
    anything = "print('hello')\n"
    assert lock.enforce(anything, "python", None) == anything
    assert lock.enforce(anything, "python", {"python": "def solve():\n    pass\n"}) == anything     # older starter, no marker
    assert lock.enforce(anything, "cpp", STORED) == anything                                          # no starter in that language
    assert lock.enforce(anything, "python", "not json at all") == anything
    assert lock.enforce(anything, "python", json.dumps([1, 2])) == anything


def test_the_starter_may_come_from_the_database_as_a_json_string():
    cheating = PYTHON.replace("print(solve(n, arr))", "print(42)")
    assert lock.enforce(cheating, "python", json.dumps(STORED)) == PYTHON
