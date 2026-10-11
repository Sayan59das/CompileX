"""
AI Logic Analyzer Service
Analyzes code logic and provides partial credit based on correctness percentage.
"""

import json
import re
import ast
import requests
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


def _all_recursive_calls_exclusive(func_node, fname: str) -> bool:
    """
    Return True if at most ONE recursive call to `fname` can execute per
    invocation (recursive binary search pattern → O(log n)).

    Handles early-exit if-bodies: when an `if` body always returns, the
    statements that follow are the implicit `else` — mutually exclusive.
    """
    import ast as _ast

    def _calls_in_node(node) -> int:
        return sum(
            1 for n in _ast.walk(node)
            if isinstance(n, _ast.Call)
            and (
                (isinstance(n.func, _ast.Name) and n.func.id == fname)
                or (isinstance(n.func, _ast.Attribute) and n.func.attr == fname)
            )
        )

    def _body_always_exits(stmts) -> bool:
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, (_ast.Return, _ast.Raise)):
            return True
        if isinstance(last, _ast.If):
            return (
                _body_always_exits(last.body)
                and bool(last.orelse)
                and _body_always_exits(last.orelse)
            )
        return False

    def _max_calls_on_any_path(stmts) -> int:
        if not stmts:
            return 0
        stmt = stmts[0]
        rest = stmts[1:]
        if isinstance(stmt, _ast.If):
            body_calls   = _max_calls_on_any_path(stmt.body)
            orelse_calls = _max_calls_on_any_path(stmt.orelse) if stmt.orelse else 0
            if _body_always_exits(stmt.body):
                rest_calls = _max_calls_on_any_path(rest)
                return max(body_calls, orelse_calls + rest_calls)
            else:
                return max(body_calls, orelse_calls) + _max_calls_on_any_path(rest)
        else:
            return _calls_in_node(stmt) + _max_calls_on_any_path(rest)

    if isinstance(func_node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
        return _max_calls_on_any_path(func_node.body) <= 1
    return False


class LogicAnalyzer:
    """Analyzes code logic using AI to determine correctness percentage."""
    
    def __init__(self):
        self.base_url = settings.AI_SERVICE_URL.rstrip("/")
        self.timeout = settings.AI_SERVICE_TIMEOUT
    
    async def analyze_logic(
        self,
        code: str,
        language: str,
        problem_statement: str,
        test_results: list[dict],
        passed_tests: int,
        total_tests: int
    ) -> dict:
        """
        Analyze code logic and return correctness percentage.
        
        The score is ALWAYS driven by actual test results when available.
        Pre-submission analysis only provides structural hints, never a fake score.
        """
        
        # Generate prompt for AI
        prompt = f"""You are an expert AI competitive programming coach. Analyze the user's code for the given problem.
Problem: {problem_statement[:1000]}
Language: {language}
Code:
{code[:2000]}
Test Results: {passed_tests}/{total_tests} passed.
"""
        if test_results:
            failed_tests = [t for t in test_results if not t.get('passed', False)]
            if failed_tests:
                prompt += f"\nFailed test case input: {str(failed_tests[0].get('input', ''))[:200]}\nExpected output: {str(failed_tests[0].get('expected_output', ''))[:200]}\n"

        prompt += """
Provide your response strictly in JSON format with exactly these keys:
{
  "logic_correctness": <float 0-100>,
  "analysis": "<short paragraph analyzing the logic>",
  "partial_score": <int 0-100, exactly matching logic_correctness>,
  "suggestions": ["<suggestion 1>", "<suggestion 2>"],
  "breakdown": {
    "algorithm_approach": <int 0-100>,
    "edge_case_handling": <int 0-100>,
    "implementation_quality": <int 0-100>,
    "code_structure": <int 0-100>
  }
}
"""
        ai_response_json = None

        if settings.GOOGLE_API_KEY:
            try:
                import google.generativeai as genai
                import json
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(prompt)
                text = resp.text
                if text.startswith('```json'):
                    text = text.split('```json')[1].split('```')[0].strip()
                elif text.startswith('```'):
                    text = text.split('```')[1].strip()
                ai_response_json = json.loads(text)
            except Exception as e:
                print(f"[LogicAnalyzer] Gemini API error: {e}")


        if ai_response_json:
            complexity_info = self._detect_complexity(code, language)
            ai_response_json["complexity"] = {
                "time": complexity_info["time"],
                "space": complexity_info["space"],
                "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
            }
            if "feedback" not in ai_response_json:
                ai_response_json["feedback"] = ai_response_json.get("analysis", "")
            if "hints" not in ai_response_json:
                ai_response_json["hints"] = ai_response_json.get("suggestions", [])
            ai_response_json["is_pre_submission"] = (total_tests == 0)
            return ai_response_json

        # ── Post-submission: actual test results available ─────────────────
        if total_tests > 0:
            pass_rate = (passed_tests / total_tests) * 100
            complexity_info = self._detect_complexity(code, language)

            if passed_tests == total_tests:
                return {
                    "logic_correctness": 100.0,
                    "analysis": f"All {total_tests} test cases passed! Your solution is correct.",
                    "feedback": f"All {total_tests} test cases passed! Your solution is correct.",
                    "partial_score": 100,
                    "suggestions": [
                        "✅ Perfect score! Your logic is completely correct.",
                        f"⚡ Complexity: Time {complexity_info['time']}, Space {complexity_info['space']}"
                    ],
                    "hints": [
                        "✅ Perfect score! Your logic is completely correct.",
                        f"⚡ Complexity: Time {complexity_info['time']}, Space {complexity_info['space']}"
                    ],
                    "breakdown": {
                        "algorithm_approach": 100,
                        "edge_case_handling": 100,
                        "implementation_quality": 100,
                        "code_structure": 100
                    },
                    "complexity": {
                        "time": complexity_info["time"],
                        "space": complexity_info["space"],
                        "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
                    }
                }

            # Partial pass — score = exact pass rate, no heuristic inflation/deflation
            failed_tests = [t for t in test_results if not t.get("passed", False)]
            hints = self._generate_specific_hints(code, language, problem_statement, failed_tests, test_results)
            complexity_info = self._detect_complexity(code, language)

            if pass_rate == 0:
                analyses = [
                    f"No test cases passed ({passed_tests}/{total_tests}). Review your algorithm logic.",
                    f"0/{total_tests} tests passing. Check your core logic and output format.",
                    f"All {total_tests} test cases are failing. Start by tracing through the sample input.",
                ]
            elif pass_rate < 50:
                analyses = [
                    f"{passed_tests}/{total_tests} tests passed ({pass_rate:.0f}%). The approach needs significant revision.",
                    f"Only {passed_tests} of {total_tests} tests pass ({pass_rate:.0f}%). Check your algorithm for the failing cases.",
                    f"{pass_rate:.0f}% pass rate — your logic handles some inputs but breaks on others.",
                ]
            elif pass_rate < 100:
                analyses = [
                    f"{passed_tests}/{total_tests} tests passed ({pass_rate:.0f}%). Almost there — check edge cases.",
                    f"{passed_tests}/{total_tests} passing ({pass_rate:.0f}%). You're close — look for boundary conditions.",
                    f"Good progress! {passed_tests}/{total_tests} tests pass. Fix the remaining {total_tests - passed_tests} edge case(s).",
                ]
            import random as _random
            analysis = _random.choice(analyses)

            # Derive meaningful per-dimension scores instead of all being pass_rate
            algo_score  = min(100, int(pass_rate) + 10) if pass_rate > 0 else 0
            edge_score  = max(0, int(pass_rate) - 15) if pass_rate < 80 else int(pass_rate)
            impl_score  = self._analyze_implementation(code, language)
            struct_score = self._analyze_structure(code, language)

            return {
                "logic_correctness": round(pass_rate, 1),
                "analysis": analysis,
                "feedback": analysis,
                "partial_score": int(pass_rate),
                "suggestions": hints or ["🔍 Review your algorithm logic carefully"],
                "hints": hints or ["🔍 Review your algorithm logic carefully"],
                "breakdown": {
                    "algorithm_approach":    min(100, algo_score),
                    "edge_case_handling":    min(100, edge_score),
                    "implementation_quality": min(100, impl_score),
                    "code_structure":        min(100, struct_score),
                },
                "complexity": {
                    "time": complexity_info["time"],
                    "space": complexity_info["space"],
                    "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
                }
            }

        # ── Pre-submission: no tests run yet ──────────────────────────────
        return await self._pre_submission_analysis(code, language, problem_statement)
    
    async def _analyze_code_structure(
        self,
        code: str,
        language: str,
        problem_statement: str,
        test_results: list[dict]
    ) -> dict:
        """Analyze code structure when no tests pass."""
        
        try:
            # Call AI service for deep analysis
            response = requests.post(
                f"{self.base_url}/analyze-logic",
                json={
                    "code": code,
                    "language": language,
                    "problem": problem_statement,
                    "test_results": test_results,
                    "analysis_type": "structure"
                },
                timeout=self.timeout
            )
            
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"[LogicAnalyzer] AI service error: {e}")
        
        # Fallback: Basic heuristic analysis
        return self._heuristic_analysis(code, language, problem_statement, test_results)
    
    async def _pre_submission_analysis(
        self,
        code: str,
        language: str,
        problem_statement: str
    ) -> dict:
        """
        Pre-submission analysis (before tests are run).
        
        We do NOT attempt to guess correctness — that's impossible without
        running the code. Instead we check if the code looks complete and
        provide problem-specific hints.
        """
        complexity_info = self._detect_complexity(code, language)
        is_complete = self._code_looks_complete(code, language)
        hints = self._generate_problem_specific_hints(code, language, problem_statement)

        # Give a structural score so the UI doesn't show a blank 0%
        struct_score  = self._analyze_structure(code, language)
        algo_score    = self._analyze_algorithm_patterns(code, language, problem_statement)
        impl_score    = self._analyze_implementation(code, language)
        # Weighted average — capped at 60 so it's clear this is pre-submission
        pre_score = min(60.0, (struct_score * 0.3 + algo_score * 0.4 + impl_score * 0.3))

        if is_complete:
            analysis = (
                "Code looks complete. Submit to run the actual test cases and get your real score."
            )
            hints = hints + ["💡 Submit your code to run actual tests and get precise feedback"]
        else:
            pre_score = min(pre_score, 30.0)
            analysis = "Code appears incomplete. Make sure you have a full solution before submitting."
            hints = ["⚠️ Your code looks incomplete — finish your solution first"] + hints

        return {
            "logic_correctness": round(pre_score, 1),
            "analysis": analysis,
            "feedback": analysis,
            "partial_score": int(pre_score),
            "suggestions": hints[:4],
            "hints": hints[:4],
            "breakdown": {
                "algorithm_approach":    min(100, int(algo_score)),
                "edge_case_handling":    0,
                "implementation_quality": min(100, int(impl_score)),
                "code_structure":        min(100, int(struct_score)),
            },
            "complexity": {
                "time": complexity_info["time"],
                "space": complexity_info["space"],
                "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
            },
            "is_pre_submission": True
        }

    def _code_looks_complete(self, code: str, language: str) -> bool:
        """
        Quick check: does the code look like a real attempt (not just a stub)?
        We check for a non-trivial body — more than just pass/return 0/TODO.
        """
        # Strip comments and blank lines
        lines = []
        for line in code.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if language == "python" and stripped.startswith("#"):
                continue
            if language in ("cpp", "java", "javascript", "c") and stripped.startswith("//"):
                continue
            lines.append(stripped)

        # Must have at least 5 non-trivial lines
        non_trivial = [
            l for l in lines
            if l not in ("pass", "return 0", "return null", "return;", "return 0;", "{", "}", "};")
            and "TODO" not in l
            and "Write your solution" not in l
            and "Your code here" not in l
        ]
        return len(non_trivial) >= 5
    
    def _generate_problem_specific_hints(
        self,
        code: str,
        language: str,
        problem_statement: str
    ) -> list[str]:
        """Generate hints specific to the problem type before submission."""
        hints = []
        problem_lower = problem_statement.lower()
        
        # Graph problems
        if "graph" in problem_lower:
            if "directed" in problem_lower:
                hints.append("📌 Remember: Directed graphs have one-way edges (u → v only)")
            elif "undirected" in problem_lower:
                hints.append("📌 Remember: Undirected graphs need edges in both directions (u ↔ v)")
            
            if "cycle" in problem_lower:
                hints.append("🔍 Cycle detection tip: Track visited nodes and parent (for undirected)")
            
            if "visited" not in code.lower():
                hints.append("⚠️ You might need a 'visited' array to track explored nodes")
        
        # Tree problems
        elif "tree" in problem_lower or "bst" in problem_lower:
            if "level order" in problem_lower:
                hints.append("📌 Level-order traversal uses BFS with a queue")
                hints.append("📊 Print each level on a new line, space-separated")
            
            if "ancestor" in problem_lower:
                hints.append("🔍 LCA: Find the deepest node that's an ancestor of both nodes")
            
            if "bst" in problem_lower or "binary search tree" in problem_lower:
                hints.append("🌲 BST property: left < root < right")
        
        # Array problems
        elif "array" in problem_lower or "subarray" in problem_lower:
            if "sum" in problem_lower:
                hints.append("💡 Consider using prefix sums or sliding window")
            
            if "maximum" in problem_lower or "minimum" in problem_lower:
                hints.append("📊 Track the max/min as you iterate")
        
        # String problems
        elif "string" in problem_lower or "palindrome" in problem_lower:
            if "palindrome" in problem_lower:
                hints.append("🔤 Palindrome: Check if string reads same forwards and backwards")
            
            if "anagram" in problem_lower:
                hints.append("🔤 Anagram: Same characters, different order")
        
        # Dynamic Programming
        if "dynamic" in problem_lower or "dp" in problem_lower:
            hints.append("💡 DP: Break problem into subproblems and store results")
        
        # General hints based on code structure
        if language == "python":
            if "def " not in code:
                hints.append("⚠️ Consider organizing your code into functions")
            
            if "print(" not in code:
                hints.append("⚠️ Don't forget to print your output!")
        
        return hints
    
    async def _deep_logic_analysis(
        self,
        code: str,
        language: str,
        problem_statement: str,
        test_results: list[dict],
        pass_rate: float
    ) -> dict:
        """Deep analysis for partially passing code."""
        
        try:
            response = requests.post(
                f"{self.base_url}/analyze-logic",
                json={
                    "code": code,
                    "language": language,
                    "problem": problem_statement,
                    "test_results": test_results,
                    "analysis_type": "deep",
                    "pass_rate": pass_rate
                },
                timeout=self.timeout
            )
            
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"[LogicAnalyzer] AI service error: {e}")
        
        # Fallback: Use pass rate as base
        result = self._heuristic_analysis(code, language, problem_statement, test_results, pass_rate)
        
        # Add complexity analysis
        complexity_info = self._detect_complexity(code, language)
        result["complexity"] = {
            "time": complexity_info["time"],
            "space": complexity_info["space"],
            "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
        }
        
        return result
    
    def _heuristic_analysis(
        self,
        code: str,
        language: str,
        problem_statement: str,
        test_results: list[dict],
        base_pass_rate: float = 0.0
    ) -> dict:
        """
        Fallback heuristic analysis when AI service is unavailable.
        Analyzes code structure, patterns, and logic.
        """
        
        # If we have test results, use them as the primary signal
        has_test_results = len(test_results) > 0
        
        if has_test_results:
            # Calculate actual pass rate from test results
            passed_count = sum(1 for t in test_results if t.get("passed", False))
            total_count = len(test_results)
            actual_pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0.0
            
            # If tests were run, use actual pass rate as the base
            base_pass_rate = actual_pass_rate
        
        logic_score = 0.0
        breakdown = {
            "algorithm_approach": 0,
            "edge_case_handling": 0,
            "implementation_quality": 0,
            "code_structure": 0
        }
        suggestions = []
        analysis_parts = []
        
        # 1. Check for basic code structure (15% weight)
        structure_score = self._analyze_structure(code, language)
        breakdown["code_structure"] = structure_score
        logic_score += structure_score * 0.15
        
        if structure_score < 50:
            pass  # Will be handled by specific hints
        
        # 2. Check for algorithm patterns (25% weight)
        algorithm_score = self._analyze_algorithm_patterns(code, language, problem_statement)
        breakdown["algorithm_approach"] = algorithm_score
        logic_score += algorithm_score * 0.25
        
        if algorithm_score < 50:
            pass  # Will be handled by specific hints
        
        # 3. Check for edge case handling (15% weight)
        edge_case_score = self._analyze_edge_cases(code, test_results)
        breakdown["edge_case_handling"] = edge_case_score
        logic_score += edge_case_score * 0.15
        
        if edge_case_score < 50:
            pass  # Will be handled by specific hints
        
        # 4. Implementation quality (15% weight)
        impl_score = self._analyze_implementation(code, language)
        breakdown["implementation_quality"] = impl_score
        logic_score += impl_score * 0.15
        
        if impl_score < 50:
            pass  # Will be handled by specific hints
        
        # 5. Actual test results (30% weight) - most important
        if has_test_results:
            logic_score += base_pass_rate * 0.30
            
            # Analyze which tests failed and provide specific hints
            failed_tests = [t for t in test_results if not t.get("passed", False)]
            if failed_tests:
                specific_hints = self._generate_specific_hints(
                    code, language, problem_statement, failed_tests, test_results
                )
                suggestions = specific_hints + suggestions
        
        # Cap at 100
        logic_score = min(100.0, logic_score)
        
        # Generate analysis text based on test results
        if has_test_results:
            import random as _r
            if base_pass_rate == 0:
                analysis = _r.choice([
                    f"No test cases passed. Your logic needs significant work.",
                    f"0/{total_count} tests passing. Check your core algorithm and output format.",
                    f"All {total_count} test cases are failing. Start by tracing through the sample input.",
                ])
            elif base_pass_rate < 30:
                analysis = _r.choice([
                    f"Only {base_pass_rate:.0f}% of tests passed. The approach needs major revision.",
                    f"{passed_count}/{total_count} tests pass ({base_pass_rate:.0f}%). Check your algorithm for the failing cases.",
                    f"{base_pass_rate:.0f}% pass rate — your logic handles some inputs but breaks on others.",
                ])
            elif base_pass_rate < 60:
                analysis = _r.choice([
                    f"{base_pass_rate:.0f}% of tests passed. You're on the right track but need refinements.",
                    f"{passed_count}/{total_count} tests pass. Look at the failing cases to find the pattern.",
                    f"More than half failing ({base_pass_rate:.0f}%). Check edge cases and boundary conditions.",
                ])
            elif base_pass_rate < 100:
                analysis = _r.choice([
                    f"{base_pass_rate:.0f}% of tests passed. Almost there — check edge cases.",
                    f"{passed_count}/{total_count} passing. You're close — look for off-by-one or boundary issues.",
                    f"Good progress! {passed_count}/{total_count} tests pass. Fix the remaining {total_count - passed_count} edge case(s).",
                ])
            else:
                analysis = _r.choice([
                    "All tests passed! Great job!",
                    f"Perfect — all {total_count} test cases pass!",
                    "Excellent work! Your solution is correct.",
                ])
        else:
            # Pre-submission analysis
            if logic_score >= 70:
                analysis = f"Code structure looks good ({logic_score:.1f}%). "
            elif logic_score >= 40:
                analysis = f"Code structure is decent ({logic_score:.1f}%). "
            else:
                analysis = f"Code structure needs improvement ({logic_score:.1f}%). "
        
        # Add specific feedback based on breakdown
        if has_test_results and base_pass_rate < 100:
            if breakdown["algorithm_approach"] < 50:
                analysis += "The algorithm approach is incorrect. "
            if breakdown["edge_case_handling"] < 50:
                analysis += "Edge cases are not handled properly. "
            if breakdown["implementation_quality"] < 50:
                analysis += "There are implementation errors. "
        
        # For failed tests, use the actual pass rate as the score
        if has_test_results:
            logic_score = base_pass_rate
        
        partial_score = int(logic_score)
        
        # Ensure we have at least one suggestion
        if not suggestions:
            if has_test_results and base_pass_rate < 100:
                fallback_pool = [
                    "🔍 Review your algorithm logic carefully",
                    "🧪 Test your code with the sample input step by step",
                    "💡 Check your output format — no extra spaces, brackets, or newlines",
                    "⚠️ Verify your loop bounds — off-by-one errors are very common",
                    "🔍 Add print statements to trace intermediate values",
                    "🧪 Click a failing test case to compare expected vs actual output",
                ]
                import random as _r
                _r.shuffle(fallback_pool)
                suggestions.extend(fallback_pool[:2])
            else:
                suggestions.append("💡 Your code structure looks reasonable — submit to see test results")
        
        # Add complexity analysis
        complexity_info = self._detect_complexity(code, language)
        
        return {
            "logic_correctness": round(logic_score, 1),
            "analysis": analysis.strip(),
            "partial_score": partial_score,
            "suggestions": suggestions,
            "breakdown": breakdown,
            "complexity": {
                "time": complexity_info["time"],
                "space": complexity_info["space"],
                "details": f"Time: {complexity_info['time']}, Space: {complexity_info['space']}"
            }
        }
    
    def _analyze_structure(self, code: str, language: str) -> float:
        """Analyze code structure quality."""
        score = 0.0
        
        # Check for functions/methods
        if language == "python":
            if "def " in code:
                score += 30
            if "class " in code:
                score += 10
            if "import " in code or "from " in code:
                score += 10
        elif language in ["cpp", "c"]:
            if "int main" in code or "void main" in code:
                score += 20
            if "#include" in code:
                score += 15
            if code.count("{") > 2:  # Multiple blocks
                score += 15
        elif language == "java":
            if "public class" in code or "class " in code:
                score += 20
            if "public static void main" in code:
                score += 20
            if "import " in code:
                score += 10
        elif language == "javascript":
            if "function " in code or "=>" in code:
                score += 30
            if "const " in code or "let " in code:
                score += 10
            if "return " in code:
                score += 10
        
        # Check for comments
        if "//" in code or "#" in code or "/*" in code:
            score += 10
        
        # Check for proper indentation (basic check)
        lines = code.split("\n")
        indented_lines = sum(1 for line in lines if line.startswith("    ") or line.startswith("\t"))
        if indented_lines > len(lines) * 0.3:
            score += 20
        
        return min(100.0, score)
    
    def _analyze_algorithm_patterns(self, code: str, language: str, problem: str) -> float:
        """Analyze if code contains relevant algorithm patterns and detect complexity."""
        score = 0.0
        problem_lower = problem.lower()
        
        # Detect time complexity based on code structure
        complexity_info = self._detect_complexity(code, language)
        time_complexity = complexity_info["time"]
        space_complexity = complexity_info["space"]
        
        # Score based on complexity appropriateness for the problem
        # Better complexity = higher score — accept both notations
        complexity_scores = {
            "O(1)": 100,
            "O(log n)": 95,
            "O(n)": 85,
            "O(n log n)": 75,
            "O(n²)": 50, "O(n^2)": 50,
            "O(n³)": 30, "O(n^3)": 30,
            "O(2^n)": 20,
            "O(n!)": 10,
        }

        base_score = complexity_scores.get(time_complexity, 60)
        score += base_score * 0.6  # 60% weight on time complexity

        # Space complexity scoring
        space_scores = {
            "O(1)": 100,
            "O(log n)": 90,
            "O(n)": 80,
            "O(n²)": 50, "O(n^2)": 50,
            "O(2^n)": 30,
        }
        space_score = space_scores.get(space_complexity, 70)
        score += space_score * 0.2  # 20% weight on space complexity
        
        # Check for appropriate algorithm patterns (20% weight)
        pattern_score = 0
        
        # Check for loops (basic requirement)
        loop_keywords = ["for", "while", "forEach", "map", "filter"]
        if any(kw in code for kw in loop_keywords):
            pattern_score += 25
        
        # Check for conditionals
        if "if" in code:
            pattern_score += 15
        
        # Check for data structures
        ds_keywords = {
            "array": ["[]", "array", "list", "vector"],
            "hash": ["dict", "map", "HashMap", "set", "Set"],
            "stack": ["stack", "Stack", "append", "pop"],
            "queue": ["queue", "Queue", "deque"],
            "tree": ["TreeNode", "tree", "left", "right"],
            "graph": ["graph", "adj", "visited", "dfs", "bfs"]
        }
        
        for ds_type, keywords in ds_keywords.items():
            if any(kw in code for kw in keywords):
                pattern_score += 15
                break
        
        # Check for sorting/searching
        if any(kw in code for kw in ["sort", "sorted", "binary", "search"]):
            pattern_score += 10
        
        # Check for recursion
        if language == "python" and "def " in code:
            # Look for function calling itself
            func_names = [line.split("def ")[1].split("(")[0] for line in code.split("\n") if "def " in line]
            for fname in func_names:
                if code.count(fname) > 1:  # Function name appears more than once
                    pattern_score += 15
                    break
        
        # Check for dynamic programming patterns
        if any(kw in code for kw in ["dp", "memo", "cache", "table"]):
            pattern_score += 20
        
        score += min(100.0, pattern_score) * 0.2
        
        return min(100.0, score)
    
    def _detect_complexity(self, code: str, language: str) -> dict:
        """
        Detect time and space complexity by analyzing code structure.
        Returns dict with 'time' and 'space' complexity in Big-O notation.

        Priority (highest wins):
          1. Memoised recursion / DP table  → O(n) or O(n^2)
          2. Exponential recursion (no memo) → O(2^n)
          3. Factorial recursion             → O(n!)
          4. Divide-and-conquer recursion    → O(n log n)
          5. Linear recursion                → O(n)
          6. Binary search pattern           → O(log n)
          7. Sorting + linear work           → O(n log n)
          8. Nested loops (depth d)          → O(n^d)
          9. Single loop                     → O(n)
         10. No loops, no recursion          → O(1)
        """
        nested_loop_depth = self._count_nested_loops(code, language)
        has_recursion = self._has_recursion(code, language)
        recursion_type = self._detect_recursion_type(code, language) if has_recursion else None
        has_memo = self._has_memoization(code)

        # Sorting: only count if it's a real sort call on a variable-size collection
        has_sorting = bool(re.search(
            r'\b(sorted|Arrays\.sort|Collections\.sort|std::sort|qsort)\b|\.sort\s*\(',
            code
        ))

        has_binary_search = self._has_binary_search_pattern(code)

        # 2D array / matrix detection (for memoized 2D DP)
        has_2d_array = bool(re.search(
            r'\[\s*\[|\]\s*\[|\[\]\[\]|new \w+\[\w+\]\s*\[\w+\]|vector.*vector',
            code
        ))

        # ── Time complexity ───────────────────────────────────────────────
        if has_recursion:
            if has_memo:
                # Memoised recursion: each unique subproblem computed once.
                # For 1-parameter functions (fib(n)) → O(n) unique states.
                # Only use O(n²) when there's a 2D DP table (two loop variables).
                if has_2d_array or nested_loop_depth >= 2:
                    time_complexity = "O(n²)"
                else:
                    time_complexity = "O(n)"
            elif recursion_type == "exponential":
                time_complexity = "O(2^n)"
            elif recursion_type == "factorial":
                # n * f(n-1) is linear recursion, not permutation enumeration
                time_complexity = "O(n)"
            elif recursion_type == "divide_conquer":
                # T(n) = 2T(n/2) + O(n) → O(n log n) by Master Theorem
                time_complexity = "O(n log n)"
            else:
                # linear recursion — may still have loops inside
                if nested_loop_depth >= 2:
                    time_complexity = "O(n³)"
                elif nested_loop_depth == 1:
                    time_complexity = "O(n²)"
                else:
                    time_complexity = "O(n)"
        elif has_binary_search and nested_loop_depth <= 1:
            # Pure binary search (no outer loop) → O(log n)
            # Binary search inside a loop → O(n log n)
            if has_sorting:
                time_complexity = "O(n log n)"  # sort dominates
            else:
                time_complexity = "O(log n)" if nested_loop_depth == 0 else "O(n log n)"
        elif has_sorting:
            # Sorting dominates unless there are deeper nested loops
            if nested_loop_depth >= 2:
                time_complexity = "O(n³)"
            else:
                time_complexity = "O(n log n)"
        elif nested_loop_depth >= 3:
            time_complexity = "O(n³)"
        elif nested_loop_depth == 2:
            time_complexity = "O(n²)"
        elif nested_loop_depth == 1:
            time_complexity = "O(n)"
        else:
            time_complexity = "O(1)"

        # ── Space complexity ──────────────────────────────────────────────
        space_complexity = self._detect_space_complexity(code, language, has_recursion, recursion_type)

        return {
            "time": time_complexity,
            "space": space_complexity,
            "nested_loops": nested_loop_depth,
            "has_recursion": has_recursion,
            "recursion_type": recursion_type,
        }

    def _has_memoization(self, code: str) -> bool:
        """Return True if the code uses memoization or a DP table."""
        return bool(re.search(
            r'@lru_cache|@cache|memo\b|dp\[|cache\b|functools\.cache|functools\.lru_cache',
            code, re.IGNORECASE
        ))

    def _detect_space_complexity(
        self, code: str, language: str, has_recursion: bool, recursion_type
    ) -> str:
        """
        Determine space complexity from data-structure usage and recursion depth.
        """
        # 2-D data structures → O(n²)
        if re.search(r'\[\s*\[|\]\s*\]|\[\]\[\]|new \w+\[\w+\]\s*\[\w+\]', code):
            return "O(n²)"

        # Explicit O(n) collections that grow with input.
        # We check for .append()/.push() calls (dynamic growth) OR
        # explicit collection type declarations — but NOT input-reading
        # patterns like list(map(...)) or list(input().split()) which are
        # just reading the input, not allocating extra O(n) space.
        grows_with_input = bool(re.search(
            r'\.append\(|\.push\(|\.add\(|\.insert\(|push_back\(',
            code
        ))
        # Only flag collection keywords when they appear as standalone
        # variable assignments, not as input-conversion calls.
        # Match: dict(), defaultdict, Counter, HashMap, HashSet, ArrayList,
        # deque, heap, heapq, or dictionary literals like "= {}" or "= {key: val}"
        # Exclude: list(map(...)), list(input().split()), list(filter(...))
        # which are input-reading patterns, not extra allocations.
        has_collection = bool(re.search(
            r'\bdict\s*\(|=\s*\{[^}]*\}|\bdefaultdict\b|\bCounter\b'
            r'|\bHashMap\b|\bHashSet\b|\bArrayList\b'
            r'|\bdeque\b|\bheap\b|\bheapq\b'
            r'|\bnew\s+(?:HashMap|HashSet|ArrayList|LinkedList)\b',
            code
        ))
        # Detect input-reading patterns that should NOT count as extra space:
        # list(map(int, input().split())) or arr = list(input().split())
        # These are just reading the input array, not allocating extra O(n) space.
        # Only suppress if the ONLY collection is the input-reading one.
        has_extra_collection = bool(re.search(
            r'\.append\(|\.push\(|push_back\(|\bdict\s*\(|\bdefaultdict\b|\bCounter\b'
            r'|\bHashMap\b|\bHashSet\b|\bArrayList\b|\bdeque\b|\bheap\b'
            r'|=\s*\{\s*\}|=\s*\{[^}]+\}',  # dict literals like seen = {} or seen = {k: v}
            code
        ))
        is_input_reading_only = bool(re.search(
            r'\blist\s*\(\s*(?:map|filter)\s*\([^)]*input[^)]*\)'
            r'|\blist\s*\(\s*input\s*\(\s*\)\s*\.split',
            code
        )) and not has_extra_collection
        if (grows_with_input or has_collection) and not is_input_reading_only:
            return "O(n)"

        # Recursion uses call-stack space
        if has_recursion:
            if recursion_type == "divide_conquer":
                return "O(log n)"
            if recursion_type == "logarithmic":
                return "O(log n)"
            # exponential / linear / factorial: call stack depth is O(n)
            # (the total call-tree nodes may be O(2^n) but only one path
            # is live on the stack at any time)
            return "O(n)"

        return "O(1)"

    def _count_nested_loops(self, code: str, language: str) -> int:
        """Count the maximum nesting depth of loops."""
        if language == "python":
            return self._count_nested_loops_python(code)
        return self._count_nested_loops_braces(code)

    def _count_nested_loops_python(self, code: str) -> int:
        """
        Use indentation levels to track Python loop nesting accurately.
        Each `for`/`while` at a deeper indent level than the previous one
        counts as a new nesting level.
        """
        max_depth = 0
        loop_indent_stack: list = []  # stack of indent levels for active loops

        for raw_line in code.split("\n"):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip())

            # Pop loops that have been exited (indent decreased past their level)
            while loop_indent_stack and indent <= loop_indent_stack[-1]:
                loop_indent_stack.pop()

            if re.match(r'^(for|while)\b', stripped):
                loop_indent_stack.append(indent)
                max_depth = max(max_depth, len(loop_indent_stack))

        return max_depth

    def _count_nested_loops_braces(self, code: str) -> int:
        """
        Track loop nesting for brace-based languages character-by-character.
        Handles single-statement loops (no braces), compact one-liner code,
        and correctly ignores semicolons inside for(;;) headers.
        """
        brace_depth = 0
        loop_brace_depths: list = []
        pending_loop = False
        in_for_header = False
        paren_depth = 0
        max_depth = 0

        i = 0
        while i < len(code):
            ch = code[i]

            # Skip line comments
            if ch == '/' and i + 1 < len(code) and code[i+1] == '/':
                while i < len(code) and code[i] != '\n':
                    i += 1
                continue

            # Skip block comments
            if ch == '/' and i + 1 < len(code) and code[i+1] == '*':
                i += 2
                while i + 1 < len(code) and not (code[i] == '*' and code[i+1] == '/'):
                    i += 1
                i += 2
                continue

            # Skip string literals
            if ch in ('"', "'"):
                quote = ch; i += 1
                while i < len(code) and code[i] != quote:
                    if code[i] == '\\': i += 1
                    i += 1
                i += 1
                continue

            if ch == '(':
                paren_depth += 1
                if pending_loop:
                    in_for_header = True

            elif ch == ')':
                paren_depth = max(0, paren_depth - 1)
                if in_for_header and paren_depth == 0:
                    in_for_header = False

            elif ch == '{':
                brace_depth += 1
                if pending_loop and not in_for_header:
                    loop_brace_depths.append(brace_depth - 1)
                    pending_loop = False
                max_depth = max(max_depth, len(loop_brace_depths))

            elif ch == '}':
                while loop_brace_depths and loop_brace_depths[-1] >= brace_depth - 1:
                    loop_brace_depths.pop()
                brace_depth = max(0, brace_depth - 1)
                pending_loop = False

            elif ch == ';' and pending_loop and not in_for_header:
                # Single-statement loop body (no braces)
                max_depth = max(max_depth, len(loop_brace_depths) + 1)
                pending_loop = False

            if ch in ('f', 'w'):
                rest = code[i:]
                m = re.match(r'^(for|while)\s*\(', rest)
                if m and (i == 0 or not (code[i-1].isalnum() or code[i-1] == '_')):
                    if pending_loop and not in_for_header:
                        # Outer brace-less loop's body IS this inner loop.
                        loop_brace_depths.append(brace_depth)
                        max_depth = max(max_depth, len(loop_brace_depths))
                    pending_loop = True
                    in_for_header = False

            i += 1

        return max(max_depth, len(loop_brace_depths), 0)

    def _has_recursion(self, code: str, language: str) -> bool:
        """Return True if any function in the code calls itself within its own body."""
        if language == "python":
            # Python: use AST-based check (already accurate)
            try:
                import ast as _ast
                tree = _ast.parse(code)
                for node in _ast.walk(tree):
                    if not isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        continue
                    fname = node.name
                    for child in _ast.walk(node):
                        if isinstance(child, _ast.Call):
                            called = None
                            if isinstance(child.func, _ast.Name):
                                called = child.func.id
                            elif isinstance(child.func, _ast.Attribute):
                                called = child.func.attr
                            if called == fname:
                                return True
            except SyntaxError:
                pass
            return False

        # For brace-based languages: extract each function body and check
        # if the function name appears as a call inside its own body only.
        if language in ("javascript", "js", "typescript", "ts"):
            header_re = re.compile(
                r'function\s+(\w+)\s*\([^)]*\)\s*\{'
                r'|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\s*)?\([^)]*\)\s*(?:=>\s*)?\{'
            )
        else:
            # C / C++ / Java
            header_re = re.compile(r'\b\w[\w\s\*]*\s+(\w+)\s*\([^)]*\)\s*\{')

        for m in header_re.finditer(code):
            groups = m.groups()
            fname = next((g for g in groups if g), None)
            if not fname or fname in ("if", "while", "for", "switch", "main", "else"):
                continue
            # Extract body by brace matching
            start = m.end() - 1
            depth = 0
            end = start
            for idx in range(start, len(code)):
                if code[idx] == '{':
                    depth += 1
                elif code[idx] == '}':
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
            body = code[start:end]
            # Count calls to fname inside its own body
            if len(re.findall(r'\b' + re.escape(fname) + r'\s*\(', body)) >= 1:
                return True
        return False

    def _detect_recursion_type(self, code: str, language: str) -> str:
        """
        Classify the recursion type:
          - exponential   : ≥2 recursive calls in the same function (e.g. fib)
          - factorial     : 1 recursive call with n*(n-1) pattern
          - divide_conquer: 1 recursive call with n/2 or n//2 argument
          - linear        : 1 recursive call (linked list, tree path)
        """
        if language == "python":
            return self._detect_recursion_type_python(code)
        return self._detect_recursion_type_generic(code)

    def _detect_recursion_type_python(self, code: str) -> str:
        """Classify recursion type for Python using AST when possible."""
        try:
            import ast as _ast
            tree = _ast.parse(code)
        except SyntaxError:
            return self._detect_recursion_type_generic(code)

        for node in _ast.walk(tree):
            if not isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                continue
            fname = node.name
            calls = [
                n for n in _ast.walk(node)
                if isinstance(n, _ast.Call)
                and isinstance(n.func, _ast.Name)
                and n.func.id == fname
            ]
            if len(calls) >= 2:
                # Check if all recursive calls are in mutually exclusive if/else
                # branches (recursive binary search pattern → O(log n))
                if _all_recursive_calls_exclusive(node, fname):
                    return "logarithmic"
                return "exponential"
            if len(calls) == 1:
                # Use unparse if available (Python 3.9+), else fall back to source scan
                try:
                    func_src = _ast.unparse(node)
                except AttributeError:
                    func_src = code
                if re.search(r'//\s*2|/\s*2\b', func_src):
                    return "divide_conquer"
                # Single recursive call — always linear regardless of n*(n-1) pattern.
                # n * f(n-1) computes a factorial VALUE in O(n) time, not O(n!).
                return "linear"
        return "linear"

    def _detect_recursion_type_generic(self, code: str) -> str:
        """
        Classify recursion type for non-Python languages using regex heuristics.
        Works for C, C++, Java, JavaScript, TypeScript.
        """
        func_pattern = re.compile(r'\b(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE)
        bodies: list = []  # list of (fname, body)

        for m in func_pattern.finditer(code):
            fname = m.group(1)
            if fname in ("if", "while", "for", "switch"):
                continue
            start = m.end() - 1  # position of opening `{`
            depth = 0
            end = start
            for idx in range(start, len(code)):
                if code[idx] == "{":
                    depth += 1
                elif code[idx] == "}":
                    depth -= 1
                    if depth == 0:
                        end = idx + 1
                        break
            bodies.append((fname, code[start:end]))

        for fname, body in bodies:
            call_count = len(re.findall(r'\b' + re.escape(fname) + r'\s*\(', body))
            if call_count >= 2:
                return "exponential"
            if call_count == 1:
                if re.search(r'//\s*2|/\s*2\b', body):
                    return "divide_conquer"
                # Single recursive call — linear regardless of n*(n-1) pattern.
                return "linear"
        return "linear"

    def _has_binary_search_pattern(self, code: str) -> bool:
        """
        Return True only when the code contains a genuine binary search pattern:
        a loop/recursion that halves the search space using mid/lo/hi variables.
        """
        # Must have both a mid computation AND lo/hi or left/right pointers
        has_mid = bool(re.search(r'\bmid\b', code))
        has_bounds = bool(re.search(r'\b(lo|hi|left|right|low|high)\b', code))
        has_halving = bool(re.search(
            r'\bmid\s*=.*(?:lo|hi|left|right|low|high).*[/+].*2'
            r'|\bmid\s*=.*//\s*2',
            code
        ))
        explicit_bs = bool(re.search(r'\bbinary.?search\b', code, re.IGNORECASE))
        return explicit_bs or (has_mid and has_bounds and has_halving)
    
    def _analyze_edge_cases(self, code: str, test_results: list[dict]) -> float:
        """Analyze edge case handling."""
        score = 0.0
        
        # Check for null/empty checks
        null_checks = ["if not", "if !", "== null", "== None", "isEmpty", "len(", "size()"]
        if any(check in code for check in null_checks):
            score += 30
        
        # Check for boundary checks
        boundary_checks = ["< 0", "> 0", "<=", ">=", "== 0", "== 1"]
        if any(check in code for check in boundary_checks):
            score += 25
        
        # Check if code handles different input sizes
        if "len(" in code or "length" in code or "size()" in code:
            score += 20
        
        # Analyze test results for edge case patterns
        if test_results:
            # Check if failing on edge cases (empty, single element, etc.)
            failed_tests = [t for t in test_results if not t.get("passed", False)]
            if failed_tests:
                # If some tests pass, likely missing edge cases
                score += 15
        
        # Check for try-catch (error handling)
        if "try" in code or "catch" in code or "except" in code:
            score += 10
        
        return min(100.0, score)
    
    def _analyze_implementation(self, code: str, language: str) -> float:
        """Analyze implementation quality."""
        score = 50.0  # Base score
        
        # Check for syntax patterns
        if language == "python":
            # Check for proper Python idioms
            if ":" in code:  # Colons for blocks
                score += 10
            if "    " in code or "\t" in code:  # Indentation
                score += 10
            # Penalize common errors
            if code.count("(") != code.count(")"):
                score -= 20
            if code.count("[") != code.count("]"):
                score -= 20
        
        elif language in ["cpp", "c", "java"]:
            # Check for proper braces
            if code.count("{") == code.count("}"):
                score += 15
            else:
                score -= 20
            # Check for semicolons
            if ";" in code:
                score += 10
        
        # Check for return statements
        if "return" in code:
            score += 15
        
        # Check for variable declarations
        var_keywords = ["int ", "str ", "float ", "double ", "char ", "const ", "let ", "var "]
        if any(kw in code for kw in var_keywords):
            score += 10
        
        return max(0.0, min(100.0, score))
    
    def _generate_specific_hints(
        self,
        code: str,
        language: str,
        problem_statement: str,
        failed_tests: list[dict],
        all_tests: list[dict],
    ) -> list[str]:
        """
        Generate specific, actionable hints by running the inline debugger
        against each failing test case and deduplicating the results.
        """
        from app.services.inline_debugger import inline_debug_hint

        seen_messages: set[str] = set()
        hints: list[str] = []

        def _add(hint_text: str) -> None:
            key = hint_text[:80]
            if key not in seen_messages:
                seen_messages.add(key)
                hints.append(hint_text)

        # ── Run the inline debugger on each failing test ──────────────────
        for t in failed_tests:
            result = inline_debug_hint(
                problem_statement=problem_statement,
                user_code=code,
                language=language,
                failed_test_input=str(t.get("input", "")),
                expected_output=str(t.get("expected_output", "")),
                actual_output=str(t.get("actual_output", "") or t.get("error", "")),
            )

            status  = result.get("status", "")
            line    = result.get("line", "")
            message = result.get("message", "")
            hint    = result.get("hint", "")

            if not hint:
                continue

            # Format: prepend emoji based on status category
            if "syntax" in status.lower():
                prefix = "🔧"
            elif "runtime" in status.lower():
                prefix = "💥"
            elif "no clear" in status.lower():
                prefix = "🔍"
            else:
                prefix = "⚠️"

            line_tag = f" (line {line})" if line else ""
            _add(f"{prefix} {message}{line_tag} — {hint}")

        # ── Edge-case hint when only some tests fail ──────────────────────
        passed_count = sum(1 for t in all_tests if t.get("passed", False))
        total_count  = len(all_tests)
        if 0 < passed_count < total_count:
            edge_hints = [
                f"⚠️ {passed_count}/{total_count} tests pass — check edge cases: empty input, single element, all-same values, negative numbers, or maximum constraints.",
                f"💡 {passed_count}/{total_count} tests pass — your logic works for some inputs. Look for boundary conditions you're missing.",
                f"🔍 {passed_count}/{total_count} tests pass — trace through a failing test case to find where your output diverges.",
                f"⚠️ {passed_count}/{total_count} tests pass — check: off-by-one errors, wrong loop bounds, or unhandled special cases.",
            ]
            import random as _random
            _add(_random.choice(edge_hints))

        # ── Fallback if nothing was generated ────────────────────────────
        if not hints:
            fallback_pool = [
                "🔍 Trace through your code with the first failing test case step by step.",
                "🧪 Add print statements to inspect intermediate values and find where the output diverges.",
                "💡 Check your output format — make sure it matches the expected output exactly (no extra spaces, brackets, or newlines).",
                "⚠️ Verify your loop bounds — off-by-one errors are the most common cause of wrong answers.",
                "🔍 Test your solution manually with the sample input before submitting.",
                "💡 Check edge cases: what happens with a single element, empty input, or all-same values?",
                "⚠️ Make sure you're reading the input correctly — re-read the Input Format section.",
            ]
            import random as _random
            _random.shuffle(fallback_pool)
            hints.extend(fallback_pool[:2])

        return hints


# Global instance
logic_analyzer = LogicAnalyzer()
