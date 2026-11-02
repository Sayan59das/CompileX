"""Independent check of the cost analysis on Python: run each program at growing sizes, count the lines it executes
(deterministic, no timing noise), fit the growth, and require the analysis to agree.

The programs are written to be unlike the ones the analysis was tuned on. Run from the backend folder:
    python -m pytest tests/test_complexity_oracle.py -q
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.setrecursionlimit(1_000_000)

import pytest

from app.services.complexity import analyze_source

MODELS = {
    "O(1)": lambda n: 1.0,
    "O(log n)": lambda n: math.log2(n),
    "O(n)": lambda n: n,
    "O(n log n)": lambda n: n * math.log2(n),
    "O(n²)": lambda n: n * n,
    "O(n² log n)": lambda n: n * n * math.log2(n),
    "O(n³)": lambda n: n ** 3,
}


def count_lines(code, entry, args):
    ns = {}
    exec(compile(code, "<prog>", "exec"), ns)
    f = ns[entry]
    count = 0

    def tracer(frame, event, arg):
        nonlocal count
        if frame.f_code.co_filename != "<prog>":
            return None
        if event == "line":
            count += 1
        return tracer

    sys.settrace(tracer)
    try:
        f(*args)
    finally:
        sys.settrace(None)
    return count


def fit(sizes, values):
    best, best_residual = None, float("inf")
    for name, model in MODELS.items():
        diffs = [math.log(max(v, 1e-12)) - math.log(model(s)) for s, v in zip(sizes, values)]
        mean = sum(diffs) / len(diffs)
        residual = sum((d - mean) ** 2 for d in diffs)
        if residual < best_residual:
            best, best_residual = name, residual
    return best


def arr(n, rng, hi=10**6):
    return [rng.randint(0, hi) for _ in range(n)]


PROGRAMS = []


def prog(name, code, entry, gen, mode="lines", sizes=None, ok=None):
    PROGRAMS.append((name, code, entry, gen, sizes or [64, 128, 256, 512], ok))


prog("bubble sort", """
def f(a):
    a = list(a)
    n = len(a)
    for i in range(n):
        for j in range(n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a
""", "f", lambda n, r: (arr(n, r),))
prog("insertion sort", """
def f(a):
    a = list(a)
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a
""", "f", lambda n, r: (arr(n, r),))
prog("selection sort", """
def f(a):
    a = list(a)
    n = len(a)
    for i in range(n):
        m = i
        for j in range(i + 1, n):
            if a[j] < a[m]:
                m = j
        a[i], a[m] = a[m], a[i]
    return a
""", "f", lambda n, r: (arr(n, r),))
prog("prefix sums", """
def f(a):
    p = [0] * (len(a) + 1)
    for i, x in enumerate(a):
        p[i + 1] = p[i] + x
    return p[-1]
""", "f", lambda n, r: (arr(n, r),))
prog("frequency dict", """
def f(a):
    c = {}
    for x in a:
        c[x] = c.get(x, 0) + 1
    best = 0
    for k in c:
        best = max(best, c[k])
    return best
""", "f", lambda n, r: (arr(n, r, 50),))
prog("two pointers sorted", """
def f(a, t):
    l, r = 0, len(a) - 1
    c = 0
    while l < r:
        s = a[l] + a[r]
        if s == t:
            c += 1
            l += 1
            r -= 1
        elif s < t:
            l += 1
        else:
            r -= 1
    return c
""", "f", lambda n, r: (sorted(arr(n, r)), 5 * 10**5))
prog("monotonic stack next greater", """
def f(a):
    res = [-1] * len(a)
    st = []
    for i in range(len(a)):
        while st and a[st[-1]] < a[i]:
            res[st.pop()] = a[i]
        st.append(i)
    return res
""", "f", lambda n, r: (arr(n, r),))
prog("sliding window sum", """
def f(a, k):
    s = sum(a[:k])
    best = s
    for i in range(k, len(a)):
        s += a[i] - a[i - k]
        best = max(best, s)
    return best
""", "f", lambda n, r: (arr(n, r), 10))
prog("longest increasing subsequence dp", """
def f(a):
    n = len(a)
    dp = [1] * n
    for i in range(n):
        for j in range(i):
            if a[j] < a[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)
""", "f", lambda n, r: (arr(n, r),))
prog("sieve of eratosthenes", """
def f(n):
    s = [True] * (n + 1)
    for i in range(2, n + 1):
        if s[i]:
            for j in range(i * i, n + 1, i):
                s[j] = False
    return sum(s)
""", "f", lambda n, r: (n,), ok={"O(n)", "O(n log n)"})
prog("binary search n times", """
def f(a, qs):
    out = 0
    for q in qs:
        lo, hi = 0, len(a) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if a[mid] < q:
                lo = mid + 1
            else:
                hi = mid - 1
        out += lo
    return out
""", "f", lambda n, r: (sorted(arr(n, r)), arr(n, r)))
prog("naive fib memo dict", """
def f(n):
    memo = {}
    def fib(k):
        if k < 2:
            return k
        if k in memo:
            return memo[k]
        memo[k] = fib(k - 1) + fib(k - 2)
        return memo[k]
    return fib(n)
""", "f", lambda n, r: (n,), sizes=[32, 64, 128, 256, 512])
prog("power by squaring", """
def f(b, e):
    r = 1
    while e > 0:
        if e & 1:
            r = r * b % 1000003
        b = b * b % 1000003
        e >>= 1
    return r
""", "f", lambda n, r: (3, n), sizes=[2**8, 2**12, 2**16, 2**20, 2**24, 2**28])
prog("matrix multiply", """
def f(n):
    a = [[1] * n for _ in range(n)]
    b = [[2] * n for _ in range(n)]
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                c[i][j] += a[i][k] * b[k][j]
    return c[0][0]
""", "f", lambda n, r: (n,), sizes=[8, 12, 16, 24, 32, 48])
prog("triangular loops", """
def f(n):
    c = 0
    for i in range(n):
        for j in range(i):
            c += 1
    return c
""", "f", lambda n, r: (n,))
prog("loops with constant inner", """
def f(n):
    c = 0
    for i in range(n):
        for j in range(n):
            for k in range(10):
                c += 1
    return c
""", "f", lambda n, r: (n,), sizes=[8, 16, 32, 64, 128, 256])
prog("independent constant loop", """
def f(n):
    c = 0
    for i in range(1000):
        c += i
    return c
""", "f", lambda n, r: (n,))
prog("two sequential loops", """
def f(a):
    c = 0
    for x in a:
        c += x
    for x in a:
        c -= x
    return c
""", "f", lambda n, r: (arr(n, r),))
prog("parentheses stack", """
def f(s):
    st = []
    for ch in s:
        if ch == '(':
            st.append(ch)
        elif st:
            st.pop()
    return len(st)
""", "f", lambda n, r: ("".join(r.choice("()") for _ in range(n)),))
prog("grid bfs", """
from collections import deque
def f(n):
    seen = [[False] * n for _ in range(n)]
    q = deque([(0, 0)])
    seen[0][0] = True
    c = 0
    while q:
        x, y = q.popleft()
        c += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and not seen[nx][ny]:
                seen[nx][ny] = True
                q.append((nx, ny))
    return c
""", "f", lambda n, r: (n,), sizes=[8, 16, 32, 48, 64])
prog("graph bfs adjacency list", """
from collections import deque
def f(adj):
    n = len(adj)
    seen = [False] * n
    q = deque([0])
    seen[0] = True
    c = 0
    while q:
        u = q.popleft()
        c += 1
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                q.append(v)
    return c
""", "f", lambda n, r: ([[ (i + 1) % n, (i * 7 + 3) % n] for i in range(n)],))
prog("recursive binary search", """
def f(a, x):
    def go(lo, hi):
        if lo > hi:
            return -1
        mid = (lo + hi) // 2
        if a[mid] == x:
            return mid
        if a[mid] < x:
            return go(mid + 1, hi)
        return go(lo, mid - 1)
    return go(0, len(a) - 1)
""", "f", lambda n, r: (list(range(n)), n + 5), sizes=[2**8, 2**10, 2**12, 2**14, 2**16, 2**18])
prog("subsets recursion", """
def f(n):
    out = []
    def go(i, cur):
        if i == n:
            out.append(1)
            return
        go(i + 1, cur)
        cur.append(i)
        go(i + 1, cur)
        cur.pop()
    go(0, [])
    return len(out)
""", "f", lambda n, r: (n,), sizes=[8, 10, 12, 14, 16], ok={"EXP"})
prog("naive fib", """
def f(n):
    if n < 2:
        return n
    return f(n - 1) + f(n - 2)
""", "f", lambda n, r: (n,), sizes=[10, 12, 14, 16, 18], ok={"EXP"})
prog("linear recursion sum", """
def f(a, i=0):
    if i == len(a):
        return 0
    return a[i] + f(a, i + 1)
""", "f", lambda n, r: (arr(n, r),))
prog("set membership in loop", """
def f(a):
    seen = set()
    c = 0
    for x in a:
        if x in seen:
            c += 1
        seen.add(x)
    return c
""", "f", lambda n, r: (arr(n, r, 10**9),))
prog("helper called n times", """
def f(a):
    def total(x):
        s = 0
        for v in x:
            s += v
        return s
    t = 0
    for i in range(len(a)):
        t += total(a)
    return t
""", "f", lambda n, r: (arr(n, r),))
prog("string palindrome two pointers", """
def f(s):
    i, j = 0, len(s) - 1
    while i < j:
        if s[i] != s[j]:
            return False
        i += 1
        j -= 1
    return True
""", "f", lambda n, r: ("a" * n,))
prog("count substrings expand", """
def f(s):
    n = len(s)
    c = 0
    for center in range(n):
        l = r = center
        while l >= 0 and r < n and s[l] == s[r]:
            c += 1
            l -= 1
            r += 1
    return c
""", "f", lambda n, r: ("a" * n,))
prog("while i += i", """
def f(n):
    i = 1
    c = 0
    while i < n:
        i += i
        c += 1
    return c
""", "f", lambda n, r: (n,), sizes=[2**8, 2**12, 2**16, 2**20, 2**24])
prog("while i = i * 3", """
def f(n):
    i = 1
    c = 0
    while i < n:
        i = i * 3
        c += 1
    return c
""", "f", lambda n, r: (n,), sizes=[2**8, 2**12, 2**16, 2**20, 2**24])
prog("two arrays two params", """
def f(a, b):
    c = 0
    for x in a:
        for y in b:
            if x == y:
                c += 1
    return c
""", "f", lambda n, r: (arr(n, r, 10**9), arr(n, r, 10**9)), sizes=[32, 64, 128, 256, 512])
prog("kadane", """
def f(a):
    best = cur = a[0]
    for i in range(1, len(a)):
        cur = max(a[i], cur + a[i])
        best = max(best, cur)
    return best
""", "f", lambda n, r: (arr(n, r),))
prog("knapsack 2d dp", """
def f(w, v, cap):
    n = len(w)
    dp = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for c in range(cap + 1):
            dp[i][c] = dp[i - 1][c]
            if w[i - 1] <= c:
                dp[i][c] = max(dp[i][c], dp[i - 1][c - w[i - 1]] + v[i - 1])
    return dp[n][cap]
""", "f", lambda n, r: ([r.randint(1, 20) for _ in range(n)], [r.randint(1, 20) for _ in range(n)], n), sizes=[16, 24, 32, 48, 64])


@pytest.mark.parametrize("name,code,entry,gen,sizes,ok", PROGRAMS, ids=[p[0] for p in PROGRAMS])
def test_the_analysis_agrees_with_what_the_program_does(name, code, entry, gen, sizes, ok):
    counts = [count_lines(code, entry, gen(n, random.Random(n))) for n in sizes]
    measured = fit(sizes, counts)
    r = analyze_source(code, "python", debug=True)
    assert r is not None
    said = r.time.fmt()
    if ok is not None:
        assert said in ok or ("EXP" in ok and said == "O(2^n)"), (said, measured)
    else:
        assert said == measured, (said, measured, counts)
