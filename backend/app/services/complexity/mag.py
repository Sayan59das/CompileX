"""The algebra the cost analysis works in: n^a * (log n)^b, or exponential.

A `Mag` is the growth of a quantity (iterations of a loop, time of a block, size of a list) in the input size n. Sums of
terms keep the dominant one (`maxm`), products add exponents (`*`), and `sqrt` / `log` of a magnitude are what loops that
square, halve or double a counter run for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

_SUP = {2: "²", 3: "³"}


@dataclass(frozen=True)
class Mag:
    a: Fraction = Fraction(0)   # exponent of n
    b: int = 0                  # exponent of log n
    exp: bool = False           # exponential in n: dominates every polynomial

    # ── ordering and algebra ───────────────────────────────────────────────
    def key(self):
        return (1 if self.exp else 0, self.a, self.b)

    def __lt__(self, other: "Mag") -> bool:
        return self.key() < other.key()

    def __le__(self, other: "Mag") -> bool:
        return self.key() <= other.key()

    def __mul__(self, other: "Mag") -> "Mag":
        if self.exp or other.exp:
            return EXP
        return Mag(self.a + other.a, self.b + other.b)

    def pow(self, k: int) -> "Mag":
        if self.exp:
            return EXP
        return Mag(self.a * k, self.b * k)

    def sqrt(self) -> "Mag":
        if self.exp:
            return EXP
        return Mag(self.a / 2, self.b // 2 if self.b % 2 == 0 else self.b)

    def log(self) -> "Mag":
        """log of a quantity of this magnitude: log(n^a) = Theta(log n); the log of a constant is a constant."""
        if self.exp:
            return N
        if self.a > 0:
            return LOG
        return ONE

    @property
    def is_const(self) -> bool:
        return not self.exp and self.a == 0 and self.b == 0

    # ── printing ───────────────────────────────────────────────────────────
    def fmt(self) -> str:
        if self.exp:
            return "O(2^n)"
        a, b = self.a, self.b
        parts = []
        if a != 0:
            if a == 1:
                parts.append("n")
            elif a.denominator == 1:
                k = a.numerator
                parts.append("n" + _SUP[k] if k in _SUP else f"n^{k}")
            elif a == Fraction(1, 2):
                parts.append("sqrt n")
            elif a.denominator == 2:
                whole = int(a - Fraction(1, 2))
                parts.append((("n" + _SUP.get(whole, f"^{whole}")) if whole > 1 else "n") + " sqrt n")
            else:
                parts.append(f"n^({a.numerator}/{a.denominator})")
        if b == 1:
            parts.append("log n")
        elif b > 1:
            parts.append(f"log{_SUP.get(b, '^' + str(b))} n")
        return "O(" + (" ".join(parts) if parts else "1") + ")"

    def __repr__(self) -> str:
        return self.fmt()


ONE = Mag()
N = Mag(Fraction(1))
LOG = Mag(Fraction(0), 1)
EXP = Mag(Fraction(0), 0, True)


def maxm(*mags: Mag) -> Mag:
    best = ONE
    for m in mags:
        if best < m:
            best = m
    return best


def minm(x: Mag, y: Mag) -> Mag:
    return x if x <= y else y


def product(mags) -> Mag:
    out = ONE
    for m in mags:
        out = out * m
    return out


_SUP_REV = {"²": 2, "³": 3}


def _exponent(tail: str) -> int:
    """The exponent written after `n` or `log`: a superscript (²), `^4`, or nothing (1)."""
    if tail in _SUP_REV:
        return _SUP_REV[tail]
    digits = tail.lstrip("^")
    return int(digits) if digits.isascii() and digits.isdigit() else 1


def parse_o(text: str) -> Optional[Mag]:
    """Inverse of fmt(); None for anything that is not one of the strings fmt() produces."""
    m = re.fullmatch(r"O\((.*)\)", text.strip())
    if not m:
        return None
    body = m.group(1).strip()
    if body == "2^n":
        return EXP
    if body == "1":
        return ONE
    a, b = Fraction(0), 0
    tokens = body.replace("sqrt n", "SQRT").split()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == "SQRT":
            a += Fraction(1, 2)
        elif t == "log":
            b += 1
            i += 1                      # the following "n"
        elif t.startswith("log"):
            b += _exponent(t[3:])
        elif t.startswith("n"):
            a += Fraction(_exponent(t[1:]))
        else:
            return None
        i += 1
    return Mag(a, b)
