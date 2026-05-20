import os
import google.generativeai as genai

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use Gemini model
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()


class PromptRequest(BaseModel):
    prompt: str
    temperature: float = 0.2
    max_tokens: int = 1024


@app.post("/generate")
async def generate(req: PromptRequest):
    try:
        response = model.generate_content(req.prompt)

        return {
            "response": response.text
        }

    except Exception as e:
        return {
            "response": f"Gemini error: {str(e)}"
        }