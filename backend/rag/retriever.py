"""
retriever.py

This file handles the RAG retrieval pipeline.

Main Flow:
User Question
        ↓
Convert question into vector embedding
        ↓
Search similar vectors in ChromaDB
        ↓
Retrieve top-10 matching chunks
        ↓
Cross-Encoder reranks chunks
        ↓
Keep top-3 most relevant chunks
        ↓
Return chunks to LLM

Purpose:
Fast retrieval + accurate reranking.
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports required libraries
# ─────────────────────────────────────────────────────────

# Used for system-level operations
import sys

# Used for file/folder path handling
from pathlib import Path


# Add backend folder into Python import path
# So project modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import project settings/configuration
from config import settings


# Import ChromaDB vector database
import chromadb


# Import ChromaDB settings class
from chromadb.config import Settings as ChromaSettings


# Import embedding model + reranker model
from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder
)


# ─────────────────────────────────────────────────────────
# MAIN RETRIEVER CLASS
# This class handles vector search + reranking
# ─────────────────────────────────────────────────────────

class HRRetriever:

    """
    Singleton-safe retriever.

    Purpose:
    Load models only once and reuse them.

    Avoids:
    Reloading heavy AI models for every request.
    """

    # Store single shared instance
    _instance = None


    # ── SINGLETON CREATION BLOCK ────────────────────────

    def __new__(cls):

        """
        Singleton pattern:
        Only one retriever object should exist.
        """

        # If instance not created yet
        if cls._instance is None:

            # Create new instance
            cls._instance = super().__new__(cls)

            # Mark as not initialized
            cls._instance._initialized = False

        # Return same shared instance
        return cls._instance


    # ── INITIALIZATION BLOCK ────────────────────────────

    def __init__(self):

        # Prevent re-initialization
        if self._initialized:
            return


        # Load embedding model
        print("🔢 Loading embedding model...")


        # This converts text → 384-dimensional vectors
        self.embedder = SentenceTransformer(
            settings.embedding_model
        )


        # Load reranker model
        print("🔁 Loading reranker model...")


        # CrossEncoder compares:
        # [query + chunk] together for better scoring
        self.reranker = CrossEncoder(
            settings.reranker_model
        )


        # Connect to ChromaDB
        print("🗃️  Connecting to ChromaDB...")


        # Create persistent ChromaDB client
        self.client = chromadb.PersistentClient(

            # Database folder path
            path=settings.chroma_db_path,

            # Disable telemetry
            settings=ChromaSettings(
                anonymized_telemetry=False
            ),
        )


        # ── COLLECTION LOADING BLOCK ────────────────────

        try:

            # Load existing ChromaDB collection
            self.collection = self.client.get_collection(

                # Collection name
                name=settings.chroma_collection_name
            )


            # Print successful DB connection
            print(
                f"✅ Connected to collection "
                f"'{settings.chroma_collection_name}' "
                f"({self.collection.count()} chunks)"
            )

        except Exception:

            # Error if collection not found
            raise RuntimeError(

                # Tell user ingestion not done
                f"ChromaDB collection "
                f"'{settings.chroma_collection_name}' "
                "not found. "

                # Suggest running ingestor
                "Run: python rag/ingestor.py"
            )


        # Mark retriever as initialized
        self._initialized = True


    # ─────────────────────────────────────────────────────
    # RETRIEVAL PIPELINE
    # This block performs:
    # Embed → Search → Rerank
    # ─────────────────────────────────────────────────────

    def retrieve(self, query: str) -> list[dict]:

        """
        Main retrieval pipeline.
        """

        # ── STEP 1: QUERY EMBEDDING ─────────────────────

        # Convert user question into embedding vector
        query_embedding = self.embedder.encode(
            query
        ).tolist()


        # ── STEP 2: VECTOR SEARCH ───────────────────────

        # Search nearest vectors inside ChromaDB
        results = self.collection.query(

            # User query embedding
            query_embeddings=[query_embedding],

            # Number of chunks to retrieve
            n_results=min(
                settings.top_k_retrieval,
                self.collection.count()
            ),

            # Return documents + metadata + distances
            include=[
                "documents",
                "metadatas",
                "distances"
            ],
        )


        # Store candidate chunks
        candidates = []


        # Loop through retrieved results
        for doc, meta, distance in zip(

            # Retrieved chunk texts
            results["documents"][0],

            # Chunk metadata
            results["metadatas"][0],

            # Vector distances
            results["distances"][0],
        ):

            # Store formatted candidate
            candidates.append({

                # Retrieved chunk text
                "text": doc,

                # Source/page metadata
                "metadata": meta,

                # Convert distance into similarity score
                "vector_score": 1 - distance,
            })


        # Return empty list if no chunks found
        if not candidates:
            return []


        # ── STEP 3: CROSS-ENCODER RERANKING ─────────────

        # Create [query, chunk] pairs
        pairs = [

            # Query + chunk pair
            [query, c["text"]]

            # For every candidate chunk
            for c in candidates
        ]


        # Predict reranking scores
        rerank_scores = self.reranker.predict(
            pairs
        )


        # Attach rerank scores to candidates
        for i, candidate in enumerate(candidates):

            # Final semantic relevance score
            candidate["score"] = float(
                rerank_scores[i]
            )


        # Sort chunks by highest score
        candidates.sort(

            # Sort using rerank score
            key=lambda x: x["score"],

            # Highest score first
            reverse=True
        )


        # Keep only top reranked chunks
        top_chunks = candidates[
            : settings.top_k_rerank
        ]


        # ── OUTPUT FORMATTING BLOCK ─────────────────────

        # Return clean final results
        return [

            {
                # Retrieved chunk text
                "text": c["text"],

                # Rounded relevance score
                "score": round(c["score"], 4),

                # Source document filename
                "source": c["metadata"].get(
                    "source_file",
                    "unknown"
                ),

                # Page number if available
                "page": c["metadata"].get(
                    "page",
                    ""
                ),
            }

            # Loop through top chunks
            for c in top_chunks
        ]


    # ─────────────────────────────────────────────────────
    # CONTEXT FORMATTER
    # This block prepares chunks for LLM prompt
    # ─────────────────────────────────────────────────────

    def format_context(self, chunks: list[dict]) -> str:

        """
        Convert retrieved chunks into prompt context.
        """

        # If no chunks found
        if not chunks:

            # Return fallback message
            return "No relevant policy information found."


        # Store formatted context parts
        parts = []


        # Loop through all chunks
        for i, chunk in enumerate(chunks, 1):

            # Build source citation text
            source_info = f"[Source: {chunk['source']}"


            # Add page number if available
            if chunk.get("page"):

                source_info += f", page {chunk['page']}"


            # Close source bracket
            source_info += "]"


            # Build final context block
            parts.append(

                f"--- Context {i} {source_info} ---\n"

                # Actual chunk text
                f"{chunk['text']}"
            )


        # Combine all context blocks
        return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────
# TESTING BLOCK
# This block runs when file executed directly
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Create retriever object
    retriever = HRRetriever()


    # Sample HR question
    query = "How many casual leaves do employees get per year?"


    # Print question
    print(f"\nQuery: {query}")


    # Run retrieval pipeline
    results = retriever.retrieve(query)


    # Print result count
    print(f"\nTop {len(results)} chunks after reranking:\n")


    # Loop through retrieved chunks
    for i, r in enumerate(results, 1):

        # Print source + score
        print(f"{i}. [{r['source']}] Score: {r['score']}")


        # Print first 150 chars of chunk
        print(f"   {r['text'][:150]}...")


        # Empty line
        print()