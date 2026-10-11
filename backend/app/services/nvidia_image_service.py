import os
import json
import httpx
import base64

class NvidiaImageService:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY", "REDACTED_NVIDIA_KEY")
        self.llm_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.llm_model = "meta/llama-3.1-8b-instruct"
        # Since standard image endpoints like stabilityai returned 404 in tests, 
        # we will use the most standard OpenAI-compatible generation endpoint supported by NIM
        # Fallback to the standard stable-diffusion-3-medium string used by NVIDIA
        self.image_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-3-medium"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def analyze_and_generate_image(self, question_text: str) -> str | None:
        """
        Analyzes a question to check if it requires an image.
        If YES, it generates an image using NVIDIA's API and returns the base64 string.
        """
        image_prompt = await self._analyze_question(question_text)
        
        if image_prompt:
            print(f"[NvidiaImage] LLM decided image is needed. Prompt: {image_prompt}")
            image_b64 = await self._generate_image(image_prompt)
            return image_b64
        
        return None

    async def _analyze_question(self, question_text: str) -> str | None:
        """
        Uses an LLM to decide if the question requires a visual diagram and returns an image prompt if so.
        Returns the prompt string, or None if no image is needed.
        """
        prompt = (
            "You are an AI assistant analyzing coding questions. Read the following coding question. "
            "Determine if this question highly benefits from a visual diagram to understand (e.g., trees, graphs, geometry, grid paths, complex physical simulations). "
            "If it DOES NOT need an image, output exactly: NO\n"
            "If it DOES need an image, output YES followed by a newline, and then a very detailed, highly visual prompt to generate an image for it. "
            "CRITICAL: You must introduce extreme variety and creativity! Even for similar problems, choose completely different artistic styles (e.g., isometric 3D, neon cyberpunk, watercolor, clean minimalist vector, photorealistic, retro 8-bit, blueprint style). "
            "Make sure the prompt is incredibly unique every single time so we never get the same image twice. "
            "For example: 'YES\\nA neon cyberpunk style geometric diagram of a binary search tree on a dark background...'\n\n"
            f"Question:\n{question_text}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.llm_url,
                    headers=self.headers,
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150,
                        "temperature": 0.9
                    }
                )
                
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content.startswith("YES"):
                    # Extract the prompt
                    parts = content.split("\n", 1)
                    if len(parts) > 1:
                        return parts[1].strip()
            else:
                print(f"[NvidiaImage] LLM returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"[NvidiaImage] Error analyzing question: {e}")
            
        return None

    async def _generate_image(self, image_prompt: str) -> str | None:
        """
        Generates an image from the prompt using the NVIDIA API.
        Returns a base64 data URI for the image.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Attempt image generation using stable-diffusion-3-medium format for NVIDIA API
                payload = {
                    "text_prompts": [{"text": image_prompt}],
                    "cfg_scale": 7,
                    "steps": 30
                }
                response = await client.post(
                    self.image_url,
                    headers=self.headers,
                    json=payload
                )
                
            if response.status_code == 200:
                data = response.json()
                # Different models might return the base64 differently in NVIDIA's specific API wrapper
                if "artifacts" in data and len(data["artifacts"]) > 0:
                    b64 = data["artifacts"][0].get("base64")
                    if b64:
                        return f"data:image/png;base64,{b64}"
                # If OpenAI standard was used instead
                if "data" in data and len(data["data"]) > 0:
                    b64 = data["data"][0].get("b64_json")
                    if b64:
                        return f"data:image/png;base64,{b64}"
                
                print("[NvidiaImage] Unexpected image generation response format.")
                return None
            else:
                print(f"[NvidiaImage] Image generation failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"[NvidiaImage] Error generating image: {e}")
            return None

nvidia_image_service = NvidiaImageService()
