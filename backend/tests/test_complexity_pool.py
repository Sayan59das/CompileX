"""Complexity of real question-pool solutions, each inside its real Python harness (the types of the arguments are read from
it). Every expected value was worked out by reading the code, not taken from the analysis.

Run from the backend folder:  python -m pytest tests/test_complexity_pool.py -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.complexity import analyze_source
from app.services.complexity.harness import python_param_types

MARKER = "You do not need to edit below"

# (id, whole file as the player has it, worst time, space or None)
CASES = [
    ('8-brute', r'''def halfway_odd_suffix(n, a):
    for i in range(n - 1, -1, -1):
        if sum(1 for x in a[i:] if x % 2 != 0) == n // 2:
            return i
    return -1

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = halfway_odd_suffix(n, a)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('19-brute', r'''def run_lengths(s):
    runs = []
    start = 0
    while start < len(s):
        end = start
        while end < len(s) and s[end] == s[start]:
            end += 1
        runs.append(end - start)
        start = end
    return runs

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = run_lengths(s)
    print(' '.join(str(x) for x in result))


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('26-brute', r'''def ways_to_reach_top(n, k, jumps):
    def count(left):
        if left == 0:
            return 1
        return sum(count(left - jump) for jump in jumps if jump <= left)

    return count(n)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    k = int(tokens[1])
    jumps = [int(t) for t in lines[idx].split()]; idx += 1
    result = ways_to_reach_top(n, k, jumps)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('27-ref', r'''def friend_groups(n, m, pairs):
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    groups = n
    for u, v in pairs:
        root_u, root_v = find(u), find(v)
        if root_u != root_v:
            parent[root_u] = root_v
            groups -= 1
    return groups

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    pairs = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = friend_groups(n, m, pairs)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('29-ref', r'''def longest_chain_of_command(n, boss):
    depth = [0] * (n + 1)
    best = 0
    for start in range(1, n + 1):
        path = []
        node = start
        while node != 0 and depth[node] == 0:
            path.append(node)
            node = boss[node - 1]
        base = depth[node] if node != 0 else 0
        for person in reversed(path):
            base += 1
            depth[person] = base
        best = max(best, depth[start])
    return best

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    boss = [int(t) for t in lines[idx].split()]; idx += 1
    result = longest_chain_of_command(n, boss)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('65-ref', r'''def biggest_generation(n, parent):
    generation = [0] * (n + 1)
    for start in range(1, n + 1):
        path = []
        node = start
        while node != 0 and generation[node] == 0:
            path.append(node)
            node = parent[node - 1]
        base = generation[node] if node != 0 else 0
        for person in reversed(path):
            base += 1
            generation[person] = base
    counts = {}
    for g in generation[1:]:
        counts[g] = counts.get(g, 0) + 1
    return max(counts.values())

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    parent = [int(t) for t in lines[idx].split()]; idx += 1
    result = biggest_generation(n, parent)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('72-ref', r'''def largest_friend_group(n, m, pairs):
    parent = list(range(n + 1))
    size = [1] * (n + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in pairs:
        root_u, root_v = find(u), find(v)
        if root_u != root_v:
            if size[root_u] < size[root_v]:
                root_u, root_v = root_v, root_u
            parent[root_v] = root_u
            size[root_u] += size[root_v]
    return max(size[find(p)] for p in range(1, n + 1))

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    pairs = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = largest_friend_group(n, m, pairs)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('73-brute', r'''def extra_roads(n, m, roads):
    neighbours = {city: [] for city in range(1, n + 1)}
    for u, v in roads:
        neighbours[u].append(v)
        neighbours[v].append(u)
    seen = set()
    groups = 0
    for start in range(1, n + 1):
        if start in seen:
            continue
        groups += 1
        seen.add(start)
        stack = [start]
        while stack:
            city = stack.pop()
            for other in neighbours[city]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
    return m - (n - groups)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    roads = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = extra_roads(n, m, roads)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('73-ref', r'''def extra_roads(n, m, roads):
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    extra = 0
    for u, v in roads:
        root_u, root_v = find(u), find(v)
        if root_u == root_v:
            extra += 1
        else:
            parent[root_u] = root_v
    return extra

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    roads = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = extra_roads(n, m, roads)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('74-brute', r'''import itertools


def friend_triangles(n, m, pairs):
    linked = {(min(u, v), max(u, v)) for u, v in pairs}
    count = 0
    for a, b, c in itertools.combinations(range(1, n + 1), 3):
        if (a, b) in linked and (a, c) in linked and (b, c) in linked:
            count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    pairs = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = friend_triangles(n, m, pairs)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n³)', 'O(n)'),
    ('75-brute', r'''def finishable_tasks(n, m, rules):
    needs = {task: [] for task in range(1, n + 1)}
    for a, b in rules:
        needs[b].append(a)
    finished = set()
    changed = True
    while changed:
        changed = False
        for task in range(1, n + 1):
            if task not in finished and all(p in finished for p in needs[task]):
                finished.add(task)
                changed = True
    return len(finished)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    rules = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = finishable_tasks(n, m, rules)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('82-brute', r'''def length_after_cancelling(s):
    changed = True
    while changed:
        changed = False
        for i in range(len(s) - 1):
            if s[i] == s[i + 1]:
                s = s[:i] + s[i + 2:]
                changed = True
                break
    return len(s)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = length_after_cancelling(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('84-ref', r'''from collections import deque


def longest_calm_stretch(n, limit, a):
    highs = deque()
    lows = deque()
    left = 0
    best = 0
    for right, value in enumerate(a):
        while highs and a[highs[-1]] <= value:
            highs.pop()
        highs.append(right)
        while lows and a[lows[-1]] >= value:
            lows.pop()
        lows.append(right)
        while a[highs[0]] - a[lows[0]] > limit:
            left += 1
            if highs[0] < left:
                highs.popleft()
            if lows[0] < left:
                lows.popleft()
        best = max(best, right - left + 1)
    return best

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    limit = int(tokens[1])
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = longest_calm_stretch(n, limit, a)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('85-ref', r'''from collections import deque


def recent_requests(n, w, times):
    window = deque()
    counts = []
    for t in times:
        window.append(t)
        while window[0] <= t - w:
            window.popleft()
        counts.append(len(window))
    return counts

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    w = int(tokens[1])
    times = [int(t) for t in lines[idx].split()]; idx += 1
    result = recent_requests(n, w, times)
    print(' '.join(str(x) for x in result))


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('89-ref', r'''def list_gcd(n, a):
    def gcd(x, y):
        return x if y == 0 else gcd(y, x % y)

    result = a[0]
    for value in a[1:]:
        result = gcd(result, value)
    return result

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = list_gcd(n, a)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', None),
    ('94-ref', r'''def ways_to_balance(s):
    ways = {0: 1}
    for ch in s:
        following = {}
        for balance, count in ways.items():
            if ch == "(":
                steps = (1,)
            elif ch == ")":
                steps = (-1,)
            else:
                steps = (1, -1)
            for step in steps:
                new_balance = balance + step
                if new_balance >= 0:
                    following[new_balance] = following.get(new_balance, 0) + count
        ways = following
    return ways.get(0, 0)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = ways_to_balance(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('94-brute', r'''import itertools


def ways_to_balance(s):
    unknown = [i for i, ch in enumerate(s) if ch == "?"]
    total = 0
    for choice in itertools.product("()", repeat=len(unknown)):
        chars = list(s)
        for position, ch in zip(unknown, choice):
            chars[position] = ch
        balance = 0
        good = True
        for ch in chars:
            balance += 1 if ch == "(" else -1
            if balance < 0:
                good = False
                break
        if good and balance == 0:
            total += 1
    return total

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = ways_to_balance(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('95-ref', r'''import math


def distinct_arrangements(s):
    result = math.factorial(len(s))
    for letter in set(s):
        result //= math.factorial(s.count(letter))
    return result

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = distinct_arrangements(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', None),
    ('95-brute', r'''import itertools


def distinct_arrangements(s):
    return len(set(itertools.permutations(s)))

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = distinct_arrangements(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('101-ref', r'''def anagram_pairs(n, words):
    groups = {}
    for word in words:
        key = "".join(sorted(word))
        groups[key] = groups.get(key, 0) + 1
    return sum(c * (c - 1) // 2 for c in groups.values())

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    words = [str(t) for t in lines[idx].split()]; idx += 1
    result = anagram_pairs(n, words)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', None),
    ('108-ref', r'''def pairs_with_gap(n, a, d):
    count = 0
    j = 0
    for i in range(n):
        if j <= i:
            j = i + 1
        while j < n and a[j] - a[i] < d:
            j += 1
        if j < n and a[j] - a[i] == d:
            count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    a = [int(t) for t in lines[idx].split()]; idx += 1
    d = int(lines[idx].strip()); idx += 1
    result = pairs_with_gap(n, a, d)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(1)'),
    ('111-ref', r'''def count_palindromic_words(n, words):
    return sum(1 for word in words if word == word[::-1])

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    words = [str(t) for t in lines[idx].split()]; idx += 1
    result = count_palindromic_words(n, words)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', None),
    ('116-ref', r'''def equal_end_substrings(s):
    total = 0
    for letter in set(s):
        c = s.count(letter)
        total += c * (c + 1) // 2
    return total

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    s = str(lines[idx].strip()); idx += 1
    result = equal_end_substrings(s)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', None),
    ('62-ref', r'''def fewest_hops(n, hop):
    if n == 1:
        return 0
    hops = 0
    window_end = 0
    farthest = 0
    for i in range(n - 1):
        farthest = max(farthest, i + hop[i])
        if i == window_end:
            if farthest <= i:
                return -1
            hops += 1
            window_end = farthest
            if window_end >= n - 1:
                return hops
    return -1

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    hop = [int(t) for t in lines[idx].split()]; idx += 1
    result = fewest_hops(n, hop)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(1)'),
    ('62-brute', r'''def fewest_hops(n, hop):
    frontier = {0}
    seen = {0}
    hops = 0
    while frontier:
        if n - 1 in frontier:
            return hops
        following = set()
        for i in frontier:
            for j in range(i + 1, min(n - 1, i + hop[i]) + 1):
                if j not in seen:
                    seen.add(j)
                    following.add(j)
        frontier = following
        hops += 1
    return -1

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    hop = [int(t) for t in lines[idx].split()]; idx += 1
    result = fewest_hops(n, hop)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('21-brute', r'''def first_repeated_reading(n, readings):
    for j in range(n):
        for i in range(j):
            if readings[i] == readings[j]:
                return readings[j]
    return -1

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    readings = [int(t) for t in lines[idx].split()]; idx += 1
    result = first_repeated_reading(n, readings)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(1)'),
    ('78-brute', r'''def previous_greater(n, a):
    answers = []
    for i in range(n):
        found = -1
        for j in range(i - 1, -1, -1):
            if a[j] > a[i]:
                found = a[j]
                break
        answers.append(found)
    return answers

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = previous_greater(n, a)
    print(' '.join(str(x) for x in result))


if __name__ == '__main__':
    main()
''', 'O(n²)', None),
    ('123-brute', r'''def record_days(n, temps):
    count = 0
    for i in range(n):
        if all(temps[j] < temps[i] for j in range(i)):
            count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    temps = [int(t) for t in lines[idx].split()]; idx += 1
    result = record_days(n, temps)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(1)'),
    ('110-ref', r'''def zero_sum_triples(n, a):
    ordered = sorted(a)
    count = 0
    for first in range(n - 2):
        left, right = first + 1, n - 1
        while left < right:
            total = ordered[first] + ordered[left] + ordered[right]
            if total == 0:
                count += 1
                left += 1
                right -= 1
            elif total < 0:
                left += 1
            else:
                right -= 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = zero_sum_triples(n, a)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', None),
    ('12-ref', r'''def smallest_price_gap(n, prices):
    ordered = sorted(prices)
    return min(ordered[i + 1] - ordered[i] for i in range(n - 1))

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    prices = [int(t) for t in lines[idx].split()]; idx += 1
    result = smallest_price_gap(n, prices)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('63-ref', r'''def rooms_needed(n, meetings):
    starts = sorted(m[0] for m in meetings)
    ends = sorted(m[1] for m in meetings)
    in_use = 0
    most = 0
    j = 0
    for s in starts:
        while j < n and ends[j] <= s:
            j += 1
            in_use -= 1
        in_use += 1
        most = max(most, in_use)
    return most

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    meetings = [[int(t) for t in lines[idx + i].split()] for i in range(n)]; idx += n
    result = rooms_needed(n, meetings)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('70-ref', r'''import heapq


def cheapest_route(n, m, s, t, roads):
    links = {city: [] for city in range(1, n + 1)}
    for u, v, w in roads:
        links[u].append((v, w))
        links[v].append((u, w))
    best = {s: 0}
    heap = [(0, s)]
    while heap:
        cost, city = heapq.heappop(heap)
        if cost > best.get(city, float("inf")):
            continue
        for other, w in links[city]:
            new_cost = cost + w
            if new_cost < best.get(other, float("inf")):
                best[other] = new_cost
                heapq.heappush(heap, (new_cost, other))
    return best.get(t, -1)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    m = int(tokens[1])
    s = int(tokens[2])
    t = int(tokens[3])
    roads = [[int(t) for t in lines[idx + i].split()] for i in range(m)]; idx += m
    result = cheapest_route(n, m, s, t, roads)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('90-ref', r'''def strings_with_k_ones(n, k):
    if k == 0 or k == n:
        return 1
    return strings_with_k_ones(n - 1, k - 1) + strings_with_k_ones(n - 1, k)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    k = int(tokens[1])
    result = strings_with_k_ones(n, k)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('92-brute', r'''def tribonacci(n):
    if n == 0:
        return 0
    if n <= 2:
        return 1
    return tribonacci(n - 1) + tribonacci(n - 2) + tribonacci(n - 3)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    result = tribonacci(n)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('53-ref', r'''def count_divisors(n):
    count = 0
    d = 1
    while d * d <= n:
        if n % d == 0:
            count += 1 if d * d == n else 2
        d += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    result = count_divisors(n)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(sqrt n)', 'O(1)'),
    ('52-brute', r'''def count_primes_up_to(n):
    count = 0
    for value in range(2, n + 1):
        divisor = 2
        while divisor * divisor <= value and value % divisor != 0:
            divisor += 1
        if divisor * divisor > value:
            count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    result = count_primes_up_to(n)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n sqrt n)', 'O(1)'),
    ('130-ref', r'''def best_window_total(n, k, profits):
    current = sum(profits[:k])
    best = current
    for i in range(k, n):
        current += profits[i] - profits[i - k]
        best = max(best, current)
    return best

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    k = int(tokens[1])
    profits = [int(t) for t in lines[idx].split()]; idx += 1
    result = best_window_total(n, k, profits)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', None),
    ('109-ref', r'''def closest_pair_sum(n, t, a):
    ordered = sorted(a)
    left, right = 0, n - 1
    best = ordered[0] + ordered[1]
    while left < right:
        total = ordered[left] + ordered[right]
        if abs(total - t) < abs(best - t) or (abs(total - t) == abs(best - t) and total < best):
            best = total
        if total < t:
            left += 1
        elif total > t:
            right -= 1
        else:
            return total
    return best

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    t = int(tokens[1])
    a = [int(t) for t in lines[idx].split()]; idx += 1
    result = closest_pair_sum(n, t, a)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('93-ref', r'''def rook_placements(n, board):
    used = [False] * n

    def place(row):
        if row == n:
            return 1
        total = 0
        for col in range(n):
            if board[row][col] == 0 and not used[col]:
                used[col] = True
                total += place(row + 1)
                used[col] = False
        return total

    return place(0)

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    board = [[int(t) for t in lines[idx + i].split()] for i in range(n)]; idx += n
    result = rook_placements(n, board)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('96-brute', r'''import itertools


def fence_colourings(n, k):
    count = 0
    for paint in itertools.product(range(k), repeat=n):
        if all(paint[i] != paint[i + 1] for i in range(n - 1)):
            count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    k = int(tokens[1])
    result = fence_colourings(n, k)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('58-ref', r'''def largest_number_from_digits(n, digits):
    return "".join(str(d) for d in sorted(digits, reverse=True))

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    digits = [int(t) for t in lines[idx].split()]; idx += 1
    result = largest_number_from_digits(n, digits)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('59-ref', r'''def most_gifts(n, b, prices):
    spent = 0
    count = 0
    for price in sorted(prices):
        if spent + price > b:
            break
        spent += price
        count += 1
    return count

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    b = int(tokens[1])
    prices = [int(t) for t in lines[idx].split()]; idx += 1
    result = most_gifts(n, b, prices)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('60-ref', r'''def boats_needed(n, limit, weights):
    ordered = sorted(weights)
    left, right = 0, n - 1
    boats = 0
    while left <= right:
        if ordered[left] + ordered[right] <= limit and left != right:
            left += 1
        right -= 1
        boats += 1
    return boats

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    limit = int(tokens[1])
    weights = [int(t) for t in lines[idx].split()]; idx += 1
    result = boats_needed(n, limit, weights)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n log n)', 'O(n)'),
    ('60-brute', r'''def boats_needed(n, limit, weights):
    def fewest(people):
        if not people:
            return 0
        first, rest = people[0], people[1:]
        options = [1 + fewest(rest)]
        for i, other in enumerate(rest):
            if first + other <= limit:
                options.append(1 + fewest(rest[:i] + rest[i + 1:]))
        return min(options)

    return fewest(tuple(weights))

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    tokens = lines[idx].split(); idx += 1
    n = int(tokens[0])
    limit = int(tokens[1])
    weights = [int(t) for t in lines[idx].split()]; idx += 1
    result = boats_needed(n, limit, weights)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(2^n)', None),
    ('80-ref', r'''def postfix_value(n, tokens):
    stack = []
    for token in tokens:
        if token in ("+", "-", "*"):
            right = stack.pop()
            left = stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            else:
                stack.append(left * right)
        else:
            stack.append(int(token))
    return stack[0]

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    tokens = [str(t) for t in lines[idx].split()]; idx += 1
    result = postfix_value(n, tokens)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
    ('43-ref', r'''def best_rod_revenue(n, prices):
    best = [0] * (n + 1)
    for length in range(1, n + 1):
        best[length] = max(prices[piece - 1] + best[length - piece] for piece in range(1, length + 1))
    return best[n]

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    prices = [int(t) for t in lines[idx].split()]; idx += 1
    result = best_rod_revenue(n, prices)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n²)', 'O(n)'),
    ('119-ref', r'''def fewest_swaps_to_sort(n, p):
    seen = [False] * n
    cycles = 0
    for start in range(n):
        if not seen[start]:
            cycles += 1
            position = start
            while not seen[position]:
                seen[position] = True
                position = p[position] - 1
    return n - cycles

# ===== Reads the input and prints the answer. You do not need to edit below. =====
def main():
    lines = sys.stdin.read().split('\n')
    idx = 0
    n = int(lines[idx].strip()); idx += 1
    p = [int(t) for t in lines[idx].split()]; idx += 1
    result = fewest_swaps_to_sort(n, p)
    print(result)


if __name__ == '__main__':
    main()
''', 'O(n)', 'O(n)'),
]


def players_part(full: str) -> str:
    lines = full.split("\n")
    at = next(i for i, line in enumerate(lines) if MARKER in line)
    return "\n".join(lines[:at])


@pytest.mark.parametrize("name,full,time,space", CASES, ids=[c[0] for c in CASES])
def test_pool_solution(name, full, time, space):
    r = analyze_source(players_part(full), "python", debug=True, harness_code=full)
    assert r is not None
    assert r.time.fmt() == time
    if space is not None:
        assert r.space.fmt() == space


def test_the_harness_tells_what_the_arguments_are():
    full = CASES[0][1]
    assert python_param_types(full) is not None
    src = (
        "def f(n, words, pairs, s):\n    return 0\n\n\n"
        "def main():\n    n = int(input())\n    words = [str(t) for t in input().split()]\n"
        "    pairs = [[int(t) for t in input().split()] for i in range(n)]\n    s = str(input().strip())\n"
        "    result = f(n, words, pairs, s)\n    print(result)\n"
    )
    assert python_param_types(src) == ("f", ["int", "List[str]", "List[List[int]]", "str"])
    assert python_param_types("def f(a):\n    return a\n") is None


def test_without_the_harness_it_still_answers():
    r = analyze_source("def f(a):\n    t = 0\n    for x in a:\n        t += x\n    return t\n", "python", debug=True)
    assert r is not None and r.time.fmt() == "O(n)"
