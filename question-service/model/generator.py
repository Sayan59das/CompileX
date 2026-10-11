"""
Generator module — loads the trained model and generates coding questions.
Falls back to a rule-based template engine if no trained model is found.
"""

import os
import json
import random
from typing import List, Optional

# Torch and model imports are optional — server works without them (uses fallback)
_TORCH_AVAILABLE = False
try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore

try:
    from .tokenizer import SimpleTokenizer
    from .transformer_model import CodingQuestionTransformer
except ImportError:
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(__file__))
        from tokenizer import SimpleTokenizer
        from transformer_model import CodingQuestionTransformer
    except ImportError:
        SimpleTokenizer = None  # type: ignore
        CodingQuestionTransformer = None  # type: ignore


# -----------------------------------------------------------------------
# Rule-based fallback (used before training)
# -----------------------------------------------------------------------

FALLBACK_TEMPLATES = {
    "arrays": [
        {
            "title": "Rotate Array",
            "problem_statement": (
                "Given an array of N integers, rotate it to the right by K positions. "
                "Elements shifted off the end wrap around to the beginning."
            ),
            "input_format": "First line: N and K.\nSecond line: N space-separated integers.",
            "output_format": "Print the rotated array on a single line.",
            "sample_input": "5 2\n1 2 3 4 5",
            "sample_output": "4 5 1 2 3",
            "test_cases": [
                {"input": "5 2\n1 2 3 4 5", "output": "4 5 1 2 3"},
                {"input": "3 1\n10 20 30", "output": "30 10 20"},
                {"input": "4 4\n1 2 3 4", "output": "1 2 3 4"},
            ],
        },
        {
            "title": "Maximum Subarray Sum",
            "problem_statement": (
                "Given an array of N integers, find the contiguous subarray "
                "(containing at least one number) which has the largest sum and return its sum."
            ),
            "input_format": "First line contains N (1 ≤ N ≤ 10^5).\nSecond line contains N space-separated integers.",
            "output_format": "Print a single integer — the maximum subarray sum.",
            "sample_input": "5\n-2 1 -3 4 -1",
            "sample_output": "4",
            "test_cases": [
                {"input": "5\n-2 1 -3 4 -1", "output": "4"},
                {"input": "1\n-1", "output": "-1"},
                {"input": "4\n1 2 3 4", "output": "10"},
            ],
        },
        {
            "title": "Two Sum",
            "problem_statement": (
                "Given an array of N integers and a target value T, "
                "find two distinct indices i and j such that arr[i] + arr[j] == T. "
                "Print the indices (1-indexed). If no such pair exists, print -1."
            ),
            "input_format": "First line: N and T.\nSecond line: N space-separated integers.",
            "output_format": "Print two space-separated indices or -1.",
            "sample_input": "4 9\n2 7 11 15",
            "sample_output": "1 2",
            "test_cases": [
                {"input": "4 9\n2 7 11 15", "output": "1 2"},
                {"input": "3 6\n1 2 4", "output": "2 3"},
                {"input": "3 100\n1 2 3", "output": "-1"},
            ],
        },
    ],
    "strings": [
        {
            "title": "Longest Palindromic Substring",
            "problem_statement": (
                "Given a string S, find the longest substring of S that is a palindrome. "
                "If there are multiple answers of the same length, print the one that appears first."
            ),
            "input_format": "A single line containing string S (1 ≤ |S| ≤ 1000, lowercase letters only).",
            "output_format": "Print the longest palindromic substring.",
            "sample_input": "babad",
            "sample_output": "bab",
            "test_cases": [
                {"input": "babad", "output": "bab"},
                {"input": "cbbd", "output": "bb"},
                {"input": "a", "output": "a"},
            ],
        },
        {
            "title": "Anagram Check",
            "problem_statement": (
                "Given two strings A and B, determine if B is an anagram of A. "
                "Two strings are anagrams if they contain the same characters with the same frequencies."
            ),
            "input_format": "First line: string A.\nSecond line: string B.",
            "output_format": "Print YES if B is an anagram of A, otherwise NO.",
            "sample_input": "listen\nsilent",
            "sample_output": "YES",
            "test_cases": [
                {"input": "listen\nsilent", "output": "YES"},
                {"input": "hello\nworld", "output": "NO"},
                {"input": "abc\ncba", "output": "YES"},
            ],
        },
        {
            "title": "Count Distinct Substrings",
            "problem_statement": (
                "Given a string S, count the number of distinct non-empty substrings."
            ),
            "input_format": "A single line containing string S (1 ≤ |S| ≤ 500, lowercase letters only).",
            "output_format": "Print a single integer — the number of distinct substrings.",
            "sample_input": "abc",
            "sample_output": "6",
            "test_cases": [
                {"input": "abc", "output": "6"},
                {"input": "aaa", "output": "3"},
                {"input": "ab", "output": "3"},
            ],
        },
    ],
    "dynamic programming": [
        {
            "title": "0/1 Knapsack Problem",
            "problem_statement": (
                "You have N items, each with a weight W[i] and value V[i], "
                "and a knapsack with capacity C. "
                "Find the maximum total value you can carry without exceeding the capacity."
            ),
            "input_format": (
                "First line: N and C.\n"
                "Next N lines: W[i] and V[i] for each item."
            ),
            "output_format": "Print a single integer — the maximum value.",
            "sample_input": "3 50\n10 60\n20 100\n30 120",
            "sample_output": "220",
            "test_cases": [
                {"input": "3 50\n10 60\n20 100\n30 120", "output": "220"},
                {"input": "1 10\n15 100", "output": "0"},
                {"input": "2 10\n5 40\n5 50", "output": "90"},
            ],
        },
        {
            "title": "Longest Common Subsequence",
            "problem_statement": (
                "Given two strings A and B, find the length of their Longest Common Subsequence (LCS). "
                "A subsequence is a sequence derived by deleting some characters without changing the order."
            ),
            "input_format": "First line: string A.\nSecond line: string B.",
            "output_format": "Print a single integer — the length of the LCS.",
            "sample_input": "abcde\nace",
            "sample_output": "3",
            "test_cases": [
                {"input": "abcde\nace", "output": "3"},
                {"input": "abc\nabc", "output": "3"},
                {"input": "abc\ndef", "output": "0"},
            ],
        },
        {
            "title": "Coin Change",
            "problem_statement": (
                "Given an array of coin denominations and a target amount, "
                "find the minimum number of coins needed to make up that amount. "
                "If it is not possible, print -1."
            ),
            "input_format": "First line: N (number of coins) and T (target).\nSecond line: N coin denominations.",
            "output_format": "Print the minimum number of coins, or -1 if impossible.",
            "sample_input": "3 11\n1 5 6",
            "sample_output": "2",
            "test_cases": [
                {"input": "3 11\n1 5 6", "output": "2"},
                {"input": "2 3\n2 4", "output": "-1"},
                {"input": "1 0\n1", "output": "0"},
            ],
        },
    ],
    "graphs": [
        {
            "title": "Shortest Path in Unweighted Graph",
            "problem_statement": (
                "Given an undirected unweighted graph with N nodes and M edges, "
                "find the shortest path (in terms of number of edges) from node S to node D. "
                "If no path exists, print -1."
            ),
            "input_format": (
                "First line: N, M, S, D.\n"
                "Next M lines: two integers u and v representing an edge."
            ),
            "output_format": "Print the shortest path length or -1.",
            "sample_input": "5 4 1 5\n1 2\n2 3\n3 4\n4 5",
            "sample_output": "4",
            "test_cases": [
                {"input": "5 4 1 5\n1 2\n2 3\n3 4\n4 5", "output": "4"},
                {"input": "3 1 1 3\n1 2", "output": "-1"},
                {"input": "2 1 1 2\n1 2", "output": "1"},
            ],
        },
        {
            "title": "Number of Connected Components",
            "problem_statement": (
                "Given an undirected graph with N nodes and M edges, "
                "find the number of connected components."
            ),
            "input_format": "First line: N and M.\nNext M lines: two integers u and v representing an edge.",
            "output_format": "Print a single integer — the number of connected components.",
            "sample_input": "5 3\n1 2\n2 3\n4 5",
            "sample_output": "2",
            "test_cases": [
                {"input": "5 3\n1 2\n2 3\n4 5", "output": "2"},
                {"input": "4 0", "output": "4"},
                {"input": "3 3\n1 2\n2 3\n1 3", "output": "1"},
            ],
        },
        {
            "title": "Detect Cycle in Directed Graph",
            "problem_statement": (
                "Given a directed graph with N nodes and M edges, "
                "determine if the graph contains a cycle."
            ),
            "input_format": "First line: N and M.\nNext M lines: two integers u and v representing a directed edge from u to v.",
            "output_format": "Print YES if a cycle exists, otherwise NO.",
            "sample_input": "3 3\n1 2\n2 3\n3 1",
            "sample_output": "YES",
            "test_cases": [
                {"input": "3 3\n1 2\n2 3\n3 1", "output": "YES"},
                {"input": "3 2\n1 2\n2 3", "output": "NO"},
                {"input": "4 4\n1 2\n2 3\n3 4\n4 2", "output": "YES"},
            ],
        },
    ],
    "trees": [
        {
            "title": "Lowest Common Ancestor",
            "problem_statement": (
                "Given a binary tree and two nodes U and V, "
                "find their Lowest Common Ancestor (LCA)."
            ),
            "input_format": "First line: N.\nNext N-1 lines: parent child pairs.\nLast line: U and V.",
            "output_format": "Print the node value of the LCA.",
            "sample_input": "5\n1 2\n1 3\n2 4\n2 5\n4 3",
            "sample_output": "1",
            "test_cases": [
                {"input": "5\n1 2\n1 3\n2 4\n2 5\n4 3", "output": "1"},
                {"input": "3\n1 2\n1 3\n2 3", "output": "1"},
            ],
        },
        {
            "title": "Height of Binary Tree",
            "problem_statement": (
                "Given a binary tree with N nodes, find its height. "
                "The height is the number of edges on the longest path from root to a leaf."
            ),
            "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
            "output_format": "Print a single integer — the height of the tree.",
            "sample_input": "5\n1 2\n1 3\n2 4\n2 5",
            "sample_output": "2",
            "test_cases": [
                {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "2"},
                {"input": "1", "output": "0"},
                {"input": "3\n1 2\n2 3", "output": "2"},
            ],
        },
        {
            "title": "Level Order Traversal",
            "problem_statement": "Given a binary tree, print its nodes level by level from left to right.",
            "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
            "output_format": "Print nodes level by level, each level on a new line.",
            "sample_input": "5\n1 2\n1 3\n2 4\n2 5",
            "sample_output": "1\n2 3\n4 5",
            "test_cases": [
                {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "1\n2 3\n4 5"},
                {"input": "1", "output": "1"},
                {"input": "3\n1 2\n1 3", "output": "1\n2 3"},
            ],
        },
    ],
    "sorting": [
        {
            "title": "Sort and Count Inversions",
            "problem_statement": (
                "Given an array of N integers, count the number of inversions. "
                "An inversion is a pair (i, j) such that i < j and arr[i] > arr[j]."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated integers.",
            "output_format": "Print the number of inversions.",
            "sample_input": "5\n2 4 1 3 5",
            "sample_output": "3",
            "test_cases": [
                {"input": "5\n2 4 1 3 5", "output": "3"},
                {"input": "3\n1 2 3", "output": "0"},
                {"input": "3\n3 2 1", "output": "3"},
            ],
        },
        {
            "title": "Merge Sorted Arrays",
            "problem_statement": (
                "Given two sorted arrays A and B of sizes N and M respectively, "
                "merge them into a single sorted array and print it."
            ),
            "input_format": "First line: N and M.\nSecond line: N sorted integers.\nThird line: M sorted integers.",
            "output_format": "Print the merged sorted array.",
            "sample_input": "3 3\n1 3 5\n2 4 6",
            "sample_output": "1 2 3 4 5 6",
            "test_cases": [
                {"input": "3 3\n1 3 5\n2 4 6", "output": "1 2 3 4 5 6"},
                {"input": "2 1\n1 2\n3", "output": "1 2 3"},
                {"input": "1 1\n5\n5", "output": "5 5"},
            ],
        },
    ],
    "stacks": [
        {
            "title": "Valid Parentheses",
            "problem_statement": (
                "Given a string containing only '(', ')', '{', '}', '[' and ']', "
                "determine if the input string is valid."
            ),
            "input_format": "A single line containing the bracket string.",
            "output_format": "Print YES if valid, otherwise NO.",
            "sample_input": "({[]})",
            "sample_output": "YES",
            "test_cases": [
                {"input": "({[]})", "output": "YES"},
                {"input": "([)]", "output": "NO"},
                {"input": "{[]}", "output": "YES"},
            ],
        },
        {
            "title": "Next Greater Element",
            "problem_statement": (
                "Given an array of N integers, for each element find the next greater element "
                "to its right. If no greater element exists, print -1."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated integers.",
            "output_format": "Print N space-separated integers.",
            "sample_input": "5\n4 5 2 10 8",
            "sample_output": "5 10 10 -1 -1",
            "test_cases": [
                {"input": "5\n4 5 2 10 8", "output": "5 10 10 -1 -1"},
                {"input": "3\n3 2 1", "output": "-1 -1 -1"},
                {"input": "3\n1 2 3", "output": "2 3 -1"},
            ],
        },
    ],
    "queues": [
        {
            "title": "Sliding Window Maximum",
            "problem_statement": (
                "Given an array of N integers and a window size K, "
                "find the maximum element in each sliding window of size K."
            ),
            "input_format": "First line: N and K.\nSecond line: N space-separated integers.",
            "output_format": "Print N-K+1 space-separated integers.",
            "sample_input": "8 3\n1 3 -1 -3 5 3 6 7",
            "sample_output": "3 3 5 5 6 7",
            "test_cases": [
                {"input": "8 3\n1 3 -1 -3 5 3 6 7", "output": "3 3 5 5 6 7"},
                {"input": "4 2\n2 1 5 3", "output": "2 5 5"},
                {"input": "3 1\n1 2 3", "output": "1 2 3"},
            ],
        },
        {
            "title": "Circular Queue Operations",
            "problem_statement": (
                "Implement a circular queue of size K. Process Q operations: "
                "ENQUEUE x (add x), DEQUEUE (remove front), FRONT (print front element or -1 if empty)."
            ),
            "input_format": "First line: K and Q.\nNext Q lines: operation name and optional value.",
            "output_format": "For each FRONT operation, print the front element or -1.",
            "sample_input": "3 5\nENQUEUE 1\nENQUEUE 2\nFRONT\nDEQUEUE\nFRONT",
            "sample_output": "1\n2",
            "test_cases": [
                {"input": "3 5\nENQUEUE 1\nENQUEUE 2\nFRONT\nDEQUEUE\nFRONT", "output": "1\n2"},
                {"input": "2 3\nFRONT\nENQUEUE 5\nFRONT", "output": "-1\n5"},
            ],
        },
    ],
    "hashing": [
        {
            "title": "Subarray with Zero Sum",
            "problem_statement": (
                "Given an array of N integers, determine if there exists a subarray with sum equal to zero."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated integers.",
            "output_format": "Print YES if such a subarray exists, otherwise NO.",
            "sample_input": "5\n4 2 -3 1 6",
            "sample_output": "YES",
            "test_cases": [
                {"input": "5\n4 2 -3 1 6", "output": "YES"},
                {"input": "3\n1 2 3", "output": "NO"},
                {"input": "4\n-1 1 -2 2", "output": "YES"},
            ],
        },
        {
            "title": "Longest Subarray with Equal 0s and 1s",
            "problem_statement": (
                "Given a binary array of N elements, "
                "find the length of the longest subarray with equal number of 0s and 1s."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated binary integers.",
            "output_format": "Print a single integer — the length of the longest such subarray.",
            "sample_input": "6\n0 1 0 1 1 0",
            "sample_output": "6",
            "test_cases": [
                {"input": "6\n0 1 0 1 1 0", "output": "6"},
                {"input": "4\n0 0 1 1", "output": "4"},
                {"input": "3\n0 0 0", "output": "0"},
            ],
        },
    ],
    "greedy": [
        {
            "title": "Activity Selection Problem",
            "problem_statement": (
                "Given N activities with start and end times, select the maximum number "
                "of non-overlapping activities."
            ),
            "input_format": "First line: N.\nNext N lines: start and end time of each activity.",
            "output_format": "Print a single integer — the maximum number of activities.",
            "sample_input": "6\n1 2\n3 4\n0 6\n5 7\n8 9\n5 9",
            "sample_output": "4",
            "test_cases": [
                {"input": "6\n1 2\n3 4\n0 6\n5 7\n8 9\n5 9", "output": "4"},
                {"input": "3\n1 3\n2 4\n3 5", "output": "2"},
                {"input": "1\n0 1", "output": "1"},
            ],
        },
        {
            "title": "Minimum Platforms",
            "problem_statement": (
                "Given arrival and departure times of N trains, find the minimum number "
                "of platforms required so that no train waits."
            ),
            "input_format": "First line: N.\nSecond line: N arrival times.\nThird line: N departure times.",
            "output_format": "Print a single integer — the minimum number of platforms.",
            "sample_input": "6\n900 940 950 1100 1500 1800\n910 1200 1120 1130 1900 2000",
            "sample_output": "3",
            "test_cases": [
                {"input": "6\n900 940 950 1100 1500 1800\n910 1200 1120 1130 1900 2000", "output": "3"},
                {"input": "3\n900 1100 1235\n1000 1200 1240", "output": "1"},
                {"input": "1\n100\n200", "output": "1"},
            ],
        },
    ],
    "linked-lists": [
        {
            "title": "Reverse a Linked List",
            "problem_statement": (
                "Given a linked list of N nodes, reverse it and print the values."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated node values.",
            "output_format": "Print the reversed linked list values.",
            "sample_input": "5\n1 2 3 4 5",
            "sample_output": "5 4 3 2 1",
            "test_cases": [
                {"input": "5\n1 2 3 4 5", "output": "5 4 3 2 1"},
                {"input": "1\n42", "output": "42"},
                {"input": "3\n10 20 30", "output": "30 20 10"},
            ],
        },
        {
            "title": "Detect Cycle in Linked List",
            "problem_statement": (
                "Given a linked list of N nodes, determine if it contains a cycle. "
                "The last node's next pointer is given as -1 (no cycle) or an index (cycle)."
            ),
            "input_format": "First line: N.\nSecond line: N node values.\nThird line: index where last node points (-1 for no cycle).",
            "output_format": "Print YES if cycle exists, otherwise NO.",
            "sample_input": "5\n1 2 3 4 5\n1",
            "sample_output": "YES",
            "test_cases": [
                {"input": "5\n1 2 3 4 5\n1", "output": "YES"},
                {"input": "3\n1 2 3\n-1", "output": "NO"},
            ],
        },
    ],
    "searching": [
        {
            "title": "Binary Search",
            "problem_statement": (
                "Given a sorted array of N integers and a target T, "
                "find the index of T using binary search. Print -1 if not found. Use 0-based indexing."
            ),
            "input_format": "First line: N and T.\nSecond line: N sorted integers.",
            "output_format": "Print the index of T or -1.",
            "sample_input": "5 3\n1 2 3 4 5",
            "sample_output": "2",
            "test_cases": [
                {"input": "5 3\n1 2 3 4 5", "output": "2"},
                {"input": "4 10\n1 2 3 4", "output": "-1"},
                {"input": "3 1\n1 2 3", "output": "0"},
            ],
        },
        {
            "title": "Find Peak Element",
            "problem_statement": (
                "Given an array of N integers, find a peak element. "
                "An element is a peak if it is greater than its neighbors. "
                "Print the index of any peak element (0-based)."
            ),
            "input_format": "First line: N.\nSecond line: N space-separated integers.",
            "output_format": "Print the index of a peak element.",
            "sample_input": "5\n1 3 2 4 1",
            "sample_output": "3",
            "test_cases": [
                {"input": "5\n1 3 2 4 1", "output": "3"},
                {"input": "3\n1 2 3", "output": "2"},
                {"input": "1\n5", "output": "0"},
            ],
        },
    ],
    "backtracking": [
        {
            "title": "N-Queens Problem",
            "problem_statement": (
                "Place N queens on an N×N chessboard such that no two queens attack each other. "
                "Print the number of distinct solutions."
            ),
            "input_format": "A single integer N.",
            "output_format": "Print the number of distinct solutions.",
            "sample_input": "4",
            "sample_output": "2",
            "test_cases": [
                {"input": "4", "output": "2"},
                {"input": "1", "output": "1"},
                {"input": "5", "output": "10"},
            ],
        },
        {
            "title": "Generate All Permutations",
            "problem_statement": (
                "Given an array of N distinct integers, generate and print all N! permutations "
                "in lexicographic order."
            ),
            "input_format": "First line: N.\nSecond line: N distinct integers.",
            "output_format": "Print each permutation on a new line.",
            "sample_input": "3\n1 2 3",
            "sample_output": "1 2 3\n1 3 2\n2 1 3\n2 3 1\n3 1 2\n3 2 1",
            "test_cases": [
                {"input": "2\n1 2", "output": "1 2\n2 1"},
                {"input": "1\n5", "output": "5"},
            ],
        },
    ],
    "recursion": [
        {
            "title": "Tower of Hanoi",
            "problem_statement": (
                "Given N disks and 3 pegs, print the minimum number of moves "
                "required to move all disks from peg 1 to peg 3."
            ),
            "input_format": "A single integer N (1 ≤ N ≤ 30).",
            "output_format": "Print a single integer — the minimum number of moves.",
            "sample_input": "3",
            "sample_output": "7",
            "test_cases": [
                {"input": "3", "output": "7"},
                {"input": "1", "output": "1"},
                {"input": "4", "output": "15"},
            ],
        },
        {
            "title": "Fibonacci Number",
            "problem_statement": (
                "Given N, compute the Nth Fibonacci number. F(0)=0, F(1)=1, F(N)=F(N-1)+F(N-2)."
            ),
            "input_format": "A single integer N (0 ≤ N ≤ 40).",
            "output_format": "Print the Nth Fibonacci number.",
            "sample_input": "10",
            "sample_output": "55",
            "test_cases": [
                {"input": "10", "output": "55"},
                {"input": "0", "output": "0"},
                {"input": "1", "output": "1"},
            ],
        },
    ],
}

DIFFICULTY_MODIFIERS = {
    "easy": "simple and beginner-friendly",
    "medium": "intermediate level",
    "hard": "advanced and challenging",
}


_last_picked: dict = {}  # topic -> last title picked, to avoid immediate repeats


def _fallback_generate(topic: str, difficulty: str) -> dict:
    """Rule-based question generator — picks randomly, avoiding immediate repeats."""
    topic_lower = topic.lower().strip()

    matched = None
    for key in FALLBACK_TEMPLATES:
        if key in topic_lower or topic_lower in key:
            matched = key
            break

    if matched is None:
        return {
            "title": f"{topic.title()} Challenge",
            "problem_statement": (
                f"Given a sequence of N integers related to {topic}, "
                f"solve the following {DIFFICULTY_MODIFIERS.get(difficulty, 'medium level')} problem: "
                f"Find the optimal solution that satisfies all given constraints."
            ),
            "input_format": "First line: N (1 ≤ N ≤ 10^5).\nSecond line: N space-separated integers.",
            "output_format": "Print the answer on a single line.",
            "sample_input": "5\n1 2 3 4 5",
            "sample_output": "15",
            "test_cases": [
                {"input": "5\n1 2 3 4 5", "output": "15"},
                {"input": "1\n0", "output": "0"},
                {"input": "3\n10 20 30", "output": "60"},
            ],
            "topic": topic,
            "difficulty": difficulty,
            "source": "template",
        }

    pool = FALLBACK_TEMPLATES[matched]
    last_title = _last_picked.get(matched)

    # Filter out the last picked title if pool has more than one entry
    candidates = [q for q in pool if q["title"] != last_title] if len(pool) > 1 else pool
    selected = random.choice(candidates).copy()

    _last_picked[matched] = selected["title"]
    selected["topic"] = topic
    selected["difficulty"] = difficulty
    selected["source"] = "template"
    return selected


# -----------------------------------------------------------------------
# Main Generator class
# -----------------------------------------------------------------------

class QuestionGenerator:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved_model", "model.pt")
    TOKENIZER_PATH = os.path.join(os.path.dirname(__file__), "saved_model", "tokenizer.json")
    
    # Cache the dynamic generator module to avoid repeated imports
    _dynamic_generator = None

    def __init__(self):
        self.model: Optional[CodingQuestionTransformer] = None
        self.tokenizer: Optional[SimpleTokenizer] = None
        if _TORCH_AVAILABLE:
            cuda_available = torch.cuda.is_available() and torch.cuda.device_count() > 0
            self.device = torch.device("cuda" if cuda_available else "cpu")
        else:
            self.device = None
        self._try_load_model()
        
        # Pre-import dynamic generator to avoid first-call delay
        self._preload_dynamic_generator()
    
    def _preload_dynamic_generator(self):
        """Pre-import the dynamic generator module to avoid first-call delay."""
        if QuestionGenerator._dynamic_generator is None:
            try:
                import importlib, sys as _sys
                _model_dir = os.path.dirname(__file__)
                if _model_dir not in _sys.path:
                    _sys.path.insert(0, _model_dir)
                QuestionGenerator._dynamic_generator = importlib.import_module("dynamic_generator")
                print("[Generator] Dynamic generator pre-loaded")
            except Exception as e:
                print(f"[Generator] Failed to pre-load dynamic generator: {e}")

    def _try_load_model(self):
        if not _TORCH_AVAILABLE:
            print("[Generator] PyTorch not available. Using rule-based fallback.")
            return
        if os.path.exists(self.MODEL_PATH) and os.path.exists(self.TOKENIZER_PATH):
            try:
                self.tokenizer = SimpleTokenizer()
                self.tokenizer.load(self.TOKENIZER_PATH)

                # Auto-detect architecture from checkpoint so we never mismatch
                ckpt = torch.load(self.MODEL_PATH, map_location=self.device)
                enc_layers = max(
                    int(k.split(".")[3])
                    for k in ckpt if k.startswith("transformer.encoder.layers.")
                ) + 1
                dec_layers = max(
                    int(k.split(".")[3])
                    for k in ckpt if k.startswith("transformer.decoder.layers.")
                ) + 1
                # Detect d_model from embedding weight shape
                d_model = ckpt["src_embedding.weight"].shape[1]
                # Detect ff dim from first encoder linear1
                ff_dim = ckpt.get(
                    "transformer.encoder.layers.0.linear1.weight",
                    torch.zeros(512, 1)
                ).shape[0]
                print(f"[Generator] Checkpoint: enc={enc_layers}, dec={dec_layers}, "
                      f"d_model={d_model}, ff={ff_dim}")

                self.model = CodingQuestionTransformer(
                    vocab_size=self.tokenizer.vocab_size,
                    d_model=d_model,
                    num_encoder_layers=enc_layers,
                    num_decoder_layers=dec_layers,
                    dim_feedforward=ff_dim,
                )
                self.model.load_state_dict(ckpt)
                self.model.to(self.device)
                self.model.eval()
                total = sum(p.numel() for p in self.model.parameters())
                print(f"[Generator] Trained model loaded on {self.device} ({total:,} params).")
            except Exception as e:
                print(f"[Generator] Failed to load model: {e}. Using fallback.")
                self.model = None
                self.tokenizer = None
        else:
            print("[Generator] No trained model found. Using rule-based fallback.")

    @property
    def is_model_loaded(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def generate(self, topic: str, difficulty: str = "medium", exclude_titles: Optional[List[str]] = None, seed: Optional[int] = None) -> dict:
        """
        Generate a coding question.
        Priority:
          1. Smart AI generator (dataset + variation) — always works
          2. Trained model (if loaded and produces valid output)
          3. Dynamic template generator — fallback
        """
        import time
        start_time = time.time()

        # ── 1. Smart AI generator (primary) ──────────────────────────────
        try:
            from model.smart_generator import generate_smart
        except ImportError:
            try:
                import sys as _sys
                _sys.path.insert(0, os.path.dirname(__file__))
                from smart_generator import generate_smart
            except ImportError:
                generate_smart = None

        if generate_smart:
            result = generate_smart(topic, difficulty, exclude_titles=exclude_titles, seed=seed)
            if result:
                elapsed = time.time() - start_time
                print(f"[Generator] ✓ Smart AI: '{result['title']}' in {elapsed:.2f}s")
                return result

        # ── 2. Trained model (if loaded and produces valid output) ────────
        if self.is_model_loaded:
            try:
                result = self._model_generate_creative(topic, difficulty)
                if (
                    result.get("title", "").strip()
                    and len(result.get("problem_statement", "")) > 50
                    and result.get("source") not in ("error_fallback", "template")
                ):
                    elapsed = time.time() - start_time
                    print(f"[Generator] ✓ Model: '{result['title']}' in {elapsed:.2f}s")
                    return result
            except Exception as e:
                print(f"[Generator] Model failed: {e}")

        # ── 3. Dynamic template generator ────────────────────────────────
        try:
            if QuestionGenerator._dynamic_generator is None:
                self._preload_dynamic_generator()
            if QuestionGenerator._dynamic_generator:
                result = QuestionGenerator._dynamic_generator.generate_dynamic(topic, difficulty)
                elapsed = time.time() - start_time
                print(f"[Generator] ✓ Dynamic: '{result.get('title', 'Unknown')}' in {elapsed:.2f}s")
                return result
        except Exception as e:
            print(f"[Generator] Dynamic failed: {e}")

        # ── 4. Static fallback ────────────────────────────────────────────
        if seed is not None:
            random.seed(seed)
        result = _fallback_generate(topic, difficulty)
        elapsed = time.time() - start_time
        print(f"[Generator] ✓ Static fallback in {elapsed:.2f}s")
        return result

    def _parse_output(self, text: str, topic: str, difficulty: str) -> dict:
        """Parse model output into structured dict."""
        result = {
            "title": "",
            "problem_statement": "",
            "input_format": "",
            "output_format": "",
            "sample_input": "",
            "sample_output": "",
            "test_cases": [],
            "topic": topic,
            "difficulty": difficulty,
            "source": "model",
        }

        sections = {
            "TITLE:": "title",
            "PROBLEM STATEMENT:": "problem_statement",
            "INPUT FORMAT:": "input_format",
            "OUTPUT FORMAT:": "output_format",
            "SAMPLE INPUT:": "sample_input",
            "SAMPLE OUTPUT:": "sample_output",
        }

        current_key = None
        lines = text.split("\n")
        buffer = []

        for line in lines:
            matched_section = None
            for marker, key in sections.items():
                if line.strip().upper().startswith(marker):
                    matched_section = key
                    remainder = line[len(marker):].strip()
                    break

            if matched_section:
                if current_key and buffer:
                    result[current_key] = "\n".join(buffer).strip()
                current_key = matched_section
                buffer = [remainder] if remainder else []
            elif current_key:
                buffer.append(line)

        if current_key and buffer:
            result[current_key] = "\n".join(buffer).strip()

        # Fallback parsing for unstructured output.
        if not any(result[field] for field in ["title", "problem_statement"]):
            clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
            if clean_lines:
                result["title"] = clean_lines[0]
                result["problem_statement"] = "\n".join(clean_lines[1:]).strip()

        return result

    def _create_creative_prompts(self, topic: str, difficulty: str) -> list:
        """
        Create varied input prompts to encourage creative question generation.
        """
        base_topic = topic.lower().strip()
        base_difficulty = difficulty.lower().strip()
        
        # Topic variations
        topic_synonyms = {
            "arrays": ["array manipulation", "list processing", "sequence operations", "vector problems"],
            "strings": ["string manipulation", "text processing", "character sequences", "word problems"],
            "graphs": ["graph theory", "network problems", "node connections", "path finding"],
            "trees": ["tree structures", "hierarchical data", "binary trees", "tree traversal"],
            "dynamic programming": ["DP optimization", "optimal substructure", "overlapping subproblems", "memoization"],
            "sorting": ["ordering algorithms", "comparison sorting", "element arrangement", "sequence sorting"],
            "searching": ["search algorithms", "element lookup", "binary search", "linear search"],
            "hashing": ["hash tables", "dictionary problems", "key-value mapping", "hash functions"],
            "greedy": ["greedy algorithms", "local optimization", "heuristic approaches", "step-by-step optimization"],
            "backtracking": ["exploration algorithms", "brute force with pruning", "recursive search", "state space search"],
        }
        
        topic_variations = topic_synonyms.get(base_topic, [base_topic])
        
        # Difficulty variations
        difficulty_modifiers = {
            "easy": ["beginner", "fundamental", "basic", "introductory"],
            "medium": ["intermediate", "moderate", "standard", "typical"],
            "hard": ["advanced", "challenging", "complex", "difficult"],
        }
        
        difficulty_variations = difficulty_modifiers.get(base_difficulty, [base_difficulty])
        
        # Create prompt variations
        prompts = []
        for t_var in topic_variations[:2]:  # Limit to avoid too many combinations
            for d_var in difficulty_variations[:2]:
                # Add some creative modifiers
                modifiers = ["", " with constraints", " with optimization", " with multiple approaches", " with edge cases"]
                for modifier in modifiers[:3]:  # Limit combinations
                    prompt = f"{t_var} {d_var}{modifier}"
                    prompts.append(prompt.strip())
        
        # Add some completely novel combinations
        novel_combinations = [
            f"creative {base_topic} challenge",
            f"unique {base_topic} problem",
            f"innovative {base_topic} solution",
            f"{base_topic} with twist",
            f"advanced {base_topic} techniques",
        ]
        
        prompts.extend(novel_combinations[:3])
        
        # Ensure we have at least the basic prompt
        if not prompts:
            prompts = [f"{base_topic} {base_difficulty}"]
            
        return list(set(prompts))  # Remove duplicates

    def _generate_with_params(
        self,
        prompt: str,
        topic: str,
        difficulty: str,
        temperature: float = 0.8,
        top_k: int = 50,
        top_p: float = 0.9,
        repetition_penalty: float = 1.1,
    ) -> dict:
        """
        Generate a question with specific sampling parameters.
        """
        try:
            src_ids = self.tokenizer.encode(prompt)
            if not src_ids:
                raise ValueError(f"Empty token sequence for prompt: {prompt}")

            src_tensor = torch.tensor([src_ids], dtype=torch.long, device=self.device)

            try:
                raw_output = self.model.generate(
                    src_tensor,
                    self.tokenizer,
                    max_new_tokens=300,  # Reduced from 400 for faster generation
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                )
            except RuntimeError as runtime_error:
                # Fall back to CPU if GPU generation fails due to device-side errors.
                if self.device.type == "cuda":
                    print(f"[Generator] GPU generation failed, falling back to CPU: {runtime_error}")
                    self.model.to("cpu")
                    self.device = torch.device("cpu")
                    src_tensor = src_tensor.to(self.device)
                    raw_output = self.model.generate(
                        src_tensor,
                        self.tokenizer,
                        max_new_tokens=400,
                        temperature=temperature,
                        top_k=top_k,
                        top_p=top_p,
                        repetition_penalty=repetition_penalty,
                    )
                else:
                    raise

            result = self._parse_output(raw_output, topic, difficulty)
            return result

        except Exception as e:
            print(f"Generation failed for prompt '{prompt}': {e}")
            return {
                "title": f"Creative {topic.title()} Problem",
                "problem_statement": f"Create a creative solution for {topic} with {difficulty} difficulty.",
                "input_format": "Input format to be determined",
                "output_format": "Output format to be determined",
                "sample_input": "Sample input",
                "sample_output": "Sample output",
                "test_cases": [],
                "topic": topic,
                "difficulty": difficulty,
                "source": "error_fallback",
            }

    def _sample_generation_config(self) -> dict:
        """Return a randomized sampling configuration to encourage diverse generations."""
        return {
            "temperature": random.choice([0.7, 0.8, 0.9, 1.0, 1.1]),
            "top_k": random.choice([20, 30, 40, 50, 60]),
            "top_p": random.choice([0.85, 0.9, 0.95, 1.0]),
            "repetition_penalty": random.choice([1.05, 1.1, 1.2]),
        }

    def _score_question_quality(self, result: dict) -> float:
        """
        Score a generated question based on completeness and creativity.
        """
        score = 0.0
        
        # Completeness score
        required_fields = ["title", "problem_statement", "input_format", "output_format", "sample_input", "sample_output"]
        for field in required_fields:
            if result.get(field) and len(str(result[field]).strip()) > 10:
                score += 1.0
        
        # Test cases bonus
        if result.get("test_cases") and len(result["test_cases"]) > 0:
            score += 0.5
        
        # Creativity indicators (avoid generic phrases)
        problem_text = str(result.get("problem_statement", "")).lower()
        generic_phrases = ["given an array", "given a string", "find the", "calculate the", "determine the"]
        creativity_penalty = sum(1 for phrase in generic_phrases if phrase in problem_text)
        score -= creativity_penalty * 0.1
        
        # Length bonus (encourage detailed problems)
        total_length = sum(len(str(result.get(field, ""))) for field in required_fields)
        if total_length > 500:
            score += 0.5
        
        return max(0, score)

    def _model_generate_creative(self, topic: str, difficulty: str) -> dict:
        """
        Generate creative, novel coding questions using enhanced sampling techniques.
        """
        # Create varied input prompts to encourage creativity
        prompt_variations = self._create_creative_prompts(topic, difficulty)
        
        print(f"[Creative] Trying {len(prompt_variations)} prompt variations...")
        
        # Try a selection of prompt variations with randomized sampling parameters.
        best_result = None
        best_score = 0
        random.shuffle(prompt_variations)

        # Limit to 2 prompts and 1 attempt each for faster generation
        for i, prompt in enumerate(prompt_variations[:2]):
            print(f"[Creative] Trying prompt {i+1}: '{prompt}'")
            config = self._sample_generation_config()
            try:
                result = self._generate_with_params(
                    prompt,
                    topic,
                    difficulty,
                    temperature=config["temperature"],
                    top_k=config["top_k"],
                    top_p=config["top_p"],
                    repetition_penalty=config["repetition_penalty"],
                )

                if result.get("source") == "error_fallback":
                    continue

                score = self._score_question_quality(result)
                print(
                    f"[Creative] Score: {score:.2f} for temp={config['temperature']}, "
                    f"top_k={config['top_k']}, top_p={config['top_p']}"
                )

                if score > best_score:
                    best_score = score
                    best_result = result

            except Exception as e:
                print(f"[Creative] Exception during generation: {e}")
                continue
        
        # If all generations failed, fall back to template
        if best_result is None or not best_result.get("title") or not best_result.get("problem_statement"):
            print("[Creative] All generations failed, using template fallback")
            fallback = _fallback_generate(topic, difficulty)
            fallback["source"] = "template"
            return fallback
            
        print(f"[Creative] Best result score: {best_score:.2f}")
        best_result["source"] = "model"
        return best_result
        
        # If all generations failed, fall back to template
        if best_result is None or not best_result.get("title") or not best_result.get("problem_statement"):
            print("[Creative] All generations failed, using template fallback")
            fallback = _fallback_generate(topic, difficulty)
            fallback["source"] = "template"
            return fallback
            
        print(f"[Creative] Best result score: {best_score:.2f}")
        best_result["source"] = "creative_model"
        return best_result


# Singleton
_generator_instance = None


def get_generator() -> QuestionGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = QuestionGenerator()
    return _generator_instance
