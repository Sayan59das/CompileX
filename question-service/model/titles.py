"""One definition of "the same title", shared by every question bank.

The backend remembers what a player has seen as normalised titles (lowercase, trimmed, every run of
whitespace collapsed to one space) and sends that list back as exclude_titles. A bank that compares
raw titles never matches a stored title with a double space in it, so that question could be served again.
"""
import re


def normalize_title(title) -> str:
    return re.sub(r"\s+", " ", str(title or "").strip().lower())
