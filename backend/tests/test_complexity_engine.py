"""The cost analysis (backend/app/services/complexity): what it says for typical solutions in all five languages, and how it
explains and qualifies its answer.

Run from the backend folder:  python -m pytest tests/test_complexity_engine.py -q
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.complexity import analyze_source
from app.services.complexity.mag import EXP, LOG, N, ONE, Mag, maxm, parse_o
from app.services.complexity_analyzer import ComplexityAnalyzer, _rank


# (name, language, code, worst time, worst space or None when either answer is defensible)
PROGRAMS = [
    ('bubble sort', 'cpp', r'''
vector<int> f(vector<int> a) {
    int n = a.size();
    for (int i = 0; i < n; i++)
        for (int j = 0; j + 1 < n - i; j++)
            if (a[j] > a[j + 1]) swap(a[j], a[j + 1]);
    return a;
}''', 'O(n²)', None),
    ('bubble sort', 'java', r'''
class S {
    static int[] f(int[] a) {
        int n = a.length;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j + 1 < n - i; j++) {
                if (a[j] > a[j + 1]) { int t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
            }
        }
        return a;
    }
}''', 'O(n²)', 'O(1)'),
    ('bubble sort', 'javascript', r'''
function f(a) {
    const n = a.length;
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - 1 - i; j++) {
            if (a[j] > a[j + 1]) { [a[j], a[j + 1]] = [a[j + 1], a[j]]; }
        }
    }
    return a;
}''', 'O(n²)', 'O(1)'),
    ('bubble sort', 'c', r'''
void f(long long* a, long long n) {
    for (long long i = 0; i < n; i++)
        for (long long j = 0; j + 1 < n - i; j++)
            if (a[j] > a[j + 1]) { long long t = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
}''', 'O(n²)', 'O(1)'),
    ('insertion sort', 'cpp', r'''
void f(vector<int>& a) {
    for (int i = 1; i < (int)a.size(); i++) {
        int key = a[i], j = i - 1;
        while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
        a[j + 1] = key;
    }
}''', 'O(n²)', 'O(1)'),
    ('insertion sort', 'java', r'''
class S {
    static void f(int[] a) {
        for (int i = 1; i < a.length; i++) {
            int key = a[i], j = i - 1;
            while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
            a[j + 1] = key;
        }
    }
}''', 'O(n²)', 'O(1)'),
    ('insertion sort', 'javascript', r'''
function f(a) {
    for (let i = 1; i < a.length; i++) {
        const key = a[i];
        let j = i - 1;
        while (j >= 0 && a[j] > key) { a[j + 1] = a[j]; j--; }
        a[j + 1] = key;
    }
}''', 'O(n²)', 'O(1)'),
    ('frequency map', 'cpp', r'''
int f(const vector<int>& a) {
    unordered_map<int, int> c;
    int best = 0;
    for (int x : a) { c[x]++; best = max(best, c[x]); }
    return best;
}''', 'O(n)', 'O(n)'),
    ('frequency map', 'java', r'''
class S {
    static int f(int[] a) {
        Map<Integer, Integer> c = new HashMap<>();
        int best = 0;
        for (int x : a) {
            c.put(x, c.getOrDefault(x, 0) + 1);
            best = Math.max(best, c.get(x));
        }
        return best;
    }
}''', 'O(n)', 'O(n)'),
    ('frequency map', 'javascript', r'''
function f(a) {
    const c = new Map();
    let best = 0;
    for (const x of a) {
        c.set(x, (c.get(x) || 0) + 1);
        best = Math.max(best, c.get(x));
    }
    return best;
}''', 'O(n)', 'O(n)'),
    ('ordered map counts', 'cpp', r'''
int f(const vector<int>& a) {
    map<int, int> c;
    for (int x : a) c[x]++;
    return c.size();
}''', 'O(n log n)', 'O(n)'),
    ('two pointers', 'cpp', r'''
int f(vector<int>& a, int t) {
    int l = 0, r = (int)a.size() - 1, c = 0;
    while (l < r) {
        int s = a[l] + a[r];
        if (s == t) { c++; l++; r--; }
        else if (s < t) l++;
        else r--;
    }
    return c;
}''', 'O(n)', 'O(1)'),
    ('two pointers', 'java', r'''
class S {
    static int f(int[] a, int t) {
        int l = 0, r = a.length - 1, c = 0;
        while (l < r) {
            int s = a[l] + a[r];
            if (s == t) { c++; l++; r--; }
            else if (s < t) l++;
            else r--;
        }
        return c;
    }
}''', 'O(n)', 'O(1)'),
    ('two pointers', 'javascript', r'''
function f(a, t) {
    let l = 0, r = a.length - 1, c = 0;
    while (l < r) {
        const s = a[l] + a[r];
        if (s === t) { c++; l++; r--; }
        else if (s < t) l++;
        else r--;
    }
    return c;
}''', 'O(n)', 'O(1)'),
    ('monotonic stack', 'cpp', r'''
vector<int> f(vector<int>& a) {
    int n = a.size();
    vector<int> res(n, -1);
    stack<int> st;
    for (int i = 0; i < n; i++) {
        while (!st.empty() && a[st.top()] < a[i]) { res[st.top()] = a[i]; st.pop(); }
        st.push(i);
    }
    return res;
}''', 'O(n)', 'O(n)'),
    ('monotonic stack', 'java', r'''
class S {
    static int[] f(int[] a) {
        int n = a.length;
        int[] res = new int[n];
        Arrays.fill(res, -1);
        Deque<Integer> st = new ArrayDeque<>();
        for (int i = 0; i < n; i++) {
            while (!st.isEmpty() && a[st.peek()] < a[i]) { res[st.pop()] = a[i]; }
            st.push(i);
        }
        return res;
    }
}''', 'O(n)', 'O(n)'),
    ('monotonic stack', 'javascript', r'''
function f(a) {
    const n = a.length;
    const res = new Array(n).fill(-1);
    const st = [];
    for (let i = 0; i < n; i++) {
        while (st.length > 0 && a[st[st.length - 1]] < a[i]) { res[st.pop()] = a[i]; }
        st.push(i);
    }
    return res;
}''', 'O(n)', 'O(n)'),
    ('lis dp', 'cpp', r'''
int f(vector<int>& a) {
    int n = a.size();
    vector<int> dp(n, 1);
    int best = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < i; j++) if (a[j] < a[i]) dp[i] = max(dp[i], dp[j] + 1);
        best = max(best, dp[i]);
    }
    return best;
}''', 'O(n²)', 'O(n)'),
    ('lis dp', 'java', r'''
class S {
    static int f(int[] a) {
        int n = a.length;
        int[] dp = new int[n];
        Arrays.fill(dp, 1);
        int best = 0;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < i; j++) if (a[j] < a[i]) dp[i] = Math.max(dp[i], dp[j] + 1);
            best = Math.max(best, dp[i]);
        }
        return best;
    }
}''', 'O(n²)', 'O(n)'),
    ('lis dp', 'javascript', r'''
function f(a) {
    const n = a.length;
    const dp = new Array(n).fill(1);
    let best = 0;
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < i; j++) if (a[j] < a[i]) dp[i] = Math.max(dp[i], dp[j] + 1);
        best = Math.max(best, dp[i]);
    }
    return best;
}''', 'O(n²)', 'O(n)'),
    ('grid dp', 'cpp', r'''
int f(vector<vector<int>>& g) {
    int n = g.size(), m = g[0].size();
    vector<vector<int>> dp(n, vector<int>(m, 0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            dp[i][j] = g[i][j] + max(i ? dp[i-1][j] : 0, j ? dp[i][j-1] : 0);
    return dp[n-1][m-1];
}''', 'O(n²)', 'O(n²)'),
    ('sieve', 'cpp', r'''
int f(int n) {
    vector<bool> s(n + 1, true);
    int c = 0;
    for (int i = 2; i <= n; i++) {
        if (s[i]) { c++; for (long long j = (long long)i * i; j <= n; j += i) s[j] = false; }
    }
    return c;
}''', 'O(n log n)', 'O(n)'),
    ('binary search', 'cpp', r'''
int f(vector<int>& a, int x) {
    int lo = 0, hi = (int)a.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == x) return mid;
        if (a[mid] < x) lo = mid + 1; else hi = mid - 1;
    }
    return -1;
}''', 'O(log n)', 'O(1)'),
    ('binary search', 'java', r'''
class S {
    static int f(int[] a, int x) {
        int lo = 0, hi = a.length - 1;
        while (lo <= hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] == x) return mid;
            if (a[mid] < x) lo = mid + 1; else hi = mid - 1;
        }
        return -1;
    }
}''', 'O(log n)', 'O(1)'),
    ('binary search', 'javascript', r'''
function f(a, x) {
    let lo = 0, hi = a.length - 1;
    while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        if (a[mid] === x) return mid;
        if (a[mid] < x) lo = mid + 1; else hi = mid - 1;
    }
    return -1;
}''', 'O(log n)', 'O(1)'),
    ('binary search n times', 'cpp', r'''
long long f(vector<int>& a, vector<int>& qs) {
    long long out = 0;
    for (int q : qs) out += lower_bound(a.begin(), a.end(), q) - a.begin();
    return out;
}''', 'O(n log n)', 'O(1)'),
    ('recursive binary search', 'cpp', r'''
int go(vector<int>& a, int lo, int hi, int x) {
    if (lo > hi) return -1;
    int mid = (lo + hi) / 2;
    if (a[mid] == x) return mid;
    if (a[mid] < x) return go(a, mid + 1, hi, x);
    return go(a, lo, mid - 1, x);
}
int f(vector<int>& a, int x) { return go(a, 0, (int)a.size() - 1, x); }''', 'O(log n)', None),
    ('fib memo', 'cpp', r'''
long long memo[100005];
long long fib(int k) {
    if (k < 2) return k;
    if (memo[k] != 0) return memo[k];
    return memo[k] = fib(k - 1) + fib(k - 2);
}
long long f(int n) { return fib(n); }''', 'O(n)', None),
    ('fib naive', 'java', r'''
class S {
    static long fib(int k) {
        if (k < 2) return k;
        return fib(k - 1) + fib(k - 2);
    }
}''', 'O(2^n)', None),
    ('fib naive', 'javascript', r'''
function fib(k) {
    if (k < 2) return k;
    return fib(k - 1) + fib(k - 2);
}''', 'O(2^n)', None),
    ('subsets', 'cpp', r'''
void go(int i, int n, vector<int>& cur, int& cnt) {
    if (i == n) { cnt++; return; }
    go(i + 1, n, cur, cnt);
    cur.push_back(i);
    go(i + 1, n, cur, cnt);
    cur.pop_back();
}
int f(int n) { vector<int> cur; int cnt = 0; go(0, n, cur, cnt); return cnt; }''', 'O(2^n)', None),
    ('merge sort', 'java', r'''
class S {
    static void ms(int[] a, int l, int r) {
        if (l >= r) return;
        int m = (l + r) / 2;
        ms(a, l, m);
        ms(a, m + 1, r);
        int[] tmp = new int[r - l + 1];
        int i = l, j = m + 1, k = 0;
        while (i <= m && j <= r) tmp[k++] = a[i] <= a[j] ? a[i++] : a[j++];
        while (i <= m) tmp[k++] = a[i++];
        while (j <= r) tmp[k++] = a[j++];
        for (int t = 0; t < tmp.length; t++) a[l + t] = tmp[t];
    }
    static void f(int[] a) { ms(a, 0, a.length - 1); }
}''', 'O(n log n)', 'O(n)'),
    ('linear recursion', 'javascript', r'''
function total(a, i) {
    if (i === a.length) return 0;
    return a[i] + total(a, i + 1);
}''', 'O(n)', 'O(n)'),
    ('bfs adjacency', 'cpp', r'''
int f(vector<vector<int>>& adj) {
    int n = adj.size();
    vector<bool> seen(n, false);
    queue<int> q;
    q.push(0); seen[0] = true;
    int c = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        c++;
        for (int v : adj[u]) if (!seen[v]) { seen[v] = true; q.push(v); }
    }
    return c;
}''', 'O(n)', 'O(n)'),
    ('bfs adjacency', 'java', r'''
class S {
    static int f(List<List<Integer>> adj) {
        int n = adj.size();
        boolean[] seen = new boolean[n];
        Deque<Integer> q = new ArrayDeque<>();
        q.add(0); seen[0] = true;
        int c = 0;
        while (!q.isEmpty()) {
            int u = q.poll();
            c++;
            for (int v : adj.get(u)) if (!seen[v]) { seen[v] = true; q.add(v); }
        }
        return c;
    }
}''', 'O(n)', 'O(n)'),
    ('bfs adjacency', 'javascript', r'''
function f(adj) {
    const n = adj.length;
    const seen = new Array(n).fill(false);
    const q = [0];
    seen[0] = true;
    let c = 0, head = 0;
    while (head < q.length) {
        const u = q[head++];
        c++;
        for (const v of adj[u]) if (!seen[v]) { seen[v] = true; q.push(v); }
    }
    return c;
}''', 'O(n)', 'O(n)'),
    ('dfs recursive', 'cpp', r'''
void dfs(int u, vector<vector<int>>& adj, vector<bool>& seen) {
    seen[u] = true;
    for (int v : adj[u]) if (!seen[v]) dfs(v, adj, seen);
}
int f(vector<vector<int>>& adj) {
    int n = adj.size();
    vector<bool> seen(n, false);
    int c = 0;
    for (int u = 0; u < n; u++) if (!seen[u]) { dfs(u, adj, seen); c++; }
    return c;
}''', 'O(n)', 'O(n)'),
    ('gcd euclid', 'cpp', r'''
long long g(long long a, long long b) { while (b) { long long t = a % b; a = b; b = t; } return a; }''', 'O(log n)', 'O(1)'),
    ('digit sum each', 'java', r'''
class S {
    static long f(int[] a) {
        long t = 0;
        for (int x : a) { while (x > 0) { t += x % 10; x /= 10; } }
        return t;
    }
}''', 'O(n log n)', 'O(1)'),
    ('palindrome', 'javascript', r'''
function f(s) {
    let i = 0, j = s.length - 1;
    while (i < j) { if (s[i] !== s[j]) return false; i++; j--; }
    return true;
}''', 'O(n)', 'O(1)'),
    ('sort then scan', 'cpp', r'''
int f(vector<int> a) {
    sort(a.begin(), a.end());
    int best = 0;
    for (int i = 1; i < (int)a.size(); i++) best = max(best, a[i] - a[i - 1]);
    return best;
}''', 'O(n log n)', None),
    ('sort then scan', 'javascript', r'''
function f(a) {
    const b = [...a].sort((x, y) => x - y);
    let best = 0;
    for (let i = 1; i < b.length; i++) best = Math.max(best, b[i] - b[i - 1]);
    return best;
}''', 'O(n log n)', 'O(n)'),
    ('contains in loop (java list)', 'java', r'''
class S {
    static int f(int[] a) {
        List<Integer> seen = new ArrayList<>();
        int c = 0;
        for (int x : a) { if (seen.contains(x)) c++; seen.add(x); }
        return c;
    }
}''', 'O(n²)', 'O(n)'),
    ('contains in loop (java set)', 'java', r'''
class S {
    static int f(int[] a) {
        Set<Integer> seen = new HashSet<>();
        int c = 0;
        for (int x : a) { if (seen.contains(x)) c++; seen.add(x); }
        return c;
    }
}''', 'O(n)', 'O(n)'),
    ('string concat in loop (java)', 'java', r'''
class S {
    static String f(int n) {
        String s = "";
        for (int i = 0; i < n; i++) s += "a";
        return s;
    }
}''', 'O(n²)', None),
    ('string builder (java)', 'java', r'''
class S {
    static String f(int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.append('a');
        return sb.toString();
    }
}''', 'O(n)', 'O(n)'),
    ('matrix multiply', 'cpp', r'''
vector<vector<long long>> f(vector<vector<long long>>& a, vector<vector<long long>>& b, int n) {
    vector<vector<long long>> c(n, vector<long long>(n, 0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            for (int k = 0; k < n; k++)
                c[i][j] += a[i][k] * b[k][j];
    return c;
}''', 'O(n³)', 'O(n²)'),
    ('malloc copy (c)', 'c', r'''
long long f(const long long* a, long long n) {
    long long* p = malloc(n * sizeof(long long));
    long long s = 0;
    for (long long i = 0; i < n; i++) { p[i] = a[i]; s += p[i]; }
    free(p);
    return s;
}''', 'O(n)', 'O(n)'),
]


def result(code: str, lang: str):
    r = analyze_source(code, lang, debug=True)
    assert r is not None, "the code could not be analyzed"
    return r


@pytest.mark.parametrize("name,lang,code,time,space", PROGRAMS, ids=[f"{n}-{l}" for n, l, *_ in PROGRAMS])
def test_typical_solutions(name, lang, code, time, space):
    r = result(code, lang)
    assert r.time.fmt() == time
    if space is not None:
        assert r.space.fmt() == space


# ── the algebra ─────────────────────────────────────────────────────────────

def test_magnitudes_multiply_add_and_print():
    assert (N * N).fmt() == "O(n²)"
    assert (N * LOG).fmt() == "O(n log n)"
    assert (N * N * N).fmt() == "O(n³)"
    assert N.pow(4).fmt() == "O(n^4)"
    assert N.sqrt().fmt() == "O(sqrt n)"
    assert (N * N.sqrt()).fmt() == "O(n sqrt n)"
    assert ONE.fmt() == "O(1)" and EXP.fmt() == "O(2^n)"
    assert maxm(N, LOG * LOG, ONE) == N and maxm(N * LOG, N) == N * LOG and maxm(EXP, N * N * N) == EXP
    assert N.log() == LOG and ONE.log() == ONE


@pytest.mark.parametrize("text", ["O(1)", "O(log n)", "O(sqrt n)", "O(n)", "O(n log n)", "O(n²)", "O(n² log n)", "O(n³)", "O(n^4)",
                                  "O(n sqrt n)", "O(2^n)"])
def test_every_printed_magnitude_parses_back(text):
    assert parse_o(text).fmt() == text


def test_ranking_orders_the_new_strings():
    order = ["O(1)", "O(log n)", "O(sqrt n)", "O(n)", "O(n log n)", "O(n sqrt n)", "O(n²)", "O(n² log n)", "O(n³)", "O(n^4)", "O(2^n)"]
    ranks = [_rank(o) for o in order]
    assert ranks == sorted(ranks) and ranks[0] < ranks[-1]


# ── explanation and confidence ──────────────────────────────────────────────

def test_a_clear_program_is_high_confidence_and_explains_each_loop_with_its_line():
    r = result("def f(n):\n    c = 0\n    for i in range(n):\n        for j in range(i):\n            c += 1\n    return c\n", "python")
    assert r.confidence == "high" and r.uncertain == []
    assert any(note.startswith("line 3") for note in r.notes) and any(note.startswith("line 4") for note in r.notes)


def test_a_loop_whose_length_cannot_be_read_lowers_the_confidence_and_says_so():
    r = result("def f(n):\n    x = n\n    while x != 1:\n        x = g(x)\n    return x\n", "python")
    assert r.time.fmt() == "O(n)" and r.confidence in ("medium", "low")
    assert any("while x != 1" in u for u in r.uncertain)
    assert any("could not tell" in note for note in r.notes)


def test_amortised_loops_are_explained_as_such():
    code = ("def f(s, k):\n    left = 0\n    seen = {}\n    best = 0\n    for right, ch in enumerate(s):\n"
            "        seen[ch] = seen.get(ch, 0) + 1\n        while len(seen) > k:\n            seen[s[left]] -= 1\n"
            "            if seen[s[left]] == 0:\n                del seen[s[left]]\n            left += 1\n"
            "        best = max(best, right - left + 1)\n    return best\n")
    r = result(code, "python")
    assert r.time.fmt() == "O(n)" and any("amortised" in note for note in r.notes)


def test_space_is_explained_too():
    r = result("def f(n):\n    a = [0] * n\n    return a\n", "python")
    assert r.space.fmt() == "O(n)" and r.space_notes and r.space_notes[0].startswith("line 2")


# ── the analyzer built on it ────────────────────────────────────────────────

def analyze_endpoint(code: str, lang: str) -> dict:
    return asyncio.run(ComplexityAnalyzer().analyze(code, lang, "Solve it."))


def test_the_endpoint_answer_uses_the_cost_analysis_and_reports_confidence():
    out = analyze_endpoint("def f(a):\n    for i in range(len(a)):\n        for j in range(len(a)):\n            pass\n", "python")
    assert out["engine"] == "cost-model" and out["time_complexity"]["worst"] == "O(n²)"
    assert out["confidence"] == "high" and out["derivation"] and "line 2" in out["analysis"]


def test_code_that_does_not_parse_falls_back_to_the_pattern_rules():
    out = analyze_endpoint("def f(a:\n    for i in range(len(a)):\n        pass\n", "python")
    assert out["engine"] == "pattern-rules" and out["confidence"] == "low" and out["confidence_notes"]
    assert out["time_complexity"]["worst"].startswith("O(")


def test_the_locked_harness_does_not_change_the_answer():
    body = "def solve(n, arr):\n    t = 0\n    for x in arr:\n        t += x\n    return t\n\n\n"
    marker = "# ===== Reads the input and prints the answer. You do not need to edit below. =====\n"
    harness = "def main():\n    n = int(input())\n    arr = list(map(int, input().split()))\n    for i in range(n):\n        for j in range(n):\n            pass\n    print(solve(n, arr))\n"
    assert analyze_endpoint(body + marker + harness, "python")["time_complexity"]["worst"] == "O(n)"
