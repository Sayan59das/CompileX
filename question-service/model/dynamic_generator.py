"""
dynamic_generator.py
Dynamically generates unique coding questions and computed test cases every call.
No external dependencies beyond Python stdlib (random, uuid, hashlib, collections, heapq, math).

ENHANCED WITH TITLE VARIATIONS:
- Each question template has multiple title variations
- Ensures every generated question has a different title
- Adds variety through synonyms and rephrasing
"""

import random
import uuid
import hashlib
import math
import heapq
from collections import defaultdict, deque
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed() -> int:
    return int(uuid.uuid4().int % (2**31))


class NoFreshQuestion(LookupError):
    """The caller has already had every template for this topic and difficulty."""


def _uid() -> str:
    return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:8]


def _rng() -> random.Random:
    return random.Random(_seed())


# ---------------------------------------------------------------------------
# Module-level title tracker — prevents any title from repeating within the
# same process lifetime (survives across API requests on the same server).
# Stores the last MAX_TRACKED varied titles that were handed out.
# ---------------------------------------------------------------------------
_MAX_TRACKED = 500
_used_titles: List[str] = []          # ordered list, newest last
_used_titles_set: set = set()         # fast lookup


def _record_title(title: str) -> None:
    global _used_titles
    low = title.lower()
    if low in _used_titles_set:
        return
    _used_titles.append(low)
    _used_titles_set.add(low)
    if len(_used_titles) > _MAX_TRACKED:
        oldest = _used_titles.pop(0)
        _used_titles_set.discard(oldest)


def _title_used(title: str) -> bool:
    return title.lower() in _used_titles_set


def clear_title_cache() -> None:
    """Reset the in-process title tracker (useful for testing)."""
    global _used_titles
    _used_titles.clear()
    _used_titles_set.clear()


def _vary_title(base_title: str, rng: random.Random, exclude_set: set = None) -> str:
    """
    Return a completely different title phrasing every call.
    Every base title has 10+ distinct variations so no two questions
    look the same even when drawn from the same template.
    When a variation is picked, a small unique numeric tag is appended
    to guarantee no two calls ever produce the exact same string.
    """
    if exclude_set is None:
        exclude_set = set()
    variations = {
        # ── Arrays ──────────────────────────────────────────────────────────
        "Maximum Subarray Sum": [
            "Maximum Subarray Sum",
            "Find the Largest Contiguous Subarray Sum",
            "Kadane's Algorithm: Max Subarray",
            "Peak Contiguous Subarray Value",
            "Greatest Sum Among All Subarrays",
            "Optimal Subarray Sum Problem",
            "Highest Sum Contiguous Segment",
            "Max Sum Subarray Finder",
            "Subarray with Maximum Total",
            "Best Subarray Sum Challenge",
        ],
        "Two Sum": [
            "Two Sum",
            "Find Pair with Given Sum",
            "Locate Two Indices That Add to Target",
            "Pair Sum Index Finder",
            "Target Sum Pair Problem",
            "Two Numbers Summing to K",
            "Index Pair for Target Total",
            "Sum Pair Lookup",
            "Find Two Elements Equal to Target",
            "Dual Index Sum Problem",
        ],
        "Rotate Array": [
            "Rotate Array",
            "Circular Shift of Array Elements",
            "Right Rotation by K Steps",
            "Array Cyclic Rotation",
            "Shift Array K Positions Right",
            "Wrap-Around Array Rotation",
            "K-Step Array Shift",
            "Rotate Elements Rightward",
            "Array Right Rotation Problem",
            "Cyclic Element Displacement",
        ],
        "Product of Array Except Self": [
            "Product of Array Except Self",
            "Array Product Without Current Element",
            "Compute Product Excluding Index",
            "Division-Free Product Array",
            "Product Array Without Self",
            "Prefix-Suffix Product Problem",
            "Exclude-Self Multiplication Array",
            "Product of All Other Elements",
            "Array Product Puzzle",
            "No-Division Product Computation",
        ],
        "Find the Missing Number": [
            "Find the Missing Number",
            "Locate the Absent Integer",
            "Missing Element in Range",
            "Identify the Gap in Sequence",
            "Which Number Is Missing?",
            "Absent Value in Array",
            "Find the Omitted Integer",
            "Detect Missing Element",
            "Gap Finder in Integer Range",
            "Missing Integer Detection",
        ],
        # ── Strings ─────────────────────────────────────────────────────────
        "Valid Anagram": [
            "Valid Anagram",
            "Check if Two Strings Are Anagrams",
            "Anagram Verification Problem",
            "Same Characters Different Order",
            "Detect Anagram Pair",
            "Character Frequency Match",
            "Anagram or Not?",
            "Rearrangement Check",
            "Letter Permutation Equality",
            "Anagram Detector",
        ],
        "Longest Palindromic Substring": [
            "Longest Palindromic Substring",
            "Find the Longest Palindrome in a String",
            "Maximum Length Palindrome Segment",
            "Palindrome Substring Finder",
            "Longest Mirror Substring",
            "Expand-Around-Center Palindrome",
            "Biggest Palindromic Segment",
            "Longest Symmetric Substring",
            "Peak Palindrome in String",
            "Palindrome Length Maximizer",
        ],
        "Reverse Words in a String": [
            "Reverse Words in a String",
            "Flip Word Order in Sentence",
            "Invert Word Sequence",
            "Backwards Word Arrangement",
            "Reverse the Sentence Words",
            "Word Order Reversal",
            "Sentence Word Flip",
            "Reverse Token Order",
            "Inverted Word Sequence Problem",
            "Mirror Word Arrangement",
        ],
        "Longest Common Prefix": [
            "Longest Common Prefix",
            "Find Shared Starting Substring",
            "Common Prefix Among Strings",
            "Longest Shared Prefix",
            "Prefix Intersection of Strings",
            "Maximum Common Start",
            "Shared Beginning of All Strings",
            "Common String Prefix Finder",
            "Longest Matching Prefix",
            "Prefix Overlap Problem",
        ],
        "Count Vowels in String": [
            "Count Vowels in String",
            "Vowel Frequency Counter",
            "How Many Vowels?",
            "Count a-e-i-o-u Occurrences",
            "Vowel Tally in Text",
            "String Vowel Counter",
            "Enumerate Vowels in Input",
            "Vowel Detection Problem",
            "Count Vocal Characters",
            "Vowel Occurrence Finder",
        ],
        # ── Graphs ──────────────────────────────────────────────────────────
        "BFS Shortest Path in Unweighted Graph": [
            "BFS Shortest Path in Unweighted Graph",
            "Minimum Hops Between Two Nodes",
            "Shortest Route via BFS",
            "Fewest Edges from Source to Destination",
            "Unweighted Graph Shortest Distance",
            "BFS Distance Between Nodes",
            "Minimum Edge Path Problem",
            "Shortest Unweighted Path Finder",
            "Graph BFS Distance Query",
            "Least Edges Path Problem",
        ],
        "Number of Islands": [
            "Number of Islands",
            "Count Connected Land Regions",
            "Island Counter in Binary Grid",
            "How Many Islands in the Grid?",
            "Connected Component Count in Grid",
            "Land Mass Counter",
            "Grid Island Detection",
            "Count Isolated Land Clusters",
            "Binary Grid Island Problem",
            "Flood Fill Island Counter",
        ],
        "Detect Cycle in Undirected Graph": [
            "Detect Cycle in Undirected Graph",
            "Does This Graph Have a Loop?",
            "Cycle Detection in Graph",
            "Find Circular Path in Graph",
            "Graph Cycle Checker",
            "Undirected Graph Loop Finder",
            "Is There a Cycle?",
            "Back Edge Detection Problem",
            "Graph Circularity Test",
            "Cycle Existence in Undirected Graph",
        ],
        "Topological Sort (Kahn's Algorithm)": [
            "Topological Sort (Kahn's Algorithm)",
            "DAG Node Ordering Problem",
            "Dependency Resolution Order",
            "Linear Ordering of DAG Nodes",
            "Topological Ordering via BFS",
            "Kahn's Topological Sort",
            "Task Dependency Sequencing",
            "DAG Traversal Order",
            "Directed Acyclic Graph Ordering",
            "Prerequisite-Based Node Ordering",
        ],
        "Dijkstra's Shortest Path": [
            "Dijkstra's Shortest Path",
            "Minimum Cost Path in Weighted Graph",
            "Shortest Weighted Distance from Source",
            "Greedy Shortest Path Algorithm",
            "Weighted Graph Distance Problem",
            "Optimal Path Cost Finder",
            "Single Source Shortest Path",
            "Minimum Weight Path Problem",
            "Dijkstra Distance Query",
            "Weighted Shortest Route Finder",
        ],
        # ── Dynamic Programming ─────────────────────────────────────────────
        "0/1 Knapsack Problem": [
            "0/1 Knapsack Problem",
            "Maximum Value Within Weight Limit",
            "Item Selection for Max Profit",
            "Weight-Constrained Value Maximization",
            "Binary Knapsack Challenge",
            "Optimal Item Packing Problem",
            "Capacity-Limited Value Maximizer",
            "Knapsack DP Problem",
            "Best Item Combination Under Capacity",
            "Weight Budget Optimization",
        ],
        "Longest Common Subsequence": [
            "Longest Common Subsequence",
            "LCS of Two Strings",
            "Maximum Shared Subsequence Length",
            "Common Subsequence Finder",
            "Longest Matching Subsequence",
            "Shared Character Sequence Problem",
            "LCS DP Problem",
            "Subsequence Overlap Maximizer",
            "Longest Mutual Subsequence",
            "Common Sequence Length Problem",
        ],
        "Coin Change — Minimum Coins": [
            "Coin Change — Minimum Coins",
            "Fewest Coins to Make Amount",
            "Minimum Denomination Count",
            "Optimal Coin Selection Problem",
            "Least Coins for Target Sum",
            "Coin Combination Minimizer",
            "Minimum Coins Required",
            "Change-Making DP Problem",
            "Smallest Coin Count for Amount",
            "Coin Denomination Optimizer",
        ],
        "Longest Increasing Subsequence": [
            "Longest Increasing Subsequence",
            "LIS of an Array",
            "Maximum Strictly Increasing Subsequence",
            "Longest Growing Subsequence",
            "Increasing Subsequence Length Problem",
            "LIS DP Challenge",
            "Longest Ascending Subsequence",
            "Maximum Monotone Subsequence",
            "Strictly Increasing Sequence Finder",
            "Longest Upward Subsequence",
        ],
        "Edit Distance (Levenshtein)": [
            "Edit Distance (Levenshtein)",
            "Minimum String Transformation Cost",
            "Fewest Edits to Convert Strings",
            "String Edit Distance Problem",
            "Levenshtein Distance Computation",
            "Minimum Operations to Match Strings",
            "String Similarity via Edit Distance",
            "Optimal String Conversion Cost",
            "Character Edit Minimizer",
            "Minimum Insert-Delete-Replace Count",
        ],
        # ── Trees ────────────────────────────────────────────────────────────
        "BST Inorder Traversal": [
            "BST Inorder Traversal",
            "Sorted Output from BST",
            "In-Order BST Walk",
            "Left-Root-Right BST Traversal",
            "BST Ascending Order Output",
            "Binary Search Tree Inorder",
            "Sorted BST Node Sequence",
            "Inorder Walk of Binary Tree",
            "BST Traversal in Sorted Order",
            "Ascending BST Node Listing",
        ],
        "Maximum Depth of Binary Tree": [
            "Maximum Depth of Binary Tree",
            "Height of a Binary Tree",
            "Deepest Level in BST",
            "Longest Root-to-Leaf Path",
            "Tree Height Computation",
            "Maximum Tree Depth Finder",
            "BST Depth Problem",
            "Tallest Branch in Binary Tree",
            "Root-to-Leaf Maximum Distance",
            "Binary Tree Height Problem",
        ],
        "Binary Tree Level Order Traversal": [
            "Binary Tree Level Order Traversal",
            "BFS Traversal of Binary Tree",
            "Layer-by-Layer Tree Output",
            "Breadth-First Tree Walk",
            "Level-Wise BST Traversal",
            "Tree Level Grouping Problem",
            "Horizontal Tree Traversal",
            "BST BFS Level Output",
            "Row-by-Row Tree Traversal",
            "Level Order BST Walk",
        ],
        "Diameter of Binary Tree": [
            "Diameter of Binary Tree",
            "Longest Path in Binary Tree",
            "Maximum Node-to-Node Distance",
            "Tree Diameter Computation",
            "Widest Path in BST",
            "Longest Branch-to-Branch Path",
            "Binary Tree Diameter Problem",
            "Maximum Distance Between Leaves",
            "Tree Width via Diameter",
            "Farthest Nodes in Binary Tree",
        ],
        "Lowest Common Ancestor of BST": [
            "Lowest Common Ancestor of BST",
            "LCA in Binary Search Tree",
            "Deepest Common Ancestor",
            "Shared Ancestor Finder",
            "Nearest Common Parent in BST",
            "LCA Problem in BST",
            "Common Ancestor Detection",
            "Deepest Shared Node in BST",
            "BST Ancestor Query",
            "Lowest Shared Parent Problem",
        ],
        # ── Stacks ───────────────────────────────────────────────────────────
        "Valid Parentheses": [
            "Valid Parentheses",
            "Balanced Bracket Checker",
            "Is the Bracket String Valid?",
            "Matching Parentheses Problem",
            "Bracket Balance Verification",
            "Parenthesis Validity Check",
            "Nested Bracket Validator",
            "Bracket Pair Matching",
            "Well-Formed Bracket Sequence",
            "Bracket Correctness Problem",
        ],
        "Next Greater Element": [
            "Next Greater Element",
            "First Larger Value to the Right",
            "Right Neighbor Greater Than Self",
            "Next Bigger Number Finder",
            "Monotonic Stack Greater Element",
            "Rightward Greater Value Problem",
            "Stack-Based Next Greater",
            "Find Next Larger in Array",
            "Greater Element to the Right",
            "Next Dominant Element Problem",
        ],
        "Min Stack": [
            "Min Stack",
            "Stack with O(1) Minimum Query",
            "Constant-Time Minimum Stack",
            "Stack Supporting getMin in O(1)",
            "Minimum-Tracking Stack",
            "Stack with Minimum Access",
            "O(1) Min Stack Design",
            "Stack Minimum Retrieval Problem",
            "Efficient Minimum Stack",
            "Stack with Instant Min Lookup",
        ],
        "Evaluate Reverse Polish Notation": [
            "Evaluate Reverse Polish Notation",
            "RPN Expression Evaluator",
            "Postfix Expression Calculator",
            "Stack-Based RPN Evaluation",
            "Compute Postfix Arithmetic",
            "Reverse Polish Calculator",
            "Postfix Notation Problem",
            "RPN Stack Computation",
            "Evaluate Postfix Expression",
            "Arithmetic RPN Solver",
        ],
        "Largest Rectangle in Histogram": [
            "Largest Rectangle in Histogram",
            "Maximum Area Rectangle in Bar Chart",
            "Biggest Rectangle Under Histogram",
            "Histogram Max Area Problem",
            "Largest Bar Chart Rectangle",
            "Maximum Histogram Rectangle",
            "Stack-Based Histogram Area",
            "Peak Rectangle in Bar Graph",
            "Optimal Rectangle in Histogram",
            "Max Area Under Histogram Bars",
        ],
        # ── Queues ───────────────────────────────────────────────────────────
        "Sliding Window Maximum": [
            "Sliding Window Maximum",
            "Maximum in Every K-Size Window",
            "Rolling Window Peak Finder",
            "Deque-Based Window Maximum",
            "Max Value in Sliding Frame",
            "Window Maximum Problem",
            "K-Window Peak Tracker",
            "Sliding Frame Maximum Query",
            "Maximum Across Moving Window",
            "Window-Based Max Finder",
        ],
        "First Non-Repeating Character": [
            "First Non-Repeating Character",
            "First Unique Character in String",
            "Earliest Non-Duplicate Letter",
            "First Singleton Character",
            "Leftmost Unique Character",
            "First Character Appearing Once",
            "Non-Repeating Letter Finder",
            "Unique Character Position Problem",
            "First Distinct Character",
            "Earliest Unique Letter Problem",
        ],
        "Circular Queue Simulation": [
            "Circular Queue Simulation",
            "Ring Buffer Queue Operations",
            "Bounded Circular Queue Problem",
            "Fixed-Size Queue Simulator",
            "Circular Buffer Implementation",
            "Queue with Wrap-Around",
            "Ring Queue Operation Simulator",
            "Circular FIFO Queue Problem",
            "Bounded Queue Simulation",
            "Wrap-Around Queue Challenge",
        ],
        "Task Scheduler": [
            "Task Scheduler",
            "CPU Task Scheduling with Cooldown",
            "Minimum Intervals for Task Completion",
            "Task Cooldown Scheduler",
            "Greedy CPU Task Ordering",
            "Minimum Time to Finish Tasks",
            "Task Execution with Idle Slots",
            "Cooldown-Based Task Planner",
            "Optimal Task Scheduling Problem",
            "CPU Scheduling Minimizer",
        ],
        "BFS Level-Order Distances": [
            "BFS Level-Order Distances",
            "Graph BFS Distance from Source",
            "Shortest Hop Count via BFS",
            "BFS Distance Array Problem",
            "Level-Wise Graph Distance",
            "BFS All-Nodes Distance Query",
            "Minimum Hops from Source Node",
            "BFS Traversal Distance Problem",
            "Graph Distance via Breadth-First",
            "Source-to-All BFS Distance",
        ],
        # ── Greedy ───────────────────────────────────────────────────────────
        "Activity Selection Problem": [
            "Activity Selection Problem",
            "Maximum Non-Overlapping Activities",
            "Greedy Interval Scheduling",
            "Most Activities Without Conflict",
            "Optimal Activity Picker",
            "Non-Conflicting Event Selector",
            "Maximum Compatible Activities",
            "Interval Scheduling Maximization",
            "Greedy Activity Planner",
            "Conflict-Free Activity Selection",
        ],
        "Fractional Knapsack": [
            "Fractional Knapsack",
            "Greedy Fractional Item Selection",
            "Maximum Value with Fractional Items",
            "Partial Item Knapsack Problem",
            "Greedy Weight-Value Optimizer",
            "Fractional Item Packing",
            "Continuous Knapsack Problem",
            "Value-per-Weight Greedy Problem",
            "Fractional Capacity Maximizer",
            "Greedy Partial Knapsack",
        ],
        "Jump Game": [
            "Jump Game",
            "Can You Reach the Last Index?",
            "Array Jump Reachability",
            "Greedy Jump Feasibility",
            "Last Index Reachability Problem",
            "Jump Array Traversal",
            "Can You Make It to the End?",
            "Greedy Reachability Check",
            "Array Hop Feasibility",
            "Jump Length Reachability",
        ],
        "Minimum Number of Platforms": [
            "Minimum Number of Platforms",
            "Minimum Train Platforms Required",
            "Peak Concurrent Train Count",
            "Platform Allocation Problem",
            "Minimum Stations for All Trains",
            "Train Overlap Minimizer",
            "Concurrent Train Platform Problem",
            "Minimum Parallel Tracks Needed",
            "Train Schedule Platform Count",
            "Greedy Platform Minimization",
        ],
    }

    if base_title in variations:
        pool = variations[base_title]
        # Prefer a variation not in the exclude set; fall back to full pool if all excluded
        available = [v for v in pool if v.lower() not in exclude_set]
        if not available:
            available = pool
        return rng.choice(available)

    # Generic fallback — combine prefix + base_title + suffix + unique token
    prefixes = ["Solve", "Compute", "Find", "Determine", "Calculate",
                "Identify", "Detect", "Evaluate", "Analyze", "Process",
                "Implement", "Design", "Build", "Optimize", "Construct"]
    suffixes = [" Problem", " Challenge", " Task", " Query",
                " Puzzle", " Exercise", " Question", " Computation",
                " Algorithm", " Solution", " Approach", " Method"]
    # Use a short random token to guarantee uniqueness even with same prefix/suffix
    token = hex(rng.randint(0x100, 0xFFF))[2:].upper()
    return f"{rng.choice(prefixes)}: {base_title}{rng.choice(suffixes)} [{token}]"


VAR_NAMES = ["nums", "arr", "data", "values", "elements", "seq", "items", "list",
             "numbers", "array", "input_arr", "collection", "dataset", "series"]
STR_NAMES = ["s", "t", "word", "text", "str1", "str2", "pattern", "input_str",
             "sentence", "phrase", "token", "line", "msg", "raw"]
NODE_NAMES = ["node", "vertex", "point", "city", "station", "hub", "location"]

# ── Problem statement phrasing pools ─────────────────────────────────────────
# Each template picks one phrasing at random so no two questions read the same.

_PS_MAX_SUBARRAY = [
    lambda var, n, lo, hi: (
        f"You are given an integer array `{var}` of length between 3 and {n}. "
        f"Your task is to find the contiguous subarray (containing at least one element) "
        f"that has the largest possible sum and return that sum. "
        f"Array values lie in the range [{lo}, {hi}]."
    ),
    lambda var, n, lo, hi: (
        f"An integer sequence `{var}` with up to {n} elements (each in [{lo}, {hi}]) is given. "
        f"Identify the contiguous segment whose elements sum to the maximum value "
        f"and output that maximum sum."
    ),
    lambda var, n, lo, hi: (
        f"Given a list `{var}` of integers (length ≤ {n}, values in [{lo}, {hi}]), "
        f"determine the subarray with the highest total. "
        f"The subarray must be contiguous and contain at least one number."
    ),
    lambda var, n, lo, hi: (
        f"Consider an array `{var}` whose {n} entries are drawn from [{lo}, {hi}]. "
        f"Find the non-empty contiguous slice of `{var}` that yields the greatest sum "
        f"and return that sum."
    ),
    lambda var, n, lo, hi: (
        f"A programmer receives array `{var}` (up to {n} integers, range [{lo}, {hi}]). "
        f"Help them locate the contiguous subarray with the maximum sum "
        f"and report the sum."
    ),
]

_PS_TWO_SUM = [
    lambda var, n, lo, hi: (
        f"Given an integer array `{var}` of length {n} (values in [{lo}, {hi}]) "
        f"and an integer `target`, return the 0-based indices of the two distinct elements "
        f"that add up to `target`. Exactly one valid pair exists."
    ),
    lambda var, n, lo, hi: (
        f"You have an array `{var}` with {n} integers (each between {lo} and {hi}). "
        f"Find two positions i and j (i < j) such that `{var}[i] + {var}[j] == target`. "
        f"Return the indices sorted in ascending order."
    ),
    lambda var, n, lo, hi: (
        f"An array `{var}` of {n} numbers (range [{lo}, {hi}]) and a target value are provided. "
        f"Locate the unique pair of indices whose values sum to the target "
        f"and output them in increasing order."
    ),
    lambda var, n, lo, hi: (
        f"Search through `{var}` (length {n}, values [{lo}, {hi}]) to find two indices "
        f"whose corresponding values sum to `target`. "
        f"Output the smaller index first. A unique solution is guaranteed."
    ),
    lambda var, n, lo, hi: (
        f"Given `{var}` ({n} integers in [{lo}, {hi}]) and a target integer, "
        f"identify the pair of 0-indexed positions that sum to the target. "
        f"Return them as two space-separated integers (ascending)."
    ),
]

_PS_ROTATE = [
    lambda var, n, lo, hi, k: (
        f"Given an array `{var}` of {n} integers (range [{lo}, {hi}]) and an integer `k`, "
        f"rotate the array to the right by `k` positions. "
        f"Elements that fall off the right end wrap around to the left."
    ),
    lambda var, n, lo, hi, k: (
        f"You are given `{var}` ({n} integers, values in [{lo}, {hi}]). "
        f"Perform a right circular rotation of `k` steps: "
        f"the last `k` elements move to the front."
    ),
    lambda var, n, lo, hi, k: (
        f"Rotate array `{var}` (length {n}, values [{lo}, {hi}]) rightward by `k` steps. "
        f"After rotation, element at index i moves to index (i + k) % n."
    ),
    lambda var, n, lo, hi, k: (
        f"An array `{var}` of {n} numbers (each in [{lo}, {hi}]) must be shifted right by `k`. "
        f"Elements displaced past the last index reappear at the beginning."
    ),
    lambda var, n, lo, hi, k: (
        f"Cyclically shift `{var}` ({n} integers, range [{lo}, {hi}]) to the right by `k` places. "
        f"Output the resulting array."
    ),
]

_PS_PRODUCT_EXCEPT_SELF = [
    lambda var, n, lo, hi: (
        f"Given integer array `{var}` of length {n} (values in [{lo}, {hi}]), "
        f"return an array where each element at index i equals the product of all "
        f"elements in `{var}` except `{var}[i]`. Division is not allowed."
    ),
    lambda var, n, lo, hi: (
        f"For array `{var}` ({n} integers, range [{lo}, {hi}]), construct a result array "
        f"where result[i] = product of every element except `{var}[i]`. "
        f"Solve this without using the division operator."
    ),
    lambda var, n, lo, hi: (
        f"You receive `{var}` (length {n}, values [{lo}, {hi}]). "
        f"Build and return an output array such that output[i] is the product "
        f"of all `{var}` elements excluding index i. No division permitted."
    ),
    lambda var, n, lo, hi: (
        f"Compute the prefix-suffix product array for `{var}` ({n} elements, [{lo}, {hi}]). "
        f"Each position i should hold the product of all other elements. "
        f"Do not use division at any step."
    ),
    lambda var, n, lo, hi: (
        f"Given `{var}` with {n} integers (range [{lo}, {hi}]), "
        f"produce an array where the i-th value equals the multiplication of all "
        f"elements except the one at position i. Division is forbidden."
    ),
]

_PS_MISSING_NUMBER = [
    lambda var, sz: (
        f"An array `{var}` contains {sz} distinct integers chosen from the range [0, {sz}]. "
        f"Exactly one number from this range is absent. Find and return it."
    ),
    lambda var, sz: (
        f"You are given `{var}` with {sz} unique values drawn from [0, {sz}]. "
        f"One integer in this range does not appear. Identify the missing number."
    ),
    lambda var, sz: (
        f"The array `{var}` holds {sz} distinct numbers, all from [0, {sz}], "
        f"but one value is missing. Determine which number is absent."
    ),
    lambda var, sz: (
        f"From the complete set {{0, 1, …, {sz}}}, one element has been removed "
        f"and the rest stored in `{var}`. Return the missing element."
    ),
    lambda var, sz: (
        f"Given a shuffled array `{var}` of {sz} distinct integers from [0, {sz}] "
        f"with exactly one gap, output the missing value."
    ),
]

_PS_PALINDROME = [
    lambda var, length, charset: (
        f"Given a string `{var}` of length up to {length} consisting of characters "
        f"from '{charset}', return the longest palindromic substring. "
        f"If multiple answers of equal length exist, return any one."
    ),
    lambda var, length, charset: (
        f"You receive string `{var}` (max length {length}, alphabet '{charset}'). "
        f"Find the longest contiguous substring that reads the same forwards and backwards."
    ),
    lambda var, length, charset: (
        f"Search string `{var}` (up to {length} characters from '{charset}') "
        f"for its longest palindromic segment and return it."
    ),
    lambda var, length, charset: (
        f"Among all substrings of `{var}` (length ≤ {length}, chars from '{charset}'), "
        f"identify the one that is a palindrome and has the greatest length."
    ),
    lambda var, length, charset: (
        f"String `{var}` uses only characters from '{charset}' and has at most {length} letters. "
        f"Return the longest substring that is a palindrome."
    ),
]

_PS_ANAGRAM = [
    lambda v1, v2, length: (
        f"Given two strings `{v1}` and `{v2}` each of length up to {length}, "
        f"return `true` if `{v2}` is an anagram of `{v1}` (same characters, same frequencies), "
        f"otherwise return `false`."
    ),
    lambda v1, v2, length: (
        f"Determine whether `{v2}` can be formed by rearranging the letters of `{v1}`. "
        f"Both strings have length ≤ {length}. Output true or false."
    ),
    lambda v1, v2, length: (
        f"Two strings `{v1}` and `{v2}` (max length {length}) are provided. "
        f"Check if they contain identical characters with identical counts. "
        f"Print true if yes, false otherwise."
    ),
    lambda v1, v2, length: (
        f"Are `{v1}` and `{v2}` anagrams? Both strings have at most {length} characters. "
        f"Return true if every character in `{v1}` appears the same number of times in `{v2}`."
    ),
    lambda v1, v2, length: (
        f"Given strings `{v1}` and `{v2}` (length ≤ {length}), "
        f"output true if one is a permutation of the other, false otherwise."
    ),
]

_PS_REVERSE_WORDS = [
    lambda var, wc: (
        f"Given a string `{var}` containing {wc} space-separated words, "
        f"reverse the order of the words and return the result."
    ),
    lambda var, wc: (
        f"You receive a sentence `{var}` with {wc} words separated by spaces. "
        f"Output the same words in reverse order."
    ),
    lambda var, wc: (
        f"Flip the word sequence in `{var}` ({wc} space-separated tokens). "
        f"The last word should appear first, and so on."
    ),
    lambda var, wc: (
        f"String `{var}` holds {wc} words. Rearrange them so the word order is reversed "
        f"and print the resulting sentence."
    ),
    lambda var, wc: (
        f"Reverse the {wc} words in `{var}`. "
        f"Words are separated by single spaces; output them in the opposite order."
    ),
]

_PS_LCP = [
    lambda n: (
        f"Given an array of {n} strings, find the longest common prefix shared by all of them. "
        f"If no common prefix exists, return an empty string."
    ),
    lambda n: (
        f"You have {n} strings. Determine the longest string that is a prefix of every one of them. "
        f"Return an empty string if no such prefix exists."
    ),
    lambda n: (
        f"Among {n} given strings, identify the maximum-length prefix that all strings share. "
        f"Output that prefix, or an empty string if none."
    ),
    lambda n: (
        f"Find the longest starting substring that is common to all {n} input strings. "
        f"If the strings share no common prefix, output an empty string."
    ),
    lambda n: (
        f"Given {n} strings, return the longest string `p` such that every input string begins with `p`. "
        f"Return \"\" if no such `p` exists."
    ),
]

_PS_COUNT_VOWELS = [
    lambda var, length: (
        f"Given a lowercase string `{var}` of length up to {length}, "
        f"count and return the total number of vowels (a, e, i, o, u)."
    ),
    lambda var, length: (
        f"You receive string `{var}` (max {length} lowercase letters). "
        f"How many vowels does it contain? Output the count."
    ),
    lambda var, length: (
        f"Count the occurrences of vowels in `{var}` (up to {length} lowercase characters). "
        f"Vowels are: a, e, i, o, u."
    ),
    lambda var, length: (
        f"String `{var}` has at most {length} lowercase letters. "
        f"Return the number of characters that are vowels (a/e/i/o/u)."
    ),
    lambda var, length: (
        f"Given `{var}` (length ≤ {length}, all lowercase), "
        f"output the total count of vowel characters present."
    ),
]

_PS_BFS_PATH = [
    lambda n: (
        f"Given an undirected unweighted graph with {n} nodes (0-indexed) and a list of edges, "
        f"find the shortest path (in number of edges) from node `src` to node `dst`. "
        f"Return -1 if no path exists."
    ),
    lambda n: (
        f"An undirected graph has {n} nodes numbered 0 to {n-1}. "
        f"Using BFS, find the minimum number of edges needed to travel from `src` to `dst`. "
        f"Output -1 if they are disconnected."
    ),
    lambda n: (
        f"You are given a {n}-node unweighted undirected graph. "
        f"Determine the fewest edges on any path from `src` to `dst`. "
        f"If no path exists, return -1."
    ),
    lambda n: (
        f"A graph with {n} vertices (0-indexed) and undirected edges is provided. "
        f"Find the BFS distance (edge count) between nodes `src` and `dst`. "
        f"Return -1 if unreachable."
    ),
    lambda n: (
        f"Given {n} nodes and a set of undirected edges, "
        f"compute the shortest hop count from `src` to `dst`. "
        f"Output -1 if no route exists."
    ),
]

_PS_ISLANDS = [
    lambda rows, cols: (
        f"Given a {rows}×{cols} binary grid where 1 represents land and 0 represents water, "
        f"count the number of islands. An island is a group of adjacent land cells "
        f"connected horizontally or vertically."
    ),
    lambda rows, cols: (
        f"A {rows} by {cols} grid contains 0s (water) and 1s (land). "
        f"Count how many distinct islands exist. "
        f"Two land cells belong to the same island if they are 4-directionally adjacent."
    ),
    lambda rows, cols: (
        f"You receive a {rows}×{cols} binary matrix. "
        f"Each 1 is a land cell; each 0 is water. "
        f"Find the total number of islands (connected components of 1s)."
    ),
    lambda rows, cols: (
        f"In a {rows}-row, {cols}-column grid of 0s and 1s, "
        f"an island is a maximal set of 1s connected via horizontal/vertical adjacency. "
        f"Return the island count."
    ),
    lambda rows, cols: (
        f"Count the islands in a {rows}×{cols} grid of land (1) and water (0). "
        f"Islands are formed by connecting adjacent land cells (up/down/left/right)."
    ),
]

_PS_CYCLE = [
    lambda n: (
        f"Given an undirected graph with {n} nodes (0-indexed) and a list of edges, "
        f"determine if the graph contains a cycle. Return true or false."
    ),
    lambda n: (
        f"An undirected graph has {n} vertices. "
        f"Check whether any cycle exists in it. Output true if yes, false otherwise."
    ),
    lambda n: (
        f"You are given {n} nodes and a set of undirected edges. "
        f"Does this graph contain a cycle? Return true or false."
    ),
    lambda n: (
        f"Detect whether the undirected graph with {n} nodes contains a circular path. "
        f"Print true if a cycle is found, false otherwise."
    ),
    lambda n: (
        f"Given a {n}-node undirected graph, "
        f"determine if there is any back edge (cycle). "
        f"Output true if a cycle exists, false if the graph is acyclic."
    ),
]

_PS_TOPO = [
    lambda n: (
        f"Given a DAG with {n} nodes (0-indexed) and directed edges, "
        f"return a valid topological ordering of the nodes. "
        f"If the graph contains a cycle, return an empty list."
    ),
    lambda n: (
        f"A directed acyclic graph has {n} nodes. "
        f"Produce a linear ordering of nodes such that for every directed edge u→v, "
        f"u appears before v. Return empty if a cycle is detected."
    ),
    lambda n: (
        f"You receive a directed graph with {n} vertices. "
        f"Using Kahn's algorithm, output a topological sort. "
        f"If the graph is not a DAG, output nothing."
    ),
    lambda n: (
        f"Find a topological ordering for the {n}-node directed graph. "
        f"Every dependency (u→v) must have u listed before v. "
        f"Return an empty sequence if a cycle exists."
    ),
    lambda n: (
        f"Given {n} nodes and directed edges representing dependencies, "
        f"output a valid task execution order (topological sort). "
        f"Return empty if ordering is impossible due to a cycle."
    ),
]

_PS_DIJKSTRA = [
    lambda n, max_w: (
        f"Given a weighted undirected graph with {n} nodes and edge weights up to {max_w}, "
        f"find the shortest distance from source node `src` to all other nodes. "
        f"Output -1 for unreachable nodes."
    ),
    lambda n, max_w: (
        f"A {n}-node weighted undirected graph is provided (max weight {max_w}). "
        f"Using Dijkstra's algorithm, compute the minimum cost path from `src` to every node. "
        f"Use -1 for nodes that cannot be reached."
    ),
    lambda n, max_w: (
        f"You have a weighted graph with {n} vertices (edge weights ≤ {max_w}). "
        f"Find the shortest weighted distance from `src` to each other node. "
        f"Output -1 if a node is unreachable."
    ),
    lambda n, max_w: (
        f"Given {n} nodes and weighted undirected edges (weights up to {max_w}), "
        f"determine the minimum travel cost from source `src` to all destinations. "
        f"Unreachable nodes should output -1."
    ),
    lambda n, max_w: (
        f"Apply Dijkstra's shortest path algorithm on a {n}-node graph "
        f"with edge weights in [1, {max_w}]. "
        f"Return the distance array from `src`; use -1 for disconnected nodes."
    ),
]

_PS_KNAPSACK = [
    lambda n, cap: (
        f"Given {n} items each with a weight and a value, and a knapsack of capacity {cap}, "
        f"find the maximum total value you can carry. Each item can be taken at most once."
    ),
    lambda n, cap: (
        f"You have {n} items (each with weight and value) and a bag that holds up to {cap} units. "
        f"Select items to maximize total value without exceeding the capacity. "
        f"Each item is either taken or left behind."
    ),
    lambda n, cap: (
        f"A thief can carry at most {cap} weight units. "
        f"There are {n} items available, each with a weight and profit. "
        f"Determine the maximum profit achievable."
    ),
    lambda n, cap: (
        f"Given {n} objects with weights and values and a knapsack capacity of {cap}, "
        f"use dynamic programming to find the highest value subset "
        f"whose total weight does not exceed {cap}."
    ),
    lambda n, cap: (
        f"You must pack items into a bag of capacity {cap}. "
        f"From {n} available items (each with weight and value), "
        f"choose a subset that maximizes value. No item may be split."
    ),
]

_PS_LCS = [
    lambda v1, v2, length, charset: (
        f"Given two strings `{v1}` and `{v2}` of length up to {length} over alphabet '{charset}', "
        f"find the length of their longest common subsequence."
    ),
    lambda v1, v2, length, charset: (
        f"Two strings `{v1}` and `{v2}` (max length {length}, chars from '{charset}') are given. "
        f"A common subsequence is a sequence that appears in both (not necessarily contiguous). "
        f"Return the length of the longest such sequence."
    ),
    lambda v1, v2, length, charset: (
        f"Find the LCS length of `{v1}` and `{v2}` "
        f"(each up to {length} characters from '{charset}'). "
        f"A subsequence preserves relative order but need not be contiguous."
    ),
    lambda v1, v2, length, charset: (
        f"Given `{v1}` and `{v2}` (alphabet '{charset}', length ≤ {length}), "
        f"compute the length of the longest sequence of characters "
        f"that is a subsequence of both strings."
    ),
    lambda v1, v2, length, charset: (
        f"Strings `{v1}` and `{v2}` use characters from '{charset}' and have at most {length} letters. "
        f"Return the maximum length of a common subsequence between them."
    ),
]

_PS_COIN = [
    lambda coins, amount: (
        f"Given coin denominations {coins} and a target amount {amount}, "
        f"find the minimum number of coins needed to make up that amount. "
        f"Return -1 if it is not possible."
    ),
    lambda coins, amount: (
        f"You have unlimited coins of denominations {coins}. "
        f"What is the fewest coins needed to total exactly {amount}? "
        f"Output -1 if no combination works."
    ),
    lambda coins, amount: (
        f"Using coin types {coins} (unlimited supply of each), "
        f"determine the smallest number of coins that sum to {amount}. "
        f"If impossible, return -1."
    ),
    lambda coins, amount: (
        f"A vending machine accepts coins of values {coins}. "
        f"Find the minimum number of coins to make change for {amount}. "
        f"Return -1 if exact change is impossible."
    ),
    lambda coins, amount: (
        f"Given denominations {coins} and target {amount}, "
        f"use dynamic programming to find the least coins required. "
        f"Output -1 if the amount cannot be formed."
    ),
]

_PS_LIS = [
    lambda var, n, lo, hi: (
        f"Given an integer array `{var}` of length {n} with values in [{lo}, {hi}], "
        f"return the length of the longest strictly increasing subsequence."
    ),
    lambda var, n, lo, hi: (
        f"Find the LIS length in `{var}` ({n} integers, range [{lo}, {hi}]). "
        f"A strictly increasing subsequence preserves order and each element is greater than the previous."
    ),
    lambda var, n, lo, hi: (
        f"You receive array `{var}` ({n} values in [{lo}, {hi}]). "
        f"Determine the length of the longest subsequence "
        f"where each element is strictly greater than the one before it."
    ),
    lambda var, n, lo, hi: (
        f"Among all strictly increasing subsequences of `{var}` "
        f"({n} integers, [{lo}, {hi}]), find the one with the greatest length."
    ),
    lambda var, n, lo, hi: (
        f"Given `{var}` (length {n}, values [{lo}, {hi}]), "
        f"compute the length of the longest subsequence "
        f"in which every successive element is larger than the previous."
    ),
]

_PS_EDIT = [
    lambda v1, v2, length: (
        f"Given two strings `{v1}` and `{v2}` of length up to {length}, "
        f"find the minimum number of operations (insert, delete, replace) "
        f"to convert `{v1}` into `{v2}`."
    ),
    lambda v1, v2, length: (
        f"Compute the Levenshtein distance between `{v1}` and `{v2}` (max length {length}). "
        f"Allowed operations: insert a character, delete a character, replace a character."
    ),
    lambda v1, v2, length: (
        f"How many single-character edits (insertions, deletions, substitutions) "
        f"are needed to transform `{v1}` into `{v2}`? Both strings have length ≤ {length}."
    ),
    lambda v1, v2, length: (
        f"Find the edit distance between strings `{v1}` and `{v2}` (length ≤ {length}). "
        f"Each insert, delete, or replace counts as one operation."
    ),
    lambda v1, v2, length: (
        f"Given `{v1}` and `{v2}` (each up to {length} characters), "
        f"return the minimum number of character-level operations "
        f"required to make them identical."
    ),
]

# ---------------------------------------------------------------------------
# ========================  ARRAYS  =========================================
# ---------------------------------------------------------------------------

def _array_max_subarray(rng: random.Random) -> Dict:
    n = rng.randint(5, 15)
    lo, hi = rng.randint(-20, -5), rng.randint(5, 20)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        best = arr[0]; cur = arr[0]
        for x in arr[1:]:
            cur = max(x, cur + x)
            best = max(best, cur)
        return best

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmt_choices = [
        f"A single line of space-separated integers representing `{var}`.",
        f"One line containing the elements of `{var}` separated by spaces.",
        f"Space-separated integers on a single line.",
        f"A single line: N integers separated by spaces.",
        f"Input: one line with the array elements.",
    ]
    output_fmt_choices = [
        "A single integer — the maximum subarray sum.",
        "Print the largest contiguous subarray sum.",
        "Output one integer: the maximum sum.",
        "The maximum sum as a single integer.",
        "One integer representing the answer.",
    ]
    return {
        "title": "Maximum Subarray Sum",
        "problem_statement": rng.choice(_PS_MAX_SUBARRAY)(var, n, lo, hi),
        "input_format": rng.choice(input_fmt_choices),
        "output_format": rng.choice(output_fmt_choices),
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _array_two_sum(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)
    lo, hi = rng.randint(1, 5), rng.randint(20, 50)
    var = rng.choice(VAR_NAMES)

    def solve(arr, target):
        seen = {}
        for i, v in enumerate(arr):
            if target - v in seen:
                return sorted([seen[target - v], i])
        return [-1, -1]

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(4, n))]
        i, j = rng.sample(range(len(a)), 2)
        t = a[i] + a[j]
        return {"input": {"array": a, "target": t}, "output": solve(a, t)}

    a = [rng.randint(lo, hi) for _ in range(n)]
    i, j = rng.sample(range(n), 2)
    target = a[i] + a[j]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        f"Line 1: space-separated integers for `{var}`. Line 2: integer `target`.",
        f"First line: the array elements. Second line: the target value.",
        f"Line 1: N integers. Line 2: target.",
        f"Two lines — array on line 1, target on line 2.",
        f"Input line 1: array. Input line 2: target integer.",
    ]
    output_fmts = [
        "Two space-separated indices (0-based, sorted ascending).",
        "Print the two 0-indexed positions in ascending order.",
        "Output: two integers — the indices of the pair.",
        "The smaller index first, then the larger index.",
        "Two integers separated by a space.",
    ]
    return {
        "title": "Two Sum",
        "problem_statement": rng.choice(_PS_TWO_SUM)(var, n, lo, hi),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{' '.join(map(str, a))}\n{target}",
        "sample_output": " ".join(map(str, solve(a, target))),
        "test_cases": tcs,
    }


def _array_rotate(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)
    lo, hi = rng.randint(-10, 0), rng.randint(10, 30)
    k = rng.randint(1, n - 1)
    var = rng.choice(VAR_NAMES)

    def solve(arr, steps):
        steps = steps % len(arr)
        return arr[-steps:] + arr[:-steps]

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        s = rng.randint(1, len(a) - 1)
        return {"input": {"array": a, "k": s}, "output": solve(a, s)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: space-separated integers. Line 2: integer k.",
        "First line: array elements. Second line: rotation steps k.",
        "Line 1: the array. Line 2: k (number of right shifts).",
        "Two lines — array then k.",
        "Input: array on line 1, k on line 2.",
    ]
    output_fmts = [
        "Space-separated integers of the rotated array.",
        "Print the array after rotation.",
        "Output the resulting array elements separated by spaces.",
        "The rotated array on one line.",
        "Elements of the rotated array, space-separated.",
    ]
    return {
        "title": "Rotate Array",
        "problem_statement": rng.choice(_PS_ROTATE)(var, n, lo, hi, k),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": " ".join(map(str, solve(sample, k))),
        "test_cases": tcs,
    }


def _array_product_except_self(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)
    lo, hi = rng.randint(-5, 1), rng.randint(2, 8)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        n = len(arr); res = [1] * n
        pre = 1
        for i in range(n):
            res[i] = pre; pre *= arr[i]
        suf = 1
        for i in range(n - 1, -1, -1):
            res[i] *= suf; suf *= arr[i]
        return res

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Space-separated integers on a single line.",
        "One line containing the array elements.",
        "A single line: the array values separated by spaces.",
        "Input: space-separated integers.",
        "One line with N integers.",
    ]
    output_fmts = [
        "Space-separated integers.",
        "Print the result array elements separated by spaces.",
        "Output the product array on one line.",
        "The answer array, space-separated.",
        "N integers on one line.",
    ]
    return {
        "title": "Product of Array Except Self",
        "problem_statement": rng.choice(_PS_PRODUCT_EXCEPT_SELF)(var, n, lo, hi),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _array_missing_number(rng: random.Random) -> Dict:
    n = rng.randint(5, 15)
    var = rng.choice(VAR_NAMES)

    def solve(arr, total_n):
        return total_n * (total_n + 1) // 2 - sum(arr)

    def make_tc():
        sz = rng.randint(4, n)
        missing = rng.randint(0, sz)
        a = [i for i in range(sz + 1) if i != missing]
        rng.shuffle(a)
        return {"input": {"array": a, "n": sz}, "output": missing}

    sz = n; missing = rng.randint(0, sz)
    sample = [i for i in range(sz + 1) if i != missing]
    rng.shuffle(sample)
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Space-separated integers on a single line.",
        "One line: the array elements (shuffled).",
        "A single line of integers.",
        "Input: the array values separated by spaces.",
        "One line with the array.",
    ]
    output_fmts = [
        "A single integer — the missing number.",
        "Print the absent value.",
        "Output the missing integer.",
        "One integer: the number that is missing.",
        "The missing number.",
    ]
    return {
        "title": "Find the Missing Number",
        "problem_statement": rng.choice(_PS_MISSING_NUMBER)(var, sz),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(missing),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  STRINGS  ========================================
# ---------------------------------------------------------------------------

def _string_longest_palindrome(rng: random.Random) -> Dict:
    length = rng.randint(6, 14)
    charset = rng.choice(["abc", "abcd", "aeiou", "abcde"])
    var = rng.choice(STR_NAMES)

    def solve(s):
        best = ""
        for i in range(len(s)):
            for l, r in [(i, i), (i, i + 1)]:
                while l >= 0 and r < len(s) and s[l] == s[r]:
                    if r - l + 1 > len(best):
                        best = s[l:r + 1]
                    l -= 1; r += 1
        return best

    def make_tc():
        s = "".join(rng.choice(charset) for _ in range(rng.randint(4, length)))
        return {"input": s, "output": solve(s)}

    sample = "".join(rng.choice(charset) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "A single string.",
        "One line containing the input string.",
        "Input: a string on a single line.",
        "A string of lowercase characters.",
        "One line: the string.",
    ]
    output_fmts = [
        "The longest palindromic substring.",
        "Print the longest palindrome found.",
        "Output the palindromic substring with maximum length.",
        "The answer: the longest palindrome.",
        "One string — the longest palindromic segment.",
    ]
    return {
        "title": "Longest Palindromic Substring",
        "problem_statement": rng.choice(_PS_PALINDROME)(var, length, charset),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": sample,
        "sample_output": solve(sample),
        "test_cases": tcs,
    }


def _string_anagram_check(rng: random.Random) -> Dict:
    length = rng.randint(4, 10)
    var1, var2 = rng.sample(STR_NAMES, 2)

    def solve(a, b):
        from collections import Counter
        return Counter(a) == Counter(b)

    def make_tc():
        base = "".join(rng.choice("abcdefgh") for _ in range(rng.randint(3, length)))
        if rng.random() < 0.5:
            lst = list(base); rng.shuffle(lst); b = "".join(lst)
        else:
            b = "".join(rng.choice("abcdefgh") for _ in range(len(base)))
        return {"input": {"s1": base, "s2": b}, "output": solve(base, b)}

    base = "".join(rng.choice("abcdefgh") for _ in range(length))
    lst = list(base); rng.shuffle(lst); b = "".join(lst)
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: string s1. Line 2: string s2.",
        "Two lines — first string on line 1, second on line 2.",
        "Input: two strings, one per line.",
        "Line 1: first string. Line 2: second string.",
        "Two separate lines, each containing one string.",
    ]
    output_fmts = [
        "true or false.",
        "Print true if anagram, false otherwise.",
        "Output: true or false (lowercase).",
        "One word: true or false.",
        "true if they are anagrams, false if not.",
    ]
    return {
        "title": "Valid Anagram",
        "problem_statement": rng.choice(_PS_ANAGRAM)(var1, var2, length),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{base}\n{b}",
        "sample_output": str(solve(base, b)).lower(),
        "test_cases": tcs,
    }


def _string_reverse_words(rng: random.Random) -> Dict:
    word_count = rng.randint(3, 7)
    var = rng.choice(STR_NAMES)
    words_pool = ["hello", "world", "code", "arena", "python", "data", "algo",
                  "tree", "graph", "sort", "stack", "queue", "loop", "hash",
                  "binary", "search", "merge", "pivot", "index", "cache"]

    def solve(s):
        return " ".join(s.split()[::-1])

    def make_tc():
        wc = rng.randint(2, word_count)
        s = " ".join(rng.choice(words_pool) for _ in range(wc))
        return {"input": s, "output": solve(s)}

    sample = " ".join(rng.choice(words_pool) for _ in range(word_count))
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "A single line string.",
        "One line containing the sentence.",
        "Input: a space-separated sequence of words.",
        "A single line with words separated by spaces.",
        "One line: the sentence to reverse.",
    ]
    output_fmts = [
        "Words in reversed order, space-separated.",
        "Print the words in reverse sequence.",
        "Output the sentence with word order flipped.",
        "The reversed word sequence on one line.",
        "Space-separated words in reverse order.",
    ]
    return {
        "title": "Reverse Words in a String",
        "problem_statement": rng.choice(_PS_REVERSE_WORDS)(var, word_count),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": sample,
        "sample_output": solve(sample),
        "test_cases": tcs,
    }


def _string_longest_common_prefix(rng: random.Random) -> Dict:
    n = rng.randint(3, 6)
    prefix_len = rng.randint(1, 4)
    charset = "abcdefghij"
    var = rng.choice(STR_NAMES)

    def solve(strs):
        if not strs: return ""
        prefix = strs[0]
        for s in strs[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix: return ""
        return prefix

    def make_tc():
        prefix = "".join(rng.choice(charset) for _ in range(rng.randint(0, prefix_len)))
        strs = [prefix + "".join(rng.choice(charset) for _ in range(rng.randint(1, 4)))
                for _ in range(rng.randint(2, n))]
        return {"input": strs, "output": solve(strs)}

    prefix = "".join(rng.choice(charset) for _ in range(prefix_len))
    sample = [prefix + "".join(rng.choice(charset) for _ in range(rng.randint(1, 4))) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Space-separated strings on one line.",
        "One line containing all strings separated by spaces.",
        "A single line: the strings separated by spaces.",
        "Input: N strings on one line.",
        "All strings on a single line, space-separated.",
    ]
    output_fmts = [
        "The longest common prefix string.",
        "Print the shared prefix (empty string if none).",
        "Output the common prefix, or empty string.",
        "One string — the longest common prefix.",
        "The prefix string (may be empty).",
    ]
    return {
        "title": "Longest Common Prefix",
        "problem_statement": rng.choice(_PS_LCP)(n),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": " ".join(sample),
        "sample_output": solve(sample),
        "test_cases": tcs,
    }


def _string_count_vowels(rng: random.Random) -> Dict:
    length = rng.randint(8, 20)
    var = rng.choice(STR_NAMES)
    VOWELS = set("aeiouAEIOU")

    def solve(s):
        return sum(1 for c in s if c in VOWELS)

    def make_tc():
        s = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(5, length)))
        return {"input": s, "output": solve(s)}

    sample = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "A single lowercase string.",
        "One line: a string of lowercase letters.",
        "Input: a lowercase string.",
        "A string on a single line (all lowercase).",
        "One line containing the string.",
    ]
    output_fmts = [
        "A single integer.",
        "Print the vowel count.",
        "Output one integer — the number of vowels.",
        "The count of vowels as an integer.",
        "One number: total vowels.",
    ]
    return {
        "title": "Count Vowels in String",
        "problem_statement": rng.choice(_PS_COUNT_VOWELS)(var, length),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": sample,
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  GRAPHS  =========================================
# ---------------------------------------------------------------------------

def _graph_bfs_shortest_path(rng: random.Random) -> Dict:
    n = rng.randint(5, 9)
    edge_prob = rng.uniform(0.3, 0.6)

    def build_graph(nodes, prob):
        adj = defaultdict(list)
        edges = []
        for i in range(nodes):
            for j in range(i + 1, nodes):
                if rng.random() < prob:
                    adj[i].append(j); adj[j].append(i)
                    edges.append((i, j))
        return adj, edges

    def solve(adj, src, dst, nodes):
        if src == dst: return 0
        visited = set([src]); q = deque([(src, 0)])
        while q:
            node, dist = q.popleft()
            for nb in adj[node]:
                if nb == dst: return dist + 1
                if nb not in visited:
                    visited.add(nb); q.append((nb, dist + 1))
        return -1

    def make_tc():
        nn = rng.randint(4, n)
        adj, edges = build_graph(nn, edge_prob)
        src, dst = rng.randint(0, nn - 1), rng.randint(0, nn - 1)
        return {"input": {"nodes": nn, "edges": edges, "src": src, "dst": dst},
                "output": solve(adj, src, dst, nn)}

    adj, edges = build_graph(n, edge_prob)
    src, dst = rng.randint(0, n - 1), rng.randint(0, n - 1)
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: n (nodes) e (edges). Next e lines: u v. Last line: src dst.",
        "First line: N E. Next E lines: edge pairs. Last line: source destination.",
        "Line 1: number of nodes and edges. Then E edge lines. Then src dst.",
        "N E on line 1. E lines of u v. Final line: src dst.",
        "Line 1: N E. Lines 2..E+1: edges. Line E+2: src dst.",
    ]
    output_fmts = [
        "Shortest path length or -1.",
        "Print the minimum edge count, or -1 if unreachable.",
        "Output the BFS distance, or -1.",
        "One integer: shortest path or -1.",
        "The minimum hops, or -1 if no path.",
    ]
    return {
        "title": "BFS Shortest Path in Unweighted Graph",
        "problem_statement": rng.choice(_PS_BFS_PATH)(n),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": (f"{n} {len(edges)}\n" +
                         "\n".join(f"{u} {v}" for u, v in edges) +
                         f"\n{src} {dst}"),
        "sample_output": str(solve(adj, src, dst, n)),
        "test_cases": tcs,
    }


def _graph_number_of_islands(rng: random.Random) -> Dict:
    rows = rng.randint(4, 7); cols = rng.randint(4, 7)

    def solve(grid):
        g = [row[:] for row in grid]
        count = 0
        def dfs(r, c):
            if r < 0 or r >= len(g) or c < 0 or c >= len(g[0]) or g[r][c] != 1: return
            g[r][c] = 0
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]: dfs(r+dr, c+dc)
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] == 1: count += 1; dfs(r, c)
        return count

    def make_tc():
        r, c = rng.randint(3, rows), rng.randint(3, cols)
        grid = [[rng.randint(0, 1) for _ in range(c)] for _ in range(r)]
        return {"input": grid, "output": solve(grid)}

    grid = [[rng.randint(0, 1) for _ in range(cols)] for _ in range(rows)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        f"{rows} lines each with {cols} space-separated 0/1 values.",
        f"R lines, each containing C space-separated binary values (0 or 1).",
        f"The grid: {rows} rows of {cols} integers (0=water, 1=land).",
        f"Input: {rows}×{cols} binary matrix, one row per line.",
        f"{rows} lines of {cols} space-separated integers.",
    ]
    output_fmts = [
        "A single integer — number of islands.",
        "Print the island count.",
        "Output one integer: the total number of islands.",
        "The number of distinct islands.",
        "One integer representing the island count.",
    ]
    return {
        "title": "Number of Islands",
        "problem_statement": rng.choice(_PS_ISLANDS)(rows, cols),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": "\n".join(" ".join(map(str, row)) for row in grid),
        "sample_output": str(solve(grid)),
        "test_cases": tcs,
    }


def _graph_detect_cycle(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)

    def solve(n, edges):
        adj = defaultdict(list)
        for u, v in edges: adj[u].append(v); adj[v].append(u)
        visited = set()
        def dfs(node, parent):
            visited.add(node)
            for nb in adj[node]:
                if nb not in visited:
                    if dfs(nb, node): return True
                elif nb != parent: return True
            return False
        for i in range(n):
            if i not in visited:
                if dfs(i, -1): return True
        return False

    def make_unique_tc():
        nn = rng.randint(3, n)
        edges = set()
        for i in range(1, nn):
            edges.add((rng.randint(0, i-1), i))
        if rng.random() < 0.5:
            u, v = rng.randint(0, nn-1), rng.randint(0, nn-1)
            if u != v: edges.add((min(u,v), max(u,v)))
        edge_list = sorted(edges)
        return {"input": {"nodes": nn, "edges": edge_list}, "output": solve(nn, edge_list)}

    edges = set()
    for i in range(1, n): edges.add((rng.randint(0, i-1), i))
    if rng.random() < 0.5:
        u, v = rng.randint(0, n-1), rng.randint(0, n-1)
        if u != v: edges.add((min(u,v), max(u,v)))
    edge_list = sorted(edges)
    seen_keys = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        tc = make_unique_tc()
        key = str(tc["input"])
        if key not in seen_keys:
            seen_keys.add(key)
            tcs.append(tc)
    input_fmts = [
        "Line 1: n e. Next e lines: u v.",
        "First line: N E. Then E lines of edge pairs.",
        "Line 1: nodes edges. Following lines: each edge as u v.",
        "N E on line 1. E edge pairs follow.",
        "Line 1: N E. Lines 2 to E+1: undirected edges.",
    ]
    output_fmts = [
        "true or false.",
        "Print true if a cycle exists, false otherwise.",
        "Output: true or false (lowercase).",
        "One word: true or false.",
        "true if cyclic, false if acyclic.",
    ]
    return {
        "title": "Detect Cycle in Undirected Graph",
        "problem_statement": rng.choice(_PS_CYCLE)(n),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{n} {len(edge_list)}\n" + "\n".join(f"{u} {v}" for u, v in edge_list),
        "sample_output": str(solve(n, edge_list)).lower(),
        "test_cases": tcs,
    }


def _graph_topological_sort(rng: random.Random) -> Dict:
    n = rng.randint(4, 9)

    def solve(n, edges):
        indegree = [0] * n
        adj = defaultdict(list)
        for u, v in edges: adj[u].append(v); indegree[v] += 1
        q = deque([i for i in range(n) if indegree[i] == 0])
        order = []
        while q:
            node = q.popleft(); order.append(node)
            for nb in adj[node]:
                indegree[nb] -= 1
                if indegree[nb] == 0: q.append(nb)
        return order if len(order) == n else []

    def make_unique_tc():
        nn = rng.randint(3, n)
        edges = set()
        for i in range(1, nn): edges.add((rng.randint(0, i-1), i))
        el = sorted(edges)
        return {"input": {"nodes": nn, "edges": el}, "output": solve(nn, el)}

    edges = set()
    for i in range(1, n): edges.add((rng.randint(0, i-1), i))
    el = sorted(edges)
    seen_keys = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        tc = make_unique_tc()
        key = str(tc["input"])
        if key not in seen_keys:
            seen_keys.add(key)
            tcs.append(tc)
    input_fmts = [
        "Line 1: n e. Next e lines: u v (directed edge u→v).",
        "First line: N E. Then E directed edges as u v.",
        "Line 1: nodes edges. Following lines: directed edge pairs.",
        "N E on line 1. E lines of directed edges follow.",
        "Line 1: N E. Lines 2..E+1: directed edges u v.",
    ]
    output_fmts = [
        "Space-separated node indices in topological order.",
        "Print the topological ordering (space-separated).",
        "Output the node sequence, or empty if cycle detected.",
        "Topological order as space-separated integers.",
        "The valid ordering, or nothing if a cycle exists.",
    ]
    return {
        "title": "Topological Sort (Kahn's Algorithm)",
        "problem_statement": rng.choice(_PS_TOPO)(n),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{n} {len(el)}\n" + "\n".join(f"{u} {v}" for u, v in el),
        "sample_output": " ".join(map(str, solve(n, el))),
        "test_cases": tcs,
    }


def _graph_dijkstra(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    max_w = rng.randint(10, 30)

    def solve(n, edges, src):
        adj = defaultdict(list)
        for u, v, w in edges: adj[u].append((v, w)); adj[v].append((u, w))
        dist = [float('inf')] * n; dist[src] = 0
        pq = [(0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]: continue
            for v, w in adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w; heapq.heappush(pq, (dist[v], v))
        return [d if d != float('inf') else -1 for d in dist]

    def make_tc():
        nn = rng.randint(3, n)
        edges = []
        for i in range(1, nn):
            edges.append((rng.randint(0, i-1), i, rng.randint(1, max_w)))
        src = rng.randint(0, nn-1)
        return {"input": {"nodes": nn, "edges": edges, "src": src}, "output": solve(nn, edges, src)}

    edges = [(rng.randint(0, i-1), i, rng.randint(1, max_w)) for i in range(1, n)]
    src = rng.randint(0, n-1)
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: n e src. Next e lines: u v w.",
        "First line: N E source. Then E weighted edges as u v w.",
        "Line 1: nodes edges src. Following lines: u v weight.",
        "N E src on line 1. E lines of weighted edges follow.",
        "Line 1: N E src. Lines 2..E+1: u v w.",
    ]
    output_fmts = [
        "n space-separated distances.",
        "Print N distances from src (space-separated), -1 if unreachable.",
        "Output the distance array.",
        "N integers: shortest distances from source.",
        "Space-separated distances to all nodes.",
    ]
    return {
        "title": "Dijkstra's Shortest Path",
        "problem_statement": rng.choice(_PS_DIJKSTRA)(n, max_w),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{n} {len(edges)} {src}\n" + "\n".join(f"{u} {v} {w}" for u, v, w in edges),
        "sample_output": " ".join(map(str, solve(n, edges, src))),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  DYNAMIC PROGRAMMING  ============================
# ---------------------------------------------------------------------------

def _dp_knapsack(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    max_w = rng.randint(10, 25)
    max_val = rng.randint(10, 30)

    def solve(weights, values, capacity):
        n = len(weights)
        dp = [[0] * (capacity + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for w in range(capacity + 1):
                dp[i][w] = dp[i-1][w]
                if weights[i-1] <= w:
                    dp[i][w] = max(dp[i][w], dp[i-1][w - weights[i-1]] + values[i-1])
        return dp[n][capacity]

    def make_tc():
        nn = rng.randint(3, n)
        cap = rng.randint(5, max_w)
        ws = [rng.randint(1, max_w // 2) for _ in range(nn)]
        vs = [rng.randint(1, max_val) for _ in range(nn)]
        return {"input": {"weights": ws, "values": vs, "capacity": cap}, "output": solve(ws, vs, cap)}

    cap = rng.randint(8, max_w)
    ws = [rng.randint(1, max_w // 2) for _ in range(n)]
    vs = [rng.randint(1, max_val) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: n capacity. Line 2: weights. Line 3: values.",
        "First line: N and capacity. Second line: item weights. Third line: item values.",
        "Line 1: number of items and bag capacity. Line 2: weights. Line 3: values.",
        "Three lines — N capacity, then weights, then values.",
        "Line 1: N cap. Line 2: space-separated weights. Line 3: space-separated values.",
    ]
    output_fmts = [
        "Maximum value as integer.",
        "Print the highest achievable value.",
        "Output one integer: the maximum total value.",
        "A single integer — the best value.",
        "The maximum value that fits in the knapsack.",
    ]
    return {
        "title": "0/1 Knapsack Problem",
        "problem_statement": rng.choice(_PS_KNAPSACK)(n, cap),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{n} {cap}\n{' '.join(map(str, ws))}\n{' '.join(map(str, vs))}",
        "sample_output": str(solve(ws, vs, cap)),
        "test_cases": tcs,
    }


def _dp_longest_common_subsequence(rng: random.Random) -> Dict:
    length = rng.randint(5, 10)
    charset = rng.choice(["abc", "abcd", "abcde"])
    v1, v2 = rng.sample(STR_NAMES, 2)

    def solve(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1] + 1
                else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]

    def make_tc():
        a = "".join(rng.choice(charset) for _ in range(rng.randint(3, length)))
        b = "".join(rng.choice(charset) for _ in range(rng.randint(3, length)))
        return {"input": {"s1": a, "s2": b}, "output": solve(a, b)}

    a = "".join(rng.choice(charset) for _ in range(length))
    b = "".join(rng.choice(charset) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: s1. Line 2: s2.",
        "Two lines — first string on line 1, second on line 2.",
        "Input: two strings, one per line.",
        "Line 1: first string. Line 2: second string.",
        "Two separate lines, each containing one string.",
    ]
    output_fmts = [
        "A single integer.",
        "Print the LCS length.",
        "Output one integer: the length of the LCS.",
        "The LCS length as a single integer.",
        "One number: the longest common subsequence length.",
    ]
    return {
        "title": "Longest Common Subsequence",
        "problem_statement": rng.choice(_PS_LCS)(v1, v2, length, charset),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{a}\n{b}",
        "sample_output": str(solve(a, b)),
        "test_cases": tcs,
    }


def _dp_coin_change(rng: random.Random) -> Dict:
    num_coins = rng.randint(3, 5)
    max_amount = rng.randint(15, 40)
    coins = sorted(rng.sample(range(1, 15), num_coins))

    def solve(coins, amount):
        dp = [float('inf')] * (amount + 1); dp[0] = 0
        for i in range(1, amount + 1):
            for c in coins:
                if c <= i and dp[i - c] + 1 < dp[i]:
                    dp[i] = dp[i - c] + 1
        return dp[amount] if dp[amount] != float('inf') else -1

    def make_tc():
        nc = rng.randint(2, num_coins)
        cs = sorted(rng.sample(range(1, 15), nc))
        amt = rng.randint(5, max_amount)
        return {"input": {"coins": cs, "amount": amt}, "output": solve(cs, amt)}

    amount = rng.randint(10, max_amount)
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: space-separated coin denominations. Line 2: amount.",
        "First line: coin values. Second line: target amount.",
        "Line 1: denominations. Line 2: amount.",
        "Two lines — coins on line 1, amount on line 2.",
        "Input: coin types on line 1, target on line 2.",
    ]
    output_fmts = [
        "Minimum number of coins or -1.",
        "Print the fewest coins needed, or -1 if impossible.",
        "Output one integer: minimum coins or -1.",
        "A single integer — minimum coins, or -1.",
        "The least number of coins, or -1 if not achievable.",
    ]
    return {
        "title": "Coin Change — Minimum Coins",
        "problem_statement": rng.choice(_PS_COIN)(coins, amount),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{' '.join(map(str, coins))}\n{amount}",
        "sample_output": str(solve(coins, amount)),
        "test_cases": tcs,
    }


def _dp_longest_increasing_subsequence(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(1, 5), rng.randint(15, 30)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        if not arr: return 0
        dp = [1] * len(arr)
        for i in range(1, len(arr)):
            for j in range(i):
                if arr[j] < arr[i]: dp[i] = max(dp[i], dp[j] + 1)
        return max(dp)

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Space-separated integers.",
        "One line containing the array elements.",
        "A single line: the array values separated by spaces.",
        "Input: space-separated integers.",
        "One line with N integers.",
    ]
    output_fmts = [
        "A single integer.",
        "Print the LIS length.",
        "Output one integer: the LIS length.",
        "The length of the longest increasing subsequence.",
        "One number: the LIS length.",
    ]
    return {
        "title": "Longest Increasing Subsequence",
        "problem_statement": rng.choice(_PS_LIS)(var, n, lo, hi),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _dp_edit_distance(rng: random.Random) -> Dict:
    length = rng.randint(4, 8)
    charset = "abcde"
    v1, v2 = rng.sample(STR_NAMES, 2)

    def solve(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1): dp[i][0] = i
        for j in range(n + 1): dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i-1] == b[j-1]: dp[i][j] = dp[i-1][j-1]
                else: dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        return dp[m][n]

    def make_tc():
        a = "".join(rng.choice(charset) for _ in range(rng.randint(2, length)))
        b = "".join(rng.choice(charset) for _ in range(rng.randint(2, length)))
        return {"input": {"s1": a, "s2": b}, "output": solve(a, b)}

    a = "".join(rng.choice(charset) for _ in range(length))
    b = "".join(rng.choice(charset) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    input_fmts = [
        "Line 1: s1. Line 2: s2.",
        "Two lines — first string on line 1, second on line 2.",
        "Input: two strings, one per line.",
        "Line 1: first string. Line 2: second string.",
        "Two separate lines, each containing one string.",
    ]
    output_fmts = [
        "A single integer.",
        "Print the edit distance.",
        "Output one integer: the minimum edit distance.",
        "The Levenshtein distance as a single integer.",
        "One number: the minimum operations needed.",
    ]
    return {
        "title": "Edit Distance (Levenshtein)",
        "problem_statement": rng.choice(_PS_EDIT)(v1, v2, length),
        "input_format": rng.choice(input_fmts),
        "output_format": rng.choice(output_fmts),
        "sample_input": f"{a}\n{b}",
        "sample_output": str(solve(a, b)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  TREES  ==========================================
# ---------------------------------------------------------------------------

def _build_bst(rng, values):
    """Returns adjacency list (parent->children) and root for a BST."""
    class Node:
        def __init__(self, v): self.v = v; self.left = self.right = None
    def insert(root, v):
        if root is None: return Node(v)
        if v < root.v: root.left = insert(root.left, v)
        else: root.right = insert(root.right, v)
        return root
    root = None
    for v in values: root = insert(root, v)
    return root


def _tree_inorder(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(1, 5), rng.randint(20, 40)

    def inorder(node):
        if node is None: return []
        return inorder(node.left) + [node.v] + inorder(node.right)

    def make_tc():
        vals = rng.sample(range(lo, hi), rng.randint(4, n))
        root = _build_bst(rng, vals)
        return {"input": sorted(vals), "output": inorder(root)}

    vals = rng.sample(range(lo, hi), n)
    root = _build_bst(rng, vals)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "BST Inorder Traversal",
        "problem_statement": (
            f"Given a BST built by inserting {n} distinct integers (range [{lo}, {hi}]) "
            f"in the given order, return the inorder traversal."
        ),
        "input_format": "Space-separated integers (insertion order).",
        "output_format": "Space-separated integers in inorder.",
        "sample_input": " ".join(map(str, vals)),
        "sample_output": " ".join(map(str, inorder(root))),
        "test_cases": tcs,
    }


def _tree_max_depth(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)
    lo, hi = 1, 50

    def max_depth(node):
        if node is None: return 0
        return 1 + max(max_depth(node.left), max_depth(node.right))

    def make_tc():
        vals = rng.sample(range(lo, hi), rng.randint(3, n))
        root = _build_bst(rng, vals)
        return {"input": vals, "output": max_depth(root)}

    vals = rng.sample(range(lo, hi), n)
    root = _build_bst(rng, vals)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Maximum Depth of Binary Tree",
        "problem_statement": (
            f"Given a BST built by inserting {n} distinct integers, "
            f"find the maximum depth (number of nodes along the longest root-to-leaf path)."
        ),
        "input_format": "Space-separated integers (insertion order).",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, vals)),
        "sample_output": str(max_depth(root)),
        "test_cases": tcs,
    }


def _tree_level_order(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = 1, 50

    def level_order(node):
        if node is None: return []
        result = []; q = deque([node])
        while q:
            level = []
            for _ in range(len(q)):
                cur = q.popleft(); level.append(cur.v)
                if cur.left: q.append(cur.left)
                if cur.right: q.append(cur.right)
            result.append(level)
        return result

    def make_tc():
        vals = rng.sample(range(lo, hi), rng.randint(3, n))
        root = _build_bst(rng, vals)
        return {"input": vals, "output": level_order(root)}

    vals = rng.sample(range(lo, hi), n)
    root = _build_bst(rng, vals)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Binary Tree Level Order Traversal",
        "problem_statement": (
            f"Given a BST built by inserting {n} distinct integers, "
            f"return its level-order traversal as a list of lists."
        ),
        "input_format": "Space-separated integers (insertion order).",
        "output_format": "Each level on a new line, space-separated.",
        "sample_input": " ".join(map(str, vals)),
        "sample_output": "\n".join(" ".join(map(str, lvl)) for lvl in level_order(root)),
        "test_cases": tcs,
    }


def _tree_diameter(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)
    lo, hi = 1, 50

    def diameter(node):
        best = [0]
        def height(node):
            if node is None: return 0
            l, r = height(node.left), height(node.right)
            best[0] = max(best[0], l + r)
            return 1 + max(l, r)
        height(node)
        return best[0]

    def make_tc():
        vals = rng.sample(range(lo, hi), rng.randint(3, n))
        root = _build_bst(rng, vals)
        return {"input": vals, "output": diameter(root)}

    vals = rng.sample(range(lo, hi), n)
    root = _build_bst(rng, vals)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Diameter of Binary Tree",
        "problem_statement": (
            f"Given a BST built by inserting {n} distinct integers, "
            f"find the diameter — the length of the longest path between any two nodes."
        ),
        "input_format": "Space-separated integers (insertion order).",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, vals)),
        "sample_output": str(diameter(root)),
        "test_cases": tcs,
    }


def _tree_lowest_common_ancestor(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = 1, 50

    def lca(root, p, q):
        if root is None: return None
        if root.v == p or root.v == q: return root.v
        l = lca(root.left, p, q); r = lca(root.right, p, q)
        if l and r: return root.v
        return l if l else r

    def make_tc():
        vals = rng.sample(range(lo, hi), rng.randint(4, n))
        root = _build_bst(rng, vals)
        p, q = rng.sample(vals, 2)
        return {"input": {"values": vals, "p": p, "q": q}, "output": lca(root, p, q)}

    vals = rng.sample(range(lo, hi), n)
    root = _build_bst(rng, vals)
    p, q = rng.sample(vals, 2)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Lowest Common Ancestor of BST",
        "problem_statement": (
            f"Given a BST built by inserting {n} distinct integers and two node values p and q, "
            f"find their lowest common ancestor."
        ),
        "input_format": "Line 1: insertion order. Line 2: p q.",
        "output_format": "A single integer — the LCA value.",
        "sample_input": f"{' '.join(map(str, vals))}\n{p} {q}",
        "sample_output": str(lca(root, p, q)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  STACKS  =========================================
# ---------------------------------------------------------------------------

def _stack_valid_parentheses(rng: random.Random) -> Dict:
    length = rng.randint(4, 12)
    pairs = rng.choice([["()", "[]", "{}"], ["()", "[]"], ["()", "{}"]])
    var = rng.choice(STR_NAMES)

    def solve(s):
        stack = []; mapping = {')': '(', ']': '[', '}': '{'}
        for c in s:
            if c in '([{': stack.append(c)
            elif c in ')]}':
                if not stack or stack[-1] != mapping[c]: return False
                stack.pop()
        return len(stack) == 0

    def make_tc():
        s = "".join(rng.choice("".join(pairs)) for _ in range(rng.randint(2, length)))
        return {"input": s, "output": solve(s)}

    sample = "".join(rng.choice("".join(pairs)) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Valid Parentheses",
        "problem_statement": (
            f"Given a string `{var}` of length up to {length} containing only "
            f"characters from '{' '.join(pairs)}', determine if the brackets are valid."
        ),
        "input_format": "A single string.",
        "output_format": "true or false.",
        "sample_input": sample,
        "sample_output": str(solve(sample)).lower(),
        "test_cases": tcs,
    }


def _stack_next_greater_element(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(1, 5), rng.randint(15, 30)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        result = [-1] * len(arr); stack = []
        for i in range(len(arr)):
            while stack and arr[stack[-1]] < arr[i]:
                result[stack.pop()] = arr[i]
            stack.append(i)
        return result

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Next Greater Element",
        "problem_statement": (
            f"Given an array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"for each element find the next greater element to its right. "
            f"If none exists, output -1."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "Space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _stack_min_stack(rng: random.Random) -> Dict:
    ops_count = rng.randint(5, 10)
    lo, hi = rng.randint(-10, 0), rng.randint(5, 20)

    def simulate(ops):
        stack = []; min_stack = []; results = []
        for op, val in ops:
            if op == "push":
                stack.append(val)
                min_stack.append(min(val, min_stack[-1] if min_stack else val))
            elif op == "pop" and stack:
                stack.pop(); min_stack.pop()
            elif op == "getMin" and stack:
                results.append(min_stack[-1])
        return results

    def make_tc():
        ops = []
        for _ in range(rng.randint(4, ops_count)):
            choice = rng.choice(["push", "push", "pop", "getMin"])
            ops.append((choice, rng.randint(lo, hi) if choice == "push" else 0))
        return {"input": ops, "output": simulate(ops)}

    ops = []
    for _ in range(ops_count):
        choice = rng.choice(["push", "push", "pop", "getMin"])
        ops.append((choice, rng.randint(lo, hi) if choice == "push" else 0))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Min Stack",
        "problem_statement": (
            f"Design a stack that supports push, pop, and getMin in O(1). "
            f"Given a sequence of {ops_count} operations, output the results of all getMin calls."
        ),
        "input_format": "Each line: operation [value]. Operations: push val, pop, getMin.",
        "output_format": "Space-separated getMin results.",
        "sample_input": "\n".join(f"{op} {val}" if op == "push" else op for op, val in ops),
        "sample_output": " ".join(map(str, simulate(ops))),
        "test_cases": tcs,
    }


def _stack_evaluate_rpn(rng: random.Random) -> Dict:
    depth = rng.randint(2, 5)

    def make_rpn(d):
        if d == 0 or rng.random() < 0.3:
            v = rng.randint(1, 15)
            return [str(v)], v
        op = rng.choice(["+", "-", "*"])
        left_tokens, lv = make_rpn(d - 1)
        right_tokens, rv = make_rpn(d - 1)
        if op == "+": val = lv + rv
        elif op == "-": val = lv - rv
        else: val = lv * rv
        return left_tokens + right_tokens + [op], val

    def solve(tokens):
        stack = []
        for t in tokens:
            if t in "+-*":
                b, a = stack.pop(), stack.pop()
                if t == "+": stack.append(a + b)
                elif t == "-": stack.append(a - b)
                else: stack.append(a * b)
            else: stack.append(int(t))
        return stack[0]

    tokens, expected = make_rpn(depth)

    # Generate unique test cases by deduplicating on the token string
    seen_keys = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        t, v = make_rpn(rng.randint(1, depth))
        key = " ".join(t)
        if key not in seen_keys:
            seen_keys.add(key)
            tcs.append({"input": t, "output": v})

    ps_variants = [
        "Evaluate an arithmetic expression in Reverse Polish Notation. Valid operators are +, -, *. Each operand is an integer.",
        "Given a list of tokens in postfix (RPN) notation, compute the result. Operators: +, -, *.",
        "Compute the value of a Reverse Polish Notation expression using a stack. Operators are +, -, *.",
        "Evaluate the postfix expression. Each token is either an integer or one of +, -, *.",
        "Using a stack, evaluate the given RPN expression. Supported operators: +, -, *.",
    ]
    return {
        "title": "Evaluate Reverse Polish Notation",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated tokens.",
        "output_format": "A single integer result.",
        "sample_input": " ".join(tokens),
        "sample_output": str(expected),
        "test_cases": tcs,
    }


def _stack_largest_rectangle_histogram(rng: random.Random) -> Dict:
    n = rng.randint(5, 12)
    max_h = rng.randint(5, 20)
    var = rng.choice(VAR_NAMES)

    def solve(heights):
        stack = []; max_area = 0; heights = heights + [0]
        for i, h in enumerate(heights):
            start = i
            while stack and stack[-1][1] > h:
                idx, ht = stack.pop()
                max_area = max(max_area, ht * (i - idx))
                start = idx
            stack.append((start, h))
        return max_area

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        h = tuple(rng.randint(0, max_h) for _ in range(rng.randint(3, n)))
        if h not in seen:
            seen.add(h)
            tcs.append({"input": list(h), "output": solve(list(h))})

    sample = [rng.randint(0, max_h) for _ in range(n)]
    ps_variants = [
        f"Given an array `{var}` of {n} non-negative integers representing bar heights (max height {max_h}), find the area of the largest rectangle in the histogram.",
        f"An array `{var}` of {n} bar heights (each ≤ {max_h}) forms a histogram. Find the maximum rectangular area that fits within it.",
        f"Given histogram bar heights `{var}` ({n} bars, max height {max_h}), compute the largest rectangle area using a stack.",
        f"Find the largest rectangle that can be formed in a histogram of {n} bars with heights up to {max_h}.",
        f"Given {n} histogram bars with heights in [0, {max_h}], return the area of the largest rectangle that fits entirely within the histogram.",
    ]
    return {
        "title": "Largest Rectangle in Histogram",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  QUEUES  =========================================
# ---------------------------------------------------------------------------

def _queue_sliding_window_max(rng: random.Random) -> Dict:
    n = rng.randint(7, 12)
    k = rng.randint(2, min(4, n - 1))
    lo, hi = rng.randint(-5, 0), rng.randint(5, 15)
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        dq = deque(); result = []
        for i, v in enumerate(arr):
            while dq and dq[0] < i - k + 1: dq.popleft()
            while dq and arr[dq[-1]] < v: dq.pop()
            dq.append(i)
            if i >= k - 1: result.append(arr[dq[0]])
        return result

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(k + 1, n))]
        kk = rng.randint(2, min(k, len(a) - 1))
        return {"input": {"array": a, "k": kk}, "output": solve(a, kk)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Sliding Window Maximum",
        "problem_statement": (
            f"Given an array `{var}` of {n} integers (range [{lo}, {hi}]) and window size k={k}, "
            f"return the maximum value in each sliding window of size k."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "Space-separated maximums.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": " ".join(map(str, solve(sample, k))),
        "test_cases": tcs,
    }


def _queue_first_non_repeating(rng: random.Random) -> Dict:
    length = rng.randint(5, 10)
    charset = "abcde"
    var = rng.choice(STR_NAMES)

    def solve(s):
        from collections import Counter
        count = Counter(s)
        for c in s:
            if count[c] == 1: return c
        return "#"

    def make_tc():
        s = "".join(rng.choice(charset) for _ in range(rng.randint(3, length)))
        return {"input": s, "output": solve(s)}

    sample = "".join(rng.choice(charset) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "First Non-Repeating Character",
        "problem_statement": (
            f"Given a string `{var}` of length up to {length} over '{charset}', "
            f"find the first non-repeating character. Return '#' if none exists."
        ),
        "input_format": "A single string.",
        "output_format": "A single character.",
        "sample_input": sample,
        "sample_output": solve(sample),
        "test_cases": tcs,
    }


def _queue_circular_queue(rng: random.Random) -> Dict:
    capacity = rng.randint(3, 6)
    ops_count = rng.randint(6, 10)
    lo, hi = 1, 20

    def simulate(capacity, ops):
        q = deque(); results = []
        for op, val in ops:
            if op == "enqueue":
                if len(q) < capacity: q.append(val); results.append(True)
                else: results.append(False)
            elif op == "dequeue":
                if q: q.popleft(); results.append(True)
                else: results.append(False)
            elif op == "front":
                results.append(q[0] if q else -1)
            elif op == "rear":
                results.append(q[-1] if q else -1)
        return results

    def make_tc():
        ops = []
        for _ in range(rng.randint(4, ops_count)):
            op = rng.choice(["enqueue", "enqueue", "dequeue", "front", "rear"])
            ops.append((op, rng.randint(lo, hi) if op == "enqueue" else 0))
        return {"input": {"capacity": capacity, "ops": ops}, "output": simulate(capacity, ops)}

    ops = []
    for _ in range(ops_count):
        op = rng.choice(["enqueue", "enqueue", "dequeue", "front", "rear"])
        ops.append((op, rng.randint(lo, hi) if op == "enqueue" else 0))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Circular Queue Simulation",
        "problem_statement": (
            f"Simulate a circular queue of capacity {capacity}. "
            f"Support: enqueue(val), dequeue(), front(), rear(). "
            f"enqueue/dequeue return true/false; front/rear return value or -1."
        ),
        "input_format": "Line 1: capacity. Each subsequent line: operation [value].",
        "output_format": "Space-separated results for each operation.",
        "sample_input": f"{capacity}\n" + "\n".join(f"{op} {val}" if op == "enqueue" else op for op, val in ops),
        "sample_output": " ".join(str(r).lower() if isinstance(r, bool) else str(r) for r in simulate(capacity, ops)),
        "test_cases": tcs,
    }


def _queue_task_scheduler(rng: random.Random) -> Dict:
    n_tasks = rng.randint(4, 8)
    cooldown = rng.randint(1, 3)
    tasks = [rng.choice("ABCDE") for _ in range(n_tasks)]

    def solve(tasks, n):
        from collections import Counter
        counts = Counter(tasks)
        max_count = max(counts.values())
        max_count_tasks = sum(1 for v in counts.values() if v == max_count)
        return max(len(tasks), (max_count - 1) * (n + 1) + max_count_tasks)

    def make_tc():
        nt = rng.randint(3, n_tasks)
        ts = [rng.choice("ABCDE") for _ in range(nt)]
        cd = rng.randint(1, cooldown)
        return {"input": {"tasks": ts, "n": cd}, "output": solve(ts, cd)}

    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Task Scheduler",
        "problem_statement": (
            f"Given a list of {n_tasks} CPU tasks labeled A-E and a cooldown period n={cooldown}, "
            f"find the minimum number of intervals needed to finish all tasks."
        ),
        "input_format": "Line 1: space-separated task labels. Line 2: cooldown n.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(tasks)}\n{cooldown}",
        "sample_output": str(solve(tasks, cooldown)),
        "test_cases": tcs,
    }


def _queue_bfs_level_order(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)
    max_w = rng.randint(5, 15)

    def solve(n, edges, src):
        adj = defaultdict(list)
        for u, v in edges: adj[u].append(v); adj[v].append(u)
        dist = [-1] * n; dist[src] = 0
        q = deque([src])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] == -1: dist[v] = dist[u] + 1; q.append(v)
        return dist

    def make_unique_tc():
        nn = rng.randint(3, n)
        edges = [(rng.randint(0, i-1), i) for i in range(1, nn)]
        src = rng.randint(0, nn - 1)
        return {"input": {"nodes": nn, "edges": edges, "src": src}, "output": solve(nn, edges, src)}

    edges = [(rng.randint(0, i-1), i) for i in range(1, n)]
    src = rng.randint(0, n - 1)

    seen_keys = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        tc = make_unique_tc()
        key = str(tc["input"])
        if key not in seen_keys:
            seen_keys.add(key)
            tcs.append(tc)

    ps_variants = [
        f"Given an undirected graph with {n} nodes and edges, find the BFS distance from source node {src} to all other nodes. Output -1 for unreachable nodes.",
        f"Using BFS, compute the shortest hop count from node {src} to every other node in a {n}-node undirected graph. Use -1 for unreachable nodes.",
        f"Find the BFS distance array from source {src} in an undirected graph with {n} nodes. Unreachable nodes get distance -1.",
        f"Given a {n}-node undirected graph, output the minimum number of edges from node {src} to each other node (-1 if unreachable).",
        f"Perform BFS from node {src} on a {n}-node graph and return the distance to every node. Use -1 for nodes that cannot be reached.",
    ]
    return {
        "title": "BFS Level-Order Distances",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: n e src. Next e lines: u v.",
        "output_format": "n space-separated distances.",
        "sample_input": f"{n} {len(edges)} {src}\n" + "\n".join(f"{u} {v}" for u, v in edges),
        "sample_output": " ".join(map(str, solve(n, edges, src))),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  GREEDY  =========================================
# ---------------------------------------------------------------------------

def _greedy_activity_selection(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    max_end = rng.randint(15, 25)

    def solve(activities):
        acts = sorted(activities, key=lambda x: x[1])
        count = 0; last_end = -1
        for start, end in acts:
            if start >= last_end: count += 1; last_end = end
        return count

    def make_tc():
        acts = []
        for _ in range(rng.randint(3, n)):
            s = rng.randint(0, max_end - 2)
            e = rng.randint(s + 1, max_end)
            acts.append((s, e))
        return {"input": acts, "output": solve(acts)}

    acts = []
    for _ in range(n):
        s = rng.randint(0, max_end - 2); e = rng.randint(s + 1, max_end)
        acts.append((s, e))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Activity Selection Problem",
        "problem_statement": (
            f"Given {n} activities with start and end times, select the maximum number "
            f"of non-overlapping activities."
        ),
        "input_format": f"{n} lines each with: start end.",
        "output_format": "Maximum number of activities.",
        "sample_input": "\n".join(f"{s} {e}" for s, e in acts),
        "sample_output": str(solve(acts)),
        "test_cases": tcs,
    }


def _greedy_fractional_knapsack(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    capacity = rng.randint(15, 30)
    max_w = rng.randint(5, 12)
    max_v = rng.randint(10, 25)

    def solve(items, cap):
        items_sorted = sorted(items, key=lambda x: x[1] / x[0], reverse=True)
        total = 0.0; rem = cap
        for w, v in items_sorted:
            if rem <= 0: break
            take = min(w, rem); total += take * (v / w); rem -= take
        return round(total, 2)

    def make_tc():
        items = [(rng.randint(1, max_w), rng.randint(1, max_v)) for _ in range(rng.randint(3, n))]
        cap = rng.randint(10, capacity)
        return {"input": {"items": items, "capacity": cap}, "output": solve(items, cap)}

    items = [(rng.randint(1, max_w), rng.randint(1, max_v)) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Fractional Knapsack",
        "problem_statement": (
            f"Given {n} items (weight, value) and knapsack capacity {capacity}, "
            f"maximize value by taking fractions of items. Round to 2 decimal places."
        ),
        "input_format": "Line 1: n capacity. Next n lines: weight value.",
        "output_format": "Maximum value (2 decimal places).",
        "sample_input": f"{n} {capacity}\n" + "\n".join(f"{w} {v}" for w, v in items),
        "sample_output": str(solve(items, capacity)),
        "test_cases": tcs,
    }


def _greedy_jump_game(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    max_jump = rng.randint(2, 5)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        max_reach = 0
        for i, v in enumerate(arr):
            if i > max_reach: return False
            max_reach = max(max_reach, i + v)
        return True

    def make_tc():
        a = [rng.randint(0, max_jump) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(0, max_jump) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Jump Game",
        "problem_statement": (
            f"Given array `{var}` of {n} non-negative integers where each element represents "
            f"max jump length from that position, determine if you can reach the last index."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "true or false.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)).lower(),
        "test_cases": tcs,
    }


def _greedy_minimum_platforms(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    max_time = rng.randint(20, 40)

    def solve(arrivals, departures):
        events = sorted([(t, 1) for t in arrivals] + [(t, -1) for t in departures])
        cur = 0; max_plat = 0
        for _, e in events:
            cur += e; max_plat = max(max_plat, cur)
        return max_plat

    def make_tc():
        nn = rng.randint(3, n)
        arrivals = sorted(rng.randint(0, max_time - 2) for _ in range(nn))
        departures = sorted(a + rng.randint(1, 5) for a in arrivals)
        return {"input": {"arrivals": arrivals, "departures": departures}, "output": solve(arrivals, departures)}

    arrivals = sorted(rng.randint(0, max_time - 2) for _ in range(n))
    departures = sorted(a + rng.randint(1, 5) for a in arrivals)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Minimum Number of Platforms",
        "problem_statement": (
            f"Given arrival and departure times of {n} trains, "
            f"find the minimum number of platforms required."
        ),
        "input_format": "Line 1: arrivals. Line 2: departures.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, arrivals))}\n{' '.join(map(str, departures))}",
        "sample_output": str(solve(arrivals, departures)),
        "test_cases": tcs,
    }


def _greedy_gas_station(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    max_gas = rng.randint(5, 12)

    def solve(gas, cost):
        total = 0; tank = 0; start = 0
        for i in range(len(gas)):
            diff = gas[i] - cost[i]; total += diff; tank += diff
            if tank < 0: start = i + 1; tank = 0
        return start if total >= 0 else -1

    def make_tc():
        nn = rng.randint(3, n)
        gas = [rng.randint(1, max_gas) for _ in range(nn)]
        cost = [rng.randint(1, max_gas) for _ in range(nn)]
        return {"input": {"gas": gas, "cost": cost}, "output": solve(gas, cost)}

    gas = [rng.randint(1, max_gas) for _ in range(n)]
    cost = [rng.randint(1, max_gas) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Gas Station",
        "problem_statement": (
            f"There are {n} gas stations in a circle. Given gas[i] and cost[i] to travel to next, "
            f"find the starting station index to complete the circuit. Return -1 if impossible."
        ),
        "input_format": "Line 1: gas values. Line 2: cost values.",
        "output_format": "Starting index or -1.",
        "sample_input": f"{' '.join(map(str, gas))}\n{' '.join(map(str, cost))}",
        "sample_output": str(solve(gas, cost)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  HASHING  ========================================
# ---------------------------------------------------------------------------

def _hashing_group_anagrams(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    length = rng.randint(3, 6)
    charset = "abcde"

    def solve(words):
        groups = defaultdict(list)
        for w in words: groups[tuple(sorted(w))].append(w)
        return sorted([sorted(g) for g in groups.values()])

    def make_tc():
        words = ["".join(rng.choice(charset) for _ in range(rng.randint(2, length)))
                 for _ in range(rng.randint(3, n))]
        return {"input": words, "output": solve(words)}

    words = ["".join(rng.choice(charset) for _ in range(length)) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Group Anagrams",
        "problem_statement": (
            f"Given {n} strings of length up to {length} over '{charset}', "
            f"group the anagrams together. Return groups sorted lexicographically."
        ),
        "input_format": "Space-separated strings.",
        "output_format": "Each group on a new line, words sorted and space-separated.",
        "sample_input": " ".join(words),
        "sample_output": "\n".join(" ".join(g) for g in solve(words)),
        "test_cases": tcs,
    }


def _hashing_subarray_sum_k(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(-5, 0), rng.randint(3, 10)
    k = rng.randint(2, 8)
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        count = 0; prefix = 0; seen = defaultdict(int); seen[0] = 1
        for v in arr:
            prefix += v
            count += seen[prefix - k]
            seen[prefix] += 1
        return count

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(4, n))]
        kk = rng.randint(1, 8)
        return {"input": {"array": a, "k": kk}, "output": solve(a, kk)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Subarray Sum Equals K",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]) and integer k={k}, "
            f"count the number of contiguous subarrays whose sum equals k."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": str(solve(sample, k)),
        "test_cases": tcs,
    }


def _hashing_longest_consecutive(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(1, 5), rng.randint(20, 40)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        s = set(arr); best = 0
        for v in s:
            if v - 1 not in s:
                cur = v; length = 1
                while cur + 1 in s: cur += 1; length += 1
                best = max(best, length)
        return best

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Longest Consecutive Sequence",
        "problem_statement": (
            f"Given an unsorted array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"find the length of the longest consecutive elements sequence. O(n) expected."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _hashing_four_sum_count(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    lo, hi = rng.randint(-5, 0), rng.randint(3, 8)

    def solve(A, B, C, D):
        ab = defaultdict(int)
        for a in A:
            for b in B: ab[a + b] += 1
        count = 0
        for c in C:
            for d in D: count += ab[-(c + d)]
        return count

    def make_tc():
        A = [rng.randint(lo, hi) for _ in range(rng.randint(2, n))]
        B = [rng.randint(lo, hi) for _ in range(rng.randint(2, n))]
        C = [rng.randint(lo, hi) for _ in range(rng.randint(2, n))]
        D = [rng.randint(lo, hi) for _ in range(rng.randint(2, n))]
        return {"input": {"A": A, "B": B, "C": C, "D": D}, "output": solve(A, B, C, D)}

    A = [rng.randint(lo, hi) for _ in range(n)]
    B = [rng.randint(lo, hi) for _ in range(n)]
    C = [rng.randint(lo, hi) for _ in range(n)]
    D = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "4Sum Count",
        "problem_statement": (
            f"Given four integer arrays A, B, C, D each of length {n} (range [{lo}, {hi}]), "
            f"count tuples (i,j,k,l) such that A[i]+B[j]+C[k]+D[l] == 0."
        ),
        "input_format": "Four lines, each with n space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, A))}\n{' '.join(map(str, B))}\n{' '.join(map(str, C))}\n{' '.join(map(str, D))}",
        "sample_output": str(solve(A, B, C, D)),
        "test_cases": tcs,
    }


def _hashing_top_k_frequent(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    k = rng.randint(2, 3)
    lo, hi = 1, 8
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        from collections import Counter
        counts = Counter(arr)
        return [x for x, _ in counts.most_common(k)]

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(5, n))]
        kk = min(k, len(set(a)))
        return {"input": {"array": a, "k": kk}, "output": solve(a, kk)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    kk = min(k, len(set(sample)))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": f"Top K Frequent Elements",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]) and integer k={kk}, "
            f"return the k most frequent elements."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "k space-separated integers.",
        "sample_input": f"{' '.join(map(str, sample))}\n{kk}",
        "sample_output": " ".join(map(str, solve(sample, kk))),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  SORTING  ========================================
# ---------------------------------------------------------------------------

def _sorting_merge_sort(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(-15, 0), rng.randint(10, 30)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        return sorted(arr)

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Sort Array (Merge Sort)",
        "problem_statement": (
            f"Given an array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"sort it in non-decreasing order using merge sort."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "Sorted space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _sorting_kth_largest(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    k = rng.randint(1, min(4, n))
    lo, hi = rng.randint(1, 5), rng.randint(20, 40)
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        return sorted(arr, reverse=True)[k - 1]

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(k + 1, n))]
        kk = rng.randint(1, min(k, len(a)))
        return {"input": {"array": a, "k": kk}, "output": solve(a, kk)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": f"Kth Largest Element",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]) and integer k={k}, "
            f"find the kth largest element."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": str(solve(sample, k)),
        "test_cases": tcs,
    }


def _sorting_count_inversions(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(1, 5), rng.randint(15, 25)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        count = 0
        for i in range(len(arr)):
            for j in range(i + 1, len(arr)):
                if arr[i] > arr[j]: count += 1
        return count

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Count Inversions",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"count the number of inversions (pairs i<j where arr[i]>arr[j])."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _sorting_sort_colors(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        return sorted(arr)

    def make_tc():
        a = [rng.randint(0, 2) for _ in range(rng.randint(4, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(0, 2) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Sort Colors (Dutch National Flag)",
        "problem_statement": (
            f"Given array `{var}` of {n} integers containing only 0, 1, 2, "
            f"sort them in-place so all 0s come first, then 1s, then 2s."
        ),
        "input_format": "Space-separated integers (0, 1, or 2).",
        "output_format": "Sorted space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _sorting_merge_intervals(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    max_end = rng.randint(15, 25)

    def solve(intervals):
        intervals = sorted(intervals)
        merged = [intervals[0]]
        for s, e in intervals[1:]:
            if s <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else: merged.append((s, e))
        return merged

    def make_tc():
        ivs = []
        for _ in range(rng.randint(3, n)):
            s = rng.randint(0, max_end - 2); e = rng.randint(s + 1, max_end)
            ivs.append((s, e))
        return {"input": ivs, "output": solve(ivs)}

    ivs = []
    for _ in range(n):
        s = rng.randint(0, max_end - 2); e = rng.randint(s + 1, max_end)
        ivs.append((s, e))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Merge Intervals",
        "problem_statement": (
            f"Given {n} intervals [start, end], merge all overlapping intervals "
            f"and return the resulting list."
        ),
        "input_format": f"{n} lines each with: start end.",
        "output_format": "Merged intervals, one per line: start end.",
        "sample_input": "\n".join(f"{s} {e}" for s, e in ivs),
        "sample_output": "\n".join(f"{s} {e}" for s, e in solve(ivs)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  SEARCHING  ======================================
# ---------------------------------------------------------------------------

def _searching_binary_search(rng: random.Random) -> Dict:
    n = rng.randint(8, 15)
    lo, hi = rng.randint(1, 5), rng.randint(30, 60)
    var = rng.choice(VAR_NAMES)

    def solve(arr, target):
        l, r = 0, len(arr) - 1
        while l <= r:
            m = (l + r) // 2
            if arr[m] == target: return m
            elif arr[m] < target: l = m + 1
            else: r = m - 1
        return -1

    def make_tc():
        a = sorted(rng.sample(range(lo, hi), rng.randint(5, n)))
        target = rng.choice(a + [rng.randint(lo, hi)])
        return {"input": {"array": a, "target": target}, "output": solve(a, target)}

    sample = sorted(rng.sample(range(lo, hi), n))
    target = rng.choice(sample + [rng.randint(lo, hi)])
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Binary Search",
        "problem_statement": (
            f"Given a sorted array `{var}` of {n} distinct integers (range [{lo}, {hi}]) "
            f"and a target, return the index of target or -1 if not found."
        ),
        "input_format": "Line 1: sorted space-separated integers. Line 2: target.",
        "output_format": "Index (0-based) or -1.",
        "sample_input": f"{' '.join(map(str, sample))}\n{target}",
        "sample_output": str(solve(sample, target)),
        "test_cases": tcs,
    }


def _searching_search_rotated(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(1, 5), rng.randint(30, 60)
    var = rng.choice(VAR_NAMES)

    def solve(arr, target):
        l, r = 0, len(arr) - 1
        while l <= r:
            m = (l + r) // 2
            if arr[m] == target: return m
            if arr[l] <= arr[m]:
                if arr[l] <= target < arr[m]: r = m - 1
                else: l = m + 1
            else:
                if arr[m] < target <= arr[r]: l = m + 1
                else: r = m - 1
        return -1

    def make_tc():
        a = sorted(rng.sample(range(lo, hi), rng.randint(4, n)))
        pivot = rng.randint(1, len(a) - 1)
        a = a[pivot:] + a[:pivot]
        target = rng.choice(a + [rng.randint(lo, hi)])
        return {"input": {"array": a, "target": target}, "output": solve(a, target)}

    a = sorted(rng.sample(range(lo, hi), n))
    pivot = rng.randint(1, n - 1); a = a[pivot:] + a[:pivot]
    target = rng.choice(a + [rng.randint(lo, hi)])
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Search in Rotated Sorted Array",
        "problem_statement": (
            f"Given a rotated sorted array `{var}` of {n} distinct integers and a target, "
            f"return the index of target or -1 if not found."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: target.",
        "output_format": "Index (0-based) or -1.",
        "sample_input": f"{' '.join(map(str, a))}\n{target}",
        "sample_output": str(solve(a, target)),
        "test_cases": tcs,
    }


def _searching_find_peak(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(1, 5), rng.randint(20, 40)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        l, r = 0, len(arr) - 1
        while l < r:
            m = (l + r) // 2
            if arr[m] < arr[m + 1]: l = m + 1
            else: r = m
        return l

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Find Peak Element",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"find any peak element index where arr[i] > arr[i-1] and arr[i] > arr[i+1]. "
            f"Assume arr[-1] = arr[n] = -inf."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A peak index (0-based).",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _searching_first_last_position(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(1, 5), rng.randint(10, 20)
    var = rng.choice(VAR_NAMES)

    def solve(arr, target):
        def first(arr, t):
            l, r, res = 0, len(arr)-1, -1
            while l <= r:
                m = (l+r)//2
                if arr[m] == t: res = m; r = m-1
                elif arr[m] < t: l = m+1
                else: r = m-1
            return res
        def last(arr, t):
            l, r, res = 0, len(arr)-1, -1
            while l <= r:
                m = (l+r)//2
                if arr[m] == t: res = m; l = m+1
                elif arr[m] < t: l = m+1
                else: r = m-1
            return res
        return [first(arr, target), last(arr, target)]

    def make_tc():
        a = sorted([rng.randint(lo, hi) for _ in range(rng.randint(4, n))])
        target = rng.choice(a + [rng.randint(lo, hi)])
        return {"input": {"array": a, "target": target}, "output": solve(a, target)}

    sample = sorted([rng.randint(lo, hi) for _ in range(n)])
    target = rng.choice(sample)
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "First and Last Position of Element",
        "problem_statement": (
            f"Given a sorted array `{var}` of {n} integers (may have duplicates, range [{lo}, {hi}]) "
            f"and a target, return [first_index, last_index]. Return [-1, -1] if not found."
        ),
        "input_format": "Line 1: sorted space-separated integers. Line 2: target.",
        "output_format": "Two space-separated integers.",
        "sample_input": f"{' '.join(map(str, sample))}\n{target}",
        "sample_output": " ".join(map(str, solve(sample, target))),
        "test_cases": tcs,
    }


def _searching_sqrt_integer(rng: random.Random) -> Dict:
    x = rng.randint(10, 10000)

    def solve(n):
        if n < 2: return n
        l, r = 1, n // 2
        while l <= r:
            m = (l + r) // 2
            if m * m == n: return m
            elif m * m < n: l = m + 1
            else: r = m - 1
        return r

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        n = rng.randint(1, 10000)
        if n not in seen:
            seen.add(n)
            tcs.append({"input": n, "output": solve(n)})

    ps_variants = [
        f"Given a non-negative integer x={x}, compute and return the integer square root (floor of sqrt(x)) without using built-in sqrt.",
        f"Find the floor of the square root of {x} using binary search. Do not use math.sqrt or **0.5.",
        f"Compute floor(sqrt({x})) using only integer arithmetic and binary search.",
        f"Given x={x}, return the largest integer r such that r*r ≤ x.",
        f"Without using built-in square root functions, find the integer square root of {x}.",
    ]
    return {
        "title": "Integer Square Root",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer.",
        "output_format": "A single integer.",
        "sample_input": str(x),
        "sample_output": str(solve(x)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  RECURSION  ======================================
# ---------------------------------------------------------------------------

def _recursion_fibonacci(rng: random.Random) -> Dict:
    n = rng.randint(8, 35)
    uid = _uid()

    def solve(n):
        a, b = 0, 1
        for _ in range(n): a, b = b, a + b
        return a

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(0, 35)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})

    ps_variants = [
        f"Given n={n}, return the nth Fibonacci number (0-indexed: F(0)=0, F(1)=1).",
        f"Compute F({n}) where F(0)=0, F(1)=1 and F(k)=F(k-1)+F(k-2).",
        f"Find the {n}th term of the Fibonacci sequence (starting F(0)=0, F(1)=1).",
        f"Using recursion or DP, calculate the Fibonacci value at index {n}.",
        f"Return F({n}): the Fibonacci sequence is 0, 1, 1, 2, 3, 5, 8, ...",
    ]
    return {
        "title": "Fibonacci Number",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer n.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _recursion_power(rng: random.Random) -> Dict:
    base = rng.randint(2, 9)
    exp = rng.randint(3, 15)

    def solve(b, e):
        if e == 0: return 1
        if e % 2 == 0: half = solve(b, e // 2); return half * half
        return b * solve(b, e - 1)

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        b = rng.randint(2, 9); e = rng.randint(0, 15)
        key = (b, e)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"base": b, "exp": e}, "output": solve(b, e)})

    ps_variants = [
        f"Implement pow(base, exp) using recursion and fast exponentiation. Compute {base}^{exp}.",
        f"Using binary exponentiation, compute {base} raised to the power {exp}.",
        f"Calculate {base}^{exp} efficiently using the fast power (exponentiation by squaring) method.",
        f"Given base={base} and exp={exp}, return base^exp using recursive fast exponentiation.",
        f"Compute the result of {base} to the power {exp} using divide-and-conquer exponentiation.",
    ]
    return {
        "title": "Power Function (Fast Exponentiation)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: base. Line 2: exp.",
        "output_format": "A single integer.",
        "sample_input": f"{base}\n{exp}",
        "sample_output": str(solve(base, exp)),
        "test_cases": tcs,
    }


def _recursion_tower_of_hanoi(rng: random.Random) -> Dict:
    n = rng.randint(2, 8)

    def solve(n):
        return (2 ** n) - 1

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(1, 10)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})

    ps_variants = [
        f"Given {n} disks in the Tower of Hanoi puzzle, find the minimum number of moves required to move all disks.",
        f"In the Tower of Hanoi problem with {n} disks, what is the minimum number of moves to transfer all disks from peg A to peg C?",
        f"Calculate the minimum moves needed to solve Tower of Hanoi with {n} disks and 3 pegs.",
        f"Tower of Hanoi: with {n} disks, return the fewest moves to move all disks from source to destination peg.",
        f"How many moves does it take to solve the Tower of Hanoi for {n} disks? Return the minimum count.",
    ]
    return {
        "title": "Tower of Hanoi — Move Count",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer n.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _recursion_flatten_nested(rng: random.Random) -> Dict:
    depth = rng.randint(2, 4)
    lo, hi = rng.randint(1, 5), rng.randint(15, 30)

    def make_nested(d):
        if d == 0 or rng.random() < 0.4:
            return rng.randint(lo, hi)
        return [make_nested(d - 1) for _ in range(rng.randint(1, 4))]

    def solve(lst):
        result = []
        def flatten(x):
            if isinstance(x, list):
                for item in x: flatten(item)
            else: result.append(x)
        flatten(lst)
        return result

    def make_tc():
        nested = make_nested(depth)
        return {"input": nested, "output": solve(nested)}

    sample = make_nested(depth)
    # Generate unique test cases by checking flattened output length as proxy
    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        tc = make_tc()
        key = str(tc["input"])
        if key not in seen:
            seen.add(key)
            tcs.append(tc)

    return {
        "title": "Flatten Nested List",
        "problem_statement": (
            f"Given a nested list of integers (depth up to {depth}), "
            f"flatten it into a single list of integers."
        ),
        "input_format": "A nested list (JSON format).",
        "output_format": "Space-separated integers.",
        "sample_input": str(sample),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _recursion_gcd(rng: random.Random) -> Dict:
    a = rng.randint(10, 500)
    b = rng.randint(10, 500)

    def solve(a, b):
        while b: a, b = b, a % b
        return a

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        x = rng.randint(5, 500); y = rng.randint(5, 500)
        key = (min(x, y), max(x, y))
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"a": x, "b": y}, "output": solve(x, y)})

    ps_variants = [
        f"Given two positive integers a={a} and b={b}, find their GCD using the Euclidean algorithm.",
        f"Compute the greatest common divisor of {a} and {b} using Euclid's recursive method.",
        f"Using the Euclidean algorithm, find GCD({a}, {b}).",
        f"Find the largest integer that divides both {a} and {b} without remainder.",
        f"Apply the Euclidean algorithm to compute the GCD of a={a} and b={b}.",
    ]
    return {
        "title": "Greatest Common Divisor (Euclidean)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: a. Line 2: b.",
        "output_format": "A single integer.",
        "sample_input": f"{a}\n{b}",
        "sample_output": str(solve(a, b)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  BACKTRACKING  ===================================
# ---------------------------------------------------------------------------

def _backtracking_permutations(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    start = rng.randint(1, 10)
    nums = list(range(start, start + n))

    def solve(nums):
        result = []
        def bt(path, remaining):
            if not remaining: result.append(path[:]); return
            for i, v in enumerate(remaining):
                path.append(v); bt(path, remaining[:i] + remaining[i+1:]); path.pop()
        bt([], nums)
        return sorted(result)

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(2, n)
        s = rng.randint(1, 15)
        ns = list(range(s, s + nn))
        key = tuple(ns)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": ns, "output": solve(ns)})

    ps_variants = [
        f"Given an array of {n} distinct integers {nums}, return all possible permutations in sorted order.",
        f"List every permutation of the {n} distinct integers {nums}. Output them in lexicographic order.",
        f"Using backtracking, generate all {n}! arrangements of {nums}.",
        f"Find all orderings of the array {nums} ({n} distinct integers). Sort the result.",
        f"Return the complete set of permutations for {nums}. Each permutation on its own line.",
    ]
    return {
        "title": "All Permutations",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated distinct integers.",
        "output_format": "Each permutation on a new line, space-separated.",
        "sample_input": " ".join(map(str, nums)),
        "sample_output": "\n".join(" ".join(map(str, p)) for p in solve(nums)),
        "test_cases": tcs,
    }


def _backtracking_subsets(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    start = rng.randint(1, 10)
    nums = list(range(start, start + n))

    def solve(nums):
        result = [[]]
        for v in nums:
            result += [s + [v] for s in result]
        return sorted(result, key=lambda x: (len(x), x))

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(2, n)
        s = rng.randint(1, 15)
        ns = list(range(s, s + nn))
        key = tuple(ns)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": ns, "output": solve(ns)})

    ps_variants = [
        f"Given an array of {n} distinct integers {nums}, return all possible subsets (power set).",
        f"Generate the power set of {nums} ({n} distinct integers). Include the empty set.",
        f"Using backtracking, enumerate every subset of {nums}. Sort by length then value.",
        f"Find all 2^{n} subsets of the array {nums}. Output each subset on its own line.",
        f"Return the complete power set for {nums}. Empty set first, then by increasing size.",
    ]
    return {
        "title": "All Subsets (Power Set)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated distinct integers.",
        "output_format": "Each subset on a new line (empty line for empty set), sorted by length then value.",
        "sample_input": " ".join(map(str, nums)),
        "sample_output": "\n".join(" ".join(map(str, s)) for s in solve(nums)),
        "test_cases": tcs,
    }


def _backtracking_n_queens_count(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)

    def solve(n):
        count = [0]
        cols = set(); diag1 = set(); diag2 = set()
        def bt(row):
            if row == n: count[0] += 1; return
            for col in range(n):
                if col in cols or (row - col) in diag1 or (row + col) in diag2: continue
                cols.add(col); diag1.add(row - col); diag2.add(row + col)
                bt(row + 1)
                cols.remove(col); diag1.remove(row - col); diag2.remove(row + col)
        bt(0)
        return count[0]

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(1, 9)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})

    ps_variants = [
        f"Given n={n}, count the number of distinct solutions to the N-Queens problem (place n queens on an n×n board so no two attack each other).",
        f"How many ways can you place {n} non-attacking queens on a {n}×{n} chessboard? Return the count.",
        f"Count all valid arrangements of {n} queens on a {n}×{n} board where no two queens share a row, column, or diagonal.",
        f"Using backtracking, find the total number of solutions to the {n}-Queens problem.",
        f"Return the number of distinct N-Queens solutions for n={n}.",
    ]
    return {
        "title": "N-Queens Count",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer n.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _backtracking_combination_sum(rng: random.Random) -> Dict:
    candidates = sorted(rng.sample(range(2, 15), rng.randint(4, 6)))
    target = rng.randint(6, 15)

    def solve(candidates, target):
        result = []
        def bt(start, path, remaining):
            if remaining == 0: result.append(path[:]); return
            for i in range(start, len(candidates)):
                if candidates[i] > remaining: break
                path.append(candidates[i]); bt(i, path, remaining - candidates[i]); path.pop()
        bt(0, [], target)
        return sorted(result)

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        cands = sorted(rng.sample(range(2, 15), rng.randint(4, 6)))
        t = rng.randint(5, 15)
        key = (tuple(cands), t)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"candidates": cands, "target": t}, "output": solve(cands, t)})

    ps_variants = [
        f"Given candidates {candidates} and target {target}, find all unique combinations that sum to target. Each number may be used unlimited times.",
        f"Using backtracking, find all combinations from {candidates} that add up to {target}. Numbers can repeat.",
        f"From the list {candidates}, find every combination (with repetition allowed) that sums to {target}.",
        f"Return all unique combinations of numbers from {candidates} that sum to {target}. Each element may be reused.",
        f"Find all ways to reach the target sum {target} using numbers from {candidates} (unlimited reuse allowed).",
    ]
    return {
        "title": "Combination Sum",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: space-separated candidates. Line 2: target.",
        "output_format": "Each combination on a new line, space-separated.",
        "sample_input": f"{' '.join(map(str, candidates))}\n{target}",
        "sample_output": "\n".join(" ".join(map(str, c)) for c in solve(candidates, target)),
        "test_cases": tcs,
    }


def _backtracking_word_search(rng: random.Random) -> Dict:
    rows, cols = rng.randint(3, 6), rng.randint(3, 6)
    charset = "ABCDEFGH"

    def solve(board, word):
        R, C = len(board), len(board[0])
        def dfs(r, c, idx, visited):
            if idx == len(word): return True
            if r < 0 or r >= R or c < 0 or c >= C: return False
            if (r, c) in visited or board[r][c] != word[idx]: return False
            visited.add((r, c))
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                if dfs(r+dr, c+dc, idx+1, visited): return True
            visited.remove((r, c))
            return False
        for r in range(R):
            for c in range(C):
                if dfs(r, c, 0, set()): return True
        return False

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        r, c = rng.randint(3, rows), rng.randint(3, cols)
        board = [[rng.choice(charset) for _ in range(c)] for _ in range(r)]
        word = "".join(rng.choice(charset) for _ in range(rng.randint(2, 5)))
        key = (tuple(tuple(row) for row in board), word)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"board": board, "word": word}, "output": solve(board, word)})

    board = [[rng.choice(charset) for _ in range(cols)] for _ in range(rows)]
    word = "".join(rng.choice(charset) for _ in range(rng.randint(2, 5)))
    ps_variants = [
        f"Given a {rows}x{cols} grid of characters and a word, determine if the word exists in the grid by moving horizontally/vertically.",
        f"Search a {rows}×{cols} character grid for the given word. Adjacent cells (up/down/left/right) form the path.",
        f"Given a {rows} row by {cols} column grid of letters, check if the word can be traced through adjacent cells.",
        f"Determine whether the word can be found in the {rows}×{cols} grid by following a path of horizontally or vertically adjacent cells.",
        f"Using DFS backtracking, find if the word exists as a connected path in the {rows}×{cols} character grid.",
    ]
    return {
        "title": "Word Search in Grid",
        "problem_statement": rng.choice(ps_variants),
        "input_format": f"Lines 1-{rows}: grid rows (space-separated chars). Last line: word.",
        "output_format": "true or false.",
        "sample_input": "\n".join(" ".join(row) for row in board) + f"\n{word}",
        "sample_output": str(solve(board, word)).lower(),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  LINKED LISTS  ===================================
# ---------------------------------------------------------------------------

def _ll_reverse(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    lo, hi = rng.randint(1, 5), rng.randint(10, 20)
    var = rng.choice(VAR_NAMES)

    def solve(lst): return lst[::-1]

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Reverse Linked List",
        "problem_statement": (
            f"Given a linked list of {n} integers (range [{lo}, {hi}]) represented as an array, "
            f"reverse it."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "Reversed space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _ll_detect_cycle(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    lo, hi = 1, 20

    def solve(lst, cycle_pos):
        return cycle_pos >= 0

    def make_tc():
        lst = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        cycle_pos = rng.choice([-1, -1, rng.randint(0, len(lst) - 1)])
        return {"input": {"list": lst, "cycle_pos": cycle_pos}, "output": solve(lst, cycle_pos)}

    lst = [rng.randint(lo, hi) for _ in range(n)]
    cycle_pos = rng.choice([-1, rng.randint(0, n - 1)])
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Detect Cycle in Linked List",
        "problem_statement": (
            f"Given a linked list of {n} integers and a cycle_pos (-1 if no cycle, "
            f"else the index where the tail connects), determine if a cycle exists."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: cycle_pos.",
        "output_format": "true or false.",
        "sample_input": f"{' '.join(map(str, lst))}\n{cycle_pos}",
        "sample_output": str(solve(lst, cycle_pos)).lower(),
        "test_cases": tcs,
    }


def _ll_merge_sorted(rng: random.Random) -> Dict:
    n1 = rng.randint(3, 6); n2 = rng.randint(3, 6)
    lo, hi = rng.randint(1, 5), rng.randint(15, 25)

    def solve(l1, l2):
        return sorted(l1 + l2)

    def make_tc():
        a = sorted(rng.randint(lo, hi) for _ in range(rng.randint(2, n1)))
        b = sorted(rng.randint(lo, hi) for _ in range(rng.randint(2, n2)))
        return {"input": {"l1": a, "l2": b}, "output": solve(a, b)}

    l1 = sorted(rng.randint(lo, hi) for _ in range(n1))
    l2 = sorted(rng.randint(lo, hi) for _ in range(n2))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Merge Two Sorted Linked Lists",
        "problem_statement": (
            f"Given two sorted linked lists of lengths {n1} and {n2} (range [{lo}, {hi}]), "
            f"merge them into one sorted list."
        ),
        "input_format": "Line 1: sorted integers for l1. Line 2: sorted integers for l2.",
        "output_format": "Merged sorted space-separated integers.",
        "sample_input": f"{' '.join(map(str, l1))}\n{' '.join(map(str, l2))}",
        "sample_output": " ".join(map(str, solve(l1, l2))),
        "test_cases": tcs,
    }


def _ll_nth_from_end(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    k = rng.randint(1, min(3, n))
    lo, hi = 1, 20
    var = rng.choice(VAR_NAMES)

    def solve(lst, k):
        return lst[len(lst) - k]

    def make_tc():
        lst = [rng.randint(lo, hi) for _ in range(rng.randint(k + 1, n))]
        kk = rng.randint(1, min(k, len(lst)))
        return {"input": {"list": lst, "k": kk}, "output": solve(lst, kk)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Nth Node From End of Linked List",
        "problem_statement": (
            f"Given a linked list `{var}` of {n} integers and integer k={k}, "
            f"return the value of the kth node from the end."
        ),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": str(solve(sample, k)),
        "test_cases": tcs,
    }


def _ll_palindrome(rng: random.Random) -> Dict:
    n = rng.randint(4, 8)
    lo, hi = 1, 9
    var = rng.choice(VAR_NAMES)

    def solve(lst):
        return lst == lst[::-1]

    def make_tc():
        if rng.random() < 0.5:
            half = [rng.randint(lo, hi) for _ in range(rng.randint(2, n // 2))]
            lst = half + half[::-1]
        else:
            lst = [rng.randint(lo, hi) for _ in range(rng.randint(3, n))]
        return {"input": lst, "output": solve(lst)}

    half = [rng.randint(lo, hi) for _ in range(n // 2)]
    sample = half + half[::-1]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Palindrome Linked List",
        "problem_statement": (
            f"Given a linked list `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"determine if it is a palindrome."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "true or false.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)).lower(),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  TWO POINTERS  ===================================
# ---------------------------------------------------------------------------

def _two_ptr_three_sum(rng: random.Random) -> Dict:
    n = rng.randint(6, 10)
    lo, hi = rng.randint(-8, -2), rng.randint(2, 8)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        arr = sorted(arr); result = []
        for i in range(len(arr) - 2):
            if i > 0 and arr[i] == arr[i-1]: continue
            l, r = i + 1, len(arr) - 1
            while l < r:
                s = arr[i] + arr[l] + arr[r]
                if s == 0:
                    result.append([arr[i], arr[l], arr[r]])
                    while l < r and arr[l] == arr[l+1]: l += 1
                    while l < r and arr[r] == arr[r-1]: r -= 1
                    l += 1; r -= 1
                elif s < 0: l += 1
                else: r -= 1
        return sorted(result)

    def make_tc():
        a = [rng.randint(lo, hi) for _ in range(rng.randint(5, n))]
        return {"input": a, "output": solve(a)}

    sample = [rng.randint(lo, hi) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "3Sum",
        "problem_statement": (
            f"Given array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"find all unique triplets that sum to zero."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "Each triplet on a new line, space-separated.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": "\n".join(" ".join(map(str, t)) for t in solve(sample)),
        "test_cases": tcs,
    }


def _two_ptr_container_water(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    max_h = rng.randint(8, 15)
    var = rng.choice(VAR_NAMES)

    def solve(heights):
        l, r = 0, len(heights) - 1; best = 0
        while l < r:
            best = max(best, min(heights[l], heights[r]) * (r - l))
            if heights[l] < heights[r]: l += 1
            else: r -= 1
        return best

    def make_tc():
        h = [rng.randint(1, max_h) for _ in range(rng.randint(4, n))]
        return {"input": h, "output": solve(h)}

    sample = [rng.randint(1, max_h) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Container With Most Water",
        "problem_statement": (
            f"Given array `{var}` of {n} heights (max {max_h}), "
            f"find two lines that together with the x-axis form a container holding the most water."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _two_ptr_remove_duplicates(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    lo, hi = rng.randint(1, 3), rng.randint(8, 15)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        return sorted(set(arr))

    def make_tc():
        a = sorted([rng.randint(lo, hi) for _ in range(rng.randint(4, n))])
        return {"input": a, "output": solve(a)}

    sample = sorted([rng.randint(lo, hi) for _ in range(n)])
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Remove Duplicates from Sorted Array",
        "problem_statement": (
            f"Given a sorted array `{var}` of {n} integers (range [{lo}, {hi}]) with duplicates, "
            f"return the unique elements in sorted order."
        ),
        "input_format": "Sorted space-separated integers.",
        "output_format": "Unique sorted space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _two_ptr_sort_squares(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(-8, -2), rng.randint(2, 8)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        return sorted(x * x for x in arr)

    def make_tc():
        a = sorted([rng.randint(lo, hi) for _ in range(rng.randint(3, n))])
        return {"input": a, "output": solve(a)}

    sample = sorted([rng.randint(lo, hi) for _ in range(n)])
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Squares of a Sorted Array",
        "problem_statement": (
            f"Given a sorted array `{var}` of {n} integers (range [{lo}, {hi}]), "
            f"return an array of the squares of each number, sorted in non-decreasing order."
        ),
        "input_format": "Sorted space-separated integers.",
        "output_format": "Sorted squared space-separated integers.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": " ".join(map(str, solve(sample))),
        "test_cases": tcs,
    }


def _two_ptr_trapping_rain(rng: random.Random) -> Dict:
    n = rng.randint(6, 12)
    max_h = rng.randint(5, 10)
    var = rng.choice(VAR_NAMES)

    def solve(heights):
        l, r = 0, len(heights) - 1
        left_max = right_max = water = 0
        while l <= r:
            if heights[l] <= heights[r]:
                if heights[l] >= left_max: left_max = heights[l]
                else: water += left_max - heights[l]
                l += 1
            else:
                if heights[r] >= right_max: right_max = heights[r]
                else: water += right_max - heights[r]
                r -= 1
        return water

    def make_tc():
        h = [rng.randint(0, max_h) for _ in range(rng.randint(4, n))]
        return {"input": h, "output": solve(h)}

    sample = [rng.randint(0, max_h) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Trapping Rain Water",
        "problem_statement": (
            f"Given array `{var}` of {n} non-negative integers (max height {max_h}) "
            f"representing an elevation map, compute how much water it can trap after raining."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  SLIDING WINDOW  =================================
# ---------------------------------------------------------------------------

def _sw_longest_substring_no_repeat(rng: random.Random) -> Dict:
    length = rng.randint(8, 15)
    charset = rng.choice(["abcde", "abcdef", "abcdefg"])
    var = rng.choice(STR_NAMES)

    def solve(s):
        seen = {}; best = 0; l = 0
        for r, c in enumerate(s):
            if c in seen and seen[c] >= l: l = seen[c] + 1
            seen[c] = r; best = max(best, r - l + 1)
        return best

    def make_tc():
        s = "".join(rng.choice(charset) for _ in range(rng.randint(4, length)))
        return {"input": s, "output": solve(s)}

    sample = "".join(rng.choice(charset) for _ in range(length))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Longest Substring Without Repeating Characters",
        "problem_statement": (
            f"Given string `{var}` of length up to {length} over '{charset}', "
            f"find the length of the longest substring without repeating characters."
        ),
        "input_format": "A single string.",
        "output_format": "A single integer.",
        "sample_input": sample,
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _sw_max_sum_subarray_k(rng: random.Random) -> Dict:
    n = rng.randint(7, 15)
    k = rng.randint(2, min(5, n - 1))
    lo, hi = rng.randint(-10, 0), rng.randint(5, 20)
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        window = sum(arr[:k]); best = window
        for i in range(k, len(arr)):
            window += arr[i] - arr[i - k]; best = max(best, window)
        return best

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        a = tuple(rng.randint(lo, hi) for _ in range(rng.randint(k + 1, n)))
        kk = rng.randint(2, min(k, len(a) - 1))
        key = (a, kk)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"array": list(a), "k": kk}, "output": solve(list(a), kk)})

    sample = [rng.randint(lo, hi) for _ in range(n)]
    ps_variants = [
        f"Given array `{var}` of {n} integers (range [{lo}, {hi}]) and window size k={k}, find the maximum sum of any contiguous subarray of size k.",
        f"Find the highest sum achievable by any contiguous subarray of exactly k={k} elements in `{var}` ({n} integers, range [{lo}, {hi}]).",
        f"Slide a window of size k={k} over `{var}` ({n} elements, [{lo}, {hi}]) and return the maximum window sum.",
        f"Given `{var}` ({n} integers in [{lo}, {hi}]) and k={k}, return the maximum sum of k consecutive elements.",
        f"Using a sliding window of size k={k}, find the maximum subarray sum in `{var}` ({n} integers, [{lo}, {hi}]).",
    ]
    return {
        "title": "Maximum Sum Subarray of Size K",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: space-separated integers. Line 2: k.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": str(solve(sample, k)),
        "test_cases": tcs,
    }


def _sw_minimum_window_substring(rng: random.Random) -> Dict:
    length = rng.randint(8, 14)
    t_len = rng.randint(2, 4)
    charset = "ABCDE"
    v1, v2 = rng.sample(STR_NAMES, 2)

    def solve(s, t):
        from collections import Counter
        need = Counter(t); missing = len(t)
        best = ""; l = 0
        for r, c in enumerate(s):
            if need[c] > 0: missing -= 1
            need[c] -= 1
            while missing == 0:
                window = s[l:r+1]
                if not best or len(window) < len(best): best = window
                need[s[l]] += 1
                if need[s[l]] > 0: missing += 1
                l += 1
        return best

    def make_tc():
        s = "".join(rng.choice(charset) for _ in range(rng.randint(6, length)))
        t = "".join(rng.choice(charset) for _ in range(rng.randint(1, t_len)))
        return {"input": {"s": s, "t": t}, "output": solve(s, t)}

    s = "".join(rng.choice(charset) for _ in range(length))
    t = "".join(rng.choice(charset) for _ in range(t_len))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Minimum Window Substring",
        "problem_statement": (
            f"Given strings `{v1}` (length {length}) and `{v2}` (length {t_len}) over '{charset}', "
            f"find the minimum window in `{v1}` that contains all characters of `{v2}`. "
            f"Return empty string if no such window exists."
        ),
        "input_format": "Line 1: s. Line 2: t.",
        "output_format": "The minimum window substring.",
        "sample_input": f"{s}\n{t}",
        "sample_output": solve(s, t),
        "test_cases": tcs,
    }


def _sw_longest_ones_after_flip(rng: random.Random) -> Dict:
    n = rng.randint(8, 15)
    k = rng.randint(1, 3)
    var = rng.choice(VAR_NAMES)

    def solve(arr, k):
        l = 0; zeros = 0; best = 0
        for r in range(len(arr)):
            if arr[r] == 0: zeros += 1
            while zeros > k: 
                if arr[l] == 0: zeros -= 1
                l += 1
            best = max(best, r - l + 1)
        return best

    def make_tc():
        a = [rng.randint(0, 1) for _ in range(rng.randint(5, n))]
        kk = rng.randint(0, k)
        return {"input": {"array": a, "k": kk}, "output": solve(a, kk)}

    sample = [rng.randint(0, 1) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Longest Subarray of 1s After Flipping K Zeros",
        "problem_statement": (
            f"Given binary array `{var}` of length {n} and integer k={k}, "
            f"find the maximum length of a subarray with all 1s after flipping at most k 0s."
        ),
        "input_format": "Line 1: space-separated 0s and 1s. Line 2: k.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, sample))}\n{k}",
        "sample_output": str(solve(sample, k)),
        "test_cases": tcs,
    }


def _sw_count_anagram_occurrences(rng: random.Random) -> Dict:
    s_len = rng.randint(8, 14)
    p_len = rng.randint(2, 4)
    charset = "abcde"
    v1, v2 = rng.sample(STR_NAMES, 2)

    def solve(s, p):
        from collections import Counter
        if len(p) > len(s): return 0
        need = Counter(p); window = Counter(s[:len(p)])
        count = 1 if window == need else 0
        for i in range(len(p), len(s)):
            window[s[i]] += 1
            old = s[i - len(p)]
            window[old] -= 1
            if window[old] == 0: del window[old]
            if window == need: count += 1
        return count

    def make_tc():
        s = "".join(rng.choice(charset) for _ in range(rng.randint(6, s_len)))
        p = "".join(rng.choice(charset) for _ in range(rng.randint(2, min(p_len, len(s)))))
        return {"input": {"s": s, "p": p}, "output": solve(s, p)}

    s = "".join(rng.choice(charset) for _ in range(s_len))
    p = "".join(rng.choice(charset) for _ in range(p_len))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Count Anagram Occurrences in String",
        "problem_statement": (
            f"Given strings `{v1}` (length {s_len}) and `{v2}` (length {p_len}) over '{charset}', "
            f"count the number of anagrams of `{v2}` in `{v1}`."
        ),
        "input_format": "Line 1: s. Line 2: p.",
        "output_format": "A single integer.",
        "sample_input": f"{s}\n{p}",
        "sample_output": str(solve(s, p)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  BINARY SEARCH  ==================================
# ---------------------------------------------------------------------------

def _bs_find_minimum_rotated(rng: random.Random) -> Dict:
    n = rng.randint(5, 10)
    lo, hi = rng.randint(1, 5), rng.randint(30, 60)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        l, r = 0, len(arr) - 1
        while l < r:
            m = (l + r) // 2
            if arr[m] > arr[r]: l = m + 1
            else: r = m
        return arr[l]

    def make_tc():
        a = sorted(rng.sample(range(lo, hi), rng.randint(4, n)))
        pivot = rng.randint(0, len(a) - 1)
        a = a[pivot:] + a[:pivot]
        return {"input": a, "output": solve(a)}

    a = sorted(rng.sample(range(lo, hi), n))
    pivot = rng.randint(0, n - 1); a = a[pivot:] + a[:pivot]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Find Minimum in Rotated Sorted Array",
        "problem_statement": (
            f"Given a rotated sorted array `{var}` of {n} distinct integers (range [{lo}, {hi}]), "
            f"find the minimum element."
        ),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, a)),
        "sample_output": str(solve(a)),
        "test_cases": tcs,
    }


def _bs_capacity_to_ship(rng: random.Random) -> Dict:
    n = rng.randint(5, 8)
    max_w = rng.randint(5, 12)
    days = rng.randint(2, min(4, n))

    def solve(weights, days):
        def can_ship(cap):
            d = 1; cur = 0
            for w in weights:
                if cur + w > cap: d += 1; cur = 0
                cur += w
            return d <= days
        lo, hi = max(weights), sum(weights)
        while lo < hi:
            mid = (lo + hi) // 2
            if can_ship(mid): hi = mid
            else: lo = mid + 1
        return lo

    def make_tc():
        ws = [rng.randint(1, max_w) for _ in range(rng.randint(4, n))]
        d = rng.randint(1, min(days, len(ws)))
        return {"input": {"weights": ws, "days": d}, "output": solve(ws, d)}

    weights = [rng.randint(1, max_w) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Capacity to Ship Packages Within D Days",
        "problem_statement": (
            f"Given {n} packages with weights (max {max_w}) and {days} days, "
            f"find the minimum ship capacity to ship all packages in order within {days} days."
        ),
        "input_format": "Line 1: space-separated weights. Line 2: days.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, weights))}\n{days}",
        "sample_output": str(solve(weights, days)),
        "test_cases": tcs,
    }


def _bs_koko_eating_bananas(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    max_pile = rng.randint(10, 20)
    h = rng.randint(n, n * 3)

    def solve(piles, h):
        def can_eat(speed):
            return sum(math.ceil(p / speed) for p in piles) <= h
        lo, hi = 1, max(piles)
        while lo < hi:
            mid = (lo + hi) // 2
            if can_eat(mid): hi = mid
            else: lo = mid + 1
        return lo

    def make_tc():
        piles = [rng.randint(1, max_pile) for _ in range(rng.randint(3, n))]
        hh = rng.randint(len(piles), len(piles) * 3)
        return {"input": {"piles": piles, "h": hh}, "output": solve(piles, hh)}

    piles = [rng.randint(1, max_pile) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Koko Eating Bananas",
        "problem_statement": (
            f"Koko has {n} piles of bananas (max pile size {max_pile}) and h={h} hours. "
            f"Find the minimum eating speed k (bananas/hour) to finish all piles within h hours."
        ),
        "input_format": "Line 1: space-separated pile sizes. Line 2: h.",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, piles))}\n{h}",
        "sample_output": str(solve(piles, h)),
        "test_cases": tcs,
    }


def _bs_median_two_sorted(rng: random.Random) -> Dict:
    n1 = rng.randint(2, 5); n2 = rng.randint(2, 5)
    lo, hi = rng.randint(1, 5), rng.randint(20, 40)

    def solve(a, b):
        merged = sorted(a + b); n = len(merged)
        if n % 2 == 1: return float(merged[n // 2])
        return (merged[n // 2 - 1] + merged[n // 2]) / 2.0

    def make_tc():
        a = sorted(rng.randint(lo, hi) for _ in range(rng.randint(2, n1)))
        b = sorted(rng.randint(lo, hi) for _ in range(rng.randint(2, n2)))
        return {"input": {"a": a, "b": b}, "output": solve(a, b)}

    a = sorted(rng.randint(lo, hi) for _ in range(n1))
    b = sorted(rng.randint(lo, hi) for _ in range(n2))
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Median of Two Sorted Arrays",
        "problem_statement": (
            f"Given two sorted arrays of lengths {n1} and {n2} (range [{lo}, {hi}]), "
            f"find the median of the merged sorted array."
        ),
        "input_format": "Line 1: sorted array a. Line 2: sorted array b.",
        "output_format": "The median as a float.",
        "sample_input": f"{' '.join(map(str, a))}\n{' '.join(map(str, b))}",
        "sample_output": str(solve(a, b)),
        "test_cases": tcs,
    }


def _bs_allocate_books(rng: random.Random) -> Dict:
    n = rng.randint(4, 7)
    m = rng.randint(2, min(3, n))
    max_pages = rng.randint(10, 20)

    def solve(pages, m):
        def feasible(max_pages_allowed):
            students = 1; cur = 0
            for p in pages:
                if cur + p > max_pages_allowed: students += 1; cur = 0
                cur += p
            return students <= m
        lo, hi = max(pages), sum(pages)
        while lo < hi:
            mid = (lo + hi) // 2
            if feasible(mid): hi = mid
            else: lo = mid + 1
        return lo

    def make_tc():
        ps = [rng.randint(1, max_pages) for _ in range(rng.randint(m, n))]
        mm = rng.randint(1, min(m, len(ps)))
        return {"input": {"pages": ps, "m": mm}, "output": solve(ps, mm)}

    pages = [rng.randint(1, max_pages) for _ in range(n)]
    tcs = [make_tc() for _ in range(6)]
    return {
        "title": "Allocate Books (Binary Search on Answer)",
        "problem_statement": (
            f"Given {n} books with page counts (max {max_pages}) and {m} students, "
            f"allocate books contiguously to minimize the maximum pages assigned to any student."
        ),
        "input_format": "Line 1: space-separated page counts. Line 2: m (students).",
        "output_format": "A single integer.",
        "sample_input": f"{' '.join(map(str, pages))}\n{m}",
        "sample_output": str(solve(pages, m)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  MATH  ===========================================
# ---------------------------------------------------------------------------

def _math_sieve_primes(rng: random.Random) -> Dict:
    n = rng.randint(20, 150)

    def solve(n):
        sieve = [True] * (n + 1); sieve[0] = sieve[1] = False
        for i in range(2, int(n**0.5) + 1):
            if sieve[i]:
                for j in range(i*i, n+1, i): sieve[j] = False
        return [i for i in range(2, n+1) if sieve[i]]

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(10, 200)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})
    return {
        "title": "Sieve of Eratosthenes",
        "problem_statement": rng.choice([
            f"Given n={n}, find all prime numbers up to and including n using the Sieve of Eratosthenes.",
            f"List all primes ≤ {n} using the Sieve of Eratosthenes algorithm.",
            f"Using the sieve method, output every prime number from 2 to {n}.",
            f"Apply the Sieve of Eratosthenes to find all primes in the range [2, {n}].",
            f"Find and print all prime numbers up to {n} using an efficient sieve.",
        ]),
        "input_format": "A single integer n.",
        "output_format": "Space-separated prime numbers.",
        "sample_input": str(n),
        "sample_output": " ".join(map(str, solve(n))),
        "test_cases": tcs,
    }


def _math_prime_factors(rng: random.Random) -> Dict:
    n = rng.randint(20, 500)

    def solve(n):
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0: factors.append(d); n //= d
            d += 1
        if n > 1: factors.append(n)
        return factors

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(2, 500)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})
    return {
        "title": "Prime Factorization",
        "problem_statement": rng.choice([
            f"Given n={n}, find the prime factorization (list all prime factors including duplicates, sorted).",
            f"Decompose {n} into its prime factors. List all factors in ascending order, including repeats.",
            f"Find the prime factorization of {n}. Output all prime factors sorted in non-decreasing order.",
            f"Return the sorted list of prime factors of {n} (with repetition).",
            f"Break down {n} into prime factors using trial division. Output them space-separated.",
        ]),
        "input_format": "A single integer n.",
        "output_format": "Space-separated prime factors.",
        "sample_input": str(n),
        "sample_output": " ".join(map(str, solve(n))),
        "test_cases": tcs,
    }


def _math_pascal_triangle(rng: random.Random) -> Dict:
    n = rng.randint(4, 10)

    def solve(n):
        triangle = [[1]]
        for i in range(1, n):
            row = [1]
            for j in range(1, i): row.append(triangle[i-1][j-1] + triangle[i-1][j])
            row.append(1); triangle.append(row)
        return triangle

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(2, 12)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})
    ps_variants = [
        f"Given n={n}, generate the first n rows of Pascal's Triangle.",
        f"Build Pascal's Triangle up to row {n}. Each row starts and ends with 1; inner values are sums of the two above.",
        f"Output the first {n} rows of Pascal's Triangle, one row per line.",
        f"Construct Pascal's Triangle for n={n} rows using the recurrence relation.",
        f"Generate and print {n} rows of Pascal's Triangle (row 1 is just [1]).",
    ]
    return {
        "title": "Pascal's Triangle",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer n.",
        "output_format": "Each row on a new line, space-separated.",
        "sample_input": str(n),
        "sample_output": "\n".join(" ".join(map(str, row)) for row in solve(n)),
        "test_cases": tcs,
    }


def _math_count_digits(rng: random.Random) -> Dict:
    n = rng.randint(100, 9999)

    def solve(n):
        count = 0
        for d in str(n):
            if d != '0' and n % int(d) == 0: count += 1
        return count

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(10, 9999)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})

    ps_variants = [
        f"Given n={n}, count how many of its digits evenly divide n (ignore digit 0).",
        f"For the number {n}, find how many of its non-zero digits are divisors of {n}.",
        f"Count the digits of {n} that divide it exactly (skip zeros).",
        f"Given {n}, return the number of its digits d (d≠0) such that {n} % d == 0.",
        f"How many non-zero digits of {n} are factors of {n}? Return the count.",
    ]
    return {
        "title": "Count Digits That Divide the Number",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _math_modular_exponentiation(rng: random.Random) -> Dict:
    base = rng.randint(2, 15)
    exp = rng.randint(10, 50)
    mod = rng.choice([1000000007, 998244353, 1009, 10007, 100003])

    def solve(b, e, m):
        result = 1; b %= m
        while e > 0:
            if e % 2 == 1: result = result * b % m
            b = b * b % m; e //= 2
        return result

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        b = rng.randint(2, 15); e = rng.randint(5, 50)
        m = rng.choice([1000000007, 998244353, 1009, 10007, 100003])
        key = (b, e, m)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": {"base": b, "exp": e, "mod": m}, "output": solve(b, e, m)})

    ps_variants = [
        f"Compute ({base}^{exp}) mod {mod} using fast modular exponentiation.",
        f"Using the fast power algorithm, calculate {base}^{exp} modulo {mod}.",
        f"Find ({base} raised to the power {exp}) mod {mod} efficiently.",
        f"Apply modular exponentiation to compute {base}^{exp} % {mod}.",
        f"Given base={base}, exp={exp}, mod={mod}, return (base^exp) % mod using binary exponentiation.",
    ]
    return {
        "title": "Modular Exponentiation",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Line 1: base. Line 2: exp. Line 3: mod.",
        "output_format": "A single integer.",
        "sample_input": f"{base}\n{exp}\n{mod}",
        "sample_output": str(solve(base, exp, mod)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  BIT MANIPULATION  ===============================
# ---------------------------------------------------------------------------

def _bit_single_number(rng: random.Random) -> Dict:
    n = rng.randint(3, 8)
    lo, hi = rng.randint(1, 10), rng.randint(20, 50)
    var = rng.choice(VAR_NAMES)

    def solve(arr):
        result = 0
        for v in arr: result ^= v
        return result

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        unique = rng.randint(lo, hi)
        pairs = [rng.randint(lo, hi) for _ in range(rng.randint(2, n))]
        arr = pairs + pairs + [unique]
        rng.shuffle(arr)
        key = tuple(sorted(arr))
        if key not in seen:
            seen.add(key)
            tcs.append({"input": arr, "output": solve(arr)})

    unique = rng.randint(lo, hi)
    pairs = [rng.randint(lo, hi) for _ in range(n)]
    sample = pairs + pairs + [unique]
    rng.shuffle(sample)
    ps_variants = [
        f"Given array `{var}` where every element appears twice except one, find the element that appears only once. Use XOR.",
        f"In array `{var}`, all numbers appear exactly twice except one. Find the unique number using bitwise XOR.",
        f"Every element in `{var}` occurs twice except for one. Return that single element using O(1) space and XOR.",
        f"Find the non-duplicate element in `{var}` where all others appear exactly twice. Use XOR for O(n) time, O(1) space.",
        f"Given `{var}` where one number appears once and all others appear twice, return the lone number using XOR.",
    ]
    return {
        "title": "Single Number (XOR)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated integers.",
        "output_format": "A single integer.",
        "sample_input": " ".join(map(str, sample)),
        "sample_output": str(solve(sample)),
        "test_cases": tcs,
    }


def _bit_count_set_bits(rng: random.Random) -> Dict:
    n = rng.randint(5, 500)

    def solve(n):
        return bin(n).count('1')

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(0, 1023)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})
    ps_variants = [
        f"Given a non-negative integer n={n}, count the number of 1-bits in its binary representation.",
        f"Count the set bits (1s) in the binary representation of {n}. This is also called the Hamming weight.",
        f"How many 1-bits does {n} have in binary? Return the popcount.",
        f"Given n={n}, return the number of 1s in its binary form (Hamming weight).",
        f"Compute the bit count (number of set bits) of the integer {n}.",
    ]
    return {
        "title": "Count Set Bits (Hamming Weight)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _bit_power_of_two(rng: random.Random) -> Dict:
    n = rng.randint(1, 1000)

    def solve(n):
        return n > 0 and (n & (n - 1)) == 0

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(0, 1024)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})
    ps_variants = [
        f"Given integer n={n}, determine if it is a power of two using bit manipulation.",
        f"Using bitwise operations, check whether {n} is a power of 2.",
        f"Is {n} a power of two? Use the bit trick (n & (n-1)) to decide.",
        f"Determine if {n} is an exact power of 2 using a single bitwise operation.",
        f"Given n={n}, return true if n is a power of two, false otherwise. Use bit manipulation.",
    ]
    return {
        "title": "Power of Two",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer.",
        "output_format": "true or false.",
        "sample_input": str(n),
        "sample_output": str(solve(n)).lower(),
        "test_cases": tcs,
    }


def _bit_reverse_bits(rng: random.Random) -> Dict:
    n = rng.randint(0, 2**16)

    def solve(n, bits=16):
        result = 0
        for _ in range(bits):
            result = (result << 1) | (n & 1)
            n >>= 1
        return result

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(0, 2**16)
        if nn not in seen:
            seen.add(nn)
            tcs.append({"input": nn, "output": solve(nn)})

    ps_variants = [
        f"Given a 16-bit unsigned integer n={n}, reverse its bits and return the result.",
        f"Reverse all 16 bits of the integer {n} and return the new value.",
        f"Given n={n}, flip the bit order of its 16-bit binary representation.",
        f"Return the integer formed by reversing the 16 bits of {n}.",
        f"Perform a 16-bit bit reversal on n={n} and output the resulting integer.",
    ]
    return {
        "title": "Reverse Bits (16-bit)",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "A single integer.",
        "output_format": "A single integer.",
        "sample_input": str(n),
        "sample_output": str(solve(n)),
        "test_cases": tcs,
    }


def _bit_subsets_bitmask(rng: random.Random) -> Dict:
    n = rng.randint(3, 5)
    start = rng.randint(1, 10)
    nums = list(range(start, start + n))

    def solve(nums):
        result = []
        for mask in range(1 << len(nums)):
            subset = [nums[i] for i in range(len(nums)) if mask & (1 << i)]
            result.append(subset)
        return sorted(result, key=lambda x: (len(x), x))

    seen = set()
    tcs = []
    attempts = 0
    while len(tcs) < 8 and attempts < 80:
        attempts += 1
        nn = rng.randint(2, n)
        s = rng.randint(1, 15)
        ns = list(range(s, s + nn))
        key = tuple(ns)
        if key not in seen:
            seen.add(key)
            tcs.append({"input": ns, "output": solve(ns)})
    ps_variants = [
        f"Given {n} distinct integers {nums}, generate all subsets using bitmask enumeration.",
        f"Using bitmask iteration, enumerate all 2^{n} subsets of {nums}.",
        f"Generate the power set of {nums} ({n} elements) by iterating over all bitmasks from 0 to 2^{n}-1.",
        f"List every subset of {nums} using bitmask technique. Sort by length then value.",
        f"For each bitmask from 0 to {2**n - 1}, extract the corresponding subset of {nums}.",
    ]
    return {
        "title": "All Subsets via Bitmask",
        "problem_statement": rng.choice(ps_variants),
        "input_format": "Space-separated distinct integers.",
        "output_format": "Each subset on a new line (empty line for empty set), sorted by length then value.",
        "sample_input": " ".join(map(str, nums)),
        "sample_output": "\n".join(" ".join(map(str, s)) for s in solve(nums)),
        "test_cases": tcs,
    }


# ---------------------------------------------------------------------------
# ========================  TOPIC REGISTRY  =================================
# ---------------------------------------------------------------------------

TOPIC_TEMPLATES: Dict[str, List] = {
    "arrays": [
        _array_max_subarray,
        _array_two_sum,
        _array_rotate,
        _array_product_except_self,
        _array_missing_number,
    ],
    "strings": [
        _string_longest_palindrome,
        _string_anagram_check,
        _string_reverse_words,
        _string_longest_common_prefix,
        _string_count_vowels,
    ],
    "graphs": [
        _graph_bfs_shortest_path,
        _graph_number_of_islands,
        _graph_detect_cycle,
        _graph_topological_sort,
        _graph_dijkstra,
    ],
    "dynamic programming": [
        _dp_knapsack,
        _dp_longest_common_subsequence,
        _dp_coin_change,
        _dp_longest_increasing_subsequence,
        _dp_edit_distance,
    ],
    "trees": [
        _tree_inorder,
        _tree_max_depth,
        _tree_level_order,
        _tree_diameter,
        _tree_lowest_common_ancestor,
    ],
    "stacks": [
        _stack_valid_parentheses,
        _stack_next_greater_element,
        _stack_min_stack,
        _stack_evaluate_rpn,
        _stack_largest_rectangle_histogram,
    ],
    "queues": [
        _queue_sliding_window_max,
        _queue_first_non_repeating,
        _queue_circular_queue,
        _queue_task_scheduler,
        _queue_bfs_level_order,
    ],
    "greedy": [
        _greedy_activity_selection,
        _greedy_fractional_knapsack,
        _greedy_jump_game,
        _greedy_minimum_platforms,
        _greedy_gas_station,
    ],
    "hashing": [
        _hashing_group_anagrams,
        _hashing_subarray_sum_k,
        _hashing_longest_consecutive,
        _hashing_four_sum_count,
        _hashing_top_k_frequent,
    ],
    "sorting": [
        _sorting_merge_sort,
        _sorting_kth_largest,
        _sorting_count_inversions,
        _sorting_sort_colors,
        _sorting_merge_intervals,
    ],
    "searching": [
        _searching_binary_search,
        _searching_search_rotated,
        _searching_find_peak,
        _searching_first_last_position,
        _searching_sqrt_integer,
    ],
    "recursion": [
        _recursion_fibonacci,
        _recursion_power,
        _recursion_tower_of_hanoi,
        _recursion_flatten_nested,
        _recursion_gcd,
    ],
    "backtracking": [
        _backtracking_permutations,
        _backtracking_subsets,
        _backtracking_n_queens_count,
        _backtracking_combination_sum,
        _backtracking_word_search,
    ],
    "linked-lists": [
        _ll_reverse,
        _ll_detect_cycle,
        _ll_merge_sorted,
        _ll_nth_from_end,
        _ll_palindrome,
    ],
    "two pointers": [
        _two_ptr_three_sum,
        _two_ptr_container_water,
        _two_ptr_remove_duplicates,
        _two_ptr_sort_squares,
        _two_ptr_trapping_rain,
    ],
    "sliding window": [
        _sw_longest_substring_no_repeat,
        _sw_max_sum_subarray_k,
        _sw_minimum_window_substring,
        _sw_longest_ones_after_flip,
        _sw_count_anagram_occurrences,
    ],
    "binary search": [
        _bs_find_minimum_rotated,
        _bs_capacity_to_ship,
        _bs_koko_eating_bananas,
        _bs_median_two_sorted,
        _bs_allocate_books,
    ],
    "math": [
        _math_sieve_primes,
        _math_prime_factors,
        _math_pascal_triangle,
        _math_count_digits,
        _math_modular_exponentiation,
    ],
    "bit manipulation": [
        _bit_single_number,
        _bit_count_set_bits,
        _bit_power_of_two,
        _bit_reverse_bits,
        _bit_subsets_bitmask,
    ],
}

# Normalise aliases so callers can use various spellings
_ALIASES: Dict[str, str] = {
    "dp": "dynamic programming",
    "dynamic_programming": "dynamic programming",
    "linked_lists": "linked-lists",
    "linkedlists": "linked-lists",
    "linked lists": "linked-lists",
    "two_pointers": "two pointers",
    "twopointers": "two pointers",
    "sliding_window": "sliding window",
    "slidingwindow": "sliding window",
    "binary_search": "binary search",
    "binarysearch": "binary search",
    "bit_manipulation": "bit manipulation",
    "bitmanipulation": "bit manipulation",
    "graph": "graphs",
    "tree": "trees",
    "stack": "stacks",
    "queue": "queues",
    "array": "arrays",
    "string": "strings",
    "hash": "hashing",
    "sort": "sorting",
    "search": "searching",
    # UI topics mapped to closest available generators
    "heaps": "sorting",
    "heap": "sorting",
    "priority queue": "sorting",
    "divide and conquer": "recursion",
    "divide_and_conquer": "recursion",
    "trie": "strings",
    "segment tree": "binary search",
    "segment_tree": "binary search",
    "fenwick tree": "binary search",
    "number theory": "math",
    "geometry": "math",
    "matrix": "arrays",
    "2d array": "arrays",
}

DIFFICULTY_LEVELS = {"easy", "medium", "hard"}

# ---------------------------------------------------------------------------
# ========================  TITLE TRACKING HELPERS  =========================
# ---------------------------------------------------------------------------

# Module-level set that remembers every title handed out this process lifetime.
# Keeps the server from repeating titles across different users/sessions.
_used_titles_set: set = set()
_used_titles_order: list = []   # insertion-order list for LRU eviction
_MAX_TRACKED_TITLES = 500       # evict oldest when we exceed this


def _record_title(title: str) -> None:
    """Add a title to the module-level tracker."""
    key = title.lower()
    if key not in _used_titles_set:
        _used_titles_set.add(key)
        _used_titles_order.append(key)
        if len(_used_titles_order) > _MAX_TRACKED_TITLES:
            evicted = _used_titles_order.pop(0)
            _used_titles_set.discard(evicted)


# Build a flat lookup from base_title -> list[variation] from _vary_title's dict.
# We extract it once at module load so generate_dynamic can use it directly.
def _build_title_variations() -> Dict[str, List[str]]:
    """Extract the variations dict from _vary_title by calling it with a sentinel."""
    # Re-declare the same dict here so generate_dynamic can access it without
    # calling _vary_title (which also does random selection).
    return {
        "Maximum Subarray Sum": ["Maximum Subarray Sum","Find the Largest Contiguous Subarray Sum","Kadane's Algorithm: Max Subarray","Peak Contiguous Subarray Value","Greatest Sum Among All Subarrays","Optimal Subarray Sum Problem","Highest Sum Contiguous Segment","Max Sum Subarray Finder","Subarray with Maximum Total","Best Subarray Sum Challenge","Largest Contiguous Sum","Max Contiguous Subarray","Kadane's Max Sum","Optimal Subarray Value","Top Subarray Sum"],
        "Two Sum": ["Two Sum","Find Pair with Given Sum","Locate Two Indices That Add to Target","Pair Sum Index Finder","Target Sum Pair Problem","Two Numbers Summing to K","Index Pair for Target Total","Sum Pair Lookup","Find Two Elements Equal to Target","Dual Index Sum Problem","Pair That Sums to Target","Two-Index Sum Finder","Target Pair Locator","Sum of Two Indices","Addend Pair Problem"],
        "Rotate Array": ["Rotate Array","Circular Shift of Array Elements","Right Rotation by K Steps","Array Cyclic Rotation","Shift Array K Positions Right","Wrap-Around Array Rotation","K-Step Array Shift","Rotate Elements Rightward","Array Right Rotation Problem","Cyclic Element Displacement","Rightward Array Shift","K-Position Rotation","Circular Array Rotation","Array Wrap Rotation","Cyclic Right Shift"],
        "Product of Array Except Self": ["Product of Array Except Self","Array Product Without Current Element","Compute Product Excluding Index","Division-Free Product Array","Product Array Without Self","Prefix-Suffix Product Problem","Exclude-Self Multiplication Array","Product of All Other Elements","Array Product Puzzle","No-Division Product Computation","Self-Excluding Product","Prefix Suffix Multiply","Product Except Current","All-But-One Product","Exclusion Product Array"],
        "Find the Missing Number": ["Find the Missing Number","Locate the Absent Integer","Missing Element in Range","Identify the Gap in Sequence","Which Number Is Missing?","Absent Value in Array","Find the Omitted Integer","Detect Missing Element","Gap Finder in Integer Range","Missing Integer Detection","Absent Integer Finder","Range Gap Detector","Missing Value Problem","Find the Hole in Sequence","Integer Gap Finder"],
        "Valid Anagram": ["Valid Anagram","Check if Two Strings Are Anagrams","Anagram Verification Problem","Same Characters Different Order","Detect Anagram Pair","Character Frequency Match","Anagram or Not?","Rearrangement Check","Letter Permutation Equality","Anagram Detector","Permutation Equality Check","Character Count Match","Anagram Pair Validator","Letter Rearrangement Test","Frequency-Based Anagram Check"],
        "Longest Palindromic Substring": ["Longest Palindromic Substring","Find the Longest Palindrome in a String","Maximum Length Palindrome Segment","Palindrome Substring Finder","Longest Mirror Substring","Expand-Around-Center Palindrome","Biggest Palindromic Segment","Longest Symmetric Substring","Peak Palindrome in String","Palindrome Length Maximizer","Max Palindrome Segment","Longest Symmetric Segment","Palindrome Expansion Problem","Widest Palindrome Substring","Longest Mirrored Segment"],
        "Reverse Words in a String": ["Reverse Words in a String","Flip Word Order in Sentence","Invert Word Sequence","Backwards Word Arrangement","Reverse the Sentence Words","Word Order Reversal","Sentence Word Flip","Reverse Token Order","Inverted Word Sequence Problem","Mirror Word Arrangement","Flip Sentence Words","Reverse Word Order","Backward Word Sequence","Word Sequence Inversion","Sentence Reversal Problem"],
        "Longest Common Prefix": ["Longest Common Prefix","Find Shared Starting Substring","Common Prefix Among Strings","Longest Shared Prefix","Prefix Intersection of Strings","Maximum Common Start","Shared Beginning of All Strings","Common String Prefix Finder","Longest Matching Prefix","Prefix Overlap Problem","Shared Prefix Finder","Maximum Prefix Match","Common Start Substring","Prefix Intersection Problem","Longest Shared Start"],
        "Count Vowels in String": ["Count Vowels in String","Vowel Frequency Counter","How Many Vowels?","Count a-e-i-o-u Occurrences","Vowel Tally in Text","String Vowel Counter","Enumerate Vowels in Input","Vowel Detection Problem","Count Vocal Characters","Vowel Occurrence Finder","Vowel Count Problem","Count Vowel Characters","Vowel Frequency Problem","Tally Vowels in String","Vowel Enumeration Task"],
        "BFS Shortest Path in Unweighted Graph": ["BFS Shortest Path in Unweighted Graph","Minimum Hops Between Two Nodes","Shortest Route via BFS","Fewest Edges from Source to Destination","Unweighted Graph Shortest Distance","BFS Distance Between Nodes","Minimum Edge Path Problem","Shortest Unweighted Path Finder","Graph BFS Distance Query","Least Edges Path Problem","Minimum Edge Count Path","BFS Hop Count","Fewest Hops Problem","Unweighted Shortest Path","BFS Minimum Distance"],
        "Number of Islands": ["Number of Islands","Count Connected Land Regions","Island Counter in Binary Grid","How Many Islands in the Grid?","Connected Component Count in Grid","Land Mass Counter","Grid Island Detection","Count Isolated Land Clusters","Binary Grid Island Problem","Flood Fill Island Counter","Grid Land Cluster Count","Connected Land Counter","Island Detection Problem","Land Region Counter","Grid Component Islands"],
        "Detect Cycle in Undirected Graph": ["Detect Cycle in Undirected Graph","Does This Graph Have a Loop?","Cycle Detection in Graph","Find Circular Path in Graph","Graph Cycle Checker","Undirected Graph Loop Finder","Is There a Cycle?","Back Edge Detection Problem","Graph Circularity Test","Cycle Existence in Undirected Graph","Loop Detection in Graph","Circular Path Finder","Graph Back-Edge Check","Undirected Cycle Detector","Cycle Presence Problem"],
        "Topological Sort (Kahn's Algorithm)": ["Topological Sort (Kahn's Algorithm)","DAG Node Ordering Problem","Dependency Resolution Order","Linear Ordering of DAG Nodes","Topological Ordering via BFS","Kahn's Topological Sort","Task Dependency Sequencing","DAG Traversal Order","Directed Acyclic Graph Ordering","Prerequisite-Based Node Ordering","DAG Linear Order","Dependency-Based Ordering","Kahn BFS Sort","Task Sequence Problem","DAG Topological Order"],
        "Dijkstra's Shortest Path": ["Dijkstra's Shortest Path","Minimum Cost Path in Weighted Graph","Shortest Weighted Distance from Source","Greedy Shortest Path Algorithm","Weighted Graph Distance Problem","Optimal Path Cost Finder","Single Source Shortest Path","Minimum Weight Path Problem","Dijkstra Distance Query","Weighted Shortest Route Finder","Minimum Cost Route","Weighted Distance Problem","Dijkstra's Algorithm","Optimal Weighted Path","Least Cost Path"],
        "0/1 Knapsack Problem": ["0/1 Knapsack Problem","Maximum Value Within Weight Limit","Item Selection for Max Profit","Weight-Constrained Value Maximization","Binary Knapsack Challenge","Optimal Item Packing Problem","Capacity-Limited Value Maximizer","Knapsack DP Problem","Best Item Combination Under Capacity","Weight Budget Optimization","Binary Item Selection","Max Value Knapsack","Weight-Limited Profit","Capacity Knapsack DP","Optimal Packing Problem"],
        "Longest Common Subsequence": ["Longest Common Subsequence","LCS of Two Strings","Maximum Shared Subsequence Length","Common Subsequence Finder","Longest Matching Subsequence","Shared Character Sequence Problem","LCS DP Problem","Subsequence Overlap Maximizer","Longest Mutual Subsequence","Common Sequence Length Problem","Max Common Subsequence","LCS Length Problem","Shared Subsequence Finder","Longest Shared Sequence","Common Subsequence DP"],
        "Coin Change — Minimum Coins": ["Coin Change — Minimum Coins","Fewest Coins to Make Amount","Minimum Denomination Count","Optimal Coin Selection Problem","Least Coins for Target Sum","Coin Combination Minimizer","Minimum Coins Required","Change-Making DP Problem","Smallest Coin Count for Amount","Coin Denomination Optimizer","Minimum Coin Count","Fewest Denominations","Coin Change DP","Least Denomination Problem","Optimal Change Problem"],
        "Longest Increasing Subsequence": ["Longest Increasing Subsequence","LIS of an Array","Maximum Strictly Increasing Subsequence","Longest Growing Subsequence","Increasing Subsequence Length Problem","LIS DP Challenge","Longest Ascending Subsequence","Maximum Monotone Subsequence","Strictly Increasing Sequence Finder","Longest Upward Subsequence","Max Increasing Subsequence","LIS Length Finder","Ascending Subsequence Problem","Longest Monotone Subsequence","Strictly Growing Sequence"],
        "Edit Distance (Levenshtein)": ["Edit Distance (Levenshtein)","Minimum String Transformation Cost","Fewest Edits to Convert Strings","String Edit Distance Problem","Levenshtein Distance Computation","Minimum Operations to Match Strings","String Similarity via Edit Distance","Optimal String Conversion Cost","Character Edit Minimizer","Minimum Insert-Delete-Replace Count","String Transformation Distance","Levenshtein Edit Count","Min Edit Operations","String Conversion Cost","Edit Operation Minimizer"],
        "BST Inorder Traversal": ["BST Inorder Traversal","Sorted Output from BST","In-Order BST Walk","Left-Root-Right BST Traversal","BST Ascending Order Output","Binary Search Tree Inorder","Sorted BST Node Sequence","Inorder Walk of Binary Tree","BST Traversal in Sorted Order","Ascending BST Node Listing","BST Sorted Walk","Inorder Tree Output","Ascending Tree Traversal","BST Left-Root-Right","Sorted Binary Tree Walk"],
        "Maximum Depth of Binary Tree": ["Maximum Depth of Binary Tree","Height of a Binary Tree","Deepest Level in BST","Longest Root-to-Leaf Path","Tree Height Computation","Maximum Tree Depth Finder","BST Depth Problem","Tallest Branch in Binary Tree","Root-to-Leaf Maximum Distance","Binary Tree Height Problem","Tree Max Depth","Deepest Tree Level","Binary Tree Depth","Max Root-to-Leaf Length","Tree Height Finder"],
        "Binary Tree Level Order Traversal": ["Binary Tree Level Order Traversal","BFS Traversal of Binary Tree","Layer-by-Layer Tree Output","Breadth-First Tree Walk","Level-Wise BST Traversal","Tree Level Grouping Problem","Horizontal Tree Traversal","BST BFS Level Output","Row-by-Row Tree Traversal","Level Order BST Walk","Tree BFS Traversal","Level-by-Level Tree Walk","Breadth Tree Traversal","Tree Row Output","Level Order Tree Walk"],
        "Diameter of Binary Tree": ["Diameter of Binary Tree","Longest Path in Binary Tree","Maximum Node-to-Node Distance","Tree Diameter Computation","Widest Path in BST","Longest Branch-to-Branch Path","Binary Tree Diameter Problem","Maximum Distance Between Leaves","Tree Width via Diameter","Farthest Nodes in Binary Tree","Max Tree Path Length","Tree Diameter Finder","Longest Tree Path","Node Distance Maximizer","Binary Tree Width"],
        "Lowest Common Ancestor of BST": ["Lowest Common Ancestor of BST","LCA in Binary Search Tree","Deepest Common Ancestor","Shared Ancestor Finder","Nearest Common Parent in BST","LCA Problem in BST","Common Ancestor Detection","Deepest Shared Node in BST","BST Ancestor Query","Lowest Shared Parent Problem","LCA BST Problem","Common BST Ancestor","Nearest Shared Ancestor","BST LCA Finder","Deepest Common Parent"],
        "Valid Parentheses": ["Valid Parentheses","Balanced Bracket Checker","Is the Bracket String Valid?","Matching Parentheses Problem","Bracket Balance Verification","Parenthesis Validity Check","Nested Bracket Validator","Bracket Pair Matching","Well-Formed Bracket Sequence","Bracket Correctness Problem","Balanced Brackets Test","Parenthesis Balance Check","Bracket Validity Problem","Nested Parenthesis Check","Bracket Matching Problem"],
        "Next Greater Element": ["Next Greater Element","First Larger Value to the Right","Right Neighbor Greater Than Self","Next Bigger Number Finder","Monotonic Stack Greater Element","Rightward Greater Value Problem","Stack-Based Next Greater","Find Next Larger in Array","Greater Element to the Right","Next Dominant Element Problem","Next Larger Element","Right Greater Value","Monotonic Stack Problem","Next Bigger Element","Rightward Dominant Value"],
        "Min Stack": ["Min Stack","Stack with O(1) Minimum Query","Constant-Time Minimum Stack","Stack Supporting getMin in O(1)","Minimum-Tracking Stack","Stack with Minimum Access","O(1) Min Stack Design","Stack Minimum Retrieval Problem","Efficient Minimum Stack","Stack with Instant Min Lookup","Minimum Stack Design","O(1) Min Query Stack","Stack Min Tracker","Constant Min Stack","Instant Minimum Stack"],
        "Evaluate Reverse Polish Notation": ["Evaluate Reverse Polish Notation","RPN Expression Evaluator","Postfix Expression Calculator","Stack-Based RPN Evaluation","Compute Postfix Arithmetic","Reverse Polish Calculator","Postfix Notation Problem","RPN Stack Computation","Evaluate Postfix Expression","Arithmetic RPN Solver","Postfix Arithmetic Evaluator","RPN Calculator","Stack Postfix Solver","Reverse Polish Evaluator","Postfix Expression Solver"],
        "Largest Rectangle in Histogram": ["Largest Rectangle in Histogram","Maximum Area Rectangle in Bar Chart","Biggest Rectangle Under Histogram","Histogram Max Area Problem","Largest Bar Chart Rectangle","Maximum Histogram Rectangle","Stack-Based Histogram Area","Peak Rectangle in Bar Graph","Optimal Rectangle in Histogram","Max Area Under Histogram Bars","Max Histogram Rectangle","Largest Bar Rectangle","Histogram Area Maximizer","Peak Bar Chart Area","Optimal Histogram Rectangle"],
        "Sliding Window Maximum": ["Sliding Window Maximum","Maximum in Every K-Size Window","Rolling Window Peak Finder","Deque-Based Window Maximum","Max Value in Sliding Frame","Window Maximum Problem","K-Window Peak Tracker","Sliding Frame Maximum Query","Maximum Across Moving Window","Window-Based Max Finder","Rolling Max Window","K-Size Window Peak","Sliding Max Finder","Window Peak Tracker","Deque Window Maximum"],
        "First Non-Repeating Character": ["First Non-Repeating Character","First Unique Character in String","Earliest Non-Duplicate Letter","First Singleton Character","Leftmost Unique Character","First Character Appearing Once","Non-Repeating Letter Finder","Unique Character Position Problem","First Distinct Character","Earliest Unique Letter Problem","First Unique Letter","Leftmost Non-Duplicate","First Singleton Letter","Earliest Distinct Character","Non-Duplicate First Char"],
        "Circular Queue Simulation": ["Circular Queue Simulation","Ring Buffer Queue Operations","Bounded Circular Queue Problem","Fixed-Size Queue Simulator","Circular Buffer Implementation","Queue with Wrap-Around","Ring Queue Operation Simulator","Circular FIFO Queue Problem","Bounded Queue Simulation","Wrap-Around Queue Challenge","Ring Buffer Simulation","Circular FIFO Simulator","Bounded Ring Queue","Wrap Queue Problem","Circular Buffer Queue"],
        "Task Scheduler": ["Task Scheduler","CPU Task Scheduling with Cooldown","Minimum Intervals for Task Completion","Task Cooldown Scheduler","Greedy CPU Task Ordering","Minimum Time to Finish Tasks","Task Execution with Idle Slots","Cooldown-Based Task Planner","Optimal Task Scheduling Problem","CPU Scheduling Minimizer","CPU Cooldown Scheduler","Task Interval Minimizer","Greedy Task Planner","Minimum Task Time","Cooldown Task Problem"],
        "BFS Level-Order Distances": ["BFS Level-Order Distances","Graph BFS Distance from Source","Shortest Hop Count via BFS","BFS Distance Array Problem","Level-Wise Graph Distance","BFS All-Nodes Distance Query","Minimum Hops from Source Node","BFS Traversal Distance Problem","Graph Distance via Breadth-First","Source-to-All BFS Distance","BFS Distance Map","All-Nodes BFS Distance","Level BFS Distance","Source BFS Distances","BFS Hop Distance Array"],
        "Activity Selection Problem": ["Activity Selection Problem","Maximum Non-Overlapping Activities","Greedy Interval Scheduling","Most Activities Without Conflict","Optimal Activity Picker","Non-Conflicting Event Selector","Maximum Compatible Activities","Interval Scheduling Maximization","Greedy Activity Planner","Conflict-Free Activity Selection","Max Non-Overlapping Events","Greedy Event Selector","Activity Conflict Resolver","Interval Activity Picker","Non-Overlapping Activity Max"],
        "Fractional Knapsack": ["Fractional Knapsack","Greedy Fractional Item Selection","Maximum Value with Fractional Items","Partial Item Knapsack Problem","Greedy Weight-Value Optimizer","Fractional Item Packing","Continuous Knapsack Problem","Value-per-Weight Greedy Problem","Fractional Capacity Maximizer","Greedy Partial Knapsack","Partial Item Selection","Fractional Value Maximizer","Greedy Knapsack Problem","Continuous Item Packing","Value Density Knapsack"],
        "Jump Game": ["Jump Game","Can You Reach the Last Index?","Array Jump Reachability","Greedy Jump Feasibility","Last Index Reachability Problem","Jump Array Traversal","Can You Make It to the End?","Greedy Reachability Check","Array Hop Feasibility","Jump Length Reachability","Array Jump Problem","Reach Last Index","Greedy Hop Check","Jump Feasibility Problem","Array Reachability Game"],
        "Minimum Number of Platforms": ["Minimum Number of Platforms","Minimum Train Platforms Required","Peak Concurrent Train Count","Platform Allocation Problem","Minimum Stations for All Trains","Train Overlap Minimizer","Concurrent Train Platform Problem","Minimum Parallel Tracks Needed","Train Schedule Platform Count","Greedy Platform Minimization","Min Train Platforms","Peak Platform Count","Train Concurrency Problem","Platform Minimizer","Minimum Track Allocation"],
        # Recursion & Backtracking titles
        "Fibonacci Number": ["Fibonacci Number","Nth Fibonacci Value","Fibonacci Sequence Element","Compute Fibonacci(N)","Fibonacci Term Finder","Nth Term of Fibonacci","Fibonacci Index Lookup","Recursive Fibonacci","Fibonacci DP Problem","Fibonacci Sequence Query","Fib(N) Computation","Fibonacci Value at N","Nth Fibonacci Term","Fibonacci Lookup","Fibonacci Sequence N"],
        "Power Function (Fast Exponentiation)": ["Power Function (Fast Exponentiation)","Fast Power Computation","Recursive Exponentiation","Compute Base to the Power","Exponentiation by Squaring","Fast Pow Algorithm","Recursive Power Function","Binary Exponentiation","Pow(Base, Exp) Problem","Efficient Power Calculation","Fast Exponent Problem","Squaring Exponentiation","Recursive Pow","Binary Power Method","Exponent by Squaring"],
        "Tower of Hanoi — Move Count": ["Tower of Hanoi — Move Count","Hanoi Minimum Moves","Tower of Hanoi Steps","Disk Move Count Problem","Hanoi Recursion Problem","Minimum Hanoi Moves","Tower Disk Transfer Count","Hanoi Move Calculator","Recursive Hanoi Count","Disk Transfer Minimum","Hanoi Step Counter","Tower Move Minimizer","Hanoi Disk Count","Recursive Tower Problem","Minimum Disk Moves"],
        "Flatten Nested List": ["Flatten Nested List","Recursive List Flattening","Nested Array Flattener","Deep Flatten Problem","Recursive Flatten","Nested List to Flat Array","Flatten Deeply Nested","Recursive Depth Flatten","Nested Structure Flattener","Multi-Level List Flatten","Deep List Flatten","Nested Array Flatten","Recursive Unwrap List","Flatten Nested Structure","Multi-Depth Flatten"],
        "Greatest Common Divisor (Euclidean)": ["Greatest Common Divisor (Euclidean)","GCD via Euclidean Algorithm","Compute GCD Recursively","Euclidean GCD Problem","Find GCD of Two Numbers","Recursive GCD Computation","GCD Using Euclid","Greatest Common Factor","Euclidean Algorithm Problem","GCD Finder","Recursive GCD","Euclid's Algorithm","GCD Computation","Common Divisor Finder","Greatest Divisor Problem"],
        "All Permutations": ["All Permutations","Generate All Arrangements","List Every Permutation","Backtracking Permutations","All Orderings of Array","Permutation Generator","Every Possible Arrangement","Full Permutation Set","Enumerate Permutations","All Array Orderings","Complete Permutation List","Backtrack All Orders","Permutation Enumeration","All Distinct Orderings","Generate Permutations"],
        "All Subsets (Power Set)": ["All Subsets (Power Set)","Generate Power Set","All Possible Subsets","Backtracking Subsets","Every Subset of Array","Subset Generator","Power Set Enumeration","All Array Subsets","Enumerate All Subsets","Complete Subset List","Full Power Set","Backtrack Subsets","Subset Enumeration","All Combinations Subset","Generate All Subsets"],
        "N-Queens Count": ["N-Queens Count","Count N-Queens Solutions","N-Queens Placement Count","Backtracking N-Queens","How Many N-Queens Solutions?","N-Queens Problem Count","Queen Placement Counter","N-Queens Backtracking","Count Valid Queen Placements","N-Queens Solution Counter","N-Queens Solver Count","Queen Arrangement Count","N-Queens Distinct Solutions","Backtrack Queen Count","Valid N-Queens Count"],
        "Combination Sum": ["Combination Sum","Find Combinations Summing to Target","Backtracking Combination Sum","All Combinations for Target","Unlimited Use Combination Sum","Combination Target Finder","Sum Combination Problem","Backtrack Sum Combinations","Target Sum Combinations","Combination Sum Backtracking","Combinations to Target","Unlimited Combination Sum","Target Combination Finder","Sum Backtracking Problem","All Target Combinations"],
        "Word Search in Grid": ["Word Search in Grid","Find Word in Matrix","Grid Word Finder","Backtracking Word Search","Word Path in Grid","Matrix Word Search","DFS Word Search","Grid Character Path","Find Word via DFS","Word Existence in Grid","Grid DFS Word Finder","Matrix Path Word","Backtrack Word Grid","Word Grid Search","DFS Grid Word Path"],
    }

_TITLE_VARIATIONS: Dict[str, List[str]] = _build_title_variations()

# Reverse map: every variation (lowercased) -> list of ALL sibling variations (lowercased)
# Used to expand exclude_titles so that if any alias of a problem is excluded,
# all aliases are excluded too — preventing the same problem under a different name.
_VARIATION_TO_SIBLINGS: Dict[str, List[str]] = {}
for _base, _variants in _TITLE_VARIATIONS.items():
    _all_lower = [v.lower() for v in _variants]
    for _v in _all_lower:
        _VARIATION_TO_SIBLINGS[_v] = _all_lower


def _make_generic_title(base_title: str, rng: random.Random) -> str:
    """Generate a unique generic title for templates not in _TITLE_VARIATIONS."""
    prefixes = ["Solve", "Compute", "Find", "Determine", "Calculate",
                "Identify", "Detect", "Evaluate", "Analyze", "Process",
                "Implement", "Design", "Build", "Optimize", "Construct"]
    suffixes = [" Problem", " Challenge", " Task", " Query",
                " Puzzle", " Exercise", " Question", " Computation",
                " Algorithm", " Solution", " Approach", " Method"]
    token = hex(rng.randint(0x1000, 0xFFFF))[2:].upper()
    return f"{rng.choice(prefixes)}: {base_title}{rng.choice(suffixes)} [{token}]"


# ---------------------------------------------------------------------------
# ========================  PUBLIC API  =====================================
# ---------------------------------------------------------------------------

def generate_dynamic(topic: str, difficulty: str, exclude_titles: List[str] = None) -> Dict[str, Any]:
    """
    Generate a unique coding question for the given topic and difficulty.

    Parameters
    ----------
    topic : str
        One of the supported topics (case-insensitive). Aliases are accepted.
    difficulty : str
        One of 'easy', 'medium', 'hard' (case-insensitive).
    exclude_titles : list of str, optional
        Additional titles to avoid (e.g. recently used by this user/session).

    Returns
    -------
    dict with keys:
        title, problem_statement, input_format, output_format,
        sample_input, sample_output, test_cases (list of dicts),
        topic, difficulty, source
    """
    # Normalise inputs
    topic_key = topic.strip().lower()
    topic_key = _ALIASES.get(topic_key, topic_key)
    difficulty = difficulty.strip().lower()

    if topic_key not in TOPIC_TEMPLATES:
        matched_key = None
        for key in TOPIC_TEMPLATES:
            if key in topic_key or topic_key in key:
                matched_key = key
                break
        if matched_key:
            topic_key = matched_key
        else:
            import random as _random
            topic_key = _random.choice(list(TOPIC_TEMPLATES.keys()))

    if difficulty not in DIFFICULTY_LEVELS:
        difficulty = "medium"

    # Build the full exclusion set: module-level tracker + caller-supplied list
    # Also expand each excluded title to include ALL its known aliases, so the
    # same problem can't reappear under a different variation name.
    caller_exclude = set(t.lower() for t in (exclude_titles or []))
    expanded_exclude = set(caller_exclude)
    for title_lower in caller_exclude:
        siblings = _VARIATION_TO_SIBLINGS.get(title_lower, [])
        expanded_exclude.update(siblings)
        # Also check partial matches: if any sibling contains the excluded word
        # (handles AI-generated titles like "Determine Longest Palindromic Substring Challenge")
        for base, variants in _TITLE_VARIATIONS.items():
            base_lower = base.lower()
            # If the excluded title contains the base title as a substring, exclude all variants
            if base_lower in title_lower or title_lower in base_lower:
                expanded_exclude.update(v.lower() for v in variants)
    full_exclude = _used_titles_set | expanded_exclude

    # Random test case count per difficulty — different every call
    tc_ranges = {
        "easy":   (5, 8),    # 5–8 test cases for easy
        "medium": (7, 10),   # 7–10 test cases for medium
        "hard":   (9, 12),   # 9–12 test cases for hard
    }
    lo_tc, hi_tc = tc_ranges[difficulty]
    # Use a fresh seed so the count is independent of the question RNG
    desired_tc = random.Random(_seed()).randint(lo_tc, hi_tc)

    # Difficulty flavour appended to problem statement
    flavour = {
        "easy":   " [Easy] Simple implementation — single loop or basic conditionals. O(n) or O(n²) is acceptable.",
        "medium": " [Medium] Requires an algorithmic approach — use DP, binary search, two pointers, BFS/DFS, or greedy. Aim for O(n log n) or O(n).",
        "hard":   " [Hard] Advanced algorithm required — segment trees, bitmask DP, complex graph algorithms, or multi-dimensional DP. Optimal time complexity expected.",
    }

    # ── Pick a template this caller has not seen ────────────────────────────
    # A template is one underlying problem; its title is only a costume. The caller's
    # history stores the template's identity (base_title), so a template whose identity
    # is already excluded is skipped. When every template has been seen there is nothing
    # fresh left, and we say so (NoFreshQuestion) instead of serving the same problem
    # again under a new costume. Only the caller's own history counts here, never what
    # other callers were served, so one player cannot use up another player's questions.
    rng = _rng()

    # Use difficulty-aware templates when available
    try:
        from model.difficulty_templates import get_difficulty_templates
        diff_templates = get_difficulty_templates(topic_key, difficulty)
    except Exception:
        diff_templates = None

    if diff_templates:
        templates = list(diff_templates)
    else:
        templates = list(TOPIC_TEMPLATES[topic_key])
    rng.shuffle(templates)

    chosen_body = None
    varied_title = None
    chosen_template_fn = None

    for template_fn in templates:
        body = template_fn(rng)
        base = body["title"]
        if base.lower() in expanded_exclude:
            continue  # this caller has already had this problem

        pool = _TITLE_VARIATIONS.get(base)
        if pool:
            # Prefer a wording nobody was served recently; never reject an unseen problem for lack of one.
            available = (
                [v for v in pool if v.lower() not in full_exclude]
                or [v for v in pool if v.lower() not in expanded_exclude]
            )
            if not available:
                continue
            varied_title = rng.choice(available)
        else:
            varied_title = _make_generic_title(base, rng)
        chosen_body = body
        chosen_template_fn = template_fn
        break

    if chosen_body is None:
        raise NoFreshQuestion(f"no unseen {difficulty} {topic_key} question is left for this caller")

    # ── Build test cases ────────────────────────────────────────────────────
    test_cases = list(chosen_body["test_cases"])

    if len(test_cases) < desired_tc:
        seen_inputs = {str(tc["input"]) for tc in test_cases}
        attempts = 0
        max_attempts = (desired_tc - len(test_cases)) * 15
        while len(test_cases) < desired_tc and attempts < max_attempts:
            attempts += 1
            extra_body = chosen_template_fn(_rng())
            for tc in extra_body["test_cases"]:
                key = str(tc["input"])
                if key not in seen_inputs:
                    test_cases.append(tc)
                    seen_inputs.add(key)
                    if len(test_cases) >= desired_tc:
                        break
        # Absolute last resort — allow a repeat rather than crash
        while len(test_cases) < desired_tc:
            test_cases.append(rng.choice(test_cases))

    test_cases = test_cases[:desired_tc]

    # ── Record and return ───────────────────────────────────────────────────
    _record_title(varied_title)
    _record_title(chosen_body["title"])

    return {
        "title": varied_title,
        "base_title": chosen_body["title"],
        "problem_statement": chosen_body["problem_statement"] + flavour[difficulty],
        "input_format": chosen_body["input_format"],
        "output_format": chosen_body["output_format"],
        "sample_input": chosen_body["sample_input"],
        "sample_output": chosen_body["sample_output"],
        "test_cases": test_cases,
        "topic": topic_key,
        "difficulty": difficulty,
        "source": f"dynamic-{_uid()}",
    }


# ---------------------------------------------------------------------------
# Quick smoke-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    test_pairs = [
        ("arrays", "easy"),
        ("strings", "medium"),
        ("graphs", "hard"),
        ("dynamic programming", "medium"),
        ("trees", "easy"),
        ("stacks", "medium"),
        ("queues", "hard"),
        ("greedy", "easy"),
        ("hashing", "medium"),
        ("sorting", "hard"),
        ("searching", "easy"),
        ("recursion", "medium"),
        ("backtracking", "hard"),
        ("linked-lists", "easy"),
        ("two pointers", "medium"),
        ("sliding window", "hard"),
        ("binary search", "medium"),
        ("math", "easy"),
        ("bit manipulation", "medium"),
    ]

    for topic, diff in test_pairs:
        q = generate_dynamic(topic, diff)
        print(f"[{diff.upper()}] {topic} -> {q['title']} | TCs: {len(q['test_cases'])} | src: {q['source']}")

    # Verify uniqueness: two calls same topic/difficulty produce different sources
    q1 = generate_dynamic("arrays", "medium")
    q2 = generate_dynamic("arrays", "medium")
    assert q1["source"] != q2["source"], "Sources should be unique!"
    print("\nUniqueness check passed.")
    print("\nSample question:")
    sample = generate_dynamic("dynamic programming", "hard")
    print(json.dumps({k: v for k, v in sample.items() if k != "test_cases"}, indent=2))
    print(f"Test cases ({len(sample['test_cases'])}):")
    for i, tc in enumerate(sample["test_cases"], 1):
        print(f"  TC{i}: input={tc['input']}  output={tc['output']}")
