"""
gemini_wrapper.py

This file creates a custom LangChain-compatible wrapper
for a local Gemini API server.

Purpose:
LangChain Agent
    ↓
GeminiLLM Wrapper
    ↓
HTTP Request
    ↓
Local Gemini API Server
    ↓
Gemini Response
"""

# Import os module for reading environment variables
import os

# Import requests library for making HTTP API calls
import requests

# Import typing helpers
from typing import Any, List, Optional

# Import LangChain base LLM class
from langchain.llms.base import LLM

# Import callback manager used internally by LangChain
from langchain.callbacks.manager import CallbackManagerForLLMRun


# Read Gemini API URL from environment variable
# If env variable not found, use localhost URL
_GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    "http://localhost:5000/generate"
)

# Read timeout value from environment variable
# Default timeout = 120 seconds
_GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "120"))


# Create custom Gemini LLM wrapper class
class GeminiLLM(LLM):

    """
    This class makes Gemini work like a LangChain LLM.
    """

    # Store Gemini API URL
    api_url: str = _GEMINI_API_URL

    # Maximum waiting time for API response
    timeout: int = _GEMINI_TIMEOUT

    # Controls randomness of AI response
    # Lower = more stable answers
    temperature: float = 0.2

    # Maximum tokens Gemini can generate
    max_tokens: int = 1024


    # Return custom LLM type name
    @property
    def _llm_type(self) -> str:
        return "gemini_flask"


    # Main function called by LangChain
    def _call(

        # User prompt sent to Gemini
        self,
        prompt: str,

        # Optional stop words
        stop: Optional[List[str]] = None,

        # LangChain internal callback manager
        run_manager: Optional[CallbackManagerForLLMRun] = None,

        # Extra optional arguments
        **kwargs: Any,
    ) -> str:

        # Safety check:
        # Ensure API URL starts with http
        if not self.api_url.startswith("http"):

            # Raise error if URL is invalid
            raise ValueError(

                # Show invalid URL
                f"Invalid GEMINI_API_URL: '{self.api_url}'\n"

                # Suggest correct .env value
                "Check your .env has: GEMINI_API_URL=http://localhost:5000/generate\n"

                # Ensure dotenv loaded correctly
                "And that python-dotenv loaded it before this class was imported."
            )

        # Create request payload sent to Gemini API
        payload = {

            # User prompt
            "prompt": prompt,

            # Response creativity level
            "temperature": self.temperature,

            # Max response length
            "max_tokens": self.max_tokens,
        }

        try:

            # Send HTTP POST request to Gemini API
            response = requests.post(

                # API endpoint URL
                self.api_url,

                # JSON request body
                json=payload,

                # Timeout limit
                timeout=self.timeout
            )

            # Raise error if HTTP request failed
            response.raise_for_status()

            # Convert API response JSON into Python dictionary
            data = response.json()

            # Handle response format:
            # {"response": "..."}
            if isinstance(data, dict) and "response" in data:
                return data["response"].strip()

            # Handle response format:
            # {"text": "..."}
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()

            # Handle Gemini candidate response structure
            if isinstance(data, dict) and "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # If API directly returned plain string
            if isinstance(data, str):
                return data.strip()

            # Convert any unknown response into string
            return str(data)

        # Error if Gemini server is not running
        except requests.exceptions.ConnectionError:

            raise ConnectionError(

                # Show connection issue
                f"Cannot reach Gemini API at '{self.api_url}'.\n"

                # Suggest solution
                "Make sure your Gemini Flask server is running."
            )

        # Error if API takes too long
        except requests.exceptions.Timeout:

            raise TimeoutError(

                # Show timeout duration
                f"Gemini API timed out after {self.timeout}s."
            )

        # Error for HTTP failures like 404/500
        except requests.exceptions.HTTPError as e:

            raise RuntimeError(

                # Show HTTP error details
                f"Gemini API HTTP error: {e}"
            )


    # Return model configuration parameters
    @property
    def _identifying_params(self) -> dict:

        return {

            # Current API URL
            "api_url": self.api_url,

            # Current temperature value
            "temperature": self.temperature
        }


# Run file directly for testing
if __name__ == "__main__":

    # Print loaded Gemini API URL
    print(f"GEMINI_API_URL = {_GEMINI_API_URL}")

    # Create GeminiLLM object
    llm = GeminiLLM()

    # Print resolved API URL
    print(f"api_url resolved to: '{llm.api_url}'")

    # Ensure URL starts with http
    assert llm.api_url.startswith("http"), f"URL is wrong: {llm.api_url}"

    # Send test prompt to Gemini API
    response = llm.invoke("Say exactly: wrapper is working")

    # Print Gemini response
    print(f"Response: {response}")

    # Print success message
    print("✅ GeminiLLM wrapper is working!")