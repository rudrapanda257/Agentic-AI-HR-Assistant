"""
config.py — Central configuration loader.
All environment variables are loaded here.
Import `settings` anywhere in the project.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    # ── Gemini Flask API ────────────────────────────────────────────────────
    gemini_api_url: str = "http://localhost:5000/generate"
    gemini_timeout: int = 30  # seconds

    # ── LangSmith ──────────────────────────────────────────────────────────
    langchain_tracing_v2: str = "true"
    langchain_api_key: str = ""
    langchain_project: str = "hr-assistant"

    # ── Google OAuth ───────────────────────────────────────────────────────
    google_credentials_path: str = "./google_credentials/credentials.json"
    google_token_path: str = "./google_credentials/token.json"

    # ── ChromaDB ───────────────────────────────────────────────────────────
    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "hr_policies"

    # ── RAG settings ───────────────────────────────────────────────────────
    chunk_size: int = 512          # tokens per chunk
    chunk_overlap: int = 50        # overlap between chunks
    top_k_retrieval: int = 10      # retrieve top-10 from vector search
    top_k_rerank: int = 3          # keep top-3 after reranking
    embedding_model: str = "all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── FastAPI ────────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = str(env_path)
        extra = "allow"


# Singleton — import this everywhere
settings = Settings()

# Set LangSmith env vars (LangChain reads these from os.environ)
os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project