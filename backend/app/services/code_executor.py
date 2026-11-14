import asyncio
import os
import tempfile
import subprocess
import weakref
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.core.config import get_settings

settings = get_settings()

# One semaphore per event loop (a semaphore is bound to the loop that first has to wait on it, and tests start a new loop per run).
_slots_by_loop: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _execution_slots() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    slots = _slots_by_loop.get(loop)
    if slots is None:
        slots = _slots_by_loop[loop] = asyncio.Semaphore(max(1, settings.MAX_CONCURRENT_EXECUTIONS))
    return slots

# Defined first: when Docker cannot be reached below, execute_code still reads this name to choose the subprocess fallback.
DOCKER_AVAILABLE = False
docker_client = None

try:
    import docker

    docker_client = docker.from_env()
    docker_client.ping()
    DOCKER_AVAILABLE = True
    print("[Sandbox] Docker available - using Docker mode")

    # Pre-pull images in background so first execution is fast
    def _prewarm():
        images = [
            "python:3.14-alpine",
            "gcc:14",
            "node:18-alpine",
            "eclipse-temurin:17-alpine",
        ]
        for img in images:
            try:
                docker_client.images.get(img)
            except Exception:
                print(f"[Sandbox] Pulling {img}...")
                docker_client.images.pull(img)
                print(f"[Sandbox] {img} ready")

    import threading
    threading.Thread(target=_prewarm, daemon=True).start()

except Exception as e:
    print(f"[Sandbox] Docker not available: {e}")
    docker_client = None


def _reconnect_docker() -> bool:
    """Restarting Docker Desktop kills the connection the client opened at import ("The pipe is being closed"): open a new one."""
    global docker_client, DOCKER_AVAILABLE
    try:
        import docker as _docker

        fresh = _docker.from_env()
        fresh.ping()
    except Exception as err:
        print(f"[Sandbox] Could not reconnect to Docker: {err}")
        return False
    docker_client = fresh
    DOCKER_AVAILABLE = True
    print("[Sandbox] Reconnected to Docker")
    return True


def _run_container(**kwargs):
    """Start a container; if the connection has gone stale, reconnect once and try again."""
    try:
        return docker_client.containers.run(**kwargs)
    except Exception:
        if not _reconnect_docker():
            raise
        return docker_client.containers.run(**kwargs)
    DOCKER_AVAILABLE = False

LANGUAGE_CONFIG = {
    "python": {
        "extension": "py",
        "docker_image": "python:3.14-alpine",
        "compile_cmd": None,
        "run_cmd": ["python", "{filename}"],
        "timeout": 10,
    },
    "cpp": {
        "extension": "cpp",
        "docker_image": "gcc:14",
        "compile_cmd": [
            "g++", "-std=c++17", "-O2", "-pipe", "-static", "-s",
            "-o", "{exe}", "{filename}",
        ],
        "run_cmd": ["{exe}"],
        "timeout": 10,
    },
    "java": {
        "extension": "java",
        "docker_image": "eclipse-temurin:17-alpine",
        "compile_cmd": ["javac", "{filename}"],
        "run_cmd": ["java", "-cp", "{dir}", "{classname}"],
        "classname": "Solution",
        "timeout": 15,
    },
    "javascript": {
        "extension": "js",
        "docker_image": "node:18-alpine",
        "compile_cmd": None,
        "run_cmd": ["node", "{filename}"],
        "timeout": 10,
    },
    "c": {
        "extension": "c",
        "docker_image": "gcc:14",
        "compile_cmd": [
            "gcc", "-std=c17", "-O2", "-pipe", "-static", "-s",
            "-o", "{exe}", "{filename}",
        ],
        "run_cmd": ["{exe}"],
        "timeout": 10,
    },
}

# Common imports/headers for each language
LANGUAGE_IMPORTS = {
    "python": """import sys
import math
import collections
import itertools
import functools
import heapq
import bisect
import re
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict, Counter, deque
from itertools import combinations, permutations, accumulate
from functools import lru_cache, reduce

""",
    "cpp": """#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <stack>
#include <deque>
#include <cmath>
#include <climits>
#include <numeric>
#include <functional>
using namespace std;

""",
    "java": """import java.util.*;
import java.io.*;
import java.math.*;
import java.util.stream.*;

""",
    "javascript": """// Common utilities available
const { performance } = require('perf_hooks');

""",
    "c": """#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <limits.h>
#include <stdbool.h>

""",
}

def _code_has_own_io(code: str, language: str) -> bool:
    """
    Detect whether the user's code already contains its own entry point / I/O.
    New-style starter code always includes a main block, so we skip the harness.
    """
    lang = language.lower()
    if lang == "python":
        return 'if __name__ == "__main__"' in code or "if __name__ == '__main__'" in code
    elif lang in ("cpp", "c"):
        return "int main(" in code or "int main (" in code
    elif lang == "java":
        return "public static void main(" in code or "static void main(" in code
    elif lang == "javascript":
        # JS starter code reads from /dev/stdin at module level
        return "readFileSync" in code or "readline" in code
    return False


def add_language_imports(code: str, language: str) -> str:
    """Add common imports/headers to user code if not already present"""
    lang = language.lower()
    if lang not in LANGUAGE_IMPORTS:
        return code
    
    imports = LANGUAGE_IMPORTS[lang]
    
    # Check if imports are already present
    if lang == "python":
        if "import " in code[:200]:
            return code
    elif lang in ["cpp", "c"]:
        if "#include" in code[:200]:
            return code
    elif lang == "java":
        if "import " in code[:200]:
            return code
    elif lang == "javascript":
        if "require(" in code[:200]:
            return code
    
    # Prepend imports to user code
    return imports + code


def _is_collection_type(param_type: str) -> bool:
    """True for list/array/vector parameter types.

    Must be consulted before any scalar check: "List[int]", "vector<int>" and
    "int[]" all contain the substring "int", so a scalar test matches them and
    would parse a single token instead of the whole sequence.
    """
    t = (param_type or "").lower()
    return (
        "list" in t
        or "array" in t
        or "vector" in t
        or "[]" in t
        or ("[" in t and "]" in t)
    )


def generate_test_harness(code: str, language: str, function_signature: dict) -> str:
    """
    Generate test harness that wraps user code with I/O handling.
    Reads from stdin, parses input, calls user function, prints output.
    """
    lang = language.lower()
    func_name = function_signature.get("function_name", "solve")
    params = function_signature.get("parameters", [])
    
    # If no parameters defined, return code as-is (stdin/stdout mode)
    if not params or len(params) == 0:
        return code
    
    has_collection = any(_is_collection_type(p.get("type", "")) for p in params)

    if lang == "python":
        # Generate Python test harness.
        #
        # Generated questions state their inputs in competitive-programming
        # form: an element count on its own line, then the sequence. The
        # signature only declares the sequence, so that count line is dropped
        # when it is unambiguously a length prefix (exactly one surplus line,
        # and it is a lone integer).
        skip_count_line = (
            f"""    if len(lines) == {len(params)} + 1 and lines[0].lstrip('-').isdigit():
        lines = lines[1:]
"""
            if has_collection
            else ""
        )
        harness = f"""# ===== USER CODE =====
{code}

# ===== TEST HARNESS (DO NOT MODIFY) =====
if __name__ == "__main__":
    import sys
    lines = [line.strip() for line in sys.stdin.read().strip().split('\\n') if line.strip()]
{skip_count_line}    line_idx = 0

"""
        # Parse each parameter
        for i, param in enumerate(params):
            param_name = param.get("name", f"arg{i}")
            param_type = param.get("type", "int")
            
            # Collection types must be checked first: "List[int]" contains the
            # substring "int", so a scalar check would claim it and parse only
            # the first token.
            if _is_collection_type(param_type):
                if "str" in param_type.lower():
                    harness += f"    {param_name} = lines[line_idx].split()\n    line_idx += 1\n"
                elif "float" in param_type.lower() or "double" in param_type.lower():
                    harness += f"    {param_name} = list(map(float, lines[line_idx].split()))\n    line_idx += 1\n"
                else:
                    harness += f"    {param_name} = list(map(int, lines[line_idx].split()))\n    line_idx += 1\n"
            elif "int" in param_type.lower():
                harness += f"    {param_name} = int(lines[line_idx])\n    line_idx += 1\n"
            elif "float" in param_type.lower() or "double" in param_type.lower():
                harness += f"    {param_name} = float(lines[line_idx])\n    line_idx += 1\n"
            elif "str" in param_type.lower():
                harness += f"    {param_name} = lines[line_idx]\n    line_idx += 1\n"
            else:
                harness += f"    {param_name} = lines[line_idx]\n    line_idx += 1\n"
        
        # Call function and print result
        param_names = [p.get("name", f"arg{i}") for i, p in enumerate(params)]
        harness += f"\n    result = {func_name}({', '.join(param_names)})\n"
        harness += """    
    # Format output
    if isinstance(result, list):
        print(' '.join(map(str, result)))
    elif isinstance(result, bool):
        print(str(result).lower())
    else:
        print(result)
"""
        return harness
    
    elif lang == "cpp":
        # Generate C++ test harness
        harness = f"""#include <bits/stdc++.h>
using namespace std;

{code}

// ===== TEST HARNESS (DO NOT MODIFY) =====
int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
"""
        # Parse each parameter
        for i, param in enumerate(params):
            param_name = param.get("name", f"arg{i}")
            param_type = param.get("type", "int")
            
            if _is_collection_type(param_type):
                harness += f"""    string line;
    getline(cin, line);
    istringstream iss(line);
    vector<int> {param_name};
    int num;
    while(iss >> num) {param_name}.push_back(num);
"""
            elif "float" in param_type.lower() or "double" in param_type.lower():
                harness += f"    double {param_name};\n    cin >> {param_name};\n"
            elif "string" in param_type.lower():
                harness += f"    string {param_name};\n    cin >> {param_name};\n"
            else:
                harness += f"    int {param_name};\n    cin >> {param_name};\n"
        
        # Call function and print result
        param_names = [p.get("name", f"arg{i}") for i, p in enumerate(params)]
        harness += f"\n    auto result = {func_name}({', '.join(param_names)});\n"
        harness += """    
    // Format output
    cout << result << endl;
    
    return 0;
}
"""
        return harness
    
    elif lang == "java":
        # Generate Java test harness
        harness = f"""import java.util.*;
import java.io.*;

{code}

// ===== TEST HARNESS (DO NOT MODIFY) =====
class Main {{
    public static void main(String[] args) throws Exception {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        
"""
        # Parse each parameter
        for i, param in enumerate(params):
            param_name = param.get("name", f"arg{i}")
            param_type = param.get("type", "int")
            
            if _is_collection_type(param_type):
                harness += f"""        String[] input{i} = br.readLine().trim().split(" ");
        int[] {param_name} = new int[input{i}.length];
        for(int j = 0; j < input{i}.length; j++) {{
            {param_name}[j] = Integer.parseInt(input{i}[j]);
        }}
"""
            elif "double" in param_type.lower() or "float" in param_type.lower():
                harness += f"        double {param_name} = Double.parseDouble(br.readLine().trim());\n"
            elif "string" in param_type.lower():
                harness += f"        String {param_name} = br.readLine().trim();\n"
            else:
                harness += f"        int {param_name} = Integer.parseInt(br.readLine().trim());\n"
        
        # Call function and print result
        param_names = [p.get("name", f"arg{i}") for i, p in enumerate(params)]
        harness += f"\n        var result = Solution.{func_name}({', '.join(param_names)});\n"
        harness += """        System.out.println(result);
    }
}
"""
        return harness
    
    elif lang == "javascript":
        # Generate JavaScript test harness
        harness = f"""// ===== USER CODE =====
{code}

// ===== TEST HARNESS (DO NOT MODIFY) =====
const fs = require('fs');
const lines = fs.readFileSync('/dev/stdin', 'utf8').trim().split('\\n').filter(l => l.trim());
let lineIdx = 0;

"""
        # Parse each parameter
        for i, param in enumerate(params):
            param_name = param.get("name", f"arg{i}")
            param_type = param.get("type", "int")
            
            if "int" in param_type.lower() or "number" in param_type.lower():
                harness += f"const {param_name} = parseInt(lines[lineIdx++]);\n"
            elif "float" in param_type.lower() or "double" in param_type.lower():
                harness += f"const {param_name} = parseFloat(lines[lineIdx++]);\n"
            elif "string" in param_type.lower():
                harness += f"const {param_name} = lines[lineIdx++];\n"
            elif "array" in param_type.lower() or "[]" in param_type:
                harness += f"const {param_name} = lines[lineIdx++].split(' ').map(Number);\n"
            else:
                harness += f"const {param_name} = lines[lineIdx++];\n"
        
        # Call function and print result
        param_names = [p.get("name", f"arg{i}") for i, p in enumerate(params)]
        harness += f"\nconst result = {func_name}({', '.join(param_names)});\n"
        harness += """
// Format output
if(Array.isArray(result)) {
    console.log(result.join(' '));
} else if(typeof result === 'boolean') {
    console.log(result.toString().toLowerCase());
} else {
    console.log(result);
}
"""
        return harness
    
    # Fallback: return original code
    return code


@dataclass
class TestCase:
    input_data: str
    expected_output: str
    is_hidden: bool = False


@dataclass
class ExecutionResult:
    success: bool
    passed: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class SubmissionResult:
    total_tests: int
    passed_tests: int
    execution_time_ms: float
    results: List[ExecutionResult]
    score: int = 0


class CodeExecutor:
    @staticmethod
    def _normalize_output(raw: str) -> str:
        """
        Normalize a single line of output for comparison.
        Handles:
          - Python list format:  [16, 8, 8, 8, 8]  →  16 8 8 8 8
          - Extra brackets/commas from any language
          - Collapsed whitespace
        """
        s = raw.strip()
        # Strip outer brackets if the whole value is wrapped: [...]
        if s.startswith('[') and s.endswith(']'):
            s = s[1:-1]
        # Remove commas (list separators)
        s = s.replace(',', ' ')
        # Collapse whitespace
        s = ' '.join(s.split())
        return s
    async def execute_code(
        self,
        code: str,
        language: str,
        test_cases: List[TestCase],
        time_limit_ms: int = 2000,
        function_signature: dict = None,
    ) -> SubmissionResult:
        if language.lower() not in LANGUAGE_CONFIG:
            return SubmissionResult(
                total_tests=len(test_cases),
                passed_tests=0,
                execution_time_ms=0,
                results=[],
                score=0,
            )

        # At most MAX_CONCURRENT_EXECUTIONS run at once; the others wait here (cheap: a waiting coroutine holds no thread and no container).
        async with _execution_slots():
            if DOCKER_AVAILABLE and docker_client:
                return await self._execute_with_docker(code, language, test_cases, function_signature)
            else:
                return await self._execute_with_subprocess(code, language, test_cases, function_signature)

    async def _execute_with_docker(
        self,
        code: str,
        language: str,
        test_cases: List[TestCase],
        function_signature: dict = None,
    ) -> SubmissionResult:
        config = LANGUAGE_CONFIG[language.lower()]
        lang = language.lower()
        
        # Add common imports/headers
        code_with_imports = add_language_imports(code, lang)
        
        # Only use the test harness if the code does NOT already contain its own I/O entry point.
        # New starter code always includes a main/if __name__ block, so we skip the harness.
        has_own_io = _code_has_own_io(code, lang)
        if not has_own_io and function_signature and function_signature.get("parameters"):
            print(f"[Executor] Using function-based harness with {len(function_signature['parameters'])} parameters")
            code_with_harness = generate_test_harness(code_with_imports, lang, function_signature)
        else:
            print(f"[Executor] Using stdin/stdout execution (code has own I/O)")
            code_with_harness = code_with_imports

        def do_execute():
            import io, tarfile

            results = []
            total_time = 0.0
            passed = 0

            try:
                container = _run_container(
                    image=config["docker_image"],
                    command=["tail", "-f", "/dev/null"],
                    detach=True,
                    network_disabled=True,
                    mem_limit="256m",
                    cpu_period=100000,
                    cpu_quota=50000,
                    working_dir="/sandbox",
                    remove=False,
                )

                try:
                    filename = (
                        f"Solution.{config['extension']}"
                        if lang == "java"
                        else f"solution.{config['extension']}"
                    )
                    exe_name = "solution"

                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                        content_bytes = code_with_harness.encode("utf-8")
                        tarinfo = tarfile.TarInfo(name=filename)
                        tarinfo.size = len(content_bytes)
                        tar.addfile(tarinfo, io.BytesIO(content_bytes))
                    tar_stream.seek(0)

                    container.exec_run(["mkdir", "-p", "/sandbox"])
                    container.put_archive("/sandbox", tar_stream.read())

                    compile_cmd = config.get("compile_cmd")
                    if compile_cmd:
                        exe_path = "/sandbox/solution"
                        filepath = f"/sandbox/{filename}"
                        cmd = [
                            c.format(
                                exe=exe_path,
                                filename=filepath,
                                dir="/sandbox",
                                classname=config.get("classname", "Solution"),
                            )
                            for c in compile_cmd
                        ]
                        exit_code, output = container.exec_run(cmd, workdir="/sandbox")
                        if exit_code != 0:
                            err = output.decode("utf-8", "replace")
                            for _ in test_cases:
                                results.append(
                                    ExecutionResult(
                                        False, False, "", f"Compilation failed:\n{err}"
                                    )
                                )
                            return results, 0.0, 0

                    run_cmd = config["run_cmd"]
                    exe_path = "/sandbox/solution"
                    filepath = f"/sandbox/{filename}"
                    run_list = [
                        c.format(
                            exe=exe_path,
                            filename=filepath,
                            dir="/sandbox",
                            classname=config.get("classname", "Solution"),
                        )
                        for c in run_cmd
                    ]
                    run_str = " ".join(run_list)

                    for test in test_cases:
                        start = datetime.now()
                        timeout_sec = config.get("timeout", 10)

                        sh_cmd = f"timeout {timeout_sec}s sh -c 'echo \"{test.input_data.replace(chr(34), chr(92) + chr(34))}\" | {run_str}'"

                        exit_code, output = container.exec_run(
                            ["sh", "-c", sh_cmd], workdir="/sandbox"
                        )
                        elapsed = (datetime.now() - start).total_seconds() * 1000
                        total_time += elapsed

                        out = output.decode("utf-8", "replace").strip()

                        if exit_code == 143 or exit_code == 137:
                            results.append(
                                ExecutionResult(
                                    False, False, "", "Time limit exceeded", elapsed
                                )
                            )
                        elif exit_code != 0:
                            results.append(
                                ExecutionResult(
                                    False,
                                    False,
                                    "",
                                    f"Runtime Error (exit {exit_code}): {out}",
                                    elapsed,
                                )
                            )
                        else:
                            # ROBUST OUTPUT COMPARISON
                            # Normalize both outputs for flexible comparison
                            actual_output = out.strip()
                            expected_output = test.expected_output.strip()
                            
                            # Split into lines and normalize each line
                            actual_lines = actual_output.split('\n')
                            expected_lines = expected_output.split('\n')
                            
                            # Remove empty lines at the end
                            while actual_lines and not actual_lines[-1].strip():
                                actual_lines.pop()
                            while expected_lines and not expected_lines[-1].strip():
                                expected_lines.pop()
                            
                            # Check if line counts match
                            if len(actual_lines) != len(expected_lines):
                                is_passed = False
                                print(f"[Executor] Line count mismatch: actual={len(actual_lines)}, expected={len(expected_lines)}")
                            else:
                                # Compare line by line with flexible whitespace/format handling
                                is_passed = True
                                for idx, (actual_line, expected_line) in enumerate(zip(actual_lines, expected_lines)):
                                    actual_normalized = self._normalize_output(actual_line)
                                    expected_normalized = self._normalize_output(expected_line)
                                    
                                    if actual_normalized != expected_normalized:
                                        # Try case-insensitive comparison for boolean-like values
                                        if actual_normalized.lower() != expected_normalized.lower():
                                            is_passed = False
                                            print(f"[Executor] Line {idx} mismatch:")
                                            print(f"  Actual:   '{actual_normalized}'")
                                            print(f"  Expected: '{expected_normalized}'")
                                            break
                            
                            if is_passed:
                                print(f"[Executor] ✓ Test case passed")
                            
                            results.append(
                                ExecutionResult(True, is_passed, out, None, elapsed)
                            )
                            if is_passed:
                                passed += 1

                finally:
                    try:
                        container.remove(force=True)
                    except:
                        pass

            except Exception as e:
                for _ in test_cases:
                    results.append(
                        ExecutionResult(False, False, "", f"Sandbox Error: {e}")
                    )

            return results, total_time, passed

        results, total_time, passed = await asyncio.to_thread(do_execute)
        score = (passed * 100 // len(test_cases)) if test_cases else 0
        return SubmissionResult(len(test_cases), passed, total_time, results, score)

    async def _execute_with_subprocess(
        self,
        code: str,
        language: str,
        test_cases: List[TestCase],
        function_signature: dict = None,
    ) -> SubmissionResult:
        config = LANGUAGE_CONFIG[language.lower()]
        lang = language.lower()
        
        # Add common imports/headers
        code_with_imports = add_language_imports(code, lang)
        
        # Only use the test harness if the code does NOT already contain its own I/O entry point.
        has_own_io = _code_has_own_io(code, lang)
        if not has_own_io and function_signature and function_signature.get("parameters"):
            print(f"[Executor] Using function-based harness with {len(function_signature['parameters'])} parameters")
            code_with_harness = generate_test_harness(code_with_imports, lang, function_signature)
        else:
            print(f"[Executor] Using stdin/stdout execution (code has own I/O)")
            code_with_harness = code_with_imports
        
        results = []
        total_time = 0.0
        passed = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            ext = config["extension"]
            filename = f"Solution.{ext}" if lang == "java" else f"solution.{ext}"
            filepath = os.path.join(tmpdir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code_with_harness)

            compile_cmd = config.get("compile_cmd")
            if compile_cmd:
                exe_name = os.path.join(tmpdir, "solution")
                cmd = [
                    c.format(
                        exe=exe_name,
                        filename=filepath,
                        dir=tmpdir,
                        classname=config.get("classname", "Solution"),
                    )
                    for c in compile_cmd
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    if result.returncode != 0:
                        err = result.stderr.decode("utf-8", "replace")
                        for _ in test_cases:
                            results.append(
                                ExecutionResult(
                                    False, False, "", f"Compilation failed:\n{err}"
                                )
                            )
                        return SubmissionResult(len(test_cases), 0, 0, results, 0)
                except Exception as e:
                    for _ in test_cases:
                        results.append(
                            ExecutionResult(False, False, "", f"Compilation Error: {e}")
                        )
                    return SubmissionResult(len(test_cases), 0, 0, results, 0)

            exe_name = os.path.join(tmpdir, "solution")
            run_cmd = [
                c.format(
                    filename=filepath,
                    exe=exe_name,
                    dir=tmpdir,
                    classname=config.get("classname", "Solution"),
                )
                for c in config["run_cmd"]
            ]

            for test in test_cases:
                start = datetime.now()
                try:
                    result = subprocess.run(
                        run_cmd,
                        input=test.input_data.encode("utf-8"),
                        capture_output=True,
                        timeout=config.get("timeout", 10),
                    )
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    total_time += elapsed

                    output = result.stdout.decode("utf-8", "replace").strip()

                    if result.returncode != 0:
                        results.append(
                            ExecutionResult(False, False, "", f"Runtime Error", elapsed)
                        )
                    else:
                        # ROBUST OUTPUT COMPARISON
                        # Normalize both outputs for flexible comparison
                        actual_output = output.strip()
                        expected_output = test.expected_output.strip()
                        
                        # Split into lines and normalize each line
                        actual_lines = actual_output.split('\n')
                        expected_lines = expected_output.split('\n')
                        
                        # Remove empty lines at the end
                        while actual_lines and not actual_lines[-1].strip():
                            actual_lines.pop()
                        while expected_lines and not expected_lines[-1].strip():
                            expected_lines.pop()
                        
                        # Check if line counts match
                        if len(actual_lines) != len(expected_lines):
                            is_passed = False
                            print(f"[Executor] Line count mismatch: actual={len(actual_lines)}, expected={len(expected_lines)}")
                        else:
                            # Compare line by line with flexible whitespace/format handling
                            is_passed = True
                            for idx, (actual_line, expected_line) in enumerate(zip(actual_lines, expected_lines)):
                                actual_normalized = self._normalize_output(actual_line)
                                expected_normalized = self._normalize_output(expected_line)
                                
                                if actual_normalized != expected_normalized:
                                    # Try case-insensitive comparison for boolean-like values
                                    if actual_normalized.lower() != expected_normalized.lower():
                                        is_passed = False
                                        print(f"[Executor] Line {idx} mismatch:")
                                        print(f"  Actual:   '{actual_normalized}'")
                                        print(f"  Expected: '{expected_normalized}'")
                                        break
                        
                        if is_passed:
                            print(f"[Executor] ✓ Test case passed")
                        
                        results.append(
                            ExecutionResult(True, is_passed, output, None, elapsed)
                        )
                        if is_passed:
                            passed += 1

                except subprocess.TimeoutExpired:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    total_time += elapsed
                    results.append(
                        ExecutionResult(
                            False, False, "", "Time limit exceeded", elapsed
                        )
                    )
                except Exception as e:
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    total_time += elapsed
                    results.append(
                        ExecutionResult(False, False, "", f"Error: {e}", elapsed)
                    )

        score = (passed * 100 // len(test_cases)) if test_cases else 0
        return SubmissionResult(len(test_cases), passed, total_time, results, score)


code_executor = CodeExecutor()
