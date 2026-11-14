import json
import hashlib
import random
import re
import asyncio
import httpx
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from app.core.config import get_settings
from app.models.models import DifficultyLevel

settings = get_settings()

STARTER_CODE = {
    "python": """# ============================================
# IMPORTANT: Read the problem description carefully!
# - Check the Input Format section
# - Check the Output Format section
# - Match the exact format shown in Sample Output
# ============================================

# Common I/O patterns:

# 1. Reading a single integer:
# n = int(input())

# 2. Reading an array of integers (space-separated):
# arr = list(map(int, input().split()))

# 3. Reading multiple lines:
# line1 = input()
# line2 = input()

# 4. Printing a single value:
# print(result)

# 5. Printing an array (IMPORTANT - use space-separated, NOT Python list format):
# print(' '.join(map(str, result)))  # Correct: "1 2 3"
# print(result)  # Wrong: "[1, 2, 3]"

# Write your solution below:

""",
    "cpp": """#include <bits/stdc++.h>
using namespace std;

// ============================================
// IMPORTANT: Read the problem description carefully!
// - Check the Input Format section
// - Check the Output Format section
// - Match the exact format shown in Sample Output
// ============================================

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Common I/O patterns:
    
    // 1. Reading a single integer:
    // int n; cin >> n;
    
    // 2. Reading an array:
    // int n; cin >> n;
    // vector<int> arr(n);
    // for(int i = 0; i < n; i++) cin >> arr[i];
    
    // 3. Reading space-separated values in one line:
    // string line;
    // getline(cin, line);
    // istringstream iss(line);
    // vector<int> arr;
    // int num;
    // while(iss >> num) arr.push_back(num);
    
    // 4. Printing a single value:
    // cout << result << endl;
    
    // 5. Printing an array (space-separated):
    // for(int i = 0; i < arr.size(); i++) {
    //     cout << arr[i];
    //     if(i < arr.size()-1) cout << " ";
    // }
    // cout << endl;
    
    // Write your solution below:
    
    return 0;
}""",
    "java": """import java.util.*;
import java.io.*;

public class Solution {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        
        // ============================================
        // IMPORTANT: Read the problem description carefully!
        // - Check the Input Format section
        // - Check the Output Format section
        // - Match the exact format shown in Sample Output
        // ============================================
        
        // Common I/O patterns:
        
        // 1. Reading a single integer:
        // int n = Integer.parseInt(br.readLine());
        
        // 2. Reading an array:
        // String[] input = br.readLine().split(" ");
        // int[] arr = new int[input.length];
        // for(int i = 0; i < input.length; i++) {
        //     arr[i] = Integer.parseInt(input[i]);
        // }
        
        // 3. Reading multiple lines:
        // String line1 = br.readLine();
        // String line2 = br.readLine();
        
        // 4. Printing a single value:
        // System.out.println(result);
        
        // 5. Printing an array (space-separated):
        // for(int i = 0; i < arr.length; i++) {
        //     System.out.print(arr[i]);
        //     if(i < arr.length-1) System.out.print(" ");
        // }
        // System.out.println();
        
        // Write your solution below:
        
    }
}""",
    "javascript": """const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');

// ============================================
// IMPORTANT: Read the problem description carefully!
// - Check the Input Format section
// - Check the Output Format section
// - Match the exact format shown in Sample Output
// ============================================

// Common I/O patterns:

// 1. Reading first line as integer:
// const n = parseInt(input[0]);

// 2. Reading array from first line:
// const arr = input[0].split(' ').map(Number);

// 3. Reading multiple lines:
// const line1 = input[0];
// const line2 = input[1];

// 4. Printing a single value:
// console.log(result);

// 5. Printing an array (space-separated):
// console.log(arr.join(' '));  // Correct: "1 2 3"
// console.log(arr);  // Wrong: "[1,2,3]"

// Write your solution below:

""",
}


def _generate_function_based_starter_code(title: str, description: str, input_format: str) -> dict:
    """Generate function-based starter code where user only writes logic."""
    
    # Analyze the problem to determine function signature
    title_lower = title.lower()
    desc_lower = description.lower()
    input_lower = input_format.lower()
    
    print(f"[Starter] ========================================")
    print(f"[Starter] Analyzing: {title}")
    print(f"[Starter] Input format: {input_format[:150]}...")
    
    # Determine function name from title
    function_name = "solve"
    if "frequency" in title_lower or "count" in title_lower:
        function_name = "frequency" if "frequency" in title_lower else "countElements"
    elif "sum" in title_lower or "add" in title_lower:
        function_name = "calculateSum"
    elif "max" in title_lower or "maximum" in title_lower:
        function_name = "findMax"
    elif "min" in title_lower or "minimum" in title_lower:
        function_name = "findMin"
    elif "search" in title_lower or "find" in title_lower:
        function_name = "search"
    elif "sort" in title_lower:
        function_name = "sortArray"
    elif "reverse" in title_lower:
        function_name = "reverse"
    elif "palindrome" in title_lower:
        function_name = "isPalindrome"
    elif "anagram" in title_lower:
        function_name = "isAnagram"
    elif "substring" in title_lower:
        function_name = "findSubstring"
    elif "tree" in title_lower or "bst" in title_lower or "binary" in title_lower:
        function_name = "processTree"
    elif "graph" in title_lower:
        function_name = "processGraph"
    
    print(f"[Starter] Function name: {function_name}")
    
    # Analyze input format to determine parameters (STRICT PRIORITY ORDER)
    # 1. Check title/description for data structure keywords (highest priority)
    # IMPORTANT: Check graph BEFORE tree because graph questions might mention "nodes"
    graph_keywords = ["graph", "edge", "vertex", "vertices", "connected component", "shortest path", "cycle", "dag", "topological", "adjacency"]
    is_graph = any(keyword in title_lower for keyword in graph_keywords)
    is_graph = is_graph or any(keyword in desc_lower for keyword in graph_keywords)
    
    # Tree keywords - more specific to avoid false positives
    tree_keywords_title = ["tree", "bst", "binary search tree", "binary tree", "ancestor", "diameter", "tree depth", "tree height", "inorder", "preorder", "postorder", "level order"]
    tree_keywords_desc = ["binary tree", "bst", "binary search tree", "tree structure", "tree node", "ancestor", "diameter", "tree depth", "tree height", "inorder", "preorder", "postorder", "level order"]
    
    is_tree = any(keyword in title_lower for keyword in tree_keywords_title)
    is_tree = is_tree or any(keyword in desc_lower for keyword in tree_keywords_desc)
    
    # If both graph and tree detected, graph takes priority
    if is_graph:
        is_tree = False
    
    # 2. Check input format for specific patterns (more robust detection)
    # Two strings: Look for multiple string inputs
    two_string_patterns = [
        "two strings" in input_lower,
        input_lower.count("string") >= 2,
        ("first line" in input_lower and "second line" in input_lower and "string" in input_lower),
        ("line 1" in input_lower and "line 2" in input_lower and "string" in input_lower),
        ("first string" in input_lower and "second string" in input_lower),
        ("string a" in input_lower and "string b" in input_lower),
        ("string s1" in input_lower and "string s2" in input_lower),
    ]
    has_two_strings = any(two_string_patterns)
    
    # Matrix: Look for 2D structure indicators
    matrix_patterns = [
        "matrix" in input_lower,
        "grid" in input_lower,
        "2d array" in input_lower,
        "2-d array" in input_lower,
        ("rows" in input_lower and "columns" in input_lower),
        ("rows" in input_lower and "cols" in input_lower),
        ("row" in input_lower and "column" in input_lower and "next" in input_lower),
        ("m rows" in input_lower or "n rows" in input_lower),
        ("r rows" in input_lower and "c columns" in input_lower),
    ]
    has_matrix = any(matrix_patterns)
    
    # Single string: Must have string but not two strings or matrix
    string_patterns = [
        "string" in input_lower,
        "word" in input_lower,
        "text" in input_lower,
    ]
    has_string = any(string_patterns) and not has_two_strings and not has_matrix
    
    # Array: Look for array/list indicators
    array_patterns = [
        "array" in input_lower,
        "integers" in input_lower,
        "elements" in input_lower,
        "space-separated" in input_lower,
        "n integers" in input_lower,
        "n numbers" in input_lower,
        "n space-separated" in input_lower,
        ("second line" in input_lower and ("integers" in input_lower or "numbers" in input_lower)),
    ]
    has_array = any(array_patterns) and not has_matrix
    
    # Log detection with more detail
    print(f"[Starter] Detection Results:")
    print(f"[Starter]   - Tree: {is_tree}")
    print(f"[Starter]   - Graph: {is_graph}")
    print(f"[Starter]   - Two Strings: {has_two_strings}")
    print(f"[Starter]   - Matrix: {has_matrix}")
    print(f"[Starter]   - Single String: {has_string}")
    print(f"[Starter]   - Array: {has_array}")
    
    # Generate appropriate starter code based on input type (STRICT PRIORITY: graph > tree > two_strings > string > matrix > array > simple)
    if is_graph:
        print(f"[Starter] ✓ Generating GRAPH starter code")
        return _generate_graph_starter(function_name)
    elif is_tree:
        print(f"[Starter] ✓ Generating TREE starter code")
        return _generate_tree_starter(function_name)
    elif has_two_strings:
        print(f"[Starter] ✓ Generating TWO STRING starter code")
        return _generate_two_string_starter(function_name)
    elif has_string:
        print(f"[Starter] ✓ Generating STRING starter code")
        return _generate_string_starter(function_name)
    elif has_matrix:
        print(f"[Starter] ✓ Generating MATRIX starter code")
        return _generate_matrix_starter(function_name)
    elif has_array:
        print(f"[Starter] ✓ Generating ARRAY starter code")
        return _generate_array_starter(function_name)
    else:
        # Default: simple integer parameter
        print(f"[Starter] ✓ Generating SIMPLE starter code (default)")
        return _generate_simple_starter(function_name)


def _generate_array_starter(function_name: str) -> dict:
    """Generate starter code for array-based problems."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(vector<int>& arr) {{
    // Write your logic here
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    string line;
    getline(cin, line);
    istringstream iss(line);
    vector<int> arr;
    int num;
    while (iss >> num) {{
        arr.push_back(num);
    }}
    
    {function_name}(arr);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(arr):
    # Write your logic here
    pass

if __name__ == "__main__":
    arr = list(map(int, input().split()))
    {function_name}(arr)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(int[] arr) {{
        // Write your logic here
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String[] input = br.readLine().split(" ");
        int[] arr = new int[input.length];
        for(int i = 0; i < input.length; i++) {{
            arr[i] = Integer.parseInt(input[i]);
        }}
        
        {function_name}(arr);
    }}
}}"""
    
    js_code = f"""function {function_name}(arr) {{
    // Write your logic here
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim();
const arr = input.split(' ').map(Number);

{function_name}(arr);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_string_starter(function_name: str) -> dict:
    """Generate starter code for string-based problems."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(string s) {{
    // Write your logic here
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    string s;
    cin >> s;
    
    {function_name}(s);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(s):
    # Write your logic here
    pass

if __name__ == "__main__":
    s = input().strip()
    {function_name}(s)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(String s) {{
        // Write your logic here
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String s = br.readLine();
        
        {function_name}(s);
    }}
}}"""
    
    js_code = f"""function {function_name}(s) {{
    // Write your logic here
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim();
const s = input;

{function_name}(s);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_two_string_starter(function_name: str) -> dict:
    """Generate starter code for two-string problems (like anagram check)."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(string s1, string s2) {{
    // Write your logic here
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    string s1, s2;
    cin >> s1 >> s2;
    
    {function_name}(s1, s2);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(s1, s2):
    # Write your logic here
    pass

if __name__ == "__main__":
    s1 = input().strip()
    s2 = input().strip()
    {function_name}(s1, s2)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(String s1, String s2) {{
        // Write your logic here
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String s1 = br.readLine();
        String s2 = br.readLine();
        
        {function_name}(s1, s2);
    }}
}}"""
    
    js_code = f"""function {function_name}(s1, s2) {{
    // Write your logic here
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');
const s1 = input[0];
const s2 = input[1];

{function_name}(s1, s2);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_matrix_starter(function_name: str) -> dict:
    """Generate starter code for matrix/2D array problems."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(vector<vector<int>>& matrix, int rows, int cols) {{
    // Write your logic here
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int rows, cols;
    cin >> rows >> cols;
    
    vector<vector<int>> matrix(rows, vector<int>(cols));
    for(int i = 0; i < rows; i++) {{
        for(int j = 0; j < cols; j++) {{
            cin >> matrix[i][j];
        }}
    }}
    
    {function_name}(matrix, rows, cols);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(matrix, rows, cols):
    # Write your logic here
    pass

if __name__ == "__main__":
    rows, cols = map(int, input().split())
    matrix = []
    for _ in range(rows):
        row = list(map(int, input().split()))
        matrix.append(row)
    {function_name}(matrix, rows, cols)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(int[][] matrix, int rows, int cols) {{
        // Write your logic here
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String[] dims = br.readLine().split(" ");
        int rows = Integer.parseInt(dims[0]);
        int cols = Integer.parseInt(dims[1]);
        
        int[][] matrix = new int[rows][cols];
        for(int i = 0; i < rows; i++) {{
            String[] row = br.readLine().split(" ");
            for(int j = 0; j < cols; j++) {{
                matrix[i][j] = Integer.parseInt(row[j]);
            }}
        }}
        
        {function_name}(matrix, rows, cols);
    }}
}}"""
    
    js_code = f"""function {function_name}(matrix, rows, cols) {{
    // Write your logic here
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');
const [rows, cols] = input[0].split(' ').map(Number);
const matrix = [];
for(let i = 1; i <= rows; i++) {{
    matrix.push(input[i].split(' ').map(Number));
}}

{function_name}(matrix, rows, cols);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_tree_starter(function_name: str) -> dict:
    """Generate starter code for tree problems."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(int arr[], int n) {{
    // Write your logic here
    // arr contains tree node values
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    cin >> n;
    int arr[n];
    for(int i = 0; i < n; i++) {{
        cin >> arr[i];
    }}
    
    {function_name}(arr, n);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(arr, n):
    # Write your logic here
    # arr contains tree node values
    pass

if __name__ == "__main__":
    n = int(input())
    arr = list(map(int, input().split()))
    {function_name}(arr, n)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(int[] arr, int n) {{
        // Write your logic here
        // arr contains tree node values
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        int n = Integer.parseInt(br.readLine());
        String[] input = br.readLine().split(" ");
        int[] arr = new int[n];
        for(int i = 0; i < n; i++) {{
            arr[i] = Integer.parseInt(input[i]);
        }}
        
        {function_name}(arr, n);
    }}
}}"""
    
    js_code = f"""function {function_name}(arr, n) {{
    // Write your logic here
    // arr contains tree node values
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');
const n = parseInt(input[0]);
const arr = input[1].split(' ').map(Number);

{function_name}(arr, n);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_graph_starter(function_name: str) -> dict:
    """Generate starter code for graph problems."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(vector<pair<int,int>>& edges, int n, int m) {{
    // Write your logic here
    // edges contains graph edges
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n, m;
    cin >> n >> m;
    
    vector<pair<int,int>> edges;
    for(int i = 0; i < m; i++) {{
        int u, v;
        cin >> u >> v;
        edges.push_back({{u, v}});
    }}
    
    {function_name}(edges, n, m);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(edges, n, m):
    # Write your logic here
    # edges contains graph edges
    pass

if __name__ == "__main__":
    n, m = map(int, input().split())
    edges = []
    for _ in range(m):
        u, v = map(int, input().split())
        edges.append((u, v))
    {function_name}(edges, n, m)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(List<int[]> edges, int n, int m) {{
        // Write your logic here
        // edges contains graph edges
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String[] nm = br.readLine().split(" ");
        int n = Integer.parseInt(nm[0]);
        int m = Integer.parseInt(nm[1]);
        
        List<int[]> edges = new ArrayList<>();
        for(int i = 0; i < m; i++) {{
            String[] edge = br.readLine().split(" ");
            int u = Integer.parseInt(edge[0]);
            int v = Integer.parseInt(edge[1]);
            edges.add(new int[]{{u, v}});
        }}
        
        {function_name}(edges, n, m);
    }}
}}"""
    
    js_code = f"""function {function_name}(edges, n, m) {{
    // Write your logic here
    // edges contains graph edges
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');
const [n, m] = input[0].split(' ').map(Number);
const edges = [];
for(let i = 1; i <= m; i++) {{
    const [u, v] = input[i].split(' ').map(Number);
    edges.push([u, v]);
}}

{function_name}(edges, n, m);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }


def _generate_simple_starter(function_name: str) -> dict:
    """Generate starter code for simple problems (single integer, etc.)."""
    cpp_code = f"""#include <bits/stdc++.h>
using namespace std;

void {function_name}(int n) {{
    // Write your logic here
    
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    cin >> n;
    
    {function_name}(n);
    
    return 0;
}}"""
    
    python_code = f"""def {function_name}(n):
    # Write your logic here
    pass

if __name__ == "__main__":
    n = int(input())
    {function_name}(n)"""
    
    java_code = f"""import java.util.*;
import java.io.*;

public class Solution {{
    
    public static void {function_name}(int n) {{
        // Write your logic here
        
    }}
    
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        int n = Integer.parseInt(br.readLine());
        
        {function_name}(n);
    }}
}}"""
    
    js_code = f"""function {function_name}(n) {{
    // Write your logic here
    
}}

const fs = require('fs');
const input = fs.readFileSync('/dev/stdin', 'utf8').trim();
const n = parseInt(input);

{function_name}(n);"""
    
    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code
    }

DIFFICULTY_HINTS = {
    DifficultyLevel.EASY: (
        "EASY: Single loop or simple conditionals. "
        "Examples: array traversal, string manipulation, basic math, counting. "
        "O(n) or O(n²) solutions are fine."
    ),
    DifficultyLevel.MEDIUM: (
        "MEDIUM: Must involve at least one of: "
        "dynamic programming, binary search, two pointers, sliding window, "
        "stack/queue tricks, graph BFS/DFS, greedy, or prefix sums. "
        "NOT just a simple loop. Aim for O(n log n) or O(n)."
    ),
    DifficultyLevel.HARD: (
        "HARD: Must involve advanced algorithms: "
        "segment trees, Fenwick trees, advanced DP (bitmask/digit/tree), "
        "Dijkstra on complex graphs, network flow, convex hull trick, or trie."
    ),
}


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except Exception:
            pass

    if start != -1:
        candidate = text[start:]
        for suffix in ['"}}}', '"}}', '"}', "}}}", "}}", "}"]:
            try:
                return json.loads(candidate + suffix)
            except Exception:
                pass
        last_comma = candidate.rfind(",")
        if last_comma > 0:
            trimmed = candidate[:last_comma]
            for suffix in ["}}}", "}}", "}"]:
                try:
                    return json.loads(trimmed + suffix)
                except Exception:
                    pass

    raise ValueError("Could not extract JSON from model response")


class AIQuestionGenerator:
    def __init__(self):
        self.base_url = settings.AI_SERVICE_URL.rstrip("/")
        self.timeout = settings.AI_SERVICE_TIMEOUT
        # Rotating index for fallback pool cycling: { "difficulty_topic" -> int }
        self._last_indices: dict[str, int] = {}

    def _get_topics(self) -> list[str]:
        """Return topics from cache or a hardcoded default list.
        We no longer make a synchronous HTTP call here — that was blocking
        the event loop every time topic=None. The AI service topics list
        never changes at runtime, so a static default is fine.
        """
        return [
            "arrays", "strings", "linked-lists", "trees", "graphs",
            "dynamic-programming", "sorting", "searching", "hashing",
            "greedy", "backtracking", "recursion", "stacks", "queues",
            "two-pointers", "sliding-window", "math", "bit-manipulation",
        ]

    async def generate_question(
        self,
        difficulty: DifficultyLevel,
        topic: Optional[str] = None,
        num_test_cases: int = None,
        description: Optional[str] = None,
        exclude_titles: list = None,
        player_ids: list = None,
    ) -> dict:
        # Randomize test case count by difficulty if not specified
        if num_test_cases is None:
            if difficulty == DifficultyLevel.EASY:
                num_test_cases = random.randint(5, 8)
            elif difficulty == DifficultyLevel.MEDIUM:
                num_test_cases = random.randint(7, 10)
            else:  # HARD
                num_test_cases = random.randint(9, 12)
        if topic is None:
            topics = self._get_topics()
            topic = random.choice(topics)

        excluded = [t.lower().strip() for t in (exclude_titles or []) if t]

        # Try the AI service once (it already retries internally up to 50 times).
        # A single async call is enough — no need to loop here and multiply latency.
        data = await self._call_ai_service(
            topic, difficulty.value, num_test_cases,
            exclude_titles=excluded, player_ids=player_ids,
        )

        if data is None:
            # AI service down or returned a duplicate — use local fallback immediately
            data = self._fallback_question(difficulty, topic, num_test_cases, exclude_titles=excluded)
            print(f"[ai] Using fallback: {data.get('title')}")

        return await _build_result(data, difficulty, topic)

    async def _call_ai_service(
        self,
        topic: str,
        difficulty: str,
        num_test_cases: int,
        exclude_titles: list = None,
        player_ids: list = None,
    ) -> dict | None:
        """Call the AI service asynchronously. Returns None if unavailable.

        player_ids are the players who will see the question; the service keeps its own per-player history of what it served (in Redis when
        it has one), so it does not repeat a question for them even when the titles in exclude_titles do not say so."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generate",
                    json={
                        "topic": topic,
                        "difficulty": difficulty,
                        "num_test_cases": num_test_cases,
                        "exclude_titles": exclude_titles or [],
                        "player_ids": [str(p) for p in (player_ids or [])] or None,
                    },
                )
            if response.is_success:
                data = response.json()
                print(f"[ai] Generated: {data.get('title', 'Unknown')}")
                return data
        except Exception as e:
            print(f"[ai] Service call failed: {e}")

        return None

    def _fallback_question(self, difficulty, topic, num_test_cases, exclude_titles: list = None) -> dict:
        # Try question_db first — real questions with correct topic/difficulty/TC counts
        try:
            import sys, os
            _ai_backend = os.path.join(
                os.path.dirname(__file__), '..', '..', '..',
                'question-service'
            )
            if _ai_backend not in sys.path:
                sys.path.insert(0, os.path.abspath(_ai_backend))
            from model.question_db import get_question as _db_get
            diff_str = difficulty.value if hasattr(difficulty, 'value') else str(difficulty).lower()
            q = _db_get(
                topic=topic or 'arrays',
                difficulty=diff_str,
                exclude_titles=exclude_titles or [],
            )
            if q:
                # Return raw fields — _build_result handles all formatting
                # so the function signature and starter code are always correct
                desc = q.get('problem_statement', q.get('description', ''))
                inp_fmt     = q.get('input_format', '')
                out_fmt     = q.get('output_format', '')
                constraints = q.get('constraints', '')
                sample_in   = q.get('sample_input', '')
                sample_out  = q.get('sample_output', '')
                tcs         = q.get('test_cases', [])
                si = sample_in or (tcs[0].get('input', '') if tcs else '')
                so = sample_out or (tcs[0].get('output', '') if tcs else '')

                return {
                    'title':         q.get('title', ''),
                    'description':   desc,   # raw body only — _build_result appends sections
                    'input_format':  inp_fmt,
                    'output_format': out_fmt,
                    'constraints':   constraints,
                    'sample_input':  si,
                    'sample_output': so,
                    'topic':         q.get('topic', topic or 'general'),
                    'test_cases':    tcs,
                }
        except Exception as e:
            print(f'[ai] question_db fallback failed: {e}')

        return self._topic_aware_fallback(difficulty, topic, num_test_cases, exclude_titles=exclude_titles)

    def _topic_aware_fallback(self, difficulty, topic, num_test_cases, exclude_titles: list = None) -> dict:
        # Accept difficulty as either a DifficultyLevel enum or a plain string
        if isinstance(difficulty, str):
            try:
                difficulty = DifficultyLevel(difficulty.lower())
            except ValueError:
                difficulty = DifficultyLevel.MEDIUM
        t = topic.lower().strip() if topic else ""

        # ── STRINGS ──────────────────────────────────────────────────────────
        if any(k in t for k in ["string", "str", "palindrome", "anagram", "substring"]):
            easy_pool = [
                {
                    "title": "Reverse a String",
                    "description": "Given a string **S**, print it in reverse order.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5).",
                    "output_format": "Print the reversed string.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "hello", "output": "olleh"},
                        {"input": "abcde", "output": "edcba"},
                        {"input": "a", "output": "a"},
                        {"input": "racecar", "output": "racecar"},
                        {"input": "OpenAI", "output": "IAnepO"},
                    ],
                },
                {
                    "title": "Check Palindrome",
                    "description": "Given a string **S**, determine if it is a palindrome (reads the same forwards and backwards).",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5, lowercase letters only).",
                    "output_format": "Print YES if S is a palindrome, otherwise NO.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "racecar", "output": "YES"},
                        {"input": "hello", "output": "NO"},
                        {"input": "a", "output": "YES"},
                        {"input": "abba", "output": "YES"},
                        {"input": "abc", "output": "NO"},
                    ],
                },
                {
                    "title": "Count Vowels",
                    "description": "Given a string **S**, count the number of vowels (a, e, i, o, u) in it.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5, lowercase letters only).",
                    "output_format": "Print a single integer — the number of vowels.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "hello", "output": "2"},
                        {"input": "aeiou", "output": "5"},
                        {"input": "bcdfg", "output": "0"},
                        {"input": "programming", "output": "3"},
                        {"input": "a", "output": "1"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Longest Palindromic Substring",
                    "description": "Given a string **S**, find the longest substring that is a palindrome. If multiple answers exist, print the first one.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 1000, lowercase letters only).",
                    "output_format": "Print the longest palindromic substring.",
                    "constraints": "1 ≤ |S| ≤ 1000",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "babad", "output": "bab"},
                        {"input": "cbbd", "output": "bb"},
                        {"input": "a", "output": "a"},
                        {"input": "racecar", "output": "racecar"},
                        {"input": "abcba", "output": "abcba"},
                        {"input": "abacaba", "output": "abacaba"},
                        {"input": "noon", "output": "noon"},
                        {"input": "abcd", "output": "a"},
                    ],
                },
                {
                    "title": "Anagram Check",
                    "description": "Given two strings **A** and **B**, determine if B is an anagram of A.",
                    "input_format": "First line: string A.\nSecond line: string B.",
                    "output_format": "Print YES if B is an anagram of A, otherwise NO.",
                    "constraints": "1 ≤ |A|, |B| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "listen\nsilent", "output": "YES"},
                        {"input": "hello\nworld", "output": "NO"},
                        {"input": "abc\ncba", "output": "YES"},
                        {"input": "rat\ncar", "output": "NO"},
                        {"input": "anagram\nnagaram", "output": "YES"},
                        {"input": "a\na", "output": "YES"},
                        {"input": "ab\nba", "output": "YES"},
                        {"input": "abc\nabc", "output": "YES"},
                    ],
                },
                {
                    "title": "Longest Common Prefix",
                    "description": "Given **N** strings, find the longest common prefix among all of them.",
                    "input_format": "First line: integer N.\nNext N lines: one string each.",
                    "output_format": "Print the longest common prefix, or an empty line if none exists.",
                    "constraints": "1 ≤ N ≤ 200\n1 ≤ |S| ≤ 200",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "3\nflower\nflow\nflight", "output": "fl"},
                        {"input": "3\ndog\nracecar\ncar", "output": ""},
                        {"input": "2\nabc\nabc", "output": "abc"},
                        {"input": "1\nhello", "output": "hello"},
                        {"input": "3\ninterspecies\ninterstellar\ninteractive", "output": "inter"},
                        {"input": "2\nprefix\npre", "output": "pre"},
                        {"input": "4\nabc\nabd\nabe\nabf", "output": "ab"},
                        {"input": "2\nxyz\nabc", "output": ""},
                    ],
                },
                {
                    "title": "Group Anagrams",
                    "description": "Given **N** strings, group the anagrams together. Print each group on a separate line with words sorted alphabetically within the group, and groups sorted by their first word.",
                    "input_format": "First line: integer N.\nNext N lines: one string each (lowercase letters only).",
                    "output_format": "Print each anagram group on one line, words separated by spaces. Sort words within each group alphabetically. Sort groups by their first word.",
                    "constraints": "1 ≤ N ≤ 1000\n1 ≤ |S| ≤ 100",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "6\neat\ntea\ntan\nate\nnat\nbat", "output": "ate eat tea\nbat\nnat tan"},
                        {"input": "1\na", "output": "a"},
                        {"input": "2\nab\nba", "output": "ab ba"},
                        {"input": "3\nabc\nbca\ncab", "output": "abc bca cab"},
                        {"input": "4\ncat\nact\ntac\ndog", "output": "act cat tac\ndog"},
                        {"input": "2\nhello\nworld", "output": "hello\nworld"},
                        {"input": "3\nlisten\nsilent\nenlist", "output": "enlist listen silent"},
                        {"input": "1\nz", "output": "z"},
                    ],
                },
                {
                    "title": "Longest Substring Without Repeating Characters",
                    "description": "Given a string **S**, find the length of the longest substring without repeating characters.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5).",
                    "output_format": "Print a single integer — the length of the longest substring without repeating characters.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "abcabcbb", "output": "3"},
                        {"input": "bbbbb", "output": "1"},
                        {"input": "pwwkew", "output": "3"},
                        {"input": "a", "output": "1"},
                        {"input": "abcdef", "output": "6"},
                        {"input": "dvdf", "output": "3"},
                        {"input": "aab", "output": "2"},
                        {"input": "tmmzuxt", "output": "5"},
                    ],
                },
                {
                    "title": "String Compression",
                    "description": "Given a string **S** of lowercase letters, compress it using run-length encoding. For each group of consecutive identical characters, output the character followed by its count. If the compressed string is not shorter than the original, output the original string.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5, lowercase letters only).",
                    "output_format": "Print the compressed string, or the original if compression doesn't reduce length.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "aabcccccaaa", "output": "a2b1c5a3"},
                        {"input": "abcd", "output": "abcd"},
                        {"input": "aabb", "output": "aabb"},
                        {"input": "aaabbb", "output": "a3b3"},
                        {"input": "a", "output": "a"},
                        {"input": "aaaaaaa", "output": "a7"},
                        {"input": "aabbcc", "output": "aabbcc"},
                        {"input": "aaabbaaa", "output": "a3b2a3"},
                    ],
                },
                {
                    "title": "Valid Parentheses String",
                    "description": "Given a string **S** containing only '(', ')', and '*', determine if it is valid. '*' can be treated as '(', ')' or an empty string.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 100).",
                    "output_format": "Print YES if the string is valid, otherwise NO.",
                    "constraints": "1 ≤ |S| ≤ 100",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "()", "output": "YES"},
                        {"input": "(*)", "output": "YES"},
                        {"input": "(*))", "output": "YES"},
                        {"input": "(((*", "output": "NO"},
                        {"input": "*", "output": "YES"},
                        {"input": "(**)", "output": "YES"},
                        {"input": ")*(", "output": "NO"},
                        {"input": "((()))", "output": "YES"},
                    ],
                },
                {
                    "title": "Zigzag String Conversion",
                    "description": "Given a string **S** and integer **N**, write the string in a zigzag pattern on N rows, then read it row by row.",
                    "input_format": "First line: string S.\nSecond line: integer N (number of rows).",
                    "output_format": "Print the zigzag-converted string.",
                    "constraints": "1 ≤ |S| ≤ 1000\n1 ≤ N ≤ 1000",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "PAYPALISHIRING\n3", "output": "PAHNAPLSIIGYIR"},
                        {"input": "PAYPALISHIRING\n4", "output": "PINALSIGYAHRPI"},
                        {"input": "A\n1", "output": "A"},
                        {"input": "AB\n1", "output": "AB"},
                        {"input": "ABCDE\n2", "output": "ACEBD"},
                        {"input": "ABCDEF\n3", "output": "AEBDFC"},
                        {"input": "ABCDEFGH\n3", "output": "AEBDFHCG"},
                        {"input": "HELLO\n2", "output": "HLOEL"},
                    ],
                },
            ]
            hard_pool = [
                {
                    "title": "Minimum Window Substring",
                    "description": "Given strings **S** and **T**, find the minimum window in S that contains all characters of T. If no such window exists, print -1.",
                    "input_format": "First line: string S.\nSecond line: string T.",
                    "output_format": "Print the minimum window substring, or -1 if not found.",
                    "constraints": "1 ≤ |S|, |T| ≤ 10^5",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "ADOBECODEBANC\nABC", "output": "BANC"},
                        {"input": "a\na", "output": "a"},
                        {"input": "a\nb", "output": "-1"},
                        {"input": "aa\naa", "output": "aa"},
                        {"input": "ADOBECODEBANC\nABC", "output": "BANC"},
                        {"input": "ab\nb", "output": "b"},
                        {"input": "bba\nab", "output": "ba"},
                        {"input": "cabwefgewcwaefgcf\ncae", "output": "cwae"},
                    ],
                },
                {
                    "title": "Count Distinct Substrings",
                    "description": "Given a string **S**, count the number of distinct non-empty substrings.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 500, lowercase letters only).",
                    "output_format": "Print a single integer — the number of distinct substrings.",
                    "constraints": "1 ≤ |S| ≤ 500",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "abc", "output": "6"},
                        {"input": "aaa", "output": "3"},
                        {"input": "ab", "output": "3"},
                        {"input": "a", "output": "1"},
                        {"input": "abab", "output": "7"},
                        {"input": "abcd", "output": "10"},
                        {"input": "aa", "output": "2"},
                        {"input": "aba", "output": "5"},
                    ],
                },
                {
                    "title": "Longest Repeating Character Replacement",
                    "description": "Given a string **S** and integer **K**, find the length of the longest substring containing the same letter after replacing at most K characters.",
                    "input_format": "First line: string S (uppercase letters only).\nSecond line: integer K.",
                    "output_format": "Print a single integer — the length of the longest valid substring.",
                    "constraints": "1 ≤ |S| ≤ 10^5\n0 ≤ K ≤ |S|",
                    "topic": "strings",
                    "test_cases": [
                        {"input": "ABAB\n2", "output": "4"},
                        {"input": "AABABBA\n1", "output": "4"},
                        {"input": "AAAA\n0", "output": "4"},
                        {"input": "ABCD\n2", "output": "3"},
                        {"input": "A\n0", "output": "1"},
                        {"input": "AABBBBA\n2", "output": "6"},
                        {"input": "ABCDE\n1", "output": "2"},
                        {"input": "AAABBBCCC\n3", "output": "6"},
                    ],
                },
            ]

        # ── LINKED LISTS ─────────────────────────────────────────────────────
        elif any(k in t for k in ["linked", "list", "node"]):
            easy_pool = [
                {
                    "title": "Reverse a Linked List",
                    "description": "Given a linked list of **N** nodes, reverse it and print the values.",
                    "input_format": "First line: N.\nSecond line: N space-separated node values.",
                    "output_format": "Print the reversed linked list values.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "5\n1 2 3 4 5", "output": "5 4 3 2 1"},
                        {"input": "1\n42", "output": "42"},
                        {"input": "3\n10 20 30", "output": "30 20 10"},
                        {"input": "4\n1 2 3 4", "output": "4 3 2 1"},
                        {"input": "2\n5 10", "output": "10 5"},
                        {"input": "6\n1 2 3 4 5 6", "output": "6 5 4 3 2 1"},
                        {"input": "3\n-1 0 1", "output": "1 0 -1"},
                        {"input": "7\n7 6 5 4 3 2 1", "output": "1 2 3 4 5 6 7"},
                    ],
                },
                {
                    "title": "Sum of Linked List",
                    "description": "Given a linked list of **N** integers, compute and print the sum of all node values.",
                    "input_format": "First line: N.\nSecond line: N space-separated node values.",
                    "output_format": "Print a single integer — the sum.",
                    "constraints": "1 ≤ N ≤ 10^5\n-10^9 ≤ val ≤ 10^9",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "5\n1 2 3 4 5", "output": "15"},
                        {"input": "1\n100", "output": "100"},
                        {"input": "3\n-1 0 1", "output": "0"},
                        {"input": "4\n10 20 30 40", "output": "100"},
                        {"input": "2\n-5 5", "output": "0"},
                        {"input": "3\n7 8 9", "output": "24"},
                        {"input": "1\n0", "output": "0"},
                        {"input": "4\n1 1 1 1", "output": "4"},
                    ],
                },
                {
                    "title": "Find Nth Node from End",
                    "description": "Given a linked list of **N** nodes and an integer **K**, find the value of the Kth node from the end.",
                    "input_format": "First line: N and K.\nSecond line: N space-separated node values.",
                    "output_format": "Print the value of the Kth node from the end.",
                    "constraints": "1 ≤ K ≤ N ≤ 10^5",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "5 2\n1 2 3 4 5", "output": "4"},
                        {"input": "5 1\n1 2 3 4 5", "output": "5"},
                        {"input": "5 5\n1 2 3 4 5", "output": "1"},
                        {"input": "3 2\n10 20 30", "output": "20"},
                        {"input": "1 1\n42", "output": "42"},
                        {"input": "4 3\n1 2 3 4", "output": "2"},
                        {"input": "6 4\n1 2 3 4 5 6", "output": "3"},
                        {"input": "2 1\n5 10", "output": "10"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Detect Cycle in Linked List",
                    "description": "Given a linked list of **N** nodes, determine if it contains a cycle. The last node's next pointer is given as -1 (no cycle) or an index (cycle, 0-indexed).",
                    "input_format": "First line: N.\nSecond line: N node values.\nThird line: index where last node points (-1 for no cycle).",
                    "output_format": "Print YES if cycle exists, otherwise NO.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "5\n1 2 3 4 5\n1", "output": "YES"},
                        {"input": "3\n1 2 3\n-1", "output": "NO"},
                        {"input": "1\n1\n-1", "output": "NO"},
                        {"input": "4\n1 2 3 4\n0", "output": "YES"},
                        {"input": "2\n1 2\n-1", "output": "NO"},
                        {"input": "3\n1 2 3\n0", "output": "YES"},
                        {"input": "5\n1 2 3 4 5\n-1", "output": "NO"},
                        {"input": "4\n1 2 3 4\n2", "output": "YES"},
                    ],
                },
                {
                    "title": "Find Middle of Linked List",
                    "description": "Given a linked list of **N** nodes, find and print the middle node's value. If two middle nodes exist, print the second one.",
                    "input_format": "First line: N.\nSecond line: N space-separated node values.",
                    "output_format": "Print the middle node value.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "5\n1 2 3 4 5", "output": "3"},
                        {"input": "6\n1 2 3 4 5 6", "output": "4"},
                        {"input": "1\n42", "output": "42"},
                        {"input": "3\n10 20 30", "output": "20"},
                        {"input": "4\n1 2 3 4", "output": "3"},
                        {"input": "7\n1 2 3 4 5 6 7", "output": "4"},
                        {"input": "2\n5 10", "output": "10"},
                        {"input": "9\n1 2 3 4 5 6 7 8 9", "output": "5"},
                    ],
                },
                {
                    "title": "Merge Two Sorted Linked Lists",
                    "description": "Given two sorted linked lists of sizes **N** and **M**, merge them into a single sorted linked list and print the values.",
                    "input_format": "First line: N and M.\nSecond line: N sorted integers (first list).\nThird line: M sorted integers (second list).",
                    "output_format": "Print the merged sorted list values.",
                    "constraints": "1 ≤ N, M ≤ 10^5",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "3 3\n1 3 5\n2 4 6", "output": "1 2 3 4 5 6"},
                        {"input": "2 2\n1 2\n3 4", "output": "1 2 3 4"},
                        {"input": "1 1\n5\n5", "output": "5 5"},
                        {"input": "3 1\n1 2 3\n4", "output": "1 2 3 4"},
                        {"input": "2 3\n1 4\n2 3 5", "output": "1 2 3 4 5"},
                        {"input": "1 3\n2\n1 3 4", "output": "1 2 3 4"},
                        {"input": "3 3\n1 2 3\n4 5 6", "output": "1 2 3 4 5 6"},
                        {"input": "2 2\n1 3\n2 4", "output": "1 2 3 4"},
                    ],
                },
                {
                    "title": "Remove Duplicates from Sorted Linked List",
                    "description": "Given a sorted linked list of **N** nodes, remove all duplicate values and print the resulting list.",
                    "input_format": "First line: N.\nSecond line: N space-separated sorted integers.",
                    "output_format": "Print the deduplicated list values.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "linked-lists",
                    "test_cases": [
                        {"input": "6\n1 1 2 3 3 4", "output": "1 2 3 4"},
                        {"input": "5\n1 1 1 1 1", "output": "1"},
                        {"input": "3\n1 2 3", "output": "1 2 3"},
                        {"input": "4\n1 1 2 2", "output": "1 2"},
                        {"input": "1\n5", "output": "5"},
                        {"input": "5\n1 2 2 3 4", "output": "1 2 3 4"},
                        {"input": "6\n1 1 1 2 2 3", "output": "1 2 3"},
                        {"input": "4\n1 2 3 4", "output": "1 2 3 4"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── TREES ─────────────────────────────────────────────────────────────
        elif any(k in t for k in ["tree", "bst", "binary", "trie"]):
            easy_pool = [
                {
                    "title": "Height of Binary Tree",
                    "description": "Given a binary tree with **N** nodes, find its height (number of edges on the longest root-to-leaf path).",
                    "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
                    "output_format": "Print a single integer — the height of the tree.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "2"},
                        {"input": "1", "output": "0"},
                        {"input": "3\n1 2\n2 3", "output": "2"},
                        {"input": "3\n1 2\n1 3", "output": "1"},
                        {"input": "4\n1 2\n2 3\n3 4", "output": "3"},
                        {"input": "2\n1 2", "output": "1"},
                        {"input": "6\n1 2\n1 3\n2 4\n2 5\n3 6", "output": "2"},
                        {"input": "4\n1 2\n1 3\n3 4", "output": "2"},
                    ],
                },
                {
                    "title": "Count Leaf Nodes",
                    "description": "Given a binary tree with **N** nodes, count the number of leaf nodes (nodes with no children).",
                    "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
                    "output_format": "Print a single integer — the number of leaf nodes.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "3"},
                        {"input": "1", "output": "1"},
                        {"input": "3\n1 2\n1 3", "output": "2"},
                        {"input": "3\n1 2\n2 3", "output": "1"},
                        {"input": "4\n1 2\n2 3\n3 4", "output": "1"},
                        {"input": "6\n1 2\n1 3\n2 4\n2 5\n3 6", "output": "3"},
                        {"input": "2\n1 2", "output": "1"},
                        {"input": "7\n1 2\n1 3\n2 4\n2 5\n3 6\n3 7", "output": "4"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Level Order Traversal",
                    "description": "Given a binary tree, print its nodes level by level from left to right.",
                    "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
                    "output_format": "Print nodes level by level, each level on a new line.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "1\n2 3\n4 5"},
                        {"input": "1", "output": "1"},
                        {"input": "3\n1 2\n1 3", "output": "1\n2 3"},
                        {"input": "3\n1 2\n2 3", "output": "1\n2\n3"},
                        {"input": "4\n1 2\n1 3\n3 4", "output": "1\n2 3\n4"},
                        {"input": "2\n1 2", "output": "1\n2"},
                        {"input": "6\n1 2\n1 3\n2 4\n2 5\n3 6", "output": "1\n2 3\n4 5 6"},
                        {"input": "4\n1 2\n2 3\n3 4", "output": "1\n2\n3\n4"},
                    ],
                },
                {
                    "title": "Lowest Common Ancestor",
                    "description": "Given a binary tree and two nodes **U** and **V**, find their Lowest Common Ancestor (LCA).",
                    "input_format": "First line: N.\nNext N-1 lines: parent child pairs.\nLast line: U and V.",
                    "output_format": "Print the node value of the LCA.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2\n1 3\n2 4\n2 5\n4 3", "output": "1"},
                        {"input": "3\n1 2\n1 3\n2 3", "output": "1"},
                        {"input": "4\n1 2\n2 3\n2 4\n3 4", "output": "2"},
                        {"input": "3\n1 2\n2 3\n1 3", "output": "1"},
                        {"input": "5\n1 2\n1 3\n2 4\n2 5\n4 5", "output": "2"},
                        {"input": "4\n1 2\n1 3\n3 4\n2 4", "output": "1"},
                        {"input": "3\n1 2\n2 3\n2 3", "output": "2"},
                        {"input": "5\n1 2\n1 3\n2 4\n3 5\n4 5", "output": "1"},
                    ],
                },
                {
                    "title": "Diameter of Binary Tree",
                    "description": "Given a binary tree with **N** nodes, find its diameter — the length of the longest path between any two nodes (measured in edges).",
                    "input_format": "First line: N.\nNext N-1 lines: parent child pairs.",
                    "output_format": "Print a single integer — the diameter.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2\n1 3\n2 4\n2 5", "output": "3"},
                        {"input": "1", "output": "0"},
                        {"input": "3\n1 2\n1 3", "output": "2"},
                        {"input": "3\n1 2\n2 3", "output": "2"},
                        {"input": "5\n1 2\n2 3\n3 4\n4 5", "output": "4"},
                        {"input": "4\n1 2\n1 3\n3 4", "output": "3"},
                        {"input": "2\n1 2", "output": "1"},
                        {"input": "6\n1 2\n1 3\n2 4\n2 5\n3 6", "output": "4"},
                    ],
                },
                {
                    "title": "Inorder Traversal",
                    "description": "Given a binary tree with **N** nodes, print its inorder traversal (left, root, right).",
                    "input_format": "First line: N.\nNext N-1 lines: parent child direction pairs (parent child L/R).",
                    "output_format": "Print the inorder traversal values separated by spaces.",
                    "constraints": "1 ≤ N ≤ 10^4",
                    "topic": "trees",
                    "test_cases": [
                        {"input": "5\n1 2 L\n1 3 R\n2 4 L\n2 5 R", "output": "4 2 5 1 3"},
                        {"input": "1", "output": "1"},
                        {"input": "3\n1 2 L\n1 3 R", "output": "2 1 3"},
                        {"input": "3\n1 2 L\n2 3 L", "output": "3 2 1"},
                        {"input": "3\n1 2 R\n2 3 R", "output": "1 2 3"},
                        {"input": "4\n1 2 L\n1 3 R\n3 4 L", "output": "2 1 4 3"},
                        {"input": "2\n1 2 L", "output": "2 1"},
                        {"input": "2\n1 2 R", "output": "1 2"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── GRAPHS ────────────────────────────────────────────────────────────
        elif any(k in t for k in ["graph", "bfs", "dfs", "path", "cycle"]):
            easy_pool = [
                {
                    "title": "Number of Connected Components",
                    "description": "Given an undirected graph with **N** nodes and **M** edges, find the number of connected components.",
                    "input_format": "First line: N and M.\nNext M lines: two integers u and v representing an edge.",
                    "output_format": "Print a single integer — the number of connected components.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ M ≤ 2×10^5",
                    "topic": "graphs",
                    "test_cases": [
                        {"input": "5 3\n1 2\n2 3\n4 5", "output": "2"},
                        {"input": "4 0", "output": "4"},
                        {"input": "3 3\n1 2\n2 3\n1 3", "output": "1"},
                        {"input": "6 2\n1 2\n3 4", "output": "4"},
                        {"input": "1 0", "output": "1"},
                        {"input": "5 5\n1 2\n2 3\n3 4\n4 5\n5 1", "output": "1"},
                        {"input": "4 2\n1 2\n3 4", "output": "2"},
                        {"input": "6 4\n1 2\n2 3\n4 5\n5 6", "output": "2"},
                    ],
                },
                {
                    "title": "BFS Traversal Order",
                    "description": "Given an undirected graph with **N** nodes and **M** edges, print the BFS traversal starting from node 1.",
                    "input_format": "First line: N and M.\nNext M lines: two integers u and v representing an edge.",
                    "output_format": "Print the BFS traversal order, space-separated.",
                    "constraints": "1 ≤ N ≤ 10^4\n0 ≤ M ≤ 2×10^4",
                    "topic": "graphs",
                    "test_cases": [
                        {"input": "4 4\n1 2\n1 3\n2 4\n3 4", "output": "1 2 3 4"},
                        {"input": "3 2\n1 2\n2 3", "output": "1 2 3"},
                        {"input": "1 0", "output": "1"},
                        {"input": "4 3\n1 2\n1 3\n1 4", "output": "1 2 3 4"},
                        {"input": "5 4\n1 2\n2 3\n3 4\n4 5", "output": "1 2 3 4 5"},
                        {"input": "3 3\n1 2\n2 3\n1 3", "output": "1 2 3"},
                        {"input": "4 2\n1 2\n3 4", "output": "1 2"},
                        {"input": "5 5\n1 2\n1 3\n2 4\n2 5\n3 5", "output": "1 2 3 4 5"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Shortest Path in Unweighted Graph",
                    "description": "Given an undirected unweighted graph with **N** nodes and **M** edges, find the shortest path from node **S** to node **D**.",
                    "input_format": "First line: N, M, S, D.\nNext M lines: two integers u and v representing an edge.",
                    "output_format": "Print the shortest path length or -1 if unreachable.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ M ≤ 2×10^5",
                    "topic": "general",
                    "test_cases": [
                        {"input": "5 4 1 5\n1 2\n2 3\n3 4\n4 5", "output": "4"},
                        {"input": "3 1 1 3\n1 2", "output": "-1"},
                        {"input": "2 1 1 2\n1 2", "output": "1"},
                        {"input": "4 4 1 4\n1 2\n2 3\n3 4\n1 4", "output": "1"},
                        {"input": "3 2 1 3\n1 2\n2 3", "output": "2"},
                        {"input": "5 5 1 5\n1 2\n1 3\n2 4\n3 5\n4 5", "output": "2"},
                        {"input": "4 3 2 4\n1 2\n2 3\n3 4", "output": "2"},
                        {"input": "3 0 1 3", "output": "-1"},
                    ],
                },
                {
                    "title": "Detect Cycle in Directed Graph",
                    "description": "Given a directed graph with **N** nodes and **M** edges, determine if the graph contains a cycle.",
                    "input_format": "First line: N and M.\nNext M lines: two integers u and v representing a directed edge from u to v.",
                    "output_format": "Print YES if a cycle exists, otherwise NO.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ M ≤ 2×10^5",
                    "topic": "graphs",
                    "test_cases": [
                        {"input": "3 3\n1 2\n2 3\n3 1", "output": "YES"},
                        {"input": "3 2\n1 2\n2 3", "output": "NO"},
                        {"input": "4 4\n1 2\n2 3\n3 4\n4 2", "output": "YES"},
                        {"input": "2 1\n1 2", "output": "NO"},
                        {"input": "4 3\n1 2\n2 3\n3 4", "output": "NO"},
                        {"input": "5 5\n1 2\n2 3\n3 4\n4 5\n5 3", "output": "YES"},
                        {"input": "4 4\n1 2\n1 3\n2 4\n3 4", "output": "NO"},
                        {"input": "3 3\n1 2\n2 3\n1 3", "output": "NO"},
                    ],
                },
                {
                    "title": "Topological Sort",
                    "description": "Given a directed acyclic graph (DAG) with **N** nodes and **M** edges, print a valid topological ordering of the nodes.",
                    "input_format": "First line: N and M.\nNext M lines: two integers u and v representing a directed edge from u to v.",
                    "output_format": "Print a valid topological order, space-separated. If multiple valid orderings exist, print the lexicographically smallest.",
                    "constraints": "1 ≤ N ≤ 10^4\n0 ≤ M ≤ 2×10^4",
                    "topic": "graphs",
                    "test_cases": [
                        {"input": "4 3\n1 2\n1 3\n2 4", "output": "1 2 3 4"},
                        {"input": "3 2\n1 2\n2 3", "output": "1 2 3"},
                        {"input": "4 4\n1 2\n1 3\n2 4\n3 4", "output": "1 2 3 4"},
                        {"input": "2 1\n1 2", "output": "1 2"},
                        {"input": "3 0", "output": "1 2 3"},
                        {"input": "5 4\n1 2\n1 3\n2 4\n3 5", "output": "1 2 3 4 5"},
                        {"input": "4 2\n2 1\n3 4", "output": "2 3 1 4"},
                        {"input": "3 3\n1 2\n1 3\n2 3", "output": "1 2 3"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── DYNAMIC PROGRAMMING ───────────────────────────────────────────────
        elif any(k in t for k in ["dynamic", "dp", "knapsack", "subsequence"]):
            easy_pool = [
                {
                    "title": "Fibonacci Number",
                    "description": "Given **N**, compute the Nth Fibonacci number. F(0)=0, F(1)=1, F(N)=F(N-1)+F(N-2).",
                    "input_format": "A single integer N (0 ≤ N ≤ 40).",
                    "output_format": "Print the Nth Fibonacci number.",
                    "constraints": "0 ≤ N ≤ 40",
                    "topic": "math",
                    "test_cases": [
                        {"input": "10", "output": "55"},
                        {"input": "0", "output": "0"},
                        {"input": "1", "output": "1"},
                        {"input": "5", "output": "5"},
                        {"input": "20", "output": "6765"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Longest Common Subsequence",
                    "description": "Given two strings **A** and **B**, find the length of their Longest Common Subsequence (LCS).",
                    "input_format": "First line: string A.\nSecond line: string B.",
                    "output_format": "Print a single integer — the length of the LCS.",
                    "constraints": "1 ≤ |A|, |B| ≤ 1000",
                    "topic": "dynamic programming",
                    "test_cases": [
                        {"input": "abcde\nace", "output": "3"},
                        {"input": "abc\nabc", "output": "3"},
                        {"input": "abc\ndef", "output": "0"},
                        {"input": "AGGTAB\nGXTXAYB", "output": "4"},
                        {"input": "a\na", "output": "1"},
                    ],
                },
                {
                    "title": "Coin Change",
                    "description": "Given an array of coin denominations and a target amount, find the minimum number of coins needed. Print -1 if impossible.",
                    "input_format": "First line: N (number of coins) and T (target).\nSecond line: N coin denominations.",
                    "output_format": "Print the minimum number of coins, or -1 if impossible.",
                    "constraints": "1 ≤ N ≤ 12\n0 ≤ T ≤ 10^4",
                    "topic": "dynamic programming",
                    "test_cases": [
                        {"input": "3 11\n1 5 6", "output": "2"},
                        {"input": "2 3\n2 4", "output": "-1"},
                        {"input": "1 0\n1", "output": "0"},
                        {"input": "3 7\n1 3 4", "output": "2"},
                        {"input": "2 10\n1 5", "output": "2"},
                    ],
                },
            ]
            hard_pool = [
                {
                    "title": "0/1 Knapsack Problem",
                    "description": "You have **N** items, each with weight W[i] and value V[i], and a knapsack with capacity **C**. Find the maximum total value you can carry.",
                    "input_format": "First line: N and C.\nNext N lines: W[i] and V[i] for each item.",
                    "output_format": "Print a single integer — the maximum value.",
                    "constraints": "1 ≤ N ≤ 100\n1 ≤ C ≤ 1000",
                    "topic": "dynamic programming",
                    "test_cases": [
                        {"input": "3 50\n10 60\n20 100\n30 120", "output": "220"},
                        {"input": "1 10\n15 100", "output": "0"},
                        {"input": "2 10\n5 40\n5 50", "output": "90"},
                        {"input": "4 8\n2 3\n3 4\n4 5\n5 6", "output": "10"},
                        {"input": "3 6\n1 1\n2 6\n3 10", "output": "16"},
                    ],
                },
            ]

        # ── STACKS ────────────────────────────────────────────────────────────
        elif any(k in t for k in ["stack", "parenthes", "bracket"]):
            easy_pool = [
                {
                    "title": "Valid Parentheses",
                    "description": "Given a string containing only '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
                    "input_format": "A single line containing the bracket string.",
                    "output_format": "Print YES if valid, otherwise NO.",
                    "constraints": "1 ≤ |S| ≤ 10^4",
                    "topic": "stacks",
                    "test_cases": [
                        {"input": "({[]})", "output": "YES"},
                        {"input": "([)]", "output": "NO"},
                        {"input": "{[]}", "output": "YES"},
                        {"input": "()", "output": "YES"},
                        {"input": "(()", "output": "NO"},
                        {"input": "[]{}()", "output": "YES"},
                        {"input": "{", "output": "NO"},
                        {"input": "((()))", "output": "YES"},
                    ],
                },
                {
                    "title": "Reverse a String Using Stack",
                    "description": "Given a string **S**, use a stack to reverse it and print the result.",
                    "input_format": "A single line containing string S (1 ≤ |S| ≤ 10^5).",
                    "output_format": "Print the reversed string.",
                    "constraints": "1 ≤ |S| ≤ 10^5",
                    "topic": "stacks",
                    "test_cases": [
                        {"input": "hello", "output": "olleh"},
                        {"input": "abcde", "output": "edcba"},
                        {"input": "a", "output": "a"},
                        {"input": "racecar", "output": "racecar"},
                        {"input": "stack", "output": "kcats"},
                        {"input": "OpenAI", "output": "IAnepO"},
                        {"input": "12345", "output": "54321"},
                        {"input": "ab", "output": "ba"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Next Greater Element",
                    "description": "Given an array of **N** integers, for each element find the next greater element to its right. If none exists, print -1.",
                    "input_format": "First line: N.\nSecond line: N space-separated integers.",
                    "output_format": "Print N space-separated integers.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "stacks",
                    "test_cases": [
                        {"input": "5\n4 5 2 10 8", "output": "5 10 10 -1 -1"},
                        {"input": "3\n3 2 1", "output": "-1 -1 -1"},
                        {"input": "3\n1 2 3", "output": "2 3 -1"},
                        {"input": "4\n2 1 2 4", "output": "4 2 4 -1"},
                        {"input": "1\n5", "output": "-1"},
                        {"input": "5\n1 3 2 4 5", "output": "3 4 4 5 -1"},
                        {"input": "4\n4 3 2 1", "output": "-1 -1 -1 -1"},
                        {"input": "6\n6 8 0 1 3 2", "output": "8 -1 1 3 -1 -1"},
                    ],
                },
                {
                    "title": "Largest Rectangle in Histogram",
                    "description": "Given an array of **N** non-negative integers representing the heights of bars in a histogram, find the area of the largest rectangle.",
                    "input_format": "First line: N.\nSecond line: N space-separated non-negative integers.",
                    "output_format": "Print a single integer — the area of the largest rectangle.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ height ≤ 10^4",
                    "topic": "stacks",
                    "test_cases": [
                        {"input": "6\n2 1 5 6 2 3", "output": "10"},
                        {"input": "1\n5", "output": "5"},
                        {"input": "3\n2 2 2", "output": "6"},
                        {"input": "5\n1 2 3 4 5", "output": "9"},
                        {"input": "3\n3 1 3", "output": "3"},
                        {"input": "4\n4 4 4 4", "output": "16"},
                        {"input": "5\n5 4 3 2 1", "output": "9"},
                        {"input": "2\n1 2", "output": "2"},
                    ],
                },
                {
                    "title": "Min Stack",
                    "description": "Design a stack that supports push, pop, and retrieving the minimum element in O(1). Given **Q** operations, process them and print the result of each getMin operation.",
                    "input_format": "First line: Q.\nNext Q lines: operation type — PUSH x, POP, or GETMIN.",
                    "output_format": "For each GETMIN operation, print the current minimum on a new line.",
                    "constraints": "1 ≤ Q ≤ 10^5\n-10^9 ≤ x ≤ 10^9",
                    "topic": "stacks",
                    "test_cases": [
                        {"input": "5\nPUSH 5\nPUSH 3\nGETMIN\nPOP\nGETMIN", "output": "3\n5"},
                        {"input": "3\nPUSH 1\nPUSH 2\nGETMIN", "output": "1"},
                        {"input": "4\nPUSH 3\nPUSH 1\nPUSH 2\nGETMIN", "output": "1"},
                        {"input": "6\nPUSH 5\nPUSH 3\nPUSH 7\nGETMIN\nPOP\nGETMIN", "output": "3\n3"},
                        {"input": "2\nPUSH 10\nGETMIN", "output": "10"},
                        {"input": "7\nPUSH 2\nPUSH 0\nGETMIN\nPOP\nGETMIN\nPUSH -1\nGETMIN", "output": "0\n2\n-1"},
                        {"input": "4\nPUSH 1\nPUSH 1\nGETMIN\nPOP", "output": "1"},
                        {"input": "5\nPUSH 5\nPUSH 4\nPUSH 3\nPOP\nGETMIN", "output": "4"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── SORTING ───────────────────────────────────────────────────────────
        elif any(k in t for k in ["sort", "inversion", "merge"]):
            easy_pool = [
                {
                    "title": "Merge Sorted Arrays",
                    "description": "Given two sorted arrays **A** and **B** of sizes N and M, merge them into a single sorted array.",
                    "input_format": "First line: N and M.\nSecond line: N sorted integers.\nThird line: M sorted integers.",
                    "output_format": "Print the merged sorted array.",
                    "constraints": "1 ≤ N, M ≤ 10^5",
                    "topic": "general",
                    "test_cases": [
                        {"input": "3 3\n1 3 5\n2 4 6", "output": "1 2 3 4 5 6"},
                        {"input": "2 1\n1 2\n3", "output": "1 2 3"},
                        {"input": "1 1\n5\n5", "output": "5 5"},
                        {"input": "3 2\n1 2 3\n4 5", "output": "1 2 3 4 5"},
                        {"input": "1 3\n2\n1 3 4", "output": "1 2 3 4"},
                        {"input": "3 3\n1 2 3\n4 5 6", "output": "1 2 3 4 5 6"},
                        {"input": "2 2\n1 3\n2 4", "output": "1 2 3 4"},
                        {"input": "4 2\n1 3 5 7\n2 4", "output": "1 2 3 4 5 7"},
                    ],
                },
                {
                    "title": "Sort Array",
                    "description": "Given an array of **N** integers, sort them in non-decreasing order and print the result.",
                    "input_format": "First line: N.\nSecond line: N space-separated integers.",
                    "output_format": "Print the sorted array.",
                    "constraints": "1 ≤ N ≤ 10^5\n-10^9 ≤ A[i] ≤ 10^9",
                    "topic": "sorting",
                    "test_cases": [
                        {"input": "5\n5 3 1 4 2", "output": "1 2 3 4 5"},
                        {"input": "3\n3 1 2", "output": "1 2 3"},
                        {"input": "1\n42", "output": "42"},
                        {"input": "4\n4 3 2 1", "output": "1 2 3 4"},
                        {"input": "5\n-3 -1 0 2 1", "output": "-3 -1 0 1 2"},
                        {"input": "3\n1 1 1", "output": "1 1 1"},
                        {"input": "6\n6 5 4 3 2 1", "output": "1 2 3 4 5 6"},
                        {"input": "4\n2 2 1 1", "output": "1 1 2 2"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Sort and Count Inversions",
                    "description": "Given an array of **N** integers, count the number of inversions. An inversion is a pair (i, j) where i < j and arr[i] > arr[j].",
                    "input_format": "First line: N.\nSecond line: N space-separated integers.",
                    "output_format": "Print the number of inversions.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "sorting",
                    "test_cases": [
                        {"input": "5\n2 4 1 3 5", "output": "3"},
                        {"input": "3\n1 2 3", "output": "0"},
                        {"input": "3\n3 2 1", "output": "3"},
                        {"input": "4\n1 3 2 4", "output": "1"},
                        {"input": "5\n5 4 3 2 1", "output": "10"},
                        {"input": "4\n2 3 8 6", "output": "1"},
                        {"input": "5\n1 5 2 4 3", "output": "4"},
                        {"input": "6\n6 5 4 3 2 1", "output": "15"},
                    ],
                },
                {
                    "title": "Kth Largest Element",
                    "description": "Given an array of **N** integers and an integer **K**, find the Kth largest element.",
                    "input_format": "First line: N and K.\nSecond line: N space-separated integers.",
                    "output_format": "Print the Kth largest element.",
                    "constraints": "1 ≤ K ≤ N ≤ 10^5\n-10^9 ≤ A[i] ≤ 10^9",
                    "topic": "sorting",
                    "test_cases": [
                        {"input": "6 2\n3 2 1 5 6 4", "output": "5"},
                        {"input": "5 4\n3 2 3 1 2", "output": "1"},
                        {"input": "3 1\n1 2 3", "output": "3"},
                        {"input": "4 2\n4 3 2 1", "output": "3"},
                        {"input": "5 3\n5 4 3 2 1", "output": "3"},
                        {"input": "3 3\n1 2 3", "output": "1"},
                        {"input": "5 1\n1 5 2 4 3", "output": "5"},
                        {"input": "4 4\n10 20 30 40", "output": "10"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── GREEDY ────────────────────────────────────────────────────────────
        elif any(k in t for k in ["greedy", "activity", "platform", "interval"]):
            easy_pool = [
                {
                    "title": "Activity Selection Problem",
                    "description": "Given **N** activities with start and end times, select the maximum number of non-overlapping activities.",
                    "input_format": "First line: N.\nNext N lines: start and end time of each activity.",
                    "output_format": "Print a single integer — the maximum number of activities.",
                    "constraints": "1 ≤ N ≤ 10^5",
                    "topic": "greedy",
                    "test_cases": [
                        {"input": "6\n1 2\n3 4\n0 6\n5 7\n8 9\n5 9", "output": "4"},
                        {"input": "3\n1 3\n2 4\n3 5", "output": "2"},
                        {"input": "1\n0 1", "output": "1"},
                        {"input": "4\n1 2\n2 3\n3 4\n4 5", "output": "4"},
                        {"input": "3\n0 10\n1 2\n3 4", "output": "2"},
                        {"input": "5\n1 4\n3 5\n0 6\n5 7\n3 9", "output": "2"},
                        {"input": "4\n0 1\n1 2\n2 3\n3 4", "output": "4"},
                        {"input": "3\n0 5\n1 3\n4 6", "output": "2"},
                    ],
                },
                {
                    "title": "Minimum Coins",
                    "description": "Given coin denominations [1, 5, 10, 25] and a target amount **N**, find the minimum number of coins needed using a greedy approach.",
                    "input_format": "A single integer N (0 ≤ N ≤ 10^6).",
                    "output_format": "Print a single integer — the minimum number of coins.",
                    "constraints": "0 ≤ N ≤ 10^6",
                    "topic": "greedy",
                    "test_cases": [
                        {"input": "41", "output": "4"},
                        {"input": "0", "output": "0"},
                        {"input": "25", "output": "1"},
                        {"input": "30", "output": "2"},
                        {"input": "11", "output": "2"},
                        {"input": "100", "output": "4"},
                        {"input": "1", "output": "1"},
                        {"input": "36", "output": "3"},
                    ],
                },
            ]
            medium_pool = [
                {
                    "title": "Jump Game",
                    "description": "Given an array of **N** non-negative integers where each element represents the maximum jump length from that position, determine if you can reach the last index starting from index 0.",
                    "input_format": "First line: N.\nSecond line: N space-separated non-negative integers.",
                    "output_format": "Print YES if you can reach the last index, otherwise NO.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ A[i] ≤ 10^5",
                    "topic": "greedy",
                    "test_cases": [
                        {"input": "5\n2 3 1 1 4", "output": "YES"},
                        {"input": "5\n3 2 1 0 4", "output": "NO"},
                        {"input": "1\n0", "output": "YES"},
                        {"input": "3\n1 1 0", "output": "YES"},
                        {"input": "4\n0 1 2 3", "output": "NO"},
                        {"input": "5\n1 1 1 1 1", "output": "YES"},
                        {"input": "3\n2 0 0", "output": "YES"},
                        {"input": "4\n1 0 0 0", "output": "NO"},
                    ],
                },
                {
                    "title": "Minimum Number of Platforms",
                    "description": "Given arrival and departure times of **N** trains, find the minimum number of platforms required so no train waits.",
                    "input_format": "First line: N.\nSecond line: N arrival times.\nThird line: N departure times.",
                    "output_format": "Print a single integer — the minimum number of platforms.",
                    "constraints": "1 ≤ N ≤ 10^5\n0 ≤ time ≤ 2359",
                    "topic": "greedy",
                    "test_cases": [
                        {"input": "6\n900 940 950 1100 1500 1800\n910 1200 1120 1130 1900 2000", "output": "3"},
                        {"input": "3\n900 1100 1235\n1000 1200 1240", "output": "1"},
                        {"input": "1\n900\n1000", "output": "1"},
                        {"input": "4\n100 200 300 400\n200 300 400 500", "output": "1"},
                        {"input": "3\n100 100 100\n200 200 200", "output": "3"},
                        {"input": "5\n900 1000 1100 1200 1300\n1000 1100 1200 1300 1400", "output": "1"},
                        {"input": "4\n900 900 900 900\n1000 1000 1000 1000", "output": "4"},
                        {"input": "3\n900 1000 1100\n1200 1300 1400", "output": "1"},
                    ],
                },
                {
                    "title": "Fractional Knapsack",
                    "description": "Given **N** items with weights and values, and a knapsack of capacity **W**, find the maximum value you can carry (fractions of items are allowed).",
                    "input_format": "First line: N and W.\nNext N lines: weight and value of each item.",
                    "output_format": "Print the maximum value with exactly 2 decimal places.",
                    "constraints": "1 ≤ N ≤ 1000\n1 ≤ W ≤ 10^6",
                    "topic": "greedy",
                    "test_cases": [
                        {"input": "3 50\n10 60\n20 100\n30 120", "output": "240.00"},
                        {"input": "1 10\n5 30", "output": "30.00"},
                        {"input": "2 10\n10 60\n20 100", "output": "60.00"},
                        {"input": "3 10\n5 30\n10 40\n20 60", "output": "55.00"},
                        {"input": "1 5\n10 20", "output": "10.00"},
                        {"input": "3 15\n5 10\n10 20\n15 30", "output": "30.00"},
                        {"input": "2 50\n20 100\n30 120", "output": "220.00"},
                        {"input": "3 20\n5 50\n10 60\n20 140", "output": "200.00"},
                    ],
                },
            ]
            hard_pool = medium_pool

        # ── DEFAULT: ARRAYS ───────────────────────────────────────────────────
        else:
            easy_pool = [
            {
                "title": "Reverse an Array",
                "description": "Given an array of **N** integers, print the array in reverse order.",
                "input_format": "First line contains an integer N denoting the number of elements.\nSecond line contains N space-separated integers.",
                "output_format": "Print the reversed array elements on a single line separated by spaces.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5\n1 2 3 4 5", "output": "5 4 3 2 1"},
                    {"input": "1\n42", "output": "42"},
                    {"input": "3\n-1 0 1", "output": "1 0 -1"},
                    {"input": "4\n10 20 30 40", "output": "40 30 20 10"},
                    {"input": "2\n7 3", "output": "3 7"},
                    {"input": "6\n1 2 3 4 5 6", "output": "6 5 4 3 2 1"},
                    {"input": "3\n100 200 300", "output": "300 200 100"},
                    {"input": "5\n5 4 3 2 1", "output": "1 2 3 4 5"},
                ],
            },
            {
                "title": "Sum of Array Elements",
                "description": "Given an array of **N** integers, find and print the sum of all elements.",
                "input_format": "First line contains an integer N — the number of elements.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the sum of all array elements.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5\n1 2 3 4 5", "output": "15"},
                    {"input": "1\n100", "output": "100"},
                    {"input": "3\n-1 0 1", "output": "0"},
                    {"input": "4\n10 20 30 40", "output": "100"},
                    {"input": "2\n-5 5", "output": "0"},
                    {"input": "3\n7 8 9", "output": "24"},
                    {"input": "4\n1 1 1 1", "output": "4"},
                    {"input": "5\n-5 -4 -3 -2 -1", "output": "-15"},
                ],
            },
            {
                "title": "Find Maximum Element",
                "description": "Given an array of **N** integers, find and print the maximum element.",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the maximum element in the array.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "6\n3 1 4 1 5 9", "output": "9"},
                    {"input": "1\n42", "output": "42"},
                    {"input": "3\n-5 -2 -8", "output": "-2"},
                    {"input": "4\n100 200 150 200", "output": "200"},
                    {"input": "2\n0 0", "output": "0"},
                    {"input": "5\n1 2 3 4 5", "output": "5"},
                    {"input": "3\n-1 -2 -3", "output": "-1"},
                    {"input": "4\n5 5 5 5", "output": "5"},
                ],
            },
            {
                "title": "Count Even Numbers",
                "description": "Given an array of **N** integers, count and print the number of even elements.",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the count of even numbers.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5\n1 2 3 4 5", "output": "2"},
                    {"input": "4\n2 4 6 8", "output": "4"},
                    {"input": "3\n1 3 5", "output": "0"},
                    {"input": "6\n-2 0 2 -4 4 6", "output": "5"},
                    {"input": "2\n1 2", "output": "1"},
                    {"input": "4\n0 0 0 0", "output": "4"},
                    {"input": "3\n1 1 1", "output": "0"},
                    {"input": "5\n2 3 4 5 6", "output": "3"},
                ],
            },
            {
                "title": "Find Second Maximum",
                "description": "Given an array of **N** integers, find and print the second largest distinct element.",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print the second largest element. If it doesn't exist, print -1.",
                "constraints": "2 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "general",
                "test_cases": [
                    {"input": "5\n1 2 3 4 5", "output": "4"},
                    {"input": "4\n5 5 3 2", "output": "3"},
                    {"input": "3\n10 20 30", "output": "20"},
                    {"input": "2\n100 200", "output": "100"},
                    {"input": "3\n-1 -2 -3", "output": "-2"},
                    {"input": "4\n1 1 1 1", "output": "-1"},
                    {"input": "5\n5 4 3 2 1", "output": "4"},
                    {"input": "3\n0 0 1", "output": "0"},
                ],
            },
            {
                "title": "Check Sorted Array",
                "description": "Given an array of **N** integers, determine if it is sorted in non-decreasing order.",
                "input_format": "First line: N.\nSecond line: N space-separated integers.",
                "output_format": "Print YES if sorted, otherwise NO.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5\n1 2 3 4 5", "output": "YES"},
                    {"input": "4\n1 3 2 4", "output": "NO"},
                    {"input": "1\n42", "output": "YES"},
                    {"input": "3\n1 1 1", "output": "YES"},
                    {"input": "4\n4 3 2 1", "output": "NO"},
                    {"input": "3\n1 2 2", "output": "YES"},
                    {"input": "5\n5 4 3 2 1", "output": "NO"},
                    {"input": "2\n1 2", "output": "YES"},
                ],
            },
            {
                "title": "Remove Duplicates from Array",
                "description": "Given a sorted array of **N** integers, remove duplicates in-place and print the unique elements.",
                "input_format": "First line: N.\nSecond line: N space-separated sorted integers.",
                "output_format": "Print the unique elements in sorted order.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "6\n1 1 2 3 3 4", "output": "1 2 3 4"},
                    {"input": "5\n1 1 1 1 1", "output": "1"},
                    {"input": "3\n1 2 3", "output": "1 2 3"},
                    {"input": "4\n1 1 2 2", "output": "1 2"},
                    {"input": "1\n5", "output": "5"},
                    {"input": "5\n1 2 2 3 4", "output": "1 2 3 4"},
                    {"input": "6\n1 1 1 2 2 3", "output": "1 2 3"},
                    {"input": "4\n1 2 3 4", "output": "1 2 3 4"},
                ],
            },
            {
                "title": "Rotate Array",
                "description": "Given an array of **N** integers and an integer **K**, rotate the array to the right by K positions.",
                "input_format": "First line: N and K.\nSecond line: N space-separated integers.",
                "output_format": "Print the rotated array.",
                "constraints": "1 <= N <= 10^5\n0 <= K <= 10^9\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5 2\n1 2 3 4 5", "output": "4 5 1 2 3"},
                    {"input": "3 1\n1 2 3", "output": "3 1 2"},
                    {"input": "4 4\n1 2 3 4", "output": "1 2 3 4"},
                    {"input": "5 0\n1 2 3 4 5", "output": "1 2 3 4 5"},
                    {"input": "3 5\n1 2 3", "output": "3 1 2"},
                    {"input": "4 2\n1 2 3 4", "output": "3 4 1 2"},
                    {"input": "1 100\n42", "output": "42"},
                    {"input": "6 3\n1 2 3 4 5 6", "output": "4 5 6 1 2 3"},
                ],
            },
        ]

            medium_pool = [
            {
                "title": "Longest Subarray with Sum K",
                "description": "Given an array of **N** integers and a target sum **K**, find the length of the longest contiguous subarray whose elements sum to exactly K.",
                "input_format": "First line contains two integers N and K.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the length of the longest subarray with sum K.\nPrint 0 if no such subarray exists.",
                "constraints": "1 <= N <= 10^5\n-10^4 <= A[i] <= 10^4\n-10^9 <= K <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "6 3\n1 2 3 1 1 1", "output": "3"},
                    {"input": "5 0\n1 -1 2 -2 3", "output": "4"},
                    {"input": "3 10\n1 2 3", "output": "0"},
                    {"input": "1 5\n5", "output": "1"},
                    {"input": "4 4\n1 2 1 3", "output": "3"},
                    {"input": "5 5\n1 2 3 4 5", "output": "2"},
                    {"input": "6 0\n0 0 0 0 0 0", "output": "6"},
                    {"input": "4 7\n3 4 1 2", "output": "2"},
                ],
            },
            {
                "title": "Two Sum",
                "description": "Given an array of **N** integers and a target value **T**, find two distinct indices i and j such that A[i] + A[j] = T. Print the indices (0-indexed).",
                "input_format": "First line contains two integers N and T.\nSecond line contains N space-separated integers.",
                "output_format": "Print two space-separated integers — the indices i and j.",
                "constraints": "2 <= N <= 10^5\n-10^9 <= A[i], T <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "4 9\n2 7 11 15", "output": "0 1"},
                    {"input": "3 6\n3 2 4", "output": "1 2"},
                    {"input": "2 10\n5 5", "output": "0 1"},
                    {"input": "5 0\n-1 1 -2 2 3", "output": "0 1"},
                    {"input": "4 7\n1 3 4 2", "output": "1 2"},
                    {"input": "3 4\n1 2 3", "output": "0 2"},
                    {"input": "4 6\n2 4 3 3", "output": "0 1"},
                    {"input": "5 10\n1 2 3 4 6", "output": "3 4"},
                ],
            },
            {
                "title": "Maximum Subarray Sum",
                "description": "Given an array of **N** integers (possibly negative), find the contiguous subarray with the largest sum and print that sum.",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the maximum subarray sum.",
                "constraints": "1 <= N <= 10^5\n-10^4 <= A[i] <= 10^4",
                "topic": "arrays",
                "test_cases": [
                    {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "output": "6"},
                    {"input": "1\n-1", "output": "-1"},
                    {"input": "4\n1 2 3 4", "output": "10"},
                    {"input": "5\n-1 -2 -3 -4 -5", "output": "-1"},
                    {"input": "6\n3 -1 2 -1 2 -3", "output": "5"},
                    {"input": "3\n-2 -3 4", "output": "4"},
                    {"input": "5\n5 4 -1 7 8", "output": "23"},
                    {"input": "4\n-2 1 -3 4", "output": "4"},
                ],
            },
            {
                "title": "Product of Array Except Self",
                "description": "Given an array of **N** integers, compute an array result where result[i] is the product of all elements except nums[i].",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print N space-separated integers — the product of all elements except self.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9\nA[i] != 0",
                "topic": "arrays",
                "test_cases": [
                    {"input": "4\n1 2 3 4", "output": "24 12 8 6"},
                    {"input": "2\n1 1", "output": "1 1"},
                    {"input": "3\n2 3 4", "output": "12 8 6"},
                    {"input": "1\n5", "output": "1"},
                    {"input": "4\n-1 1 -1 1", "output": "1 -1 1 -1"},
                    {"input": "3\n1 2 3", "output": "6 3 2"},
                    {"input": "4\n2 2 2 2", "output": "8 8 8 8"},
                    {"input": "3\n3 4 5", "output": "20 15 12"},
                ],
            },
            {
                "title": "Trapping Rain Water",
                "description": "Given **N** non-negative integers representing an elevation map where each bar has width 1, compute how much water it can trap after raining.",
                "input_format": "First line: N.\nSecond line: N space-separated non-negative integers.",
                "output_format": "Print a single integer — the total water trapped.",
                "constraints": "1 <= N <= 10^5\n0 <= height[i] <= 10^4",
                "topic": "arrays",
                "test_cases": [
                    {"input": "12\n0 1 0 2 1 0 1 3 2 1 2 1", "output": "6"},
                    {"input": "6\n4 2 0 3 2 5", "output": "9"},
                    {"input": "3\n1 0 1", "output": "1"},
                    {"input": "4\n3 0 0 3", "output": "6"},
                    {"input": "1\n5", "output": "0"},
                    {"input": "5\n0 1 0 1 0", "output": "1"},
                    {"input": "4\n1 2 3 4", "output": "0"},
                    {"input": "5\n4 1 1 1 4", "output": "9"},
                ],
            },
            {
                "title": "Sliding Window Maximum",
                "description": "Given an array of **N** integers and a window size **K**, find the maximum element in each sliding window of size K.",
                "input_format": "First line: N and K.\nSecond line: N space-separated integers.",
                "output_format": "Print the maximum of each window, space-separated.",
                "constraints": "1 <= K <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "arrays",
                "test_cases": [
                    {"input": "8 3\n1 3 -1 -3 5 3 6 7", "output": "3 3 5 5 6 7"},
                    {"input": "4 2\n1 2 3 4", "output": "2 3 4"},
                    {"input": "3 1\n1 2 3", "output": "1 2 3"},
                    {"input": "4 4\n4 3 2 1", "output": "4"},
                    {"input": "5 3\n5 3 4 2 1", "output": "5 4 4"},
                    {"input": "6 2\n2 1 5 3 6 4", "output": "2 5 5 6 6"},
                    {"input": "4 2\n4 3 2 1", "output": "4 3 2"},
                    {"input": "5 2\n1 3 2 5 4", "output": "3 3 5 5"},
                ],
            },
            ]

            hard_pool = [
            {
                "title": "Range Minimum Query",
                "description": "Given an array of **N** integers, answer **Q** queries. Each query gives L and R — find the minimum element in A[L..R] (1-indexed). Use a **Sparse Table** for O(1) per query after O(N log N) preprocessing.",
                "input_format": "First line: two integers N and Q.\nSecond line: N space-separated integers.\nNext Q lines: each contains two integers L and R.",
                "output_format": "For each query, print the minimum value on a new line.",
                "constraints": "1 <= N, Q <= 10^5\n-10^9 <= A[i] <= 10^9\n1 <= L <= R <= N",
                "topic": "arrays",
                "test_cases": [
                    {"input": "5 3\n3 1 4 1 5\n1 3\n2 5\n1 5", "output": "1\n1\n1"},
                    {"input": "3 1\n5 3 7\n1 3", "output": "3"},
                    {"input": "4 2\n2 4 1 3\n1 4\n2 3", "output": "1\n1"},
                    {"input": "1 1\n42\n1 1", "output": "42"},
                    {"input": "6 3\n1 2 3 4 5 6\n1 6\n2 4\n3 5", "output": "1\n2\n3"},
                    {"input": "5 2\n5 4 3 2 1\n1 5\n2 4", "output": "1\n2"},
                    {"input": "4 4\n3 1 4 2\n1 1\n2 2\n3 3\n4 4", "output": "3\n1\n4\n2"},
                    {"input": "6 2\n6 5 4 3 2 1\n1 3\n4 6", "output": "4\n1"},
                ],
            },
            {
                "title": "Longest Increasing Subsequence",
                "description": "Given an array of **N** integers, find the length of the longest strictly increasing subsequence.",
                "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
                "output_format": "Print a single integer — the length of the longest increasing subsequence.",
                "constraints": "1 <= N <= 10^5\n-10^9 <= A[i] <= 10^9",
                "topic": "dynamic programming",
                "test_cases": [
                    {"input": "8\n10 9 2 5 3 7 101 18", "output": "4"},
                    {"input": "3\n0 1 0", "output": "2"},
                    {"input": "1\n0", "output": "1"},
                    {"input": "5\n5 4 3 2 1", "output": "1"},
                    {"input": "6\n1 2 3 4 5 6", "output": "6"},
                    {"input": "7\n3 10 2 1 20 4 5", "output": "4"},
                    {"input": "5\n1 3 2 4 5", "output": "4"},
                    {"input": "6\n2 5 3 7 11 8", "output": "5"},
                ],
            },
            {
                "title": "Shortest Path in Weighted Graph",
                "description": "Given a weighted graph with N nodes and M edges, find the shortest path from node 1 to node N using Dijkstra's algorithm.",
                "input_format": "First line: N M.\nNext M lines: u v w (edge from u to v with weight w).",
                "output_format": "Print the shortest distance from 1 to N, or -1 if unreachable.",
                "constraints": "1 <= N, M <= 10^5\n1 <= w <= 10^9",
                "topic": "graphs",
                "test_cases": [
                    {"input": "4 4\n1 2 5\n2 3 3\n3 4 1\n1 4 10", "output": "9"},
                    {"input": "3 2\n1 2 5\n2 3 10", "output": "15"},
                    {"input": "2 1\n1 2 3", "output": "3"},
                    {"input": "3 0", "output": "-1"},
                    {"input": "5 6\n1 2 2\n2 3 3\n3 5 4\n1 3 10\n1 4 5\n4 5 1", "output": "10"},
                    {"input": "4 3\n1 2 1\n2 3 2\n3 4 3", "output": "6"},
                    {"input": "3 3\n1 2 10\n1 3 5\n2 3 2", "output": "7"},
                    {"input": "2 0", "output": "-1"},
                ],
            },
            ]

        pools = {
            DifficultyLevel.EASY: easy_pool,
            DifficultyLevel.MEDIUM: hard_pool,   # medium → serve hard questions
            DifficultyLevel.HARD: medium_pool,   # hard   → serve medium questions
        }

        questions = pools.get(difficulty, hard_pool)

        # Build exclusion set from recently used titles (case-insensitive)
        # Also expand semantically: if any excluded title contains a keyword
        # (e.g. "palindrom"), block all fallback questions sharing that keyword.
        raw_exclude = set(t.lower() for t in (exclude_titles or []))

        _SEMANTIC_KEYWORDS = [
            "palindrom", "anagram", "fibonacci", "factorial", "prime",
            "armstrong", "binary search", "bubble sort", "selection sort",
            "insertion sort", "merge sort", "quick sort", "linked list",
            "circular linked", "doubly linked", "knapsack",
            "longest common subsequence", "edit distance", "levenshtein",
            "dijkstra", "topological sort", "flood fill", "number of islands",
            "two sum", "three sum", "maximum subarray", "kadane", "coin change",
            "valid parenthes", "balanced bracket", "reverse string",
            "reverse words", "reverse linked", "detect cycle",
            "lowest common ancestor", "level order", "inorder traversal",
            "binary tree", "sliding window", "two pointer", "prefix sum",
        ]

        active_keywords = [
            kw for kw in _SEMANTIC_KEYWORDS
            if any(kw in excl for excl in raw_exclude)
        ]

        def _is_blocked_fallback(q: dict) -> bool:
            title_low = q.get("title", "").lower()
            if title_low in raw_exclude:
                return True
            for kw in active_keywords:
                if kw in title_low:
                    return True
            return False

        exclude_set = raw_exclude  # kept for compatibility below

        # Try to find a question whose title hasn't been used recently
        cache_key = f"{difficulty.value}_{topic}"
        last_idx = self._last_indices.get(cache_key, -1)

        selected = None
        for offset in range(len(questions)):
            idx = (last_idx + 1 + offset) % len(questions)
            candidate = questions[idx]
            if not _is_blocked_fallback(candidate):
                selected = candidate
                self._last_indices[cache_key] = idx
                break

        if selected is None:
            # All fallback questions are in the exclude list — just advance the index
            next_idx = (last_idx + 1) % len(questions)
            self._last_indices[cache_key] = next_idx
            selected = questions[next_idx]

        # Trim test cases to a varying count so every question has a different number
        # Use a hash of the title for deterministic but varied counts (5-12)
        import hashlib as _hl
        title_hash = int(_hl.md5(selected.get("title", "x").encode()).hexdigest(), 16)
        tc_counts = [5, 6, 7, 8, 9, 10, 11, 12, 5, 7, 6, 10, 8, 9, 11, 7]
        target_tc = tc_counts[title_hash % len(tc_counts)]
        tcs = selected.get("test_cases", [])
        if len(tcs) > target_tc:
            selected = dict(selected)  # shallow copy to avoid mutating the pool
            selected["test_cases"] = tcs[:target_tc]

        return selected


def _generate_starter_code_from_signature(sig: dict, title: str, desc: str, input_fmt: str) -> dict:
    """
    Generate complete stdin/stdout starter code for all 4 languages.
    Each template includes:
      - The function stub (user writes logic here)
      - A main entry point that reads from stdin and calls the function
    This way the code runs as-is without any external test harness wrapping.
    """
    func_name = sig.get("function_name", "solve")
    params = sig.get("parameters", [])
    return_type = sig.get("return_type", "int")
    return_desc = sig.get("return_description", "the result")

    # Build param strings per language
    py_params   = ", ".join(p["name"] for p in params)
    cpp_params  = ", ".join(_cpp_type(p) + " " + p["name"] for p in params)
    java_params = ", ".join(_java_type(p) + " " + p["name"] for p in params)
    js_params   = ", ".join(p["name"] for p in params)

    # Build docstring param lines
    py_param_docs  = "\n".join(f"    # {p['name']}: {p.get('type','?')}" for p in params)
    java_param_docs = "\n".join(f"     * @param {p['name']} ({p.get('type','?')})" for p in params)

    # ── Build per-language I/O reading code from input_format ────────────
    py_reads, cpp_reads, java_reads, js_reads, actual_vars = _build_io_from_format(input_fmt, params)

    # Use actual variable names from I/O reads as the call arguments.
    # This ensures the function call always matches what was read from stdin,
    # even when _generate_function_signature returned wrong/empty params
    # or when the format uses different names than the signature (e.g. s1/s2 vs s/t).
    if actual_vars:
        call_args = ", ".join(actual_vars)
        # Rebuild function signature params when:
        #   - params is empty/wrong count, OR
        #   - param names don't match actual variable names (e.g. s,t vs s1,s2)
        param_names_match = (
            params and
            len(params) == len(actual_vars) and
            all(p["name"] == v for p, v in zip(params, actual_vars))
        )
        if not param_names_match:
            # Infer types from input_format for the actual vars,
            # but preserve types from original params where names match
            orig_type_map = {p["name"]: p.get("type", "int") for p in params}
            inferred_params = _infer_params_from_vars(actual_vars, input_fmt)
            # Keep original type if the var name existed in the original signature
            for p in inferred_params:
                if p["name"] in orig_type_map:
                    p["type"] = orig_type_map[p["name"]]
            params = inferred_params
            py_params   = ", ".join(p["name"] for p in params)
            cpp_params  = ", ".join(_cpp_type(p) + " " + p["name"] for p in params)
            java_params = ", ".join(_java_type(p) + " " + p["name"] for p in params)
            js_params   = ", ".join(p["name"] for p in params)
            py_param_docs  = "\n".join(f"    # {p['name']}: {p.get('type','?')}" for p in params)
            java_param_docs = "\n".join(f"     * @param {p['name']} ({p.get('type','?')})" for p in params)
    else:
        call_args = ", ".join(p["name"] for p in params)

    # ── Python output formatting ──────────────────────────────────────────
    rt_lower = return_type.lower()
    if "list" in rt_lower or "[]" in rt_lower:
        py_print = "print(' '.join(map(str, result)))"
        cpp_print = """for (int i = 0; i < (int)result.size(); i++) {
        cout << result[i];
        if (i + 1 < (int)result.size()) cout << " ";
    }
    cout << endl;"""
        java_print = """StringBuilder sb = new StringBuilder();
        for (int i = 0; i < result.length; i++) {
            if (i > 0) sb.append(' ');
            sb.append(result[i]);
        }
        System.out.println(sb.toString());"""
        js_print = "console.log(result.join(' '));"
    elif "bool" in rt_lower:
        py_print = 'print("YES" if result else "NO")'
        cpp_print = 'cout << (result ? "YES" : "NO") << endl;'
        java_print = 'System.out.println(result ? "YES" : "NO");'
        js_print = 'console.log(result ? "YES" : "NO");'
    elif "str" in rt_lower or "string" in rt_lower:
        py_print = "print(result)"
        cpp_print = "cout << result << endl;"
        java_print = "System.out.println(result);"
        js_print = "console.log(result);"
    else:
        py_print = "print(result)"
        cpp_print = "cout << result << endl;"
        java_print = "System.out.println(result);"
        js_print = "console.log(result);"

    # ── Python ────────────────────────────────────────────────────────────
    python_code = f'''def {func_name}({py_params}):
    """
    {title}

    Parameters:
{py_param_docs}

    Returns:
        {return_type}: {return_desc}
    """
    # ============================================
    # TODO: Write your solution logic here
    # ============================================

    pass

# DO NOT MODIFY: Test code
if __name__ == "__main__":
{py_reads}
    result = {func_name}({call_args})
    {py_print}
'''

    # ── C++ ───────────────────────────────────────────────────────────────
    cpp_code = f'''#include <bits/stdc++.h>
using namespace std;

/**
 * {title}
 * @return {return_desc}
 */
{_cpp_return_type(return_type)} {func_name}({cpp_params}) {{
    // ============================================
    // TODO: Write your solution logic here
    // ============================================

}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

{cpp_reads}
    auto result = {func_name}({call_args});
    {cpp_print}
    return 0;
}}
'''
    java_code = f'''import java.util.*;
import java.io.*;

public class Solution {{
    /**
     * {title}
     *
{java_param_docs}
     * @return {return_desc}
     */
    public static {_java_return_type(return_type)} {func_name}({java_params}) {{
        // ============================================
        // TODO: Write your solution logic here
        // ============================================

        return {_java_default(return_type)};
    }}

    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
{java_reads}
        {_java_return_type(return_type)} result = {func_name}({call_args});
        {java_print}
    }}
}}
'''

    # ── JavaScript ────────────────────────────────────────────────────────
    js_code = f'''/**
 * {title}
 * @return {{{return_type}}} {return_desc}
 */
function {func_name}({js_params}) {{
    // ============================================
    // TODO: Write your solution logic here
    // ============================================

}}

// DO NOT MODIFY: Test code
const fs = require('fs');
const _lines = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n');
let _idx = 0;
{js_reads}
const result = {func_name}({call_args});
{js_print}
'''

    return {
        "python": python_code,
        "cpp": cpp_code,
        "java": java_code,
        "javascript": js_code,
        "c": _build_c_io(params, return_type, func_name, []),
    }


def _parse_input_format(input_fmt: str) -> list:
    """Kept for compatibility — use _build_io_from_format directly."""
    return []


def _infer_params_from_vars(var_names: list, input_fmt: str) -> list:
    """
    Infer parameter types from variable names and input_format.
    Used when _generate_function_signature returned wrong/empty params.
    """
    import re as _re
    fl = (input_fmt or "").lower()
    params = []

    # Known scalar (int) variable names
    _int_names = {"n", "e", "k", "m", "t", "q", "d", "r", "c", "p", "x", "y", "z",
                  "src", "dst", "start", "end", "target", "capacity", "days", "cooldown",
                  "cycle_pos", "cycle_start", "pos", "idx", "count", "size", "len",
                  "a", "b", "left", "right", "lo", "hi", "mid"}
    # Known string variable names
    _str_names = {"s", "s1", "s2", "t", "str1", "str2", "word", "text", "pattern"}
    # Known array variable names
    _arr_names = {"arr", "nums", "items", "weights", "arrivals", "departures",
                  "candidates", "list", "seq", "array", "l1", "l2",
                  "tasks", "labels", "A", "B", "C", "D"}

    for name in var_names:
        nl = name.lower()
        if nl in ("ops",):
            t = "List"
        elif nl in ("board",):
            t = "List[List[str]]"
        elif nl in ("grid",):
            t = "List[List[int]]"
        elif nl in ("edges",):
            t = "List[List[int]]"
        elif name in _str_names or nl in _str_names:
            t = "str"
        elif nl in ("tasks", "labels") or "task" in nl or "label" in nl:
            t = "List[str]"
        elif name in _arr_names or nl in _arr_names:
            t = "List[int]"
        elif name in _int_names or nl in _int_names:
            t = "int"
        elif name in ("A", "B", "C", "D"):
            # 4Sum arrays
            t = "List[int]"
        else:
            # Guess from input_format context
            # If the format mentions "space-separated" near this var, it's an array
            if "space-separated" in fl or "space separated" in fl:
                t = "List[int]"
            else:
                t = "int"
        params.append({"name": name, "type": t, "description": name})
    return params


def _build_io_from_format(input_fmt: str, params: list) -> tuple:
    """
    Build stdin-reading code for all 4 languages based on input_format + param types.

    Handles every pattern produced by dynamic_generator:
      - Simple array / single int / single string
      - Array + int  (Two Sum, Sliding Window, Subarray Sum, etc.)
      - Two arrays   (arrivals/departures, merge sorted lists, 4Sum lines)
      - Two strings  (anagram, palindrome)
      - Two ints     (GCD, etc.)
      - Graph        (Line 1: n e [src]. Next e lines: u v [w])
      - Grid         (N lines each with M space-separated values)
      - Stack/Queue ops  (Each line: operation [value])
      - Word search  (grid rows + last line: word)
      - Four arrays  (4Sum: four lines each with n integers)
      - Combination sum / cycle detection / task scheduler

    Returns (py_reads, cpp_reads, java_reads, js_reads) — each a string of
    indented code ready to drop into the template.
    """
    import re as _re

    fmt = (input_fmt or "").strip()
    fl  = fmt.lower()

    py_l   = []
    cpp_l  = []
    java_l = []
    js_l   = []

    # ── helpers ────────────────────────────────────────────────────────────

    def param_name(idx: int, fallback: str) -> str:
        """Return the actual param name at position idx, or fallback."""
        if params and idx < len(params):
            return params[idx]["name"]
        return fallback

    def param_type(idx: int) -> str:
        if params and idx < len(params):
            return params[idx].get("type", "int").lower()
        return "int"

    def is_array_type(t: str) -> bool:
        return "list" in t or "array" in t or "[]" in t

    def is_str_type(t: str) -> bool:
        return "str" in t or "string" in t

    def emit_int_array(name: str):
        py_l.append(f"    {name} = list(map(int, input().split()))")
        cpp_l.append(f"    string _{name}_line; getline(cin, _{name}_line);")
        cpp_l.append(f"    istringstream _{name}_iss(_{name}_line);")
        cpp_l.append(f"    vector<int> {name};")
        cpp_l.append(f"    {{ int _v; while (_{name}_iss >> _v) {name}.push_back(_v); }}")
        java_l.append(f"        String[] _{name}Parts = br.readLine().trim().split(\" \");")
        java_l.append(f"        int[] {name} = new int[_{name}Parts.length];")
        java_l.append(f"        for (int i = 0; i < _{name}Parts.length; i++) {name}[i] = Integer.parseInt(_{name}Parts[i]);")
        js_l.append(f"const {name} = _lines[_idx++].split(' ').map(Number);")

    def emit_str_array(name: str):
        """Array of strings (e.g. task labels)."""
        py_l.append(f"    {name} = input().split()")
        cpp_l.append(f"    string _{name}_line; getline(cin, _{name}_line);")
        cpp_l.append(f"    istringstream _{name}_iss(_{name}_line);")
        cpp_l.append(f"    vector<string> {name};")
        cpp_l.append(f"    {{ string _v; while (_{name}_iss >> _v) {name}.push_back(_v); }}")
        java_l.append(f"        String[] {name} = br.readLine().trim().split(\" \");")
        js_l.append(f"const {name} = _lines[_idx++].split(' ');")

    def emit_int(name: str):
        py_l.append(f"    {name} = int(input())")
        cpp_l.append(f"    int {name}; cin >> {name}; cin.ignore();")
        java_l.append(f"        int {name} = Integer.parseInt(br.readLine().trim());")
        js_l.append(f"const {name} = parseInt(_lines[_idx++]);")

    def emit_string(name: str):
        py_l.append(f"    {name} = input().strip()")
        cpp_l.append(f"    string {name}; getline(cin, {name});")
        java_l.append(f"        String {name} = br.readLine().trim();")
        js_l.append(f"const {name} = _lines[_idx++].trim();")

    def emit_two_ints_one_line(n1: str, n2: str):
        """Two ints on the same line: 'n e' or 'a b'."""
        py_l.append(f"    {n1}, {n2} = map(int, input().split())")
        cpp_l.append(f"    int {n1}, {n2}; cin >> {n1} >> {n2}; cin.ignore();")
        java_l.append(f"        StringTokenizer _st = new StringTokenizer(br.readLine());")
        java_l.append(f"        int {n1} = Integer.parseInt(_st.nextToken());")
        java_l.append(f"        int {n2} = Integer.parseInt(_st.nextToken());")
        js_l.append(f"const [{n1}, {n2}] = _lines[_idx++].split(' ').map(Number);")

    def emit_three_ints_one_line(n1: str, n2: str, n3: str):
        py_l.append(f"    {n1}, {n2}, {n3} = map(int, input().split())")
        cpp_l.append(f"    int {n1}, {n2}, {n3}; cin >> {n1} >> {n2} >> {n3}; cin.ignore();")
        java_l.append(f"        StringTokenizer _st2 = new StringTokenizer(br.readLine());")
        java_l.append(f"        int {n1} = Integer.parseInt(_st2.nextToken());")
        java_l.append(f"        int {n2} = Integer.parseInt(_st2.nextToken());")
        java_l.append(f"        int {n3} = Integer.parseInt(_st2.nextToken());")
        js_l.append(f"const [{n1}, {n2}, {n3}] = _lines[_idx++].split(' ').map(Number);")

    def emit_grid(rows_var: str, num_rows_expr: str = "n"):
        """Read a 2-D grid of ints."""
        py_l.append(f"    {rows_var} = [list(map(int, input().split())) for _ in range({num_rows_expr})]")
        cpp_l.append(f"    vector<vector<int>> {rows_var}({num_rows_expr});")
        cpp_l.append(f"    for (int _r = 0; _r < {num_rows_expr}; _r++) {{")
        cpp_l.append(f"        string _row_line; getline(cin, _row_line);")
        cpp_l.append(f"        istringstream _row_iss(_row_line);")
        cpp_l.append(f"        int _v; while (_row_iss >> _v) {rows_var}[_r].push_back(_v);")
        cpp_l.append(f"    }}")
        java_l.append(f"        int[][] {rows_var} = new int[{num_rows_expr}][];")
        java_l.append(f"        for (int _r = 0; _r < {num_rows_expr}; _r++) {{")
        java_l.append(f"            String[] _rp = br.readLine().trim().split(\" \");")
        java_l.append(f"            {rows_var}[_r] = new int[_rp.length];")
        java_l.append(f"            for (int _c = 0; _c < _rp.length; _c++) {rows_var}[_r][_c] = Integer.parseInt(_rp[_c]);")
        java_l.append(f"        }}")
        js_l.append(f"const {rows_var} = [];")
        js_l.append(f"for (let _r = 0; _r < {num_rows_expr}; _r++) {{")
        js_l.append(f"    {rows_var}.push(_lines[_idx++].split(' ').map(Number));")
        js_l.append(f"}}")

    def emit_char_grid(rows_var: str, num_rows_expr: str = "n"):
        """Read a 2-D grid of chars (word search board)."""
        py_l.append(f"    {rows_var} = [input().split() for _ in range({num_rows_expr})]")
        cpp_l.append(f"    vector<vector<string>> {rows_var}({num_rows_expr});")
        cpp_l.append(f"    for (int _r = 0; _r < {num_rows_expr}; _r++) {{")
        cpp_l.append(f"        string _row_line; getline(cin, _row_line);")
        cpp_l.append(f"        istringstream _row_iss(_row_line);")
        cpp_l.append(f"        string _v; while (_row_iss >> _v) {rows_var}[_r].push_back(_v);")
        cpp_l.append(f"    }}")
        java_l.append(f"        String[][] {rows_var} = new String[{num_rows_expr}][];")
        java_l.append(f"        for (int _r = 0; _r < {num_rows_expr}; _r++) {{")
        java_l.append(f"            {rows_var}[_r] = br.readLine().trim().split(\" \");")
        java_l.append(f"        }}")
        js_l.append(f"const {rows_var} = [];")
        js_l.append(f"for (let _r = 0; _r < {num_rows_expr}; _r++) {{")
        js_l.append(f"    {rows_var}.push(_lines[_idx++].split(' '));")
        js_l.append(f"}}")

    # ══════════════════════════════════════════════════════════════════════
    # Pattern matching — most specific first, single if/elif chain
    # ══════════════════════════════════════════════════════════════════════

    # ── 1. Graph: "Line 1: n e [src]. Next e lines: u v [w]" ──────────────
    if "next" in fl and "line" in fl and ("edge" in fl or "u v" in fl or "u v w" in fl):
        weighted = "w" in fl or "weight" in fl
        has_src  = "src" in fl
        if has_src:
            emit_three_ints_one_line("n", "e", "src")
        else:
            emit_two_ints_one_line("n", "e")
        if weighted:
            py_l.append("    edges = []")
            py_l.append("    for _ in range(e):")
            py_l.append("        u, v, w = map(int, input().split())")
            py_l.append("        edges.append((u, v, w))")
            cpp_l.append("    vector<tuple<int,int,int>> edges;")
            cpp_l.append("    for (int _i = 0; _i < e; _i++) {")
            cpp_l.append("        int u, v, w; cin >> u >> v >> w;")
            cpp_l.append("        edges.push_back({u, v, w});")
            cpp_l.append("    } cin.ignore();")
            java_l.append("        List<int[]> edges = new ArrayList<>();")
            java_l.append("        for (int _i = 0; _i < e; _i++) {")
            java_l.append("            StringTokenizer _et = new StringTokenizer(br.readLine());")
            java_l.append("            int u = Integer.parseInt(_et.nextToken());")
            java_l.append("            int v = Integer.parseInt(_et.nextToken());")
            java_l.append("            int w = Integer.parseInt(_et.nextToken());")
            java_l.append("            edges.add(new int[]{u, v, w});")
            java_l.append("        }")
            js_l.append("const edges = [];")
            js_l.append("for (let _i = 0; _i < e; _i++) {")
            js_l.append("    const [u, v, w] = _lines[_idx++].split(' ').map(Number);")
            js_l.append("    edges.push([u, v, w]);")
            js_l.append("}")
        else:
            py_l.append("    edges = []")
            py_l.append("    for _ in range(e):")
            py_l.append("        u, v = map(int, input().split())")
            py_l.append("        edges.append((u, v))")
            cpp_l.append("    vector<pair<int,int>> edges;")
            cpp_l.append("    for (int _i = 0; _i < e; _i++) {")
            cpp_l.append("        int u, v; cin >> u >> v;")
            cpp_l.append("        edges.push_back({u, v});")
            cpp_l.append("    } cin.ignore();")
            java_l.append("        List<int[]> edges = new ArrayList<>();")
            java_l.append("        for (int _i = 0; _i < e; _i++) {")
            java_l.append("            StringTokenizer _et = new StringTokenizer(br.readLine());")
            java_l.append("            int u = Integer.parseInt(_et.nextToken());")
            java_l.append("            int v = Integer.parseInt(_et.nextToken());")
            java_l.append("            edges.add(new int[]{u, v});")
            java_l.append("        }")
            js_l.append("const edges = [];")
            js_l.append("for (let _i = 0; _i < e; _i++) {")
            js_l.append("    const [u, v] = _lines[_idx++].split(' ').map(Number);")
            js_l.append("    edges.push([u, v]);")
            js_l.append("}")

    # ── 2. Stack/Queue ops: "Each line: operation [value]" ────────────────
    elif "each line" in fl and ("operation" in fl or "push" in fl or "enqueue" in fl or "dequeue" in fl):
        has_capacity = "capacity" in fl
        if has_capacity:
            cap_name = param_name(0, "capacity")
            emit_int(cap_name)
        py_l.append("    ops = []")
        py_l.append("    for line in __import__('sys').stdin:")
        py_l.append("        line = line.strip()")
        py_l.append("        if not line: continue")
        py_l.append("        parts = line.split()")
        py_l.append("        ops.append((parts[0], int(parts[1])) if len(parts) > 1 else (parts[0], None))")
        cpp_l.append("    vector<pair<string,int>> ops;")
        cpp_l.append("    { string _op_line;")
        cpp_l.append("      while (getline(cin, _op_line)) {")
        cpp_l.append("          if (_op_line.empty()) continue;")
        cpp_l.append("          istringstream _oss(_op_line);")
        cpp_l.append("          string _op; int _val = 0; _oss >> _op;")
        cpp_l.append("          if (_oss >> _val) ops.push_back({_op, _val});")
        cpp_l.append("          else ops.push_back({_op, 0});")
        cpp_l.append("      }}")
        java_l.append("        List<String[]> ops = new ArrayList<>();")
        java_l.append("        String _opLine;")
        java_l.append("        while ((_opLine = br.readLine()) != null) {")
        java_l.append("            _opLine = _opLine.trim();")
        java_l.append("            if (_opLine.isEmpty()) continue;")
        java_l.append("            ops.add(_opLine.split(\" \"));")
        java_l.append("        }")
        js_l.append("const ops = [];")
        js_l.append("while (_idx < _lines.length) {")
        js_l.append("    const _op = _lines[_idx++].trim();")
        js_l.append("    if (_op) ops.push(_op.split(' '));")
        js_l.append("}")

    # ── 3. Word search: "Lines 1-N: grid rows. Last line: word." ──────────
    #    Must come before the generic grid/multi-line checks
    elif ("grid row" in fl and ("last line" in fl or "word" in fl)) or \
         (_re.search(r'lines?\s+1[-\u2013]\d+', fl) and ("grid" in fl or "row" in fl) and "word" in fl):
        m = _re.search(r'lines?\s+1[-\u2013](\d+)', fl)
        num_rows = int(m.group(1)) if m else 4
        board_name = param_name(0, "board")
        word_name  = param_name(1, "word")
        emit_char_grid(board_name, str(num_rows))
        emit_string(word_name)

    # ── 4. Grid: "N lines each with M space-separated values" ─────────────
    elif _re.search(r'\d+\s+lines?\s+(each\s+with|of)', fl) or \
         (_re.search(r'lines?\s+\d+[-\u2013]\d+', fl) and "grid" in fl):
        m = _re.search(r'(\d+)\s+lines?', fl)
        num_rows = int(m.group(1)) if m else 4
        grid_name = param_name(0, "grid")
        emit_grid(grid_name, str(num_rows))

    # ── 5. Four lines of arrays: "Four lines, each with n integers" ───────
    elif "four lines" in fl or _re.search(r'4\s+lines', fl):
        names = [param_name(i, chr(65 + i)) for i in range(4)]  # A, B, C, D
        for nm in names:
            emit_int_array(nm)

    # ── 6. Multi-line format: "Line 1: ... Line 2: ..." ───────────────────
    elif _re.search(r'line\s+[12]', fl):
        # Check if this is a "Line 1: X. Each subsequent line: ops" pattern
        has_ops_tail = ("each subsequent line" in fl or "each following line" in fl) and \
                       ("operation" in fl or "push" in fl or "enqueue" in fl or "dequeue" in fl)

        # Split on "Line N:" markers only
        segments = _re.split(r'line\s+\d+\s*:', fl)
        segments = [s.strip().rstrip('.').strip() for s in segments if s.strip()]
        # Remove the ops tail from the last segment if present
        if has_ops_tail and segments:
            last = segments[-1]
            for tail_marker in ["each subsequent line", "each following line"]:
                if tail_marker in last:
                    segments[-1] = last[:last.index(tail_marker)].strip().rstrip('.')

        param_idx = 0
        for seg in segments:
            if not seg:
                continue

            # Try to extract a variable name from the segment text itself.
            # Priority: backtick > "for/representing X" > "type X" > bare short id
            # Reject generic English words that aren't variable names.
            _generic_words = {
                "integers", "values", "separated", "sorted", "space", "with",
                "the", "and", "for", "each", "line", "lines", "integer", "string",
                "strings", "number", "numbers", "element", "elements", "array",
                "list", "data", "input", "output", "order", "insertion", "given",
                "following", "subsequent", "next", "last", "first", "second",
            }
            seg_var = None
            # 1. backtick-quoted: `varname`
            bm = _re.search(r'`([a-zA-Z_]\w*)`', seg)
            if bm:
                seg_var = bm.group(1)
            if not seg_var:
                # 2. "for X" or "representing X"
                fm = _re.search(r'(?:for|representing)\s+([a-zA-Z_]\w*)', seg)
                if fm and fm.group(1).lower() not in _generic_words:
                    seg_var = fm.group(1)
            if not seg_var:
                # 3. "string X", "integer X", "int X", "float X"
                vm = _re.search(r'(?:string|integer|int|float)\s+([a-zA-Z_]\w*)', seg)
                if vm and vm.group(1).lower() not in _generic_words:
                    seg_var = vm.group(1)
            if not seg_var:
                # 4. Segment is just a bare identifier (e.g. "a", "b", "arrivals", "k")
                bare = seg.strip().rstrip('.')
                if _re.match(r'^[a-zA-Z_]\w{0,20}$', bare) and bare.lower() not in _generic_words:
                    seg_var = bare
            if not seg_var:
                # 5. Last word in segment if it looks like a var name
                wm = _re.search(r'\b([a-zA-Z_]\w{0,20})\s*\.?\s*$', seg)
                if wm and wm.group(1).lower() not in _generic_words:
                    seg_var = wm.group(1)

            name = seg_var or param_name(param_idx, f"p{param_idx}")
            # Better fallback names based on what the segment describes
            if not seg_var:
                seg_lower = seg.lower()
                if "space-separated" in seg_lower or ("integer" in seg_lower and "array" not in seg_lower and "list" not in seg_lower and "single" not in seg_lower):
                    # Likely an array — use param name or 'arr'
                    name = param_name(param_idx, "arr") if not params else name
                elif "string" in seg_lower:
                    name = param_name(param_idx, "s") if not params else name
            ptype = param_type(param_idx)
            param_idx += 1

            # Detect what this segment describes
            is_arr = (
                "space-separated" in seg
                or ("integer" in seg and ("array" in seg or "list" in seg))
                or is_array_type(ptype)
                or bool(_re.search(r'(arr|nums?|items?|weights?|arrivals?|departures?|candidates?|tasks?|list)', seg))
            )
            is_str = (
                "string" in seg or "word" in seg or "char" in seg
                or is_str_type(ptype)
                or bool(_re.search(r'\bs[12]\b', seg))
            )
            is_two = bool(_re.search(r'\b[a-z]\s+[a-z]\b', seg)) and not is_arr and not is_str

            if is_arr:
                emit_int_array(name)
            elif is_str:
                emit_string(name)
            elif is_two:
                name2 = param_name(param_idx, f"p{param_idx}")
                param_idx += 1
                emit_two_ints_one_line(name, name2)
            else:
                emit_int(name)

        # Emit ops reader for the tail if present
        if has_ops_tail:
            py_l.append("    ops = []")
            py_l.append("    for line in __import__('sys').stdin:")
            py_l.append("        line = line.strip()")
            py_l.append("        if not line: continue")
            py_l.append("        parts = line.split()")
            py_l.append("        ops.append((parts[0], int(parts[1])) if len(parts) > 1 else (parts[0], None))")
            cpp_l.append("    vector<pair<string,int>> ops;")
            cpp_l.append("    { string _op_line;")
            cpp_l.append("      while (getline(cin, _op_line)) {")
            cpp_l.append("          if (_op_line.empty()) continue;")
            cpp_l.append("          istringstream _oss(_op_line);")
            cpp_l.append("          string _op; int _val = 0; _oss >> _op;")
            cpp_l.append("          if (_oss >> _val) ops.push_back({_op, _val});")
            cpp_l.append("          else ops.push_back({_op, 0});")
            cpp_l.append("      }}")
            java_l.append("        List<String[]> ops = new ArrayList<>();")
            java_l.append("        String _opLine;")
            java_l.append("        while ((_opLine = br.readLine()) != null) {")
            java_l.append("            _opLine = _opLine.trim();")
            java_l.append("            if (_opLine.isEmpty()) continue;")
            java_l.append("            ops.add(_opLine.split(\" \"));")
            java_l.append("        }")
            js_l.append("const ops = [];")
            js_l.append("while (_idx < _lines.length) {")
            js_l.append("    const _op = _lines[_idx++].trim();")
            js_l.append("    if (_op) ops.push(_op.split(' '));")
            js_l.append("}")

    # ── 7. Single string ───────────────────────────────────────────────────
    elif ("single" in fl and "string" in fl) or \
         ("lowercase string" in fl) or \
         ("single line string" in fl) or \
         (len(params) == 1 and is_str_type(param_type(0)) and "space" not in fl):
        emit_string(param_name(0, "s"))

    # ── 8. Single integer ──────────────────────────────────────────────────
    elif ("single integer" in fl) or \
         (len(params) == 1 and not is_array_type(param_type(0)) and not is_str_type(param_type(0)) and "space" not in fl):
        emit_int(param_name(0, "n"))

    # ── 9. Default: one line per param, type-driven ────────────────────────
    else:
        if params:
            for p in params:
                name = p["name"]
                t = p.get("type", "int").lower()
                if is_array_type(t):
                    emit_int_array(name)
                elif is_str_type(t):
                    emit_string(name)
                else:
                    emit_int(name)
        else:
            emit_int_array("arr")

    # ── Consume a leading element-count line ───────────────────────────────
    # Many generated formats read "First line: N. Second line: N space-separated
    # integers", but the function signature only declares the sequence. Without
    # consuming that first line the array read swallows the count instead
    # (arr becomes [4] for input "4\n3 4 -1 1"), so every test case fails.
    # Only applies when the format announces a first-line count, the reads start
    # with a sequence read, and no emitted variable already consumed it.
    _fl_head = fl.split("second line")[0] if "second line" in fl else ""
    # A lone count only — "N and X" means the first line carries a second value
    # the sequence read must not swallow, so leave those formats alone.
    _declares_count = bool(
        _re.search(r"first line[^.]*\b(n|m|k|size|length|count)\b", _fl_head)
    ) and not _re.search(r"\band\b|,", _fl_head)
    _reads_one_line_only = len(py_l) == 1 and "input().split()" in (py_l[0] if py_l else "")
    if _declares_count and _reads_one_line_only:
        # Consumed without parsing: the line is discarded either way, and the
        # sequence length is already implied by the sequence itself.
        py_l.insert(0, "    _ = input()  # element count line (implied by the sequence)")
        cpp_l.insert(0, "    string _hdr; getline(cin, _hdr);")
        java_l.insert(0, "        br.readLine();")
        js_l.insert(0, "_idx++;")

    # ── Join and return ────────────────────────────────────────────────────
    # Collect the actual top-level variable names created (for call_args).
    # We parse py_l to find assignment targets, skipping loop-internal vars.
    actual_vars = []
    seen = set()
    # Variables that are loop-internal and should NOT be passed as args
    _loop_internal = {"line", "parts", "u", "v", "w", "_v", "_r", "_c", "_i",
                      "_op", "_val", "_op_line", "_row_line", "_row_iss"}
    import re as _re2
    in_loop = False
    loop_indent = 0
    for raw_line in py_l:
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip())

        # Track loop entry
        if stripped.startswith("for ") or stripped.startswith("while "):
            in_loop = True
            loop_indent = indent
            continue

        # Track loop exit (dedent back to or before loop level)
        if in_loop and stripped and indent <= loop_indent and not stripped.startswith(("for ", "while ")):
            in_loop = False

        # Skip lines inside loops
        if in_loop:
            continue

        # Skip non-assignment lines
        if "=" not in stripped or stripped.startswith(("if ", "elif ", "else", "#")):
            continue

        # Match assignment: varname = ... or varname, varname2 = ...
        m = _re2.match(r'^([a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)\s*=(?!=)', stripped)
        if m:
            names = [n.strip() for n in m.group(1).split(',')]
            for n in names:
                if n not in seen and not n.startswith('_') and n not in _loop_internal:
                    seen.add(n)
                    actual_vars.append(n)

    return (
        "\n".join(py_l),
        "\n".join(cpp_l),
        "\n".join(java_l),
        "\n".join(js_l),
        actual_vars,   # ← actual variable names created by the I/O reads
    )


def _cpp_type(param: dict) -> str:
    t = param.get("type", "int").lower()
    if "list" in t or "array" in t or "[]" in t:
        return "vector<int>"
    if "string" in t or "str" in t:
        return "string"
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _cpp_return_type(t: str) -> str:
    t = t.lower()
    if "list" in t or "array" in t or "[]" in t:
        return "vector<int>"
    if "string" in t or "str" in t:
        return "string"
    if "bool" in t:
        return "bool"
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _c_param_type(param: dict) -> str:
    """C type for a function parameter."""
    t = param.get("type", "int").lower()
    if "list" in t or "array" in t or "[]" in t:
        return "int*"
    if "string" in t or "str" in t:
        return "char*"
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _c_return_type(t: str) -> str:
    t = t.lower()
    if "list" in t or "array" in t or "[]" in t:
        return "void"   # C returns via output param or prints directly
    if "string" in t or "str" in t:
        return "void"
    if "bool" in t:
        return "int"    # C has no bool, use int
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _build_c_io(params: list, return_type: str, func_name: str, call_args_list: list) -> str:
    """
    Build a complete C main() that reads stdin, calls the function, and prints the result.
    Returns the full C source as a string.
    """
    rt = return_type.lower()
    is_list_return = "list" in rt or "array" in rt or "[]" in rt
    is_str_return  = "str" in rt or "string" in rt
    is_bool_return = "bool" in rt

    lines = []
    lines.append("#include <stdio.h>")
    lines.append("#include <stdlib.h>")
    lines.append("#include <string.h>")
    lines.append("")

    # Build function signature
    c_params = []
    for p in params:
        t = p.get("type", "int").lower()
        name = p["name"]
        if "list" in t or "array" in t or "[]" in t:
            c_params.append(f"int* {name}, int {name}_len")
        elif "str" in t or "string" in t:
            c_params.append(f"char* {name}")
        elif "double" in t or "float" in t:
            c_params.append(f"double {name}")
        else:
            c_params.append(f"int {name}")

    c_ret = _c_return_type(return_type)
    sig = f"{c_ret} {func_name}({', '.join(c_params) if c_params else 'void'})"

    lines.append(f"/**")
    lines.append(f" * TODO: Write your solution logic here")
    lines.append(f" */")
    lines.append(f"{sig} {{")
    lines.append(f"    // ============================================")
    lines.append(f"    // TODO: Write your solution logic here")
    lines.append(f"    // ============================================")
    lines.append(f"")
    if c_ret != "void":
        lines.append(f"    return 0;")
    lines.append(f"}}")
    lines.append("")
    lines.append("int main() {")

    # Build I/O reading for each param
    actual_call_args = []
    for p in params:
        t = p.get("type", "int").lower()
        name = p["name"]
        if "list" in t or "array" in t or "[]" in t:
            lines.append(f"    // Read array {name}")
            lines.append(f"    int {name}_len = 0;")
            lines.append(f"    int {name}_buf[10000];")
            lines.append(f"    char _line_{name}[100000];")
            lines.append(f"    if (fgets(_line_{name}, sizeof(_line_{name}), stdin)) {{")
            lines.append(f"        char* _tok = strtok(_line_{name}, \" \\n\");")
            lines.append(f"        while (_tok) {{ {name}_buf[{name}_len++] = atoi(_tok); _tok = strtok(NULL, \" \\n\"); }}")
            lines.append(f"    }}")
            actual_call_args.append(f"{name}_buf")
            actual_call_args.append(f"{name}_len")
        elif "str" in t or "string" in t:
            lines.append(f"    char {name}[10000];")
            lines.append(f"    scanf(\"%s\", {name});")
            actual_call_args.append(name)
        elif "double" in t or "float" in t:
            lines.append(f"    double {name};")
            lines.append(f"    scanf(\"%lf\", &{name});")
            actual_call_args.append(name)
        else:
            lines.append(f"    int {name};")
            lines.append(f"    scanf(\"%d\", &{name});")
            actual_call_args.append(name)

    lines.append("")
    call_str = ", ".join(actual_call_args)

    # Print result
    if is_list_return:
        # For list return, function prints directly (void return)
        lines.append(f"    {func_name}({call_str});")
    elif is_str_return:
        lines.append(f"    {func_name}({call_str});")
    elif is_bool_return:
        lines.append(f"    int result = {func_name}({call_str});")
        lines.append(f"    printf(\"%s\\n\", result ? \"YES\" : \"NO\");")
    else:
        lines.append(f"    {c_ret} result = {func_name}({call_str});")
        if "double" in c_ret:
            lines.append(f"    printf(\"%.6f\\n\", result);")
        else:
            lines.append(f"    printf(\"%d\\n\", result);")

    lines.append("    return 0;")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def _java_type(param: dict) -> str:
    t = param.get("type", "int").lower()
    if "list" in t or "array" in t or "[]" in t:
        return "int[]"
    if "string" in t or "str" in t:
        return "String"
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _java_return_type(t: str) -> str:
    t = t.lower()
    if "list" in t or "array" in t or "[]" in t:
        return "int[]"
    if "string" in t or "str" in t:
        return "String"
    if "bool" in t:
        return "boolean"
    if "double" in t or "float" in t:
        return "double"
    return "int"


def _java_default(t: str) -> str:
    t = t.lower()
    if "list" in t or "array" in t or "[]" in t:
        return "new int[]{}"
    if "string" in t or "str" in t:
        return '""'
    if "bool" in t:
        return "false"
    return "0"


def _example_values(params: list) -> list:
    vals = []
    for p in params:
        t = p.get("type", "int").lower()
        if "list" in t or "array" in t or "[]" in t:
            vals.append("[1, 2, 3]")
        elif "string" in t or "str" in t:
            vals.append('"hello"')
        elif "bool" in t:
            vals.append("True")
        elif "double" in t or "float" in t:
            vals.append("1.0")
        else:
            vals.append("5")
    return vals


def _clean_description(desc: str, input_fmt: str, output_fmt: str) -> tuple:
    """
    Strip raw competitive-programming markers from the description body.
    Markers like -----Input-----, -----Output-----, -----Examples-----,
    -----Note-----, -----Explanation----- are removed from the body.
    The clean body text (problem statement only) is returned along with
    any input/output/note content extracted from the raw markers.

    Returns: (clean_body, extracted_input, extracted_output, extracted_note)
    """
    import re

    # Patterns for raw section markers (various styles)
    RAW_SECTION_RE = re.compile(
        r'-{2,}\s*(Input|Output|Examples?|Note|Explanation|Constraints?|'
        r'Sample Input|Sample Output|Format|Scoring|Subtasks?)\s*-{2,}',
        re.IGNORECASE
    )

    # Split on raw markers
    parts = RAW_SECTION_RE.split(desc)

    if len(parts) <= 1:
        # No raw markers — description is already clean
        return desc.strip(), input_fmt, output_fmt, ''

    # parts[0] = body text before first marker
    # parts[1], parts[2] = marker name, content, marker name, content, ...
    body = parts[0].strip()

    extracted_input = input_fmt
    extracted_output = output_fmt
    extracted_note = ''

    i = 1
    while i < len(parts) - 1:
        section_name = parts[i].strip().lower()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ''
        i += 2

        if 'input' in section_name and not extracted_input:
            extracted_input = content
        elif 'output' in section_name and not extracted_output:
            extracted_output = content
        elif 'note' in section_name or 'explanation' in section_name:
            if content:
                extracted_note = content
        # Skip examples/scoring/subtasks — they clutter the display

    return body, extracted_input, extracted_output, extracted_note


_TYPED_STARTER_LANGUAGES = ("python", "cpp", "java", "javascript")


def _typed_signature(data: dict):
    """(function_signature, starter_code) when the question already carries its own, else None.

    Reviewed questions arrive with a real signature and starter code that were checked end to end, so
    guessing them again from the title and text would only make them worse. Anything incomplete falls
    back to the guess, exactly as before.
    """
    code = data.get("starter_code")
    params = data.get("parameters")
    name = data.get("function_name")
    return_type = data.get("return_type")
    if not (isinstance(code, dict) and isinstance(params, list) and params and isinstance(name, str) and name and return_type):
        return None
    if any(not isinstance(code.get(lang), str) or not code[lang].strip() for lang in _TYPED_STARTER_LANGUAGES):
        return None
    if any(not isinstance(p, dict) or not p.get("name") or not p.get("type") for p in params):
        return None
    signature = {
        "function_name": name,
        "parameters": params,
        "return_type": return_type,
        "return_description": data.get("return_description") or "The answer to the problem",
    }
    return signature, {lang: text for lang, text in code.items() if isinstance(text, str) and text.strip()}


def _legacy_typed(data: dict, tests: list):
    """(function_signature, starter_code) for a question that has none of its own, read off its stored tests, else None.

    The starter code of these questions used to be guessed from the wording of the input format, and for most of the built-in
    questions the guess read the wrong lines (only the first line of a two-line input, one edge of a list of edges), so no
    solution could pass. This reads the structure from the stored test inputs themselves, requires it to parse EVERY one of
    them with every line accounted for, and builds the starters of all five languages from it with the same generators the
    reviewed questions use (app/services/scaffold.py). When the structure cannot be established it answers None and the old
    guess stays, exactly as before."""
    try:
        from app.services import legacy_typing, scaffold

        pairs = [(t["input"], t["output"]) for t in tests if isinstance(t, dict) and isinstance(t.get("input"), str) and isinstance(t.get("output"), str)]
        if not pairs:
            return None
        typed = legacy_typing.type_question(pairs, pairs[0][0], pairs[0][1], extended=True, input_format=str(data.get("input_format") or ""))
        if typed is None:
            return None
        code = scaffold.served_starter(typed)
        signature = {
            "function_name": typed["function_name"],
            "parameters": typed["parameters"],
            "return_type": typed["return_type"],
            "return_description": typed["return_description"],
        }
        if not isinstance(code, dict) or any(not isinstance(code.get(lang), str) or not code[lang].strip() for lang in _TYPED_STARTER_LANGUAGES):
            return None
        return signature, {lang: text for lang, text in code.items() if isinstance(text, str) and text.strip()}
    except Exception as e:  # an optional improvement: never let it stop a question from being served
        print(f"[ai] Could not type {data.get('title')!r} from its tests: {e}")
        return None


_DIAGRAM_POOL = None
_DIAGRAM_CACHE: "OrderedDict[str, Optional[str]]" = OrderedDict()
_DIAGRAM_CACHE_SIZE = 256


def _diagram_pool() -> ThreadPoolExecutor:
    """The threads that draw diagrams: a few of their own, so drawing never runs on the event loop (every socket and request waits while
    it does) and never uses the threads that run players' code."""
    global _DIAGRAM_POOL
    if _DIAGRAM_POOL is None:
        _DIAGRAM_POOL = ThreadPoolExecutor(max_workers=max(1, settings.DIAGRAM_WORKERS), thread_name_prefix="diagram")
    return _DIAGRAM_POOL


async def _draw_diagram(question: dict) -> Optional[str]:
    """The diagram (a data-URL PNG, or None when there is none) for what the question says, drawn off the event loop.

    The picture depends only on the question's own text and sample, so it is remembered: a reviewed or collected question is served to
    many players and is drawn once, not once per player. A failure is raised, never remembered."""
    key = hashlib.sha1(json.dumps(question, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if key in _DIAGRAM_CACHE:
        _DIAGRAM_CACHE.move_to_end(key)
        return _DIAGRAM_CACHE[key]
    from app.services.diagram_generator import diagram_generator
    diagram = await asyncio.get_running_loop().run_in_executor(_diagram_pool(), diagram_generator.diagram_for_question, question)
    _DIAGRAM_CACHE[key] = diagram
    while len(_DIAGRAM_CACHE) > _DIAGRAM_CACHE_SIZE:
        _DIAGRAM_CACHE.popitem(last=False)
    return diagram


async def _build_result(
    data: dict, difficulty: DifficultyLevel, topic: Optional[str]
) -> dict:
    title = data.get("title", "Untitled Problem").strip()
    raw_desc = (data.get("description") or data.get("problem_statement") or "").strip()
    input_fmt = data.get("input_format", "").strip()
    output_fmt = data.get("output_format", "").strip()
    constraints = data.get("constraints", "").strip()
    tcs = data.get("test_cases", [])
    sample_input = data.get("sample_input", "")
    sample_output = data.get("sample_output", "")

    if not tcs or len(tcs) == 0:
        print("[ai] Warning: No test_cases in response, using fallback")
        tcs = _generate_fallback_test_cases(raw_desc)

    # Clean the description — strip raw -----Section----- markers
    desc, input_fmt, output_fmt, note = _clean_description(raw_desc, input_fmt, output_fmt)

    # Build structured description with **Section** markers for frontend
    full_description = desc

    if input_fmt:
        full_description += f"\n\n**Input Format**\n{input_fmt}"
    if output_fmt:
        full_description += f"\n\n**Output Format**\n{output_fmt}"
    if constraints:
        full_description += f"\n\n**Constraints**\n{constraints}"

    # Use top-level sample fields if available, otherwise fall back to first test case
    si = sample_input or (tcs[0].get('input', '') if tcs else '')
    so = sample_output or (tcs[0].get('output', '') if tcs else '')
    if si:
        full_description += f"\n\n**Sample Input**\n{si}"
    if so:
        full_description += f"\n\n**Sample Output**\n{so}"
    if note:
        full_description += f"\n\n**Note**\n{note}"

    # Function signature metadata: a reviewed question brings its own; otherwise it is read off the question's own tests, and
    # only when that cannot be established is it guessed from the text
    typed = _typed_signature(data) or _legacy_typed(data, tcs)
    function_signature = typed[0] if typed else _generate_function_signature(title, raw_desc, data.get("topic", topic), input_fmt)

    print(f"[ai] Function signature: {function_signature['function_name']}({len(function_signature['parameters'])} params) -> {function_signature['return_type']}")

    # A diagram for graph and tree questions, drawn from the question's own sample input and schema. Nothing is painted by
    # an image model (it cannot be trusted to draw exactly these edges), and when the structure cannot be established for
    # certain there is no diagram rather than a wrong one.
    diagram = None
    try:
        diagram = await _draw_diagram({
            "title": title,
            "topic": data.get("topic", topic),
            "problem_statement": raw_desc,
            "input_format": input_fmt or data.get("input_format", ""),
            "input_schema": data.get("input_schema"),
            "sample_input": si,
        })
        if diagram:
            print(f"[ai] Diagram drawn for: {title}")
    except Exception as e:
        print(f"[ai] Diagram generation failed: {e}")

    # Generate function-based starter code using the function signature
    # The test harness (I/O parsing) is added automatically at execution time
    starter_code = typed[1] if typed else _generate_starter_code_from_signature(function_signature, title, desc, input_fmt)

    return {
        "title": title,
        "base_title": (data.get("base_title") or title).strip(),
        "description": full_description,
        "difficulty": difficulty,
        "topic": data.get("topic", topic) or "general",
        "test_cases": json.dumps(tcs),
        "starter_code": json.dumps(starter_code),
        "function_name": function_signature["function_name"],
        "parameters": json.dumps(function_signature["parameters"]),
        "return_type": function_signature["return_type"],
        "return_description": function_signature["return_description"],
        "diagram": diagram,  # Add diagram to response
    }


def _generate_fallback_test_cases(description: str) -> list:
    test_cases = [
        {"input": "5\n1 2 3 4 5", "output": "15"},
        {"input": "3\n1 2 3", "output": "6"},
        {"input": "1\n10", "output": "10"},
        {"input": "2\n5 5", "output": "10"},
        {"input": "4\n1 2 3 4", "output": "10"},
    ]
    return test_cases


def _generate_function_signature(title: str, description: str, topic: str, input_format: str = "") -> dict:
    """
    Generate function signature from input_format (primary) + title keywords.
    The input_format field is always structured and reliable — use it to
    determine what parameters the function takes. Title keywords determine
    the function name and return type.
    """
    tl = title.lower()
    dl = description.lower()
    inp = (input_format or "").lower()

    # ── Step 1: Determine function name from title ────────────────────────
    func_name = "solve"
    if "two sum" in tl:                          func_name = "twoSum"
    elif "maximum subarray" in tl or "max subarray" in tl: func_name = "maxSubArray"
    elif "product" in tl and "except" in tl:     func_name = "productExceptSelf"
    elif "trapping rain" in tl:                  func_name = "trap"
    elif "count inversion" in tl:                func_name = "countInversions"
    elif "sliding window" in tl or "window maximum" in tl: func_name = "slidingWindowMax"
    elif "reverse" in tl and ("string" in tl or "str" in tl): func_name = "reverseString"
    elif "reverse" in tl and "array" in tl:      func_name = "reverseArray"
    elif "reverse" in tl and "linked" in tl:     func_name = "reverseList"
    elif "palindrome" in tl and "longest" in tl: func_name = "longestPalindrome"
    elif "palindrome" in tl:                     func_name = "isPalindrome"
    elif "anagram" in tl:                        func_name = "isAnagram"
    elif "vowel" in tl:                          func_name = "countVowels"
    elif "common prefix" in tl:                  func_name = "longestCommonPrefix"
    elif "minimum window" in tl:                 func_name = "minWindow"
    elif "longest common subsequence" in tl or "lcs" in tl: func_name = "longestCommonSubsequence"
    elif "longest increasing" in tl or "lis" in tl: func_name = "lengthOfLIS"
    elif "edit distance" in tl or "levenshtein" in tl: func_name = "editDistance"
    elif "coin change" in tl:                    func_name = "coinChange"
    elif "knapsack" in tl:                       func_name = "knapsack"
    elif "fibonacci" in tl:                      func_name = "fibonacci"
    elif "factorial" in tl:                      func_name = "factorial"
    elif "prime" in tl and "check" in tl:        func_name = "isPrime"
    elif "gcd" in tl or "greatest common" in tl: func_name = "gcd"
    elif "sum of digit" in tl:                   func_name = "sumOfDigits"
    elif "binary search" in tl:                  func_name = "binarySearch"
    elif "merge sort" in tl:                     func_name = "mergeSort"
    elif "bubble sort" in tl:                    func_name = "bubbleSort"
    elif "topological" in tl:                    func_name = "topologicalSort"
    elif "dijkstra" in tl or "shortest path" in tl: func_name = "shortestPath"
    elif "cycle" in tl and ("graph" in tl or "directed" in tl): func_name = "hasCycle"
    elif "connected component" in tl:            func_name = "countComponents"
    elif "number of island" in tl:               func_name = "numIslands"
    elif "bfs" in tl:                            func_name = "bfs"
    elif "dfs" in tl:                            func_name = "dfs"
    elif "inorder" in tl:                        func_name = "inorderTraversal"
    elif "level order" in tl:                    func_name = "levelOrder"
    elif "max depth" in tl or "height" in tl and "tree" in tl: func_name = "maxDepth"
    elif "diameter" in tl and "tree" in tl:      func_name = "diameterOfTree"
    elif "lowest common ancestor" in tl or "lca" in tl: func_name = "lowestCommonAncestor"
    elif "valid parenthes" in tl or "balanced bracket" in tl: func_name = "isValid"
    elif "next greater" in tl:                   func_name = "nextGreaterElement"
    elif "kth largest" in tl or "kth smallest" in tl: func_name = "findKth"
    elif "merge interval" in tl:                 func_name = "mergeIntervals"
    elif "sort color" in tl:                     func_name = "sortColors"
    elif "jump game" in tl:                      func_name = "canJump"
    elif "activity selection" in tl:             func_name = "activitySelection"
    elif "fractional knapsack" in tl:            func_name = "fractionalKnapsack"
    elif "maximum" in tl or "max" in tl:         func_name = "findMax"
    elif "minimum" in tl or "min" in tl:         func_name = "findMin"
    elif "count" in tl:                          func_name = "count"
    elif "sum" in tl:                            func_name = "calculateSum"
    elif "sort" in tl:                           func_name = "sortArray"
    elif "search" in tl or "find" in tl:         func_name = "search"

    # ── Step 2: Determine parameters from input_format ────────────────────
    # This is the reliable signal — input_format always describes what's read
    params = []

    # Graph: N nodes + M edges
    if any(x in inp for x in ["edges", "edge", "graph", "node", "vertex", "vertices"]):
        if "weight" in inp or "weighted" in inp:
            params = [
                {"name": "n", "type": "int", "description": "Number of nodes", "example": "5"},
                {"name": "edges", "type": "List[List[int]]", "description": "Weighted edges [u, v, w]", "example": "[[0,1,4],[1,2,2]]"},
            ]
        else:
            params = [
                {"name": "n", "type": "int", "description": "Number of nodes", "example": "5"},
                {"name": "edges", "type": "List[List[int]]", "description": "Edges [u, v]", "example": "[[0,1],[1,2]]"},
            ]
        if "source" in inp or "src" in inp or "start" in inp:
            params.append({"name": "src", "type": "int", "description": "Source node", "example": "0"})
        if "destination" in inp or "dst" in inp or "end" in inp:
            params.append({"name": "dst", "type": "int", "description": "Destination node", "example": "4"})

    # Matrix / Grid
    elif any(x in inp for x in ["matrix", "grid", "rows", "columns", "2d"]):
        params = [
            {"name": "grid", "type": "List[List[int]]", "description": "2D grid/matrix", "example": "[[1,0],[0,1]]"},
        ]
        if "rows" in inp and "col" in inp:
            params = [
                {"name": "rows", "type": "int", "description": "Number of rows", "example": "3"},
                {"name": "cols", "type": "int", "description": "Number of columns", "example": "3"},
            ] + params

    # Two strings
    elif inp.count("string") >= 2 or ("first" in inp and "second" in inp and "string" in inp) \
         or ("s1" in inp and "s2" in inp) or ("string a" in inp and "string b" in inp):
        params = [
            {"name": "s1", "type": "str", "description": "First string", "example": "'listen'"},
            {"name": "s2", "type": "str", "description": "Second string", "example": "'silent'"},
        ]

    # Single string
    elif "string" in inp or "word" in inp or "text" in inp or "characters" in inp:
        params = [
            {"name": "s", "type": "str", "description": "Input string", "example": "'hello'"},
        ]
        if "integer k" in inp or "window" in inp or "size k" in inp:
            params.append({"name": "k", "type": "int", "description": "Window size or parameter K", "example": "3"})

    # Array + target/k
    elif any(x in inp for x in ["array", "integers", "elements", "space-separated", "n integers", "n numbers"]):
        params = [
            {"name": "arr", "type": "List[int]", "description": "Array of integers", "example": "[1, 2, 3, 4, 5]"},
        ]
        if "target" in inp:
            params.append({"name": "target", "type": "int", "description": "Target value", "example": "9"})
        elif "k" in inp and ("kth" in inp or "k-th" in inp or "k largest" in inp or "k smallest" in inp):
            params.append({"name": "k", "type": "int", "description": "K value", "example": "2"})
        elif "capacity" in inp or "weight" in inp:
            params.append({"name": "capacity", "type": "int", "description": "Capacity", "example": "10"})

    # Single integer (factorial, fibonacci, prime check, etc.)
    elif any(x in inp for x in ["single integer", "a single", "one integer", "integer n"]):
        params = [
            {"name": "n", "type": "int", "description": "Input integer", "example": "10"},
        ]

    # Two integers (GCD, LCM, etc.)
    elif inp.count("integer") >= 2 or ("a and b" in inp) or ("two integers" in inp):
        params = [
            {"name": "a", "type": "int", "description": "First integer", "example": "12"},
            {"name": "b", "type": "int", "description": "Second integer", "example": "18"},
        ]

    # Fallback: use topic to guess
    else:
        topic_l = (topic or "").lower()
        if "string" in topic_l:
            params = [{"name": "s", "type": "str", "description": "Input string", "example": "'hello'"}]
        elif "graph" in topic_l:
            params = [
                {"name": "n", "type": "int", "description": "Number of nodes", "example": "5"},
                {"name": "edges", "type": "List[List[int]]", "description": "Edge list", "example": "[[0,1]]"},
            ]
        elif "tree" in topic_l:
            params = [{"name": "arr", "type": "List[int]", "description": "Tree nodes (level-order)", "example": "[1,2,3]"}]
        elif "math" in topic_l:
            params = [{"name": "n", "type": "int", "description": "Input integer", "example": "10"}]
        else:
            params = [{"name": "arr", "type": "List[int]", "description": "Input array", "example": "[1, 2, 3]"}]

    # ── Step 3: Determine return type ─────────────────────────────────────
    return_type = _infer_return_type(title, description)

    return {
        "function_name": func_name,
        "parameters": params,
        "return_type": return_type,
        "return_description": "The result",
    }
    
def _infer_return_type(title: str, description: str) -> str:
    """
    Infer the return type from title and description when the keyword
    matching in _generate_function_signature left it as the default 'int'.
    """
    tl = title.lower()
    dl = description.lower()
    combined = tl + " " + dl

    # ── Clearly returns bool ──────────────────────────────────────────────
    bool_signals = [
        "is valid", "is palindrome", "is anagram", "has cycle",
        "can reach", "can jump", "can finish", "can complete",
        "check if", "determine if", "return true", "return false",
        "return boolean", "returns true or false", "yes or no",
        "detect cycle", "valid parenthes", "valid bracket",
        "are strings anagram", "check anagram",
    ]
    if any(s in combined for s in bool_signals):
        return "bool"

    # ── Clearly returns string ────────────────────────────────────────────
    str_signals = [
        "return a string", "return string", "returns a string",
        "longest palindromic substring", "minimum window substring",
        "reverse string", "reverse words",
    ]
    if any(s in combined for s in str_signals):
        return "str"

    # ── Clearly returns int (single number) ──────────────────────────────
    # These look like they might return arrays but actually return a count/sum/index
    int_overrides = [
        "maximum subarray sum", "max subarray sum", "largest contiguous subarray sum",
        "maximum sum subarray", "kadane",
        "count inversion", "number of inversion",
        "count vowel", "count digit", "count element",
        "length of", "size of", "number of",
        "minimum number of", "maximum number of",
        "find the missing", "missing number",
        "integer square root", "square root",
        "fibonacci", "factorial",
        "gcd", "lcm", "greatest common",
        "sieve", "prime",
        "pascal", "binomial",
        "diameter of", "height of", "depth of",
        "maximum depth", "minimum depth",
        "number of islands", "count islands",
        "jump game",  # returns bool actually, handled above
        "capacity to ship", "minimum capacity",
        "task scheduler",  # returns int (min time)
        "minimum platforms", "minimum number of platforms",
        "subarray sum equals k",  # returns count
        "4sum count", "four sum count",
        "longest consecutive sequence",
        "kth largest", "kth smallest",
        "search in rotated",
        "first and last position",  # returns List[int] actually
        "integer square",
        "modular exponentiation",
        "count digits",
        "gas station",
    ]
    if any(s in tl for s in int_overrides):
        return "int"

    # ── Clearly returns List[int] ─────────────────────────────────────────
    list_desc_signals = [
        "return an array", "return array", "returns an array", "returns array",
        "return a list", "return list", "returns a list", "returns list",
        "output array", "output the array",
        "answer array", "result array",
        "rearrange", "reorder",
        "prefix product", "suffix product",
        "product of all elements except",
        "product except self", "product excluding",
    ]
    list_title_signals = [
        "rotate array", "sort array", "sort colors", "reverse array",
        "product except", "product puzzle", "product excluding",
        "product array",
        "merge sorted", "merge intervals",
        "next greater element", "next smaller element",
        "two sum",  # returns indices
        "sliding window maximum",
        "top k frequent",
        "combination sum",
        "level order", "zigzag", "spiral",
        "rearrange", "shuffle",
    ]
    if any(s in dl for s in list_desc_signals):
        return "List[int]"
    if any(s in tl for s in list_title_signals):
        return "List[int]"

    return "int"


# Global instance
ai_generator = AIQuestionGenerator()
