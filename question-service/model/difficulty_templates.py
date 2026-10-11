# difficulty_templates.py
# Difficulty-aware question templates for dynamic_generator.py
import random
from typing import Dict, List, Any

# ---------------------------------------------------------------------------
# EASY ARRAY TEMPLATES
# Simple single-loop problems: sum, max, min, count, reverse, etc.
# ---------------------------------------------------------------------------

def _easy_array_sum(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)
    lo, hi = rng.randint(1, 5), rng.randint(10, 50)
    arr = [rng.randint(lo, hi) for _ in range(n)]

    def solve(a): return sum(a)

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Sum of Array Elements",
        "problem_statement": (
            f"Given an array of {n} integers, calculate and print the sum of all elements. "
            f"Each element is between {lo} and {hi}."
        ),
        "input_format": f"First line: N (number of elements). Second line: N space-separated integers.",
        "output_format": "A single integer — the sum of all elements.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


def _easy_array_max(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)
    lo, hi = rng.randint(-20, 0), rng.randint(10, 100)
    arr = [rng.randint(lo, hi) for _ in range(n)]

    def solve(a): return max(a)

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Find Maximum Element",
        "problem_statement": (
            f"Given an array of {n} integers (values between {lo} and {hi}), "
            f"find and print the largest element."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "A single integer — the maximum element.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


def _easy_array_reverse(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    lo, hi = 1, 99
    arr = [rng.randint(lo, hi) for _ in range(n)]

    def solve(a): return list(reversed(a))

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Reverse an Array",
        "problem_statement": (
            f"Given an array of {n} integers, print the array in reverse order."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "The reversed array elements separated by spaces.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": " ".join(map(str, solve(arr))),
        "test_cases": tcs,
    }


def _easy_array_count_even_odd(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    arr = [rng.randint(1, 50) for _ in range(n)]

    def solve(a):
        evens = sum(1 for x in a if x % 2 == 0)
        odds = len(a) - evens
        return f"{evens} {odds}"

    def make_tc():
        a = [rng.randint(1, 50) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Count Even and Odd Numbers",
        "problem_statement": (
            f"Given an array of {n} positive integers, count how many are even and how many are odd. "
            f"Print the count of even numbers followed by the count of odd numbers."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "Two integers on one line: count of even numbers, then count of odd numbers.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": solve(arr),
        "test_cases": tcs,
    }


def _easy_array_linear_search(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    arr = [rng.randint(1, 30) for _ in range(n)]
    target = rng.choice(arr + [rng.randint(31, 50)])

    def solve(a, t):
        for i, v in enumerate(a):
            if v == t:
                return i
        return -1

    def make_tc():
        a = [rng.randint(1, 30) for _ in range(rng.randint(4, n))]
        t = rng.choice(a + [rng.randint(31, 50)])
        return {"input": {"array": a, "target": t}, "output": solve(a, t)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Linear Search",
        "problem_statement": (
            f"Given an array of {n} integers and a target value, "
            f"find the index (0-based) of the first occurrence of the target. "
            f"If the target is not found, print -1."
        ),
        "input_format": "First line: N and target. Second line: N space-separated integers.",
        "output_format": "A single integer — the 0-based index of the target, or -1 if not found.",
        "sample_input": f"{n} {target}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr, target)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# EASY STRING TEMPLATES
# ---------------------------------------------------------------------------

def _easy_string_reverse(rng: random.Random) -> Dict:
    length = rng.randint(4, 10)
    s = "".join(rng.choice("abcdefghij") for _ in range(length))

    def solve(x): return x[::-1]

    def make_tc():
        x = "".join(rng.choice("abcdefghij") for _ in range(rng.randint(3, length)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Reverse a String",
        "problem_statement": (
            f"Given a string of lowercase letters, print it in reverse order."
        ),
        "input_format": "A single string on one line.",
        "output_format": "The reversed string.",
        "sample_input": s,
        "sample_output": solve(s),
        "test_cases": tcs,
    }


def _easy_string_palindrome_check(rng: random.Random) -> Dict:
    def make_palindrome(r):
        half = "".join(r.choice("abcde") for _ in range(r.randint(2, 5)))
        return half + half[::-1]

    s = make_palindrome(rng) if rng.random() < 0.5 else "".join(rng.choice("abcde") for _ in range(rng.randint(4, 8)))

    def solve(x): return "true" if x == x[::-1] else "false"

    def make_tc():
        if rng.random() < 0.5:
            x = make_palindrome(rng)
        else:
            x = "".join(rng.choice("abcde") for _ in range(rng.randint(3, 8)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Check if String is Palindrome",
        "problem_statement": (
            "Given a string of lowercase letters, determine if it is a palindrome. "
            "A palindrome reads the same forwards and backwards. Print true or false."
        ),
        "input_format": "A single string on one line.",
        "output_format": "Print true if the string is a palindrome, false otherwise.",
        "sample_input": s,
        "sample_output": solve(s),
        "test_cases": tcs,
    }


def _easy_string_count_chars(rng: random.Random) -> Dict:
    length = rng.randint(5, 12)
    s = "".join(rng.choice("abcde") for _ in range(length))
    ch = rng.choice("abcde")

    def solve(x, c): return x.count(c)

    def make_tc():
        x = "".join(rng.choice("abcde") for _ in range(rng.randint(4, length)))
        c = rng.choice("abcde")
        return {"input": {"s": x, "c": c}, "output": solve(x, c)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Count Character Occurrences",
        "problem_statement": (
            f"Given a string and a character, count how many times the character appears in the string."
        ),
        "input_format": "First line: the string. Second line: the character to count.",
        "output_format": "A single integer — the number of occurrences.",
        "sample_input": f"{s}\n{ch}",
        "sample_output": str(solve(s, ch)),
        "test_cases": tcs,
    }


def _easy_string_uppercase(rng: random.Random) -> Dict:
    length = rng.randint(4, 10)
    s = "".join(rng.choice("abcdefghij") for _ in range(length))

    def solve(x): return x.upper()

    def make_tc():
        x = "".join(rng.choice("abcdefghij") for _ in range(rng.randint(3, length)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Convert String to Uppercase",
        "problem_statement": (
            "Given a string of lowercase letters, convert it to uppercase and print the result."
        ),
        "input_format": "A single string of lowercase letters.",
        "output_format": "The string in uppercase.",
        "sample_input": s,
        "sample_output": solve(s),
        "test_cases": tcs,
    }


def _easy_string_length(rng: random.Random) -> Dict:
    length = rng.randint(4, 15)
    s = "".join(rng.choice("abcdefghijklmnop") for _ in range(length))

    def solve(x): return len(x)

    def make_tc():
        x = "".join(rng.choice("abcdefghijklmnop") for _ in range(rng.randint(3, length)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Find Length of String",
        "problem_statement": (
            "Given a string, print its length (number of characters)."
        ),
        "input_format": "A single string on one line.",
        "output_format": "A single integer — the length of the string.",
        "sample_input": s,
        "sample_output": str(solve(s)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# EASY MATH TEMPLATES
# ---------------------------------------------------------------------------

def _easy_math_factorial(rng: random.Random) -> Dict:
    n = rng.randint(3, 10)

    def solve(x):
        r = 1
        for i in range(2, x + 1):
            r *= i
        return r

    def make_tc():
        x = rng.randint(0, 12)
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Factorial of a Number",
        "problem_statement": (
            f"Given a non-negative integer N (0 <= N <= 12), compute and print N! (N factorial). "
            f"Recall that 0! = 1 and N! = N * (N-1) * ... * 1."
        ),
        "input_format": "A single integer N.",
        "output_format": "A single integer — the factorial of N.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _easy_math_fibonacci(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)

    def solve(x):
        if x <= 1:
            return x
        a, b = 0, 1
        for _ in range(2, x + 1):
            a, b = b, a + b
        return b

    def make_tc():
        x = rng.randint(0, 15)
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Nth Fibonacci Number",
        "problem_statement": (
            f"Given a non-negative integer N, print the Nth Fibonacci number. "
            f"The sequence starts: F(0)=0, F(1)=1, F(2)=1, F(3)=2, F(4)=3, ..."
        ),
        "input_format": "A single integer N (0 <= N <= 20).",
        "output_format": "A single integer — the Nth Fibonacci number.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _easy_math_prime_check(rng: random.Random) -> Dict:
    n = rng.randint(2, 50)

    def solve(x):
        if x < 2:
            return "false"
        for i in range(2, int(x**0.5) + 1):
            if x % i == 0:
                return "false"
        return "true"

    def make_tc():
        x = rng.randint(1, 100)
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Check if Number is Prime",
        "problem_statement": (
            f"Given a positive integer N, determine if it is a prime number. "
            f"Print true if N is prime, false otherwise."
        ),
        "input_format": "A single integer N (1 <= N <= 10^6).",
        "output_format": "Print true if N is prime, false otherwise.",
        "sample_input": str(n),
        "sample_output": solve(n),
        "test_cases": tcs,
    }


def _easy_math_sum_digits(rng: random.Random) -> Dict:
    n = rng.randint(10, 9999)

    def solve(x):
        return sum(int(d) for d in str(x))

    def make_tc():
        x = rng.randint(1, 99999)
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Sum of Digits",
        "problem_statement": (
            f"Given a positive integer N, compute the sum of its digits. "
            f"For example, if N = 1234, the answer is 1+2+3+4 = 10."
        ),
        "input_format": "A single positive integer N.",
        "output_format": "A single integer — the sum of digits of N.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _easy_math_gcd(rng: random.Random) -> Dict:
    a = rng.randint(2, 50)
    b = rng.randint(2, 50)

    def solve(x, y):
        while y:
            x, y = y, x % y
        return x

    def make_tc():
        x = rng.randint(1, 100)
        y = rng.randint(1, 100)
        return {"input": {"a": x, "b": y}, "output": solve(x, y)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Greatest Common Divisor",
        "problem_statement": (
            f"Given two positive integers A and B, find their Greatest Common Divisor (GCD). "
            f"The GCD is the largest integer that divides both A and B without a remainder."
        ),
        "input_format": "Two integers A and B on a single line.",
        "output_format": "A single integer — the GCD of A and B.",
        "sample_input": f"{a} {b}",
        "sample_output": str(solve(a, b)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# EASY RECURSION TEMPLATES
# ---------------------------------------------------------------------------

def _easy_recursion_sum_natural(rng: random.Random) -> Dict:
    n = rng.randint(5, 20)

    def solve(x): return x * (x + 1) // 2

    def make_tc():
        x = rng.randint(1, 50)
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Sum of First N Natural Numbers",
        "problem_statement": (
            f"Given a positive integer N, compute the sum of the first N natural numbers "
            f"(1 + 2 + 3 + ... + N) using recursion."
        ),
        "input_format": "A single integer N (1 <= N <= 1000).",
        "output_format": "A single integer — the sum.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _easy_recursion_power(rng: random.Random) -> Dict:
    base = rng.randint(2, 5)
    exp = rng.randint(1, 6)

    def solve(b, e): return b ** e

    def make_tc():
        b = rng.randint(1, 6)
        e = rng.randint(0, 8)
        return {"input": {"base": b, "exp": e}, "output": solve(b, e)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Power of a Number",
        "problem_statement": (
            f"Given a base B and exponent E, compute B raised to the power E (B^E) using recursion. "
            f"You may assume E >= 0."
        ),
        "input_format": "Two integers B and E on a single line.",
        "output_format": "A single integer — B raised to the power E.",
        "sample_input": f"{base} {exp}",
        "sample_output": str(solve(base, exp)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# EASY SORTING TEMPLATES
# ---------------------------------------------------------------------------

def _easy_sorting_bubble(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    arr = [rng.randint(1, 50) for _ in range(n)]

    def solve(a): return sorted(a)

    def make_tc():
        a = [rng.randint(1, 50) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Sort Array in Ascending Order",
        "problem_statement": (
            f"Given an array of {n} integers, sort them in ascending (non-decreasing) order "
            f"and print the sorted array."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "The sorted array elements separated by spaces.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": " ".join(map(str, solve(arr))),
        "test_cases": tcs,
    }


def _easy_sorting_find_second_max(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    arr = list({rng.randint(1, 50) for _ in range(n + 5)})[:n]
    while len(arr) < 3:
        arr.append(rng.randint(1, 50))

    def solve(a):
        s = sorted(set(a), reverse=True)
        return s[1] if len(s) >= 2 else s[0]

    def make_tc():
        a = list({rng.randint(1, 50) for _ in range(rng.randint(4, n + 3))})
        while len(a) < 3:
            a.append(rng.randint(1, 50))
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(5, 8))]
    return {
        "title": "Find Second Largest Element",
        "problem_statement": (
            f"Given an array of {n} distinct integers, find and print the second largest element."
        ),
        "input_format": "First line: N. Second line: N space-separated distinct integers.",
        "output_format": "A single integer — the second largest element.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD ARRAY TEMPLATES
# Advanced: segment trees, complex DP, advanced data structures
# ---------------------------------------------------------------------------

def _hard_array_max_subarray_with_indices(rng: random.Random) -> Dict:
    n = rng.randint(8, 20)
    lo, hi = rng.randint(-50, -10), rng.randint(10, 50)
    arr = [rng.randint(lo, hi) for _ in range(n)]

    def solve(a):
        best_sum = a[0]; best_l = best_r = 0
        cur = a[0]; cur_l = 0
        for i in range(1, len(a)):
            if cur + a[i] < a[i]:
                cur = a[i]; cur_l = i
            else:
                cur += a[i]
            if cur > best_sum:
                best_sum = cur; best_l = cur_l; best_r = i
        return f"{best_sum} {best_l} {best_r}"

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(5, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Maximum Subarray Sum with Indices",
        "problem_statement": (
            f"Given an array of {n} integers (values in [{lo}, {hi}]), find the contiguous subarray "
            f"with the maximum sum. Print the maximum sum, the starting index (0-based), "
            f"and the ending index (0-based) separated by spaces. "
            f"If multiple subarrays have the same maximum sum, print the one with the smallest starting index."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "Three integers: max_sum start_index end_index.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": solve(arr),
        "test_cases": tcs,
    }


def _hard_array_range_sum_queries(rng: random.Random) -> Dict:
    n = rng.randint(6, 15)
    q = rng.randint(4, 8)
    arr = [rng.randint(1, 100) for _ in range(n)]
    queries = [(rng.randint(0, n - 2), rng.randint(0, n - 1)) for _ in range(q)]
    queries = [(min(l, r), max(l, r)) for l, r in queries]

    def solve(a, qs):
        prefix = [0] * (len(a) + 1)
        for i, v in enumerate(a):
            prefix[i + 1] = prefix[i] + v
        return [str(prefix[r + 1] - prefix[l]) for l, r in qs]

    def make_tc():
        a = [rng.randint(1, 100) for _ in range(rng.randint(5, n))]
        qs = [(rng.randint(0, len(a) - 2), rng.randint(0, len(a) - 1)) for _ in range(rng.randint(3, q))]
        qs = [(min(l, r), max(l, r)) for l, r in qs]
        return {
            "input": {"array": a, "queries": qs},
            "output": "\n".join(solve(a, qs))
        }

    sample_in = f"{n}\n{' '.join(map(str, arr))}\n{q}\n" + "\n".join(f"{l} {r}" for l, r in queries)
    sample_out = "\n".join(solve(arr, queries))
    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Range Sum Queries with Prefix Array",
        "problem_statement": (
            f"Given an array of {n} integers and {q} range queries, "
            f"for each query (L, R) compute the sum of elements from index L to R (inclusive, 0-based). "
            f"Use prefix sums to answer each query in O(1) time."
        ),
        "input_format": (
            "First line: N. Second line: N space-separated integers. "
            "Third line: Q (number of queries). Next Q lines: each contains L and R."
        ),
        "output_format": "For each query, print the sum on a separate line.",
        "sample_input": sample_in,
        "sample_output": sample_out,
        "test_cases": tcs,
    }


def _hard_array_trapping_rain_water(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    arr = [rng.randint(0, 10) for _ in range(n)]

    def solve(a):
        if len(a) < 3:
            return 0
        left_max = [0] * len(a)
        right_max = [0] * len(a)
        left_max[0] = a[0]
        for i in range(1, len(a)):
            left_max[i] = max(left_max[i - 1], a[i])
        right_max[-1] = a[-1]
        for i in range(len(a) - 2, -1, -1):
            right_max[i] = max(right_max[i + 1], a[i])
        return sum(min(left_max[i], right_max[i]) - a[i] for i in range(len(a)))

    def make_tc():
        a = [rng.randint(0, 10) for _ in range(rng.randint(5, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Trapping Rain Water",
        "problem_statement": (
            f"Given an array of {n} non-negative integers representing the height of bars in a histogram, "
            f"compute how much water can be trapped between the bars after it rains. "
            f"Use the two-pointer or prefix-max approach for an O(n) solution."
        ),
        "input_format": "First line: N. Second line: N space-separated non-negative integers (bar heights).",
        "output_format": "A single integer — the total units of water trapped.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


def _hard_array_longest_increasing_subarray(rng: random.Random) -> Dict:
    n = rng.randint(8, 18)
    arr = [rng.randint(1, 50) for _ in range(n)]

    def solve(a):
        if not a:
            return 0
        max_len = cur_len = 1
        for i in range(1, len(a)):
            if a[i] > a[i - 1]:
                cur_len += 1
                max_len = max(max_len, cur_len)
            else:
                cur_len = 1
        return max_len

    def make_tc():
        a = [rng.randint(1, 50) for _ in range(rng.randint(5, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Longest Strictly Increasing Subarray",
        "problem_statement": (
            f"Given an array of {n} integers, find the length of the longest contiguous subarray "
            f"where each element is strictly greater than the previous one. "
            f"Note: this is a contiguous subarray, not a subsequence."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "A single integer — the length of the longest strictly increasing subarray.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


def _hard_array_count_inversions(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    arr = [rng.randint(1, 30) for _ in range(n)]

    def solve(a):
        count = 0
        for i in range(len(a)):
            for j in range(i + 1, len(a)):
                if a[i] > a[j]:
                    count += 1
        return count

    def make_tc():
        a = [rng.randint(1, 30) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Count Inversions in Array",
        "problem_statement": (
            f"Given an array of {n} integers, count the number of inversions. "
            f"An inversion is a pair (i, j) where i < j but arr[i] > arr[j]. "
            f"An efficient solution uses merge sort to count inversions in O(n log n)."
        ),
        "input_format": "First line: N. Second line: N space-separated integers.",
        "output_format": "A single integer — the number of inversions.",
        "sample_input": f"{n}\n{' '.join(map(str, arr))}",
        "sample_output": str(solve(arr)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD STRING TEMPLATES
# ---------------------------------------------------------------------------

def _hard_string_longest_without_repeat(rng: random.Random) -> Dict:
    length = rng.randint(8, 16)
    s = "".join(rng.choice("abcdefgh") for _ in range(length))

    def solve(x):
        seen = {}
        best = 0
        left = 0
        for right, c in enumerate(x):
            if c in seen and seen[c] >= left:
                left = seen[c] + 1
            seen[c] = right
            best = max(best, right - left + 1)
        return best

    def make_tc():
        x = "".join(rng.choice("abcdefgh") for _ in range(rng.randint(5, length)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Longest Substring Without Repeating Characters",
        "problem_statement": (
            f"Given a string of length up to {length}, find the length of the longest substring "
            f"that contains no repeating characters. Use the sliding window technique for O(n) time."
        ),
        "input_format": "A single string on one line.",
        "output_format": "A single integer — the length of the longest substring without repeating characters.",
        "sample_input": s,
        "sample_output": str(solve(s)),
        "test_cases": tcs,
    }


def _hard_string_minimum_window(rng: random.Random) -> Dict:
    t_len = rng.randint(2, 4)
    t = "".join(rng.choice("abcde") for _ in range(t_len))
    s_len = rng.randint(t_len + 2, t_len + 8)
    s = "".join(rng.choice("abcde") for _ in range(s_len))
    # Ensure t is a substring possibility
    insert_at = rng.randint(0, len(s))
    s = s[:insert_at] + t + s[insert_at:]

    def solve(string, pattern):
        from collections import Counter
        need = Counter(pattern)
        have = {}
        formed = 0
        required = len(need)
        left = 0
        best = ""
        for right, c in enumerate(string):
            have[c] = have.get(c, 0) + 1
            if c in need and have[c] == need[c]:
                formed += 1
            while formed == required:
                window = string[left:right + 1]
                if not best or len(window) < len(best):
                    best = window
                lc = string[left]
                have[lc] -= 1
                if lc in need and have[lc] < need[lc]:
                    formed -= 1
                left += 1
        return best if best else ""

    def make_tc():
        p = "".join(rng.choice("abcde") for _ in range(rng.randint(2, 3)))
        sl = rng.randint(len(p) + 2, len(p) + 8)
        sx = "".join(rng.choice("abcde") for _ in range(sl))
        ins = rng.randint(0, len(sx))
        sx = sx[:ins] + p + sx[ins:]
        return {"input": {"s": sx, "t": p}, "output": solve(sx, p)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Minimum Window Substring",
        "problem_statement": (
            f"Given strings S and T, find the minimum length substring of S that contains "
            f"all characters of T (including duplicates). If no such substring exists, return an empty string. "
            f"Use the sliding window technique for an efficient O(n) solution."
        ),
        "input_format": "First line: string S. Second line: string T.",
        "output_format": "The minimum window substring, or empty string if none exists.",
        "sample_input": f"{s}\n{t}",
        "sample_output": solve(s, t),
        "test_cases": tcs,
    }


def _hard_string_edit_distance(rng: random.Random) -> Dict:
    length = rng.randint(4, 8)
    s1 = "".join(rng.choice("abcde") for _ in range(length))
    s2 = "".join(rng.choice("abcde") for _ in range(rng.randint(3, length + 2)))

    def solve(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
        return dp[m][n]

    def make_tc():
        a = "".join(rng.choice("abcde") for _ in range(rng.randint(3, length)))
        b = "".join(rng.choice("abcde") for _ in range(rng.randint(3, length + 2)))
        return {"input": {"s1": a, "s2": b}, "output": solve(a, b)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Edit Distance Between Two Strings",
        "problem_statement": (
            f"Given two strings S1 and S2, find the minimum number of operations "
            f"(insert, delete, or replace a character) required to convert S1 into S2. "
            f"This is the classic Levenshtein distance problem, solved with dynamic programming."
        ),
        "input_format": "First line: string S1. Second line: string S2.",
        "output_format": "A single integer — the minimum edit distance.",
        "sample_input": f"{s1}\n{s2}",
        "sample_output": str(solve(s1, s2)),
        "test_cases": tcs,
    }


def _hard_string_count_distinct_subsequences(rng: random.Random) -> Dict:
    length = rng.randint(5, 9)
    s = "".join(rng.choice("abc") for _ in range(length))
    t_len = rng.randint(2, 3)
    t = "".join(rng.choice("abc") for _ in range(t_len))

    def solve(string, pattern):
        m, n = len(string), len(pattern)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = 1
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                dp[i][j] = dp[i - 1][j]
                if string[i - 1] == pattern[j - 1]:
                    dp[i][j] += dp[i - 1][j - 1]
        return dp[m][n]

    def make_tc():
        sx = "".join(rng.choice("abc") for _ in range(rng.randint(4, length)))
        tx = "".join(rng.choice("abc") for _ in range(rng.randint(2, 3)))
        return {"input": {"s": sx, "t": tx}, "output": solve(sx, tx)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Count Distinct Subsequences",
        "problem_statement": (
            f"Given strings S and T, count the number of distinct subsequences of S "
            f"that equal T. A subsequence is formed by deleting some (or no) characters "
            f"from S without changing the order of remaining characters. "
            f"Use dynamic programming for an O(m*n) solution."
        ),
        "input_format": "First line: string S. Second line: string T.",
        "output_format": "A single integer — the number of distinct subsequences.",
        "sample_input": f"{s}\n{t}",
        "sample_output": str(solve(s, t)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD GRAPH TEMPLATES
# ---------------------------------------------------------------------------

def _hard_graph_bellman_ford(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    edges = []
    seen = set()
    for _ in range(rng.randint(n, n * 2)):
        u = rng.randint(0, n - 1)
        v = rng.randint(0, n - 1)
        if u != v and (u, v) not in seen:
            w = rng.randint(-5, 20)
            edges.append((u, v, w))
            seen.add((u, v))
    src = 0

    def solve(nodes, edgs, source):
        dist = [float('inf')] * nodes
        dist[source] = 0
        for _ in range(nodes - 1):
            for u, v, w in edgs:
                if dist[u] != float('inf') and dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
        return " ".join(str(d) if d != float('inf') else "-1" for d in dist)

    def make_tc():
        nn = rng.randint(3, n)
        es = []
        ss = set()
        for _ in range(rng.randint(nn, nn * 2)):
            u = rng.randint(0, nn - 1)
            v = rng.randint(0, nn - 1)
            if u != v and (u, v) not in ss:
                w = rng.randint(-5, 20)
                es.append((u, v, w))
                ss.add((u, v))
        return {"input": {"nodes": nn, "edges": es, "src": 0}, "output": solve(nn, es, 0)}

    edge_str = "\n".join(f"{u} {v} {w}" for u, v, w in edges)
    sample_in = f"{n} {len(edges)} {src}\n{edge_str}"
    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Bellman-Ford Shortest Paths",
        "problem_statement": (
            f"Given a directed weighted graph with {n} nodes (0-indexed) and edges that may have "
            f"negative weights, find the shortest distance from source node 0 to all other nodes "
            f"using the Bellman-Ford algorithm. Output -1 for unreachable nodes. "
            f"Assume no negative-weight cycles exist."
        ),
        "input_format": (
            "First line: N (nodes), M (edges), src (source node). "
            "Next M lines: each contains u v w (directed edge from u to v with weight w)."
        ),
        "output_format": "N space-separated integers — shortest distance from src to each node (0 to N-1). Use -1 for unreachable.",
        "sample_input": sample_in,
        "sample_output": solve(n, edges, src),
        "test_cases": tcs,
    }


def _hard_graph_strongly_connected(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    edges = []
    seen = set()
    for _ in range(rng.randint(n, n + 4)):
        u = rng.randint(0, n - 1)
        v = rng.randint(0, n - 1)
        if u != v and (u, v) not in seen:
            edges.append((u, v))
            seen.add((u, v))

    def solve(nodes, edgs):
        from collections import defaultdict
        graph = defaultdict(list)
        rgraph = defaultdict(list)
        for u, v in edgs:
            graph[u].append(v)
            rgraph[v].append(u)
        visited = [False] * nodes
        order = []
        def dfs1(node):
            stack = [(node, False)]
            while stack:
                nd, done = stack.pop()
                if done:
                    order.append(nd)
                    continue
                if visited[nd]:
                    continue
                visited[nd] = True
                stack.append((nd, True))
                for nb in graph[nd]:
                    if not visited[nb]:
                        stack.append((nb, False))
        for i in range(nodes):
            if not visited[i]:
                dfs1(i)
        visited2 = [False] * nodes
        scc_count = 0
        def dfs2(node):
            stack = [node]
            while stack:
                nd = stack.pop()
                if visited2[nd]:
                    continue
                visited2[nd] = True
                for nb in rgraph[nd]:
                    if not visited2[nb]:
                        stack.append(nb)
        for node in reversed(order):
            if not visited2[node]:
                dfs2(node)
                scc_count += 1
        return scc_count

    edge_str = "\n".join(f"{u} {v}" for u, v in edges)
    sample_in = f"{n} {len(edges)}\n{edge_str}"

    def make_tc():
        nn = rng.randint(3, n)
        es = []
        ss = set()
        for _ in range(rng.randint(nn, nn + 3)):
            u = rng.randint(0, nn - 1)
            v = rng.randint(0, nn - 1)
            if u != v and (u, v) not in ss:
                es.append((u, v))
                ss.add((u, v))
        return {"input": {"nodes": nn, "edges": es}, "output": solve(nn, es)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Count Strongly Connected Components",
        "problem_statement": (
            f"Given a directed graph with {n} nodes (0-indexed) and directed edges, "
            f"count the number of Strongly Connected Components (SCCs) using Kosaraju's algorithm. "
            f"An SCC is a maximal set of nodes where every node is reachable from every other node."
        ),
        "input_format": "First line: N (nodes) and M (edges). Next M lines: each contains u v (directed edge u->v).",
        "output_format": "A single integer — the number of strongly connected components.",
        "sample_input": sample_in,
        "sample_output": str(solve(n, edges)),
        "test_cases": tcs,
    }


def _hard_graph_floyd_warshall(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    INF = 10**9
    matrix = [[INF] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0
    edges = []
    for i in range(n):
        for j in range(n):
            if i != j and rng.random() < 0.5:
                w = rng.randint(1, 20)
                matrix[i][j] = w
                edges.append((i, j, w))

    def solve(nodes, mat):
        dist = [row[:] for row in mat]
        for k in range(nodes):
            for i in range(nodes):
                for j in range(nodes):
                    if dist[i][k] + dist[k][j] < dist[i][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
        rows = []
        for row in dist:
            rows.append(" ".join(str(v) if v < INF else "-1" for v in row))
        return "\n".join(rows)

    mat_str = "\n".join(" ".join(str(v) if v < INF else "-1" for v in row) for row in matrix)
    sample_in = f"{n}\n{mat_str}"

    def make_tc():
        nn = rng.randint(3, n)
        m2 = [[INF] * nn for _ in range(nn)]
        for i in range(nn):
            m2[i][i] = 0
        for i in range(nn):
            for j in range(nn):
                if i != j and rng.random() < 0.5:
                    m2[i][j] = rng.randint(1, 20)
        return {"input": {"nodes": nn, "matrix": m2}, "output": solve(nn, m2)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "All-Pairs Shortest Paths (Floyd-Warshall)",
        "problem_statement": (
            f"Given a weighted directed graph with {n} nodes as an adjacency matrix, "
            f"find the shortest path between every pair of nodes using the Floyd-Warshall algorithm. "
            f"Input -1 in the matrix means no direct edge. Output -1 for unreachable pairs."
        ),
        "input_format": (
            "First line: N. Next N lines: the N×N adjacency matrix "
            "(use -1 for no direct edge, 0 on diagonal)."
        ),
        "output_format": "N lines, each with N space-separated shortest distances (-1 if unreachable).",
        "sample_input": sample_in,
        "sample_output": solve(n, matrix),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD DYNAMIC PROGRAMMING TEMPLATES
# ---------------------------------------------------------------------------

def _hard_dp_matrix_chain(rng: random.Random) -> Dict:
    n = rng.randint(3, 6)
    dims = [rng.randint(2, 15) for _ in range(n + 1)]

    def solve(d):
        n = len(d) - 1
        dp = [[0] * n for _ in range(n)]
        for length in range(2, n + 1):
            for i in range(n - length + 1):
                j = i + length - 1
                dp[i][j] = float('inf')
                for k in range(i, j):
                    cost = dp[i][k] + dp[k + 1][j] + d[i] * d[k + 1] * d[j + 1]
                    dp[i][j] = min(dp[i][j], cost)
        return dp[0][n - 1]

    def make_tc():
        nn = rng.randint(3, n)
        d = [rng.randint(2, 15) for _ in range(nn + 1)]
        return {"input": d, "output": solve(d)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Matrix Chain Multiplication",
        "problem_statement": (
            f"Given {n} matrices where the i-th matrix has dimensions dims[i-1] x dims[i], "
            f"find the minimum number of scalar multiplications needed to multiply all matrices together. "
            f"Use dynamic programming (Matrix Chain Multiplication DP)."
        ),
        "input_format": f"First line: N+1 space-separated integers representing the dimension array (N+1 values for N matrices).",
        "output_format": "A single integer — the minimum number of scalar multiplications.",
        "sample_input": " ".join(map(str, dims)),
        "sample_output": str(solve(dims)),
        "test_cases": tcs,
    }


def _hard_dp_word_break(rng: random.Random) -> Dict:
    words = ["cat", "cats", "and", "sand", "dog", "the", "a", "an", "in", "is"]
    dict_size = rng.randint(3, 6)
    word_dict = rng.sample(words, dict_size)
    s = "".join(rng.sample(word_dict, rng.randint(2, 3)))

    def solve(string, dictionary):
        n = len(string)
        dp = [False] * (n + 1)
        dp[0] = True
        for i in range(1, n + 1):
            for j in range(i):
                if dp[j] and string[j:i] in dictionary:
                    dp[i] = True
                    break
        return "true" if dp[n] else "false"

    def make_tc():
        d = rng.sample(words, rng.randint(3, 5))
        sx = "".join(rng.sample(d, rng.randint(2, 3)))
        if rng.random() < 0.3:
            sx += "xyz"
        return {"input": {"s": sx, "dict": d}, "output": solve(sx, set(d))}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Word Break Problem",
        "problem_statement": (
            f"Given a string S and a dictionary of words, determine if S can be segmented "
            f"into a space-separated sequence of one or more dictionary words. "
            f"Print true if possible, false otherwise. Use dynamic programming."
        ),
        "input_format": "First line: string S. Second line: space-separated dictionary words.",
        "output_format": "Print true if S can be segmented using dictionary words, false otherwise.",
        "sample_input": f"{s}\n{' '.join(word_dict)}",
        "sample_output": solve(s, set(word_dict)),
        "test_cases": tcs,
    }


def _hard_dp_palindrome_partitioning(rng: random.Random) -> Dict:
    length = rng.randint(5, 9)
    s = "".join(rng.choice("abc") for _ in range(length))

    def solve(string):
        n = len(string)
        is_pal = [[False] * n for _ in range(n)]
        for i in range(n):
            is_pal[i][i] = True
        for i in range(n - 1):
            is_pal[i][i + 1] = (string[i] == string[i + 1])
        for length in range(3, n + 1):
            for i in range(n - length + 1):
                j = i + length - 1
                is_pal[i][j] = (string[i] == string[j]) and is_pal[i + 1][j - 1]
        dp = [float('inf')] * n
        for i in range(n):
            if is_pal[0][i]:
                dp[i] = 0
            else:
                for j in range(1, i + 1):
                    if is_pal[j][i]:
                        dp[i] = min(dp[i], dp[j - 1] + 1)
        return dp[n - 1]

    def make_tc():
        x = "".join(rng.choice("abc") for _ in range(rng.randint(4, length)))
        return {"input": x, "output": solve(x)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Palindrome Partitioning — Minimum Cuts",
        "problem_statement": (
            f"Given a string S of length {length}, find the minimum number of cuts needed "
            f"to partition S such that every substring in the partition is a palindrome. "
            f"Use dynamic programming with palindrome precomputation."
        ),
        "input_format": "A single string on one line.",
        "output_format": "A single integer — the minimum number of cuts.",
        "sample_input": s,
        "sample_output": str(solve(s)),
        "test_cases": tcs,
    }


def _hard_dp_bitmask_tsp(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    INF = 10**9
    dist = [[INF] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0
        for j in range(n):
            if i != j:
                dist[i][j] = rng.randint(1, 20)

    def solve(d, nodes):
        dp = [[INF] * nodes for _ in range(1 << nodes)]
        dp[1][0] = 0
        for mask in range(1 << nodes):
            for u in range(nodes):
                if not (mask & (1 << u)):
                    continue
                if dp[mask][u] == INF:
                    continue
                for v in range(nodes):
                    if mask & (1 << v):
                        continue
                    new_mask = mask | (1 << v)
                    if dp[mask][u] + d[u][v] < dp[new_mask][v]:
                        dp[new_mask][v] = dp[mask][u] + d[u][v]
        full = (1 << nodes) - 1
        ans = INF
        for u in range(1, nodes):
            if dp[full][u] + d[u][0] < ans:
                ans = dp[full][u] + d[u][0]
        return ans if ans < INF else -1

    mat_str = "\n".join(" ".join(map(str, row)) for row in dist)
    sample_in = f"{n}\n{mat_str}"

    def make_tc():
        nn = rng.randint(3, n)
        d = [[INF] * nn for _ in range(nn)]
        for i in range(nn):
            d[i][i] = 0
            for j in range(nn):
                if i != j:
                    d[i][j] = rng.randint(1, 20)
        return {"input": {"nodes": nn, "dist": d}, "output": solve(d, nn)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Travelling Salesman Problem (Bitmask DP)",
        "problem_statement": (
            f"Given {n} cities and a distance matrix, find the minimum cost to visit all cities "
            f"exactly once and return to the starting city (city 0). "
            f"Use bitmask dynamic programming for an O(2^n * n^2) solution."
        ),
        "input_format": "First line: N. Next N lines: the N×N distance matrix.",
        "output_format": "A single integer — the minimum tour cost.",
        "sample_input": sample_in,
        "sample_output": str(solve(dist, n)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD TREE TEMPLATES
# ---------------------------------------------------------------------------

def _hard_tree_serialize_deserialize(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    vals = rng.sample(range(1, 50), n)

    def build_bst(values):
        if not values:
            return []
        root = values[0]
        left = [v for v in values[1:] if v < root]
        right = [v for v in values[1:] if v >= root]
        return [root] + build_bst(left) + build_bst(right)

    def solve(values):
        return " ".join(map(str, values))

    def make_tc():
        vv = rng.sample(range(1, 50), rng.randint(4, n))
        return {"input": vv, "output": solve(build_bst(vv))}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    bst_order = build_bst(vals)
    return {
        "title": "BST Preorder Traversal",
        "problem_statement": (
            f"Given {n} distinct integers inserted into a Binary Search Tree (BST) in the given order, "
            f"perform a preorder traversal (root, left, right) and print the node values. "
            f"Build the BST by inserting each value one by one."
        ),
        "input_format": "First line: N. Second line: N space-separated integers (insertion order).",
        "output_format": "The preorder traversal values separated by spaces.",
        "sample_input": f"{n}\n{' '.join(map(str, vals))}",
        "sample_output": solve(bst_order),
        "test_cases": tcs,
    }


def _hard_tree_path_sum(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    vals = [rng.randint(1, 20) for _ in range(n)]
    target = rng.randint(sum(vals[:3]), sum(vals[:5]))

    def solve(values, tgt):
        if not values:
            return "false"
        # Simulate a complete binary tree path sum check
        # Check if any root-to-leaf path sums to target
        def has_path(idx, remaining):
            if idx >= len(values):
                return False
            remaining -= values[idx]
            left = 2 * idx + 1
            right = 2 * idx + 2
            if left >= len(values) and right >= len(values):
                return remaining == 0
            return has_path(left, remaining) or has_path(right, remaining)
        return "true" if has_path(0, tgt) else "false"

    def make_tc():
        vv = [rng.randint(1, 20) for _ in range(rng.randint(4, n))]
        tgt = rng.randint(1, sum(vv))
        return {"input": {"values": vv, "target": tgt}, "output": solve(vv, tgt)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Path Sum in Binary Tree",
        "problem_statement": (
            f"Given a binary tree represented as a level-order array of {n} integers "
            f"and a target sum, determine if there exists a root-to-leaf path "
            f"whose node values sum to the target. Print true or false."
        ),
        "input_format": "First line: N and target. Second line: N space-separated integers (level-order tree).",
        "output_format": "Print true if such a path exists, false otherwise.",
        "sample_input": f"{n} {target}\n{' '.join(map(str, vals))}",
        "sample_output": solve(vals, target),
        "test_cases": tcs,
    }


def _hard_tree_kth_smallest_bst(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    vals = sorted(rng.sample(range(1, 50), n))
    k = rng.randint(1, n)

    def solve(sorted_vals, kk):
        return sorted_vals[kk - 1]

    def make_tc():
        vv = sorted(rng.sample(range(1, 50), rng.randint(4, n)))
        kk = rng.randint(1, len(vv))
        return {"input": {"values": vv, "k": kk}, "output": solve(vv, kk)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Kth Smallest Element in BST",
        "problem_statement": (
            f"Given a BST with {n} nodes (provided as sorted values for simplicity) "
            f"and an integer K, find the Kth smallest element. "
            f"Use inorder traversal which visits BST nodes in sorted order."
        ),
        "input_format": "First line: N and K. Second line: N space-separated integers (BST inorder = sorted).",
        "output_format": "A single integer — the Kth smallest element.",
        "sample_input": f"{n} {k}\n{' '.join(map(str, vals))}",
        "sample_output": str(solve(vals, k)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD SORTING TEMPLATES
# ---------------------------------------------------------------------------

def _hard_sorting_merge_k_sorted(rng: random.Random) -> Dict:
    k = rng.randint(3, 5)
    lists = [sorted(rng.randint(1, 50) for _ in range(rng.randint(2, 5))) for _ in range(k)]

    def solve(lsts):
        import heapq
        heap = []
        for i, lst in enumerate(lsts):
            if lst:
                heapq.heappush(heap, (lst[0], i, 0))
        result = []
        while heap:
            val, li, idx = heapq.heappop(heap)
            result.append(val)
            if idx + 1 < len(lsts[li]):
                heapq.heappush(heap, (lsts[li][idx + 1], li, idx + 1))
        return result

    result = solve(lists)
    lists_str = "\n".join(" ".join(map(str, lst)) for lst in lists)
    sample_in = f"{k}\n{lists_str}"

    def make_tc():
        kk = rng.randint(2, k)
        lsts = [sorted(rng.randint(1, 50) for _ in range(rng.randint(2, 4))) for _ in range(kk)]
        return {"input": {"k": kk, "lists": lsts}, "output": solve(lsts)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Merge K Sorted Lists",
        "problem_statement": (
            f"Given {k} sorted arrays, merge them into a single sorted array. "
            f"Use a min-heap (priority queue) for an efficient O(N log K) solution, "
            f"where N is the total number of elements."
        ),
        "input_format": (
            "First line: K (number of sorted arrays). "
            "Next K lines: each line contains the elements of one sorted array."
        ),
        "output_format": "A single line with all elements merged in sorted order, space-separated.",
        "sample_input": sample_in,
        "sample_output": " ".join(map(str, result)),
        "test_cases": tcs,
    }


def _hard_sorting_largest_number(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    nums = [rng.randint(1, 99) for _ in range(n)]

    def solve(a):
        from functools import cmp_to_key
        def cmp(x, y):
            if str(x) + str(y) > str(y) + str(x):
                return -1
            elif str(x) + str(y) < str(y) + str(x):
                return 1
            return 0
        s = sorted(a, key=cmp_to_key(cmp))
        result = "".join(map(str, s))
        return str(int(result))

    def make_tc():
        a = [rng.randint(1, 99) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Largest Number from Array",
        "problem_statement": (
            f"Given an array of {n} non-negative integers, arrange them to form the largest possible number. "
            f"For example, [3, 30, 34, 5, 9] → 9534330. "
            f"Use a custom comparator sort."
        ),
        "input_format": "First line: N. Second line: N space-separated non-negative integers.",
        "output_format": "A single string/integer — the largest number formed.",
        "sample_input": f"{n}\n{' '.join(map(str, nums))}",
        "sample_output": solve(nums),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# HARD SEARCHING TEMPLATES
# ---------------------------------------------------------------------------

def _hard_searching_median_two_arrays(rng: random.Random) -> Dict:
    n1 = rng.randint(2, 5)
    n2 = rng.randint(2, 5)
    arr1 = sorted(rng.randint(1, 50) for _ in range(n1))
    arr2 = sorted(rng.randint(1, 50) for _ in range(n2))

    def solve(a, b):
        merged = sorted(a + b)
        n = len(merged)
        if n % 2 == 1:
            return str(merged[n // 2])
        else:
            return f"{(merged[n//2-1] + merged[n//2]) / 2:.1f}"

    def make_tc():
        a = sorted(rng.randint(1, 50) for _ in range(rng.randint(2, n1)))
        b = sorted(rng.randint(1, 50) for _ in range(rng.randint(2, n2)))
        return {"input": {"arr1": a, "arr2": b}, "output": solve(a, b)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Median of Two Sorted Arrays",
        "problem_statement": (
            f"Given two sorted arrays of sizes {n1} and {n2}, find the median of the combined sorted array. "
            f"If the total length is odd, return the middle element. "
            f"If even, return the average of the two middle elements (as a decimal with 1 place). "
            f"An O(log(min(m,n))) binary search solution is expected."
        ),
        "input_format": (
            "First line: N1 and N2. "
            "Second line: N1 sorted integers. "
            "Third line: N2 sorted integers."
        ),
        "output_format": "The median value (integer or decimal with 1 decimal place).",
        "sample_input": f"{n1} {n2}\n{' '.join(map(str, arr1))}\n{' '.join(map(str, arr2))}",
        "sample_output": solve(arr1, arr2),
        "test_cases": tcs,
    }


def _hard_searching_kth_smallest_matrix(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    matrix = [sorted(rng.randint(1, 50) for _ in range(n)) for _ in range(n)]
    k = rng.randint(1, n * n)

    def solve(mat, kk):
        import heapq
        heap = [(mat[0][0], 0, 0)]
        visited = {(0, 0)}
        count = 0
        while heap:
            val, r, c = heapq.heappop(heap)
            count += 1
            if count == kk:
                return val
            for nr, nc in [(r + 1, c), (r, c + 1)]:
                if nr < len(mat) and nc < len(mat[0]) and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    heapq.heappush(heap, (mat[nr][nc], nr, nc))
        return -1

    mat_str = "\n".join(" ".join(map(str, row)) for row in matrix)
    sample_in = f"{n} {k}\n{mat_str}"

    def make_tc():
        nn = rng.randint(2, n)
        mat = [sorted(rng.randint(1, 50) for _ in range(nn)) for _ in range(nn)]
        kk = rng.randint(1, nn * nn)
        return {"input": {"n": nn, "k": kk, "matrix": mat}, "output": solve(mat, kk)}

    tcs = [make_tc() for _ in range(rng.randint(6, 10))]
    return {
        "title": "Kth Smallest Element in Sorted Matrix",
        "problem_statement": (
            f"Given an {n}×{n} matrix where each row and column is sorted in ascending order, "
            f"find the Kth smallest element. "
            f"Use binary search on the value range or a min-heap approach."
        ),
        "input_format": "First line: N and K. Next N lines: each row of the matrix.",
        "output_format": "A single integer — the Kth smallest element.",
        "sample_input": sample_in,
        "sample_output": str(solve(matrix, k)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# MEDIUM TEMPLATES (more algorithmic than easy, less complex than hard)
# These are the existing templates from dynamic_generator.py — they are
# already medium-level. We just reference them here for the registry.
# ---------------------------------------------------------------------------
# (Medium templates are imported from dynamic_generator.py directly)


# ---------------------------------------------------------------------------
# DIFFICULTY-AWARE TOPIC REGISTRY
# Maps (topic, difficulty) -> list of template functions
# ---------------------------------------------------------------------------

# These are imported lazily to avoid circular imports
def _get_difficulty_templates():
    """
    Returns a dict mapping (topic, difficulty) -> [template_functions].
    Medium templates are pulled from dynamic_generator's TOPIC_TEMPLATES.
    """
    try:
        from model.dynamic_generator import (
            _array_max_subarray, _array_two_sum, _array_rotate,
            _array_product_except_self, _array_missing_number,
            _string_longest_palindrome, _string_anagram_check,
            _string_reverse_words, _string_longest_common_prefix, _string_count_vowels,
            _graph_bfs_shortest_path, _graph_number_of_islands,
            _graph_detect_cycle, _graph_topological_sort, _graph_dijkstra,
            _dp_knapsack, _dp_longest_common_subsequence,
            _dp_coin_change, _dp_longest_increasing_subsequence, _dp_edit_distance,
            _tree_inorder, _tree_max_depth, _tree_level_order,
            _tree_diameter, _tree_lowest_common_ancestor,
            _stack_valid_parentheses, _stack_next_greater_element,
            _stack_min_stack, _stack_evaluate_rpn, _stack_largest_rectangle_histogram,
            _queue_sliding_window_max, _queue_first_non_repeating,
            _queue_circular_queue, _queue_task_scheduler, _queue_bfs_level_order,
            _greedy_activity_selection, _greedy_fractional_knapsack,
            _greedy_jump_game, _greedy_minimum_platforms,
            _hashing_group_anagrams, _hashing_subarray_sum_k,
            _hashing_longest_consecutive, _hashing_top_k_frequent,
            _sorting_merge_sort, _sorting_kth_largest,
            _sorting_count_inversions, _sorting_sort_colors, _sorting_merge_intervals,
            _searching_binary_search, _searching_search_rotated,
            _searching_find_peak, _searching_first_last_position, _searching_sqrt_integer,
            _recursion_fibonacci, _recursion_power,
            _recursion_tower_of_hanoi, _recursion_flatten_nested, _recursion_gcd,
            _backtracking_permutations, _backtracking_subsets,
            _backtracking_n_queens_count, _backtracking_combination_sum, _backtracking_word_search,
            _ll_reverse, _ll_detect_cycle, _ll_merge_sorted, _ll_nth_from_end, _ll_palindrome,
            _two_ptr_three_sum, _two_ptr_container_water,
            _two_ptr_remove_duplicates, _two_ptr_sort_squares, _two_ptr_trapping_rain,
            _sw_longest_substring_no_repeat, _sw_max_sum_subarray_k,
            _sw_minimum_window_substring, _sw_longest_ones_after_flip, _sw_count_anagram_occurrences,
            _bs_find_minimum_rotated, _bs_capacity_to_ship,
            _bs_koko_eating_bananas, _bs_median_two_sorted, _bs_allocate_books,
            _math_sieve_primes, _math_prime_factors,
            _math_pascal_triangle, _math_count_digits, _math_modular_exponentiation,
            _bit_single_number, _bit_count_set_bits,
            _bit_power_of_two, _bit_reverse_bits, _bit_subsets_bitmask,
        )
    except ImportError:
        return {}

    return {
        # ── ARRAYS ──────────────────────────────────────────────────────────
        ("arrays", "easy"): [
            _easy_array_sum, _easy_array_max, _easy_array_reverse,
            _easy_array_count_even_odd, _easy_array_linear_search,
        ],
        ("arrays", "medium"): [
            _array_max_subarray, _array_two_sum, _array_rotate,
            _array_product_except_self, _array_missing_number,
        ],
        ("arrays", "hard"): [
            _hard_array_max_subarray_with_indices, _hard_array_range_sum_queries,
            _hard_array_trapping_rain_water, _hard_array_longest_increasing_subarray,
            _hard_array_count_inversions,
        ],
        # ── STRINGS ─────────────────────────────────────────────────────────
        ("strings", "easy"): [
            _easy_string_reverse, _easy_string_palindrome_check,
            _easy_string_count_chars, _easy_string_uppercase, _easy_string_length,
        ],
        ("strings", "medium"): [
            _string_longest_palindrome, _string_anagram_check,
            _string_reverse_words, _string_longest_common_prefix, _string_count_vowels,
        ],
        ("strings", "hard"): [
            _hard_string_longest_without_repeat, _hard_string_minimum_window,
            _hard_string_edit_distance, _hard_string_count_distinct_subsequences,
        ],
        # ── GRAPHS ──────────────────────────────────────────────────────────
        ("graphs", "easy"): [
            _graph_bfs_shortest_path, _graph_number_of_islands, _graph_detect_cycle,
        ],
        ("graphs", "medium"): [
            _graph_bfs_shortest_path, _graph_number_of_islands,
            _graph_detect_cycle, _graph_topological_sort, _graph_dijkstra,
        ],
        ("graphs", "hard"): [
            _hard_graph_bellman_ford, _hard_graph_strongly_connected,
            _hard_graph_floyd_warshall, _graph_dijkstra, _graph_topological_sort,
        ],
        # ── DYNAMIC PROGRAMMING ─────────────────────────────────────────────
        ("dynamic programming", "easy"): [
            _recursion_fibonacci, _dp_coin_change, _dp_longest_increasing_subsequence,
        ],
        ("dynamic programming", "medium"): [
            _dp_knapsack, _dp_longest_common_subsequence,
            _dp_coin_change, _dp_longest_increasing_subsequence, _dp_edit_distance,
        ],
        ("dynamic programming", "hard"): [
            _hard_dp_matrix_chain, _hard_dp_word_break,
            _hard_dp_palindrome_partitioning, _hard_dp_bitmask_tsp,
            _dp_knapsack, _dp_edit_distance,
        ],
        # ── TREES ────────────────────────────────────────────────────────────
        ("trees", "easy"): [
            _tree_inorder, _tree_max_depth, _tree_level_order,
        ],
        ("trees", "medium"): [
            _tree_inorder, _tree_max_depth, _tree_level_order,
            _tree_diameter, _tree_lowest_common_ancestor,
        ],
        ("trees", "hard"): [
            _hard_tree_serialize_deserialize, _hard_tree_path_sum,
            _hard_tree_kth_smallest_bst, _tree_diameter, _tree_lowest_common_ancestor,
        ],
        # ── STACKS ───────────────────────────────────────────────────────────
        ("stacks", "easy"): [
            _stack_valid_parentheses, _stack_min_stack,
        ],
        ("stacks", "medium"): [
            _stack_valid_parentheses, _stack_next_greater_element,
            _stack_min_stack, _stack_evaluate_rpn, _stack_largest_rectangle_histogram,
        ],
        ("stacks", "hard"): [
            _stack_largest_rectangle_histogram, _stack_evaluate_rpn,
            _stack_next_greater_element,
        ],
        # ── QUEUES ───────────────────────────────────────────────────────────
        ("queues", "easy"): [
            _queue_first_non_repeating, _queue_circular_queue,
        ],
        ("queues", "medium"): [
            _queue_sliding_window_max, _queue_first_non_repeating,
            _queue_circular_queue, _queue_task_scheduler, _queue_bfs_level_order,
        ],
        ("queues", "hard"): [
            _queue_sliding_window_max, _queue_task_scheduler, _queue_bfs_level_order,
        ],
        # ── GREEDY ───────────────────────────────────────────────────────────
        ("greedy", "easy"): [
            _greedy_activity_selection, _greedy_jump_game,
        ],
        ("greedy", "medium"): [
            _greedy_activity_selection, _greedy_fractional_knapsack,
            _greedy_jump_game, _greedy_minimum_platforms,
        ],
        ("greedy", "hard"): [
            _greedy_fractional_knapsack, _greedy_minimum_platforms,
        ],
        # ── HASHING ──────────────────────────────────────────────────────────
        ("hashing", "easy"): [
            _hashing_top_k_frequent, _hashing_group_anagrams,
        ],
        ("hashing", "medium"): [
            _hashing_group_anagrams, _hashing_subarray_sum_k,
            _hashing_longest_consecutive, _hashing_top_k_frequent,
        ],
        ("hashing", "hard"): [
            _hashing_subarray_sum_k, _hashing_longest_consecutive,
            _hashing_group_anagrams,
        ],
        # ── SORTING ──────────────────────────────────────────────────────────
        ("sorting", "easy"): [
            _easy_sorting_bubble, _easy_sorting_find_second_max,
        ],
        ("sorting", "medium"): [
            _sorting_merge_sort, _sorting_kth_largest,
            _sorting_sort_colors, _sorting_merge_intervals,
        ],
        ("sorting", "hard"): [
            _hard_sorting_merge_k_sorted, _hard_sorting_largest_number,
            _sorting_count_inversions, _sorting_kth_largest,
        ],
        # ── SEARCHING ────────────────────────────────────────────────────────
        ("searching", "easy"): [
            _easy_array_linear_search, _searching_binary_search,
        ],
        ("searching", "medium"): [
            _searching_binary_search, _searching_search_rotated,
            _searching_find_peak, _searching_first_last_position, _searching_sqrt_integer,
        ],
        ("searching", "hard"): [
            _hard_searching_median_two_arrays, _hard_searching_kth_smallest_matrix,
            _searching_search_rotated, _bs_allocate_books,
        ],
        # ── RECURSION ────────────────────────────────────────────────────────
        ("recursion", "easy"): [
            _easy_recursion_sum_natural, _easy_recursion_power,
            _easy_math_factorial, _easy_math_fibonacci,
        ],
        ("recursion", "medium"): [
            _recursion_fibonacci, _recursion_power,
            _recursion_tower_of_hanoi, _recursion_flatten_nested, _recursion_gcd,
        ],
        ("recursion", "hard"): [
            _backtracking_permutations, _backtracking_n_queens_count,
            _backtracking_combination_sum, _backtracking_word_search,
        ],
        # ── BACKTRACKING ─────────────────────────────────────────────────────
        ("backtracking", "easy"): [
            _backtracking_subsets, _backtracking_permutations,
        ],
        ("backtracking", "medium"): [
            _backtracking_permutations, _backtracking_subsets,
            _backtracking_n_queens_count, _backtracking_combination_sum,
        ],
        ("backtracking", "hard"): [
            _backtracking_n_queens_count, _backtracking_combination_sum,
            _backtracking_word_search,
        ],
        # ── LINKED LISTS ─────────────────────────────────────────────────────
        ("linked-lists", "easy"): [
            _ll_reverse, _ll_nth_from_end,
        ],
        ("linked-lists", "medium"): [
            _ll_reverse, _ll_detect_cycle, _ll_merge_sorted,
            _ll_nth_from_end, _ll_palindrome,
        ],
        ("linked-lists", "hard"): [
            _ll_detect_cycle, _ll_merge_sorted, _ll_palindrome,
        ],
        # ── TWO POINTERS ─────────────────────────────────────────────────────
        ("two pointers", "easy"): [
            _two_ptr_remove_duplicates, _two_ptr_sort_squares,
        ],
        ("two pointers", "medium"): [
            _two_ptr_three_sum, _two_ptr_container_water,
            _two_ptr_remove_duplicates, _two_ptr_sort_squares, _two_ptr_trapping_rain,
        ],
        ("two pointers", "hard"): [
            _two_ptr_three_sum, _two_ptr_container_water, _two_ptr_trapping_rain,
        ],
        # ── SLIDING WINDOW ───────────────────────────────────────────────────
        ("sliding window", "easy"): [
            _sw_max_sum_subarray_k, _sw_longest_substring_no_repeat,
        ],
        ("sliding window", "medium"): [
            _sw_longest_substring_no_repeat, _sw_max_sum_subarray_k,
            _sw_longest_ones_after_flip, _sw_count_anagram_occurrences,
        ],
        ("sliding window", "hard"): [
            _sw_minimum_window_substring, _sw_longest_ones_after_flip,
            _sw_count_anagram_occurrences,
        ],
        # ── BINARY SEARCH ────────────────────────────────────────────────────
        ("binary search", "easy"): [
            _searching_binary_search, _searching_find_peak,
        ],
        ("binary search", "medium"): [
            _bs_find_minimum_rotated, _bs_capacity_to_ship,
            _bs_koko_eating_bananas, _bs_allocate_books,
        ],
        ("binary search", "hard"): [
            _hard_searching_median_two_arrays, _hard_searching_kth_smallest_matrix,
            _bs_median_two_sorted, _bs_allocate_books,
        ],
        # ── MATH ─────────────────────────────────────────────────────────────
        ("math", "easy"): [
            _easy_math_factorial, _easy_math_fibonacci,
            _easy_math_prime_check, _easy_math_sum_digits, _easy_math_gcd,
        ],
        ("math", "medium"): [
            _math_sieve_primes, _math_prime_factors,
            _math_pascal_triangle, _math_count_digits, _math_modular_exponentiation,
        ],
        ("math", "hard"): [
            _math_modular_exponentiation, _math_sieve_primes,
            _math_prime_factors, _hard_dp_bitmask_tsp,
        ],
        # ── BIT MANIPULATION ─────────────────────────────────────────────────
        ("bit manipulation", "easy"): [
            _bit_single_number, _bit_count_set_bits, _bit_power_of_two,
        ],
        ("bit manipulation", "medium"): [
            _bit_single_number, _bit_count_set_bits,
            _bit_power_of_two, _bit_reverse_bits, _bit_subsets_bitmask,
        ],
        ("bit manipulation", "hard"): [
            _bit_subsets_bitmask, _bit_reverse_bits, _bit_count_set_bits,
        ],
    }


# Cache the registry after first load
_DIFFICULTY_REGISTRY = None


def get_difficulty_templates(topic: str, difficulty: str):
    """
    Get the list of template functions for a given topic and difficulty.
    Returns None if no specific templates exist (caller should use default).
    """
    global _DIFFICULTY_REGISTRY
    if _DIFFICULTY_REGISTRY is None:
        _DIFFICULTY_REGISTRY = _get_difficulty_templates()
    return _DIFFICULTY_REGISTRY.get((topic, difficulty))
