"""
gemini_wrapper.py — Fixed version.

ROOT CAUSE OF BUG: Field(default_factory=lambda: settings.gemini_api_url)
in Pydantic v2 + LangChain BaseLLM causes the Field annotation string
to be passed as the URL instead of the actual value.

FIX: Read env vars directly at module level with os.getenv(),
use plain string defaults in the class body.
"""
import os
import requests
from typing import Any, List, Optional
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun

# Read at module load time — reliable, no Pydantic Field issues
_GEMINI_API_URL = os.getenv("GEMINI_API_URL", "http://localhost:5000/generate")
_GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "30"))


class GeminiLLM(LLM):
    """LangChain-compatible wrapper for a local Gemini Flask API."""

    # Plain string defaults — NO Field(default_factory=...) 
    api_url: str = _GEMINI_API_URL
    timeout: int = _GEMINI_TIMEOUT
    temperature: float = 0.2
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "gemini_flask"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        # Safety check
        if not self.api_url.startswith("http"):
            raise ValueError(
                f"Invalid GEMINI_API_URL: '{self.api_url}'\n"
                "Check your .env has: GEMINI_API_URL=http://localhost:5000/generate\n"
                "And that python-dotenv loaded it before this class was imported."
            )

        payload = {
            "prompt": prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "response" in data:
                return data["response"].strip()
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()
            if isinstance(data, dict) and "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if isinstance(data, str):
                return data.strip()
            return str(data)

        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach Gemini API at '{self.api_url}'.\n"
                "Make sure your Gemini Flask server is running."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Gemini API timed out after {self.timeout}s.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Gemini API HTTP error: {e}")

    @property
    def _identifying_params(self) -> dict:
        return {"api_url": self.api_url, "temperature": self.temperature}


if __name__ == "__main__":
    print(f"GEMINI_API_URL = {_GEMINI_API_URL}")
    llm = GeminiLLM()
    print(f"api_url resolved to: '{llm.api_url}'")
    assert llm.api_url.startswith("http"), f"URL is wrong: {llm.api_url}"
    response = llm.invoke("Say exactly: wrapper is working")
    print(f"Response: {response}")
    print("✅ GeminiLLM wrapper is working!")