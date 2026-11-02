"""The complexity analyzer: what it reports for known solutions, in the real typed starters.

The player's code ends up inside a locked harness (below the marker line). The analyzer must read only the player's part:
before that, an untouched stub came out as O(n) time and O(n^2) space, and a correct O(n) C solution as O(n^2).

Run from the backend folder:  python -m pytest tests/test_complexity_analyzer.py -q
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.complexity_analyzer import ComplexityAnalyzer, _players_part

LANGS = ("python", "cpp", "java", "javascript", "c")

# The real typed starter for `n:int, arr:int[n]` -> int: everything above the signature, and the locked harness from the
# marker line down. The player's code goes between them.
HEAD = {
    'python': r'''import sys

''',
    'cpp': r'''#include <bits/stdc++.h>
using namespace std;
''',
    'java': r'''import java.util.*;
import java.util.stream.*;
import java.io.*;

public class Solution {''',
    'javascript': r'''''',
    'c': r'''#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
''',
}

TAIL = {
    'python': r'''# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    arr = [int(t) for t in lines[idx].split()]; idx += 1
    result = solve(n, arr)
    print(result)


if __name__ == '__main__':
    main()
''',
    'cpp': r'''// ===== Reads the input and prints the answer. You do not need to edit below. =====
int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    vector<string> lines;
    string line;
    while (getline(cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    size_t idx = 0;
    auto _ints = [](const string& s) { vector<long long> v; istringstream is(s); long long x; while (is >> x) v.push_back(x); return v; };
    auto _words = [](const string& s) { vector<string> v; istringstream is(s); string x; while (is >> x) v.push_back(x); return v; };
    auto _trim = [](const string& s) { size_t a = s.find_first_not_of(" \t"); if (a == string::npos) return string(); size_t b = s.find_last_not_of(" \t"); return s.substr(a, b - a + 1); };
    long long n = stoll(_trim(lines[idx++]));
    vector<long long> arr = _ints(lines[idx++]);
    auto result = solve(n, arr);
    cout << result << "\n";
    return 0;
}
''',
    'java': r'''    // ===== Reads the input and prints the answer. You do not need to edit below. =====
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        List<String> lines = new ArrayList<>();
        String ln;
        while ((ln = br.readLine()) != null) lines.add(ln);
        int idx = 0;
        long n = Long.parseLong(lines.get(idx++).trim());
        long[] arr = Arrays.stream(lines.get(idx++).trim().split("\\s+")).filter(_s -> !_s.isEmpty()).mapToLong(Long::parseLong).toArray();
        long result = solve(n, arr);
        System.out.println(result);
    }
}
''',
    'javascript': r'''// ===== Reads the input and prints the answer. You do not need to edit below. =====
const lines = require('fs').readFileSync(0, 'utf8').split('\n');
let idx = 0;
const n = Number(lines[idx++].trim());
const arr = lines[idx++].trim().split(/\s+/).filter(x => x.length).map(Number);
const result = solve(n, arr);
console.log(String(result));
''',
    'c': r'''// ===== Reads the input and prints the answer. You do not need to edit below. =====
static char** _lines;
static long long _line_count;

static const char* _next(long long* idx) {
    long long i = (*idx)++;
    return i < _line_count ? _lines[i] : "";
}

static const char* _at(char** t, long long count, long long i) {
    return i < count ? t[i] : "";
}

static char* _trim(const char* s) {
    while (*s == ' ' || *s == '\t') s++;
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t')) n--;
    return strndup(s, n);
}

static long long* _ints(const char* s, long long* count) {
    long long cap = 16, n = 0;
    long long* out = (long long*)malloc(cap * sizeof(long long));
    char* end;
    for (;;) {
        while (*s == ' ' || *s == '\t') s++;
        if (!*s) break;
        long long v = strtoll(s, &end, 10);
        if (end == s) break;
        if (n == cap) { cap *= 2; out = (long long*)realloc(out, cap * sizeof(long long)); }
        out[n++] = v;
        s = end;
    }
    *count = n;
    return out;
}

static char** _words(const char* s, long long* count) {
    long long cap = 16, n = 0;
    char** out = (char**)malloc(cap * sizeof(char*));
    for (;;) {
        while (*s == ' ' || *s == '\t') s++;
        if (!*s) break;
        const char* start = s;
        while (*s && *s != ' ' && *s != '\t') s++;
        if (n == cap) { cap *= 2; out = (char**)realloc(out, cap * sizeof(char*)); }
        out[n++] = strndup(start, (size_t)(s - start));
    }
    *count = n;
    return out;
}

int main(void) {
    char* _buf = NULL;
    size_t _cap = 0;
    ssize_t _got;
    long long _alloc = 1024;
    _lines = (char**)malloc(_alloc * sizeof(char*));
    while ((_got = getline(&_buf, &_cap, stdin)) != -1) {
        while (_got > 0 && (_buf[_got - 1] == '\n' || _buf[_got - 1] == '\r')) _buf[--_got] = '\0';
        if (_line_count == _alloc) { _alloc *= 2; _lines = (char**)realloc(_lines, _alloc * sizeof(char*)); }
        _lines[_line_count++] = strdup(_buf);
    }
    free(_buf);
    long long idx = 0;
    long long n = strtoll(_next(&idx), NULL, 10);
    long long arr_len;
    long long* arr = _ints(_next(&idx), &arr_len);
    long long result = solve(n, arr, arr_len);
    printf("%lld\n", result);
    return 0;
}
''',
}


def in_starter(lang: str, player_code: str) -> str:
    return HEAD[lang] + "\n" + player_code + "\n" + TAIL[lang]


def analyze(code: str, lang: str) -> dict:
    return asyncio.run(ComplexityAnalyzer().analyze(code, lang, "Solve it."))


def worst(result: dict) -> tuple:
    return result["time_complexity"]["worst"], result["space_complexity"]["worst"]


# (shape, worst time, worst space or None when either answer is defensible, {language: the player's code})
CORPUS = [
    ('constant', 'O(1)', 'O(1)', {
        'python': r'''def solve(n, arr):
    return n * 2
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    return n * 2;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        return n * 2;
    }
''',
        'javascript': r'''function solve(n, arr) {
    return n * 2;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    return n * 2;
}
''',
    }),
    ('linear scan', 'O(n)', 'O(1)', {
        'python': r'''def solve(n, arr):
    total = 0
    for x in arr:
        total += x
    return total
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long total = 0;
    for (long long x : arr) total += x;
    return total;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long total = 0;
        for (long x : arr) total += x;
        return total;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let total = 0;
    for (const x of arr) total += x;
    return total;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long total = 0;
    for (long long i = 0; i < arr_len; i++) total += arr[i];
    return total;
}
''',
    }),
    ('prefix array', 'O(n)', 'O(n)', {
        'python': r'''def solve(n, arr):
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + arr[i]
    return prefix[n]
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    vector<long long> prefix(n + 1, 0);
    for (long long i = 0; i < n; i++) prefix[i + 1] = prefix[i] + arr[i];
    return prefix[n];
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long[] prefix = new long[(int) n + 1];
        for (int i = 0; i < n; i++) prefix[i + 1] = prefix[i] + arr[i];
        return prefix[(int) n];
    }
''',
        'javascript': r'''function solve(n, arr) {
    const prefix = new Array(n + 1).fill(0);
    for (let i = 0; i < n; i++) prefix[i + 1] = prefix[i] + arr[i];
    return prefix[n];
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long* prefix = calloc(n + 1, sizeof(long long));
    for (long long i = 0; i < n; i++) prefix[i + 1] = prefix[i] + arr[i];
    long long r = prefix[n];
    free(prefix);
    return r;
}
''',
    }),
    ('pair loops', 'O(n²)', 'O(1)', {
        'python': r'''def solve(n, arr):
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == 0:
                count += 1
    return count
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long count = 0;
    for (long long i = 0; i < n; i++)
        for (long long j = i + 1; j < n; j++)
            if (arr[i] + arr[j] == 0) count++;
    return count;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long count = 0;
        for (int i = 0; i < n; i++)
            for (int j = i + 1; j < n; j++)
                if (arr[i] + arr[j] == 0) count++;
        return count;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let count = 0;
    for (let i = 0; i < n; i++)
        for (let j = i + 1; j < n; j++)
            if (arr[i] + arr[j] === 0) count++;
    return count;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long count = 0;
    for (long long i = 0; i < n; i++)
        for (long long j = i + 1; j < n; j++)
            if (arr[i] + arr[j] == 0) count++;
    return count;
}
''',
    }),
    ('triple loops', 'O(n³)', 'O(1)', {
        'python': r'''def solve(n, arr):
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if arr[i] + arr[j] + arr[k] == 0:
                    count += 1
    return count
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long count = 0;
    for (long long i = 0; i < n; i++)
        for (long long j = i + 1; j < n; j++)
            for (long long k = j + 1; k < n; k++)
                if (arr[i] + arr[j] + arr[k] == 0) count++;
    return count;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long count = 0;
        for (int i = 0; i < n; i++)
            for (int j = i + 1; j < n; j++)
                for (int k = j + 1; k < n; k++)
                    if (arr[i] + arr[j] + arr[k] == 0) count++;
        return count;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let count = 0;
    for (let i = 0; i < n; i++)
        for (let j = i + 1; j < n; j++)
            for (let k = j + 1; k < n; k++)
                if (arr[i] + arr[j] + arr[k] === 0) count++;
    return count;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long count = 0;
    for (long long i = 0; i < n; i++)
        for (long long j = i + 1; j < n; j++)
            for (long long k = j + 1; k < n; k++)
                if (arr[i] + arr[j] + arr[k] == 0) count++;
    return count;
}
''',
    }),
    ('sort then scan', 'O(n log n)', None, {
        'python': r'''def solve(n, arr):
    b = sorted(arr)
    best = 0
    for i in range(1, n):
        best = max(best, b[i] - b[i - 1])
    return best
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    vector<long long> b = arr;
    sort(b.begin(), b.end());
    long long best = 0;
    for (long long i = 1; i < n; i++) best = max(best, b[i] - b[i - 1]);
    return best;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long[] b = arr.clone();
        Arrays.sort(b);
        long best = 0;
        for (int i = 1; i < n; i++) best = Math.max(best, b[i] - b[i - 1]);
        return best;
    }
''',
        'javascript': r'''function solve(n, arr) {
    const b = [...arr].sort((x, y) => x - y);
    let best = 0;
    for (let i = 1; i < n; i++) best = Math.max(best, b[i] - b[i - 1]);
    return best;
}
''',
        'c': r'''static int cmp(const void* a, const void* b) {
    long long x = *(const long long*)a, y = *(const long long*)b;
    return (x > y) - (x < y);
}

long long solve(long long n, const long long* arr, long long arr_len) {
    long long* b = malloc(n * sizeof(long long));
    memcpy(b, arr, n * sizeof(long long));
    qsort(b, n, sizeof(long long), cmp);
    long long best = 0;
    for (long long i = 1; i < n; i++) if (b[i] - b[i - 1] > best) best = b[i] - b[i - 1];
    free(b);
    return best;
}
''',
    }),
    ('hash map count', 'O(n)', 'O(n)', {
        'python': r'''def solve(n, arr):
    seen = {}
    best = 0
    for x in arr:
        seen[x] = seen.get(x, 0) + 1
        best = max(best, seen[x])
    return best
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    unordered_map<long long, long long> seen;
    long long best = 0;
    for (long long x : arr) {
        seen[x]++;
        best = max(best, seen[x]);
    }
    return best;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        Map<Long, Long> seen = new HashMap<>();
        long best = 0;
        for (long x : arr) {
            seen.merge(x, 1L, Long::sum);
            best = Math.max(best, seen.get(x));
        }
        return best;
    }
''',
        'javascript': r'''function solve(n, arr) {
    const seen = new Map();
    let best = 0;
    for (const x of arr) {
        seen.set(x, (seen.get(x) || 0) + 1);
        best = Math.max(best, seen.get(x));
    }
    return best;
}
''',
    }),
    ('binary search', 'O(log n)', 'O(1)', {
        'python': r'''def solve(n, arr):
    lo, hi = 0, n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == 7:
            return mid
        if arr[mid] < 7:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long lo = 0, hi = n - 1;
    while (lo <= hi) {
        long long mid = (lo + hi) / 2;
        if (arr[mid] == 7) return mid;
        if (arr[mid] < 7) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        int lo = 0, hi = (int) n - 1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (arr[mid] == 7) return mid;
            if (arr[mid] < 7) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let lo = 0, hi = n - 1;
    while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        if (arr[mid] === 7) return mid;
        if (arr[mid] < 7) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long lo = 0, hi = n - 1;
    while (lo <= hi) {
        long long mid = (lo + hi) / 2;
        if (arr[mid] == 7) return mid;
        if (arr[mid] < 7) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
''',
    }),
    ('naive fib recursion', 'O(2^n)', 'O(n)', {
        'python': r'''def fib(k):
    if k < 2:
        return k
    return fib(k - 1) + fib(k - 2)


def solve(n, arr):
    return fib(n)
''',
        'cpp': r'''long long fib(long long k) {
    if (k < 2) return k;
    return fib(k - 1) + fib(k - 2);
}

long long solve(long long n, const vector<long long>& arr) {
    return fib(n);
}
''',
        'java': r'''    static long fib(long k) {
        if (k < 2) return k;
        return fib(k - 1) + fib(k - 2);
    }

    static long solve(long n, long[] arr) {
        return fib(n);
    }
''',
        'javascript': r'''function fib(k) {
    if (k < 2) return k;
    return fib(k - 1) + fib(k - 2);
}

function solve(n, arr) {
    return fib(n);
}
''',
        'c': r'''long long fib(long long k) {
    if (k < 2) return k;
    return fib(k - 1) + fib(k - 2);
}

long long solve(long long n, const long long* arr, long long arr_len) {
    return fib(n);
}
''',
    }),
    ('1D dp', 'O(n)', 'O(n)', {
        'python': r'''def solve(n, arr):
    dp = [0] * n
    dp[0] = arr[0]
    for i in range(1, n):
        dp[i] = max(dp[i - 1], arr[i])
    return dp[n - 1]
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    vector<long long> dp(n);
    dp[0] = arr[0];
    for (long long i = 1; i < n; i++) dp[i] = max(dp[i - 1], arr[i]);
    return dp[n - 1];
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long[] dp = new long[(int) n];
        dp[0] = arr[0];
        for (int i = 1; i < n; i++) dp[i] = Math.max(dp[i - 1], arr[i]);
        return dp[(int) n - 1];
    }
''',
        'javascript': r'''function solve(n, arr) {
    const dp = new Array(n).fill(0);
    dp[0] = arr[0];
    for (let i = 1; i < n; i++) dp[i] = Math.max(dp[i - 1], arr[i]);
    return dp[n - 1];
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long* dp = calloc(n, sizeof(long long));
    dp[0] = arr[0];
    for (long long i = 1; i < n; i++) dp[i] = dp[i - 1] > arr[i] ? dp[i - 1] : arr[i];
    long long r = dp[n - 1];
    free(dp);
    return r;
}
''',
    }),
    ('2D dp table', 'O(n²)', 'O(n²)', {
        'python': r'''def solve(n, arr):
    dp = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dp[i][j] = arr[i] + arr[j]
    return dp[n - 1][n - 1]
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    vector<vector<long long>> dp(n, vector<long long>(n, 0));
    for (long long i = 0; i < n; i++)
        for (long long j = 0; j < n; j++)
            dp[i][j] = arr[i] + arr[j];
    return dp[n - 1][n - 1];
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long[][] dp = new long[(int) n][(int) n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                dp[i][j] = arr[i] + arr[j];
        return dp[(int) n - 1][(int) n - 1];
    }
''',
        'javascript': r'''function solve(n, arr) {
    const dp = Array.from({ length: n }, () => new Array(n).fill(0));
    for (let i = 0; i < n; i++)
        for (let j = 0; j < n; j++)
            dp[i][j] = arr[i] + arr[j];
    return dp[n - 1][n - 1];
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long* dp = calloc(n * n, sizeof(long long));
    for (long long i = 0; i < n; i++)
        for (long long j = 0; j < n; j++)
            dp[i * n + j] = arr[i] + arr[j];
    long long r = dp[(n - 1) * n + n - 1];
    free(dp);
    return r;
}
''',
    }),
    ('linear recursion', 'O(n)', 'O(n)', {
        'python': r'''def total(i, arr):
    if i == len(arr):
        return 0
    return arr[i] + total(i + 1, arr)


def solve(n, arr):
    return total(0, arr)
''',
        'cpp': r'''long long total(long long i, const vector<long long>& arr) {
    if (i == (long long)arr.size()) return 0;
    return arr[i] + total(i + 1, arr);
}

long long solve(long long n, const vector<long long>& arr) {
    return total(0, arr);
}
''',
        'java': r'''    static long total(int i, long[] arr) {
        if (i == arr.length) return 0;
        return arr[i] + total(i + 1, arr);
    }

    static long solve(long n, long[] arr) {
        return total(0, arr);
    }
''',
        'javascript': r'''function total(i, arr) {
    if (i === arr.length) return 0;
    return arr[i] + total(i + 1, arr);
}

function solve(n, arr) {
    return total(0, arr);
}
''',
        'c': r'''long long total(long long i, const long long* arr, long long len) {
    if (i == len) return 0;
    return arr[i] + total(i + 1, arr, len);
}

long long solve(long long n, const long long* arr, long long arr_len) {
    return total(0, arr, arr_len);
}
''',
    }),
    ('two pointers', 'O(n)', 'O(1)', {
        'python': r'''def solve(n, arr):
    l, r = 0, n - 1
    best = 0
    while l < r:
        best = max(best, arr[l] + arr[r])
        if arr[l] < arr[r]:
            l += 1
        else:
            r -= 1
    return best
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long l = 0, r = n - 1, best = 0;
    while (l < r) {
        best = max(best, arr[l] + arr[r]);
        if (arr[l] < arr[r]) l++;
        else r--;
    }
    return best;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        int l = 0, r = (int) n - 1;
        long best = 0;
        while (l < r) {
            best = Math.max(best, arr[l] + arr[r]);
            if (arr[l] < arr[r]) l++;
            else r--;
        }
        return best;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let l = 0, r = n - 1, best = 0;
    while (l < r) {
        best = Math.max(best, arr[l] + arr[r]);
        if (arr[l] < arr[r]) l++;
        else r--;
    }
    return best;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long l = 0, r = n - 1, best = 0;
    while (l < r) {
        long long s = arr[l] + arr[r];
        if (s > best) best = s;
        if (arr[l] < arr[r]) l++;
        else r--;
    }
    return best;
}
''',
    }),
    ('halving loop', 'O(log n)', 'O(1)', {
        'python': r'''def solve(n, arr):
    steps = 0
    while n > 1:
        n //= 2
        steps += 1
    return steps
''',
        'cpp': r'''long long solve(long long n, const vector<long long>& arr) {
    long long steps = 0;
    while (n > 1) {
        n /= 2;
        steps++;
    }
    return steps;
}
''',
        'java': r'''    static long solve(long n, long[] arr) {
        long steps = 0;
        while (n > 1) {
            n /= 2;
            steps++;
        }
        return steps;
    }
''',
        'javascript': r'''function solve(n, arr) {
    let steps = 0;
    while (n > 1) {
        n = Math.floor(n / 2);
        steps++;
    }
    return steps;
}
''',
        'c': r'''long long solve(long long n, const long long* arr, long long arr_len) {
    long long steps = 0;
    while (n > 1) {
        n /= 2;
        steps++;
    }
    return steps;
}
''',
    }),
]

# (name, language, code, worst time or None, worst space or None): loops that halve or double a counter, and look-alikes that
# must not be taken for them, plus arrays and allocations sized by the input
LOOPS_AND_ALLOCATIONS = [
    ('py digit sum', 'python', r'''def f(n):
    t = 0
    while n > 0:
        t += n % 10
        n //= 10
    return t
''', 'O(log n)', 'O(1)'),
    ('py shift down', 'python', r'''def f(n):
    c = 0
    while n:
        c += n & 1
        n >>= 1
    return c
''', 'O(log n)', 'O(1)'),
    ('py int(n/2)', 'python', r'''def f(n):
    c = 0
    while n > 1:
        n = int(n / 2)
        c += 1
    return c
''', 'O(log n)', 'O(1)'),
    ('py doubling', 'python', r'''def f(n):
    i = 1
    c = 0
    while i < n:
        i <<= 1
        c += 1
    return c
''', 'O(log n)', 'O(1)'),
    ('py n = n // 2', 'python', r'''def f(n):
    c = 0
    while n > 0:
        n = n // 2
        c += 1
    return c
''', 'O(log n)', 'O(1)'),
    ('py scan with log inside', 'python', r'''def f(arr):
    t = 0
    for x in arr:
        while x > 0:
            x //= 2
            t += 1
    return t
''', 'O(n log n)', None),
    ('py log loop beside a scan', 'python', r'''def f(arr, n):
    t = 0
    while n > 0:
        n //= 2
        t += 1
    for x in arr:
        t += x
    return t
''', 'O(n)', 'O(1)'),
    ('cpp doubling for', 'cpp', r'''long long f(long long n) {
    long long c = 0;
    for (long long i = 1; i < n; i *= 2) c++;
    return c;
}
''', 'O(log n)', 'O(1)'),
    ('cpp do-while', 'cpp', r'''int digits(long long n) {
    int c = 0;
    do {
        n /= 10;
        c++;
    } while (n > 0);
    return c;
}
''', 'O(log n)', 'O(1)'),
    ('cpp shift', 'cpp', r'''int bits(unsigned long long n) {
    int c = 0;
    while (n) {
        c += n & 1;
        n >>= 1;
    }
    return c;
}
''', 'O(log n)', 'O(1)'),
    ('java halving for', 'java', r'''    static int f(int n) {
        int c = 0;
        for (int i = n; i > 0; i /= 2) c++;
        return c;
    }
''', 'O(log n)', 'O(1)'),
    ('js floor halving', 'javascript', r'''function f(n) {
    let c = 0;
    while (n > 0) {
        n = Math.floor(n / 10);
        c++;
    }
    return c;
}
''', 'O(log n)', 'O(1)'),
    ('c scan with log inside', 'c', r'''long long f(const long long* a, long long n) {
    long long t = 0;
    for (long long i = 0; i < n; i++) {
        long long x = a[i];
        while (x > 0) {
            x /= 2;
            t++;
        }
    }
    return t;
}
''', 'O(n log n)', None),
    ('cpp braceless nested log', 'cpp', r'''long long f(long long n) {
    long long t = 0;
    for (long long i = 0; i < n; i++)
        for (long long j = 1; j < n; j *= 2)
            t++;
    return t;
}
''', 'O(n log n)', None),
    ('py n -= 1', 'python', r'''def f(n):
    c = 0
    while n > 0:
        n -= 1
        c += 1
    return c
''', 'O(n)', 'O(1)'),
    ('py i += 2', 'python', r'''def f(n):
    i = 0
    while i < n:
        i += 2
    return i
''', 'O(n)', 'O(1)'),
    ('py halved var is not the counter', 'python', r'''def f(n, x):
    i = 0
    while i < n:
        x //= 2
        i += 1
    return x
''', 'O(n)', 'O(1)'),
    ('py doubling but unbounded cond', 'python', r'''def f(n):
    i = 1
    c = 0
    while i > 0 and c < n:
        i *= 2
        c += 1
    return c
''', 'O(n)', None),
    ('cpp n -= 3', 'cpp', r'''int f(int n) {
    int c = 0;
    while (n > 0) {
        n -= 3;
        c++;
    }
    return c;
}
''', 'O(n)', 'O(1)'),
    ('cpp for with unrelated halving', 'cpp', r'''long long f(long long n, long long x) {
    for (long long i = 0; i < n; i++) {
        x /= 2;
    }
    return x;
}
''', 'O(n)', 'O(1)'),
    ('cpp comment/string noise', 'cpp', r'''long long f(long long n) {
    // while (n > 0) n /= 2;
    const char* s = "for (i = 1; i < n; i *= 2)";
    long long t = 0;
    for (long long i = 0; i < n; i++) t += i;
    return t;
}
''', 'O(n)', 'O(1)'),
    ('cpp binary search still log', 'cpp', r'''int f(vector<int>& a, int x) {
    int lo = 0, hi = (int)a.size() - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (a[mid] == x) return mid;
        if (a[mid] < x) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
''', 'O(log n)', 'O(1)'),
    ('java 2d sized by n', 'java', r'''    static long f(int n) {
        long[][] g = new long[n][n];
        return g[0][0];
    }
''', None, 'O(n²)'),
    ('c fixed malloc is O(1)', 'c', r'''typedef struct { int v; } Node;
int f(void) {
    Node* p = malloc(sizeof(Node));
    p->v = 1;
    int r = p->v;
    free(p);
    return r;
}
''', 'O(1)', 'O(1)'),
    ('c malloc sized by n', 'c', r'''long long f(long long n) {
    long long* a = malloc(n * sizeof(long long));
    long long r = 0;
    for (long long i = 0; i < n; i++) { a[i] = i; r += a[i]; }
    free(a);
    return r;
}
''', 'O(n)', 'O(n)'),
    ('js 2d via map', 'javascript', r'''function f(n) {
    const g = [...Array(n)].map(() => Array(n).fill(0));
    return g.length;
}
''', None, 'O(n²)'),
    ('gcd with a temp (cpp)', 'cpp', r'''long long g(long long a, long long b) {
    while (b != 0) {
        long long t = b;
        b = a % b;
        a = t;
    }
    return a;
}
''', 'O(log n)', 'O(1)'),
    ('gcd split remainder (java)', 'java', r'''    static long g(long a, long b) {
        while (b > 0) {
            long t = a % b;
            a = b;
            b = t;
        }
        return a;
    }
''', 'O(log n)', 'O(1)'),
    ('gcd destructuring (js)', 'javascript', r'''function g(a, b) {
    while (b) {
        [a, b] = [b, a % b];
    }
    return a;
}
''', 'O(log n)', 'O(1)'),
    ('gcd (c)', 'c', r'''long long g(long long a, long long b) {
    while (b) {
        long long t = a % b;
        a = b;
        b = t;
    }
    return a;
}
''', 'O(log n)', 'O(1)'),
    ('trial division is not Euclid', 'cpp', r'''bool p(long long n) {
    long long i = 2;
    while (i < n) {
        long long r = n % i;
        if (r == 0) return false;
        i = i + 1;
    }
    return true;
}
''', 'O(n)', 'O(1)'),
    ('counter reduced modulo a constant', 'python', r'''def f(n):
    c = 0
    while c < n:
        c = (c + 1) % 1000000
    return c
''', 'O(n)', 'O(1)'),
]

# Classic patterns. (name, language, code, worst time, worst space)
CLASSIC = [
    ('two pointers on sorted (inner while)', 'cpp', r'''int f(vector<int>& a, int t) {
    sort(a.begin(), a.end());
    int l = 0, r = a.size() - 1, c = 0;
    while (l < r) {
        int s = a[l] + a[r];
        if (s == t) { c++; l++; r--; }
        else if (s < t) l++;
        else r--;
    }
    return c;
}
''', 'O(n log n)', 'O(1)'),
    ('lru_cache fib', 'python', r'''from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
''', 'O(n)', 'O(n)'),
    ('merge sort', 'python', r'''def merge_sort(a):
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out
''', 'O(n log n)', 'O(n)'),
    ('subarray sum with prefix + hash', 'python', r'''def f(arr, k):
    prefix = 0
    seen = {0: 1}
    count = 0
    for x in arr:
        prefix += x
        count += seen.get(prefix - k, 0)
        seen[prefix] = seen.get(prefix, 0) + 1
    return count
''', 'O(n)', 'O(n)'),
    ('matrix multiply', 'python', r'''def f(a, b, n):
    c = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                c[i][j] += a[i][k] * b[k][j]
    return c
''', 'O(n³)', 'O(n²)'),
    ('fast power', 'python', r'''def power(b, e):
    r = 1
    while e > 0:
        if e & 1:
            r *= b
        b *= b
        e >>= 1
    return r
''', 'O(log n)', 'O(1)'),
    ('dfs on graph', 'python', r'''def f(adj, n):
    seen = [False] * n
    def dfs(u):
        seen[u] = True
        for v in adj[u]:
            if not seen[v]:
                dfs(v)
    c = 0
    for u in range(n):
        if not seen[u]:
            dfs(u)
            c += 1
    return c
''', 'O(n)', 'O(n)'),
    ('counting sort style (two sequential loops)', 'python', r'''def f(arr, m):
    cnt = [0] * (m + 1)
    for x in arr:
        cnt[x] += 1
    out = []
    for v in range(m + 1):
        out.extend([v] * cnt[v])
    return out
''', 'O(n)', 'O(n)'),
    ('nested loops with early exit (two sum brute force)', 'cpp', r'''vector<int> f(vector<int>& a, int t) {
    for (int i = 0; i < (int)a.size(); i++)
        for (int j = i + 1; j < (int)a.size(); j++)
            if (a[i] + a[j] == t) return {i, j};
    return {};
}
''', 'O(n²)', 'O(1)'),
    ('euclid gcd', 'python', r'''def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
''', 'O(log n)', 'O(1)'),
    ('sliding window (inner while, amortised)', 'python', r'''def f(s, k):
    left = 0
    seen = {}
    best = 0
    for right, ch in enumerate(s):
        seen[ch] = seen.get(ch, 0) + 1
        while len(seen) > k:
            seen[s[left]] -= 1
            if seen[s[left]] == 0:
                del seen[s[left]]
            left += 1
        best = max(best, right - left + 1)
    return best
''', 'O(n)', 'O(n)'),
    ('sqrt loop i*i <= n', 'python', r'''def is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True
''', 'O(sqrt n)', 'O(1)'),
    ('kadane (index loop)', 'python', r'''def f(arr):
    best = cur = arr[0]
    for i in range(1, len(arr)):
        cur = max(arr[i], cur + arr[i])
        best = max(best, cur)
    return best
''', 'O(n)', 'O(1)'),
    ('kadane (slice copies the array)', 'python', r'''def f(arr):
    best = cur = arr[0]
    for x in arr[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
''', 'O(n)', 'O(n)'),
]

@pytest.mark.parametrize("lang", LANGS)
def test_an_untouched_stub_is_constant_time_and_space(lang):
    stub = HEAD[lang] + "\n" + {
        "python": "def solve(n, arr):\n    pass\n",
        "cpp": "long long solve(long long n, const vector<long long>& arr) {\n    return 0;\n}\n",
        "java": "    static long solve(long n, long[] arr) {\n        return 0;\n    }\n",
        "javascript": "function solve(n, arr) {\n}\n",
        "c": "long long solve(long long n, const long long* arr, long long arr_len) {\n    return 0;\n}\n",
    }[lang] + "\n" + TAIL[lang]
    assert worst(analyze(stub, lang)) == ("O(1)", "O(1)")     # the harness reads the whole input; that is not the player's cost


def test_only_the_players_part_is_analyzed():
    code = "def solve(n):\n    return n\n\n# ===== Reads the input. You do not need to edit below. =====\nfor i in range(9):\n    pass\n"
    assert _players_part(code) == "def solve(n):\n    return n\n"
    assert _players_part(code.replace("\n", "\r\n")).startswith("def solve(n):")
    unmarked = "def solve(n):\n    for i in range(n):\n        pass\n"
    assert _players_part(unmarked) == unmarked                  # older / custom questions are analyzed whole
    assert worst(analyze(unmarked, "python"))[0] == "O(n)"


def _corpus_params():
    for name, time, space, codes in CORPUS:
        for lang, code in codes.items():
            yield pytest.param(lang, code, time, space, id=f"{name}-{lang}")


@pytest.mark.parametrize("lang,code,time,space", list(_corpus_params()))
def test_known_solutions_in_the_real_starters(lang, code, time, space):
    got_time, got_space = worst(analyze(in_starter(lang, code), lang))
    assert got_time == time
    if space is not None:
        assert got_space == space


def _case_params(cases):
    for name, lang, code, time, space in cases:
        yield pytest.param(lang, code, time, space, id=f"{name}-{lang}")


@pytest.mark.parametrize("lang,code,time,space", list(_case_params(LOOPS_AND_ALLOCATIONS)))
def test_log_loops_look_alikes_and_sized_allocations(lang, code, time, space):
    got_time, got_space = worst(analyze(code, lang))
    if time is not None:
        assert got_time == time
    if space is not None:
        assert got_space == space


@pytest.mark.parametrize("lang,code,time,space", list(_case_params(CLASSIC)))
def test_classic_patterns(lang, code, time, space):
    assert worst(analyze(code, lang)) == (time, space)
