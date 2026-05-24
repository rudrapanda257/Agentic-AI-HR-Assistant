"""
gemini_api.py

This file creates a FastAPI server for Gemini AI.

Main Flow:
User Prompt
      ↓
FastAPI Endpoint (/generate)
      ↓
Gemini SDK
      ↓
Gemini Model
      ↓
Generated Response
      ↓
Return JSON Response

Purpose:
Acts as a local API server for Gemini.
LangChain wrapper sends HTTP requests to this server.
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports required libraries
# ─────────────────────────────────────────────────────────

# Used for reading environment variables
import os

# Google Gemini SDK
import google.generativeai as genai


# FastAPI framework for creating API server
from fastapi import FastAPI


# Pydantic model for request validation
from pydantic import BaseModel


# Load variables from .env file
from dotenv import load_dotenv


# Async support library
import asyncio


# ─────────────────────────────────────────────────────────
# ENVIRONMENT SETUP BLOCK
# This block loads .env variables
# ─────────────────────────────────────────────────────────

# Load environment variables from .env file
load_dotenv()


# ─────────────────────────────────────────────────────────
# GEMINI CONFIGURATION BLOCK
# This block configures Gemini SDK
# ─────────────────────────────────────────────────────────

# Configure Gemini SDK using API key
genai.configure(

    # Read GEMINI_API_KEY from .env
    api_key=os.getenv("GEMINI_API_KEY")
)


# Load Gemini model
model = genai.GenerativeModel(

    # Gemini model name
    "gemini-2.5-flash"
)


# ─────────────────────────────────────────────────────────
# FASTAPI SERVER BLOCK
# This block creates FastAPI application
# ─────────────────────────────────────────────────────────

# Create FastAPI app/server object
app = FastAPI()


# ─────────────────────────────────────────────────────────
# REQUEST MODEL BLOCK
# This block defines API request structure
# ─────────────────────────────────────────────────────────

class PromptRequest(BaseModel):

    """
    Request body structure for /generate API.
    """

    # User prompt text
    prompt: str

    # AI creativity/randomness level
    temperature: float = 0.2

    # Maximum response token length
    max_tokens: int = 1024


# ─────────────────────────────────────────────────────────
# API ENDPOINT BLOCK
# This block handles AI generation requests
# ─────────────────────────────────────────────────────────

@app.post("/generate")

# Async API function
async def generate(req: PromptRequest):

    """
    Receive prompt from client
    → Send to Gemini
    → Return generated response
    """

    try:

        # Call Gemini model
        response = model.generate_content(

            # User prompt
            req.prompt,

            # Generation settings
            generation_config={

                # Response randomness
                "temperature": req.temperature,

                # Maximum output length
                "max_output_tokens": req.max_tokens
            },

            # Request timeout settings
            request_options={

                # Maximum waiting time
                "timeout": 110
            }
        )


        # Return successful response
        return {

            # Gemini generated text
            "response": response.text
        }


    # Error handling block
    except Exception as e:

        # Return error response
        return {

            # Error message
            "response": f"Gemini error: {str(e)}"
        }