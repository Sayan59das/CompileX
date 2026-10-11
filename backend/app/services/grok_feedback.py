"""
AI Feedback Service
Provides conversational code analysis and hints using NVIDIA NIM (Nemotron) if configured,
Google Gemini, or an intelligent local structural/complexity analysis engine (offline mode).
"""

import re
from typing import List, Dict, Optional
from app.services.logic_analyzer import LogicAnalyzer


class GrokFeedbackService:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def chat(
        self,
        user_message: str,
        code: str,
        language: str,
        problem_statement: str,
        conversation_history: List[Dict],
    ) -> str:
        """
        Send a message to the AI Code Coach with full context and return the assistant reply.
        If Google Gemini is configured, uses Gemini. Otherwise, uses an intelligent local AST & complexity engine.
        """
        from app.core.config import get_settings
        settings = get_settings()

        # 1. Try NVIDIA Nemotron AI API if configured
        api_key = self.api_key or getattr(settings, "NVIDIA_API_KEY", "")
        if api_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key,
                    timeout=10.0,
                )
                
                context_block = (
                    f"Problem: {(problem_statement or 'Not provided')[:1500]}\n\n"
                    f"Language: {language}\n\n"
                    f"User's current code:\n"
                    f"```{language}\n{(code or 'No code yet')[:4000]}\n```"
                )
                system_prompt = (
                    "You are an expert competitive programming coach and AI coding mentor embedded inside CompileX. "
                    "Be direct, encouraging, and give actionable guidance or hints without necessarily dumping the complete raw solution unless asked. "
                    "Explain root causes of bugs, logical flaws, or how to optimize time and space complexity."
                )
                
                messages = [
                    {"role": "system", "content": f"{system_prompt}\n\n[PROBLEM CONTEXT]\n{context_block}\n[/PROBLEM CONTEXT]"}
                ]
                for h in (conversation_history or [])[-8:]:
                    role = h.get("role", "user")
                    if role in ("user", "assistant"):
                        messages.append({"role": role, "content": str(h.get("content", ""))})
                messages.append({"role": "user", "content": user_message})
                
                completion = await client.chat.completions.create(
                    model="nvidia/nemotron-3-ultra-550b-a55b",
                    messages=messages,
                    temperature=1,
                    top_p=0.95,
                    max_tokens=16384,
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384},
                    stream=True,
                )
                
                content_pieces = []
                reasoning_pieces = []
                async for chunk in completion:
                    if not chunk.choices:
                        continue
                    reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                    if reasoning:
                        reasoning_pieces.append(reasoning)
                    if chunk.choices[0].delta.content is not None:
                        content_pieces.append(chunk.choices[0].delta.content)
                        
                final_content = "".join(content_pieces).strip()
                if not final_content and reasoning_pieces:
                    final_content = "".join(reasoning_pieces).strip()
                        
                if final_content:
                    return final_content
            except Exception as e:
                print(f"[AIFeedback] NVIDIA Nemotron API error: {e}")

        # 2. Try Google Gemini if configured
        if settings.GOOGLE_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                context_block = (
                    f"Problem: {(problem_statement or 'Not provided')[:800]}\n\n"
                    f"Language: {language}\n\n"
                    f"User's current code:\n"
                    f"```{language}\n{(code or 'No code yet')[:3000]}\n```"
                )
                system_prompt = (
                    "You are an expert competitive programming coach embedded inside CompileX. "
                    "Be concise, direct, and give actionable advice without giving away the full solution. "
                    "Explain WHY something is wrong or how to improve complexity."
                )
                full_prompt = f"{system_prompt}\n\n[CONTEXT]\n{context_block}\n[/CONTEXT]\n\nUser Question: {user_message}"
                
                resp = model.generate_content(full_prompt)
                if resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"[AIFeedback] Gemini API error: {e}")

        # 2. Intelligent Offline Code Coach Engine (No external API keys needed!)
        msg_lower = user_message.lower().strip()
        analyzer = LogicAnalyzer()
        comp = analyzer._detect_complexity(code or "", language or "python")
        time_comp = comp.get("time", "O(n)")
        space_comp = comp.get("space", "O(1)")

        if not code or not code.strip() or len(code.strip()) < 10:
            return (
                "🤖 **CompileX AI Coach:**\n\n"
                "I see you haven't written much code yet! To get started on this problem:\n"
                "1. **Read carefully**: Identify the exact input format and required output.\n"
                "2. **Base cases**: Start by writing down simple base cases or edge conditions.\n"
                "3. **Drafting**: Write an initial brute-force approach first, then we can optimize it!"
            )

        if any(w in msg_lower for w in ["why is my code wrong", "wrong", "bug", "error", "fail", "fix", "issue"]):
            return (
                f"🤖 **CompileX Code Coach Analysis:**\n\n"
                f"Let's troubleshoot your `{language}` code (Current complexity: `{time_comp}`):\n\n"
                "1. **Check Loop Bounds**: Look carefully for off-by-one errors in your loops (e.g. `< n` vs `<= n` or 0-indexed vs 1-indexed bounds).\n"
                "2. **Return Value & Type**: Verify that your function returns the exact data type and structure required by the problem description.\n"
                "3. **Edge Conditions**: Are you handling empty inputs (`len == 0`), negative numbers, or single elements correctly?\n\n"
                "👉 *Tip: Click 'Analyze Now' above or run custom test cases to see which specific input is failing!*"
            )

        if any(w in msg_lower for w in ["time complexity", "complexity", "big-o", "explain", "speed", "memory", "space"]):
            return (
                f"⚡ **Complexity Analysis:**\n\n"
                f"• **Estimated Time Complexity**: `{time_comp}`\n"
                f"• **Estimated Space Complexity**: `{space_comp}`\n\n"
                "**How we derived this:** Our structural AST scanner evaluated your loops, recursive calls, and data structures.\n"
                "• If you have nested loops (`O(n²)`), consider whether the inner loop can be replaced by a lookup in a Hash Set/Map (`O(1)`).\n"
                "• If using recursion without memoization, check if subproblems overlap!"
            )

        if any(w in msg_lower for w in ["optimize", "faster", "better", "improve", "efficient"]):
            return (
                f"🚀 **Optimization Strategy (Current: `{time_comp}`):**\n\n"
                "1. **Eliminate Redundant Work**: Avoid recalculating values inside loops or repeated array slicing inside recursive steps.\n"
                "2. **Upgrade Data Structures**: If searching for elements in an array (`O(n)`), convert the lookup collection to a Set or Dict (`O(1)`).\n"
                "3. **Two Pointers / Sliding Window**: For contiguous subarray or pair problems, sorting or two-pointer techniques can often reduce `O(n²)` down to `O(n log n)` or `O(n)`!"
            )

        if any(w in msg_lower for w in ["edge case", "missing", "test", "corner"]):
            return (
                "🔍 **Critical Edge Cases Checklist:**\n\n"
                "• **Minimal Inputs**: What happens when the input array/string is empty (`[]` or `\"\"`) or has exactly 1 element?\n"
                "• **Duplicate Values**: Does your logic break if all elements are identical (e.g. `[5, 5, 5]`)?\n"
                "• **Extreme Values**: Check for negative integers, zeros, or potential integer overflow if numbers can be very large.\n"
                "• **No Solution Present**: Does your code return the correct default fallback value when no solution exists?"
            )

        return (
            f"🤖 **CompileX AI Code Coach:**\n\n"
            f"I have reviewed your current `{language}` implementation (Time: `{time_comp}`, Space: `{space_comp}`).\n\n"
            "Here is how I can coach you through this problem:\n"
            "• **Find bugs**: Ask me *\"Why is my code wrong?\"*\n"
            "• **Analyze performance**: Ask *\"Explain the time complexity\"*\n"
            "• **Optimize runtime**: Ask *\"How can I optimize this?\"*\n"
            "• **Test coverage**: Ask *\"What edge cases am I missing?\"*"
        )


_instance: Optional[GrokFeedbackService] = None


def get_grok_service() -> GrokFeedbackService:
    global _instance
    if _instance is None:
        from app.core.config import get_settings
        settings = get_settings()
        api_key = getattr(settings, "NVIDIA_API_KEY", "")
        _instance = GrokFeedbackService(api_key=api_key)
    return _instance
