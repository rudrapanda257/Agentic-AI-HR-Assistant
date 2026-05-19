"""
retriever.py — Vector search + cross-encoder reranking.

Flow for every query:
    1. Embed query with all-MiniLM-L6-v2 (same model as ingestor)
    2. Cosine similarity search in ChromaDB → top-10 candidates
    3. Cross-encoder reranks all 10 → returns top-3 with real relevance scores

Why reranking?
    Embedding models (bi-encoders) are fast but approximate.
    Cross-encoders read BOTH query + chunk together → much more accurate scores.
    Cost: ~200ms extra per query. Worth it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer, CrossEncoder


class HRRetriever:
    """
    Singleton-safe retriever. Loads models once, reuses for every query.
    
    Usage:
        retriever = HRRetriever()
        results = retriever.retrieve("How many leaves do I get?")
        # returns: [{"text": "...", "score": 0.95, "source": "leave-policy.pdf"}, ...]
    """

    _instance = None

    def __new__(cls):
        # Singleton pattern — models are expensive to load
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        print("🔢 Loading embedding model (cached after first run)...")
        self.embedder = SentenceTransformer(settings.embedding_model)

        print("🔁 Loading reranker model (cached after first run)...")
        self.reranker = CrossEncoder(settings.reranker_model)

        print("🗃️  Connecting to ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        try:
            self.collection = self.client.get_collection(
                name=settings.chroma_collection_name
            )
            print(f"✅ Connected to collection '{settings.chroma_collection_name}' "
                  f"({self.collection.count()} chunks)")
        except Exception:
            raise RuntimeError(
                f"ChromaDB collection '{settings.chroma_collection_name}' not found. "
                "Run: python rag/ingestor.py"
            )

        self._initialized = True

    def retrieve(self, query: str) -> list[dict]:
        """
        Full retrieval pipeline: embed → search → rerank.
        
        Returns top-k chunks as dicts with text, score, and source metadata.
        """
        # ── Step 1: Embed the query ────────────────────────────────────────
        query_embedding = self.embedder.encode(query).tolist()

        # ── Step 2: Vector search — get top-10 candidates ─────────────────
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(settings.top_k_retrieval, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        candidates = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            candidates.append({
                "text": doc,
                "metadata": meta,
                "vector_score": 1 - distance,  # convert distance → similarity
            })

        if not candidates:
            return []

        # ── Step 3: Cross-encoder reranking ───────────────────────────────
        # CrossEncoder takes [query, passage] pairs and scores each
        pairs = [[query, c["text"]] for c in candidates]
        rerank_scores = self.reranker.predict(pairs)

        # Attach rerank scores
        for i, candidate in enumerate(candidates):
            candidate["score"] = float(rerank_scores[i])

        # Sort by rerank score descending, keep top-k
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = candidates[: settings.top_k_rerank]

        # ── Format output ──────────────────────────────────────────────────
        return [
            {
                "text": c["text"],
                "score": round(c["score"], 4),
                "source": c["metadata"].get("source_file", "unknown"),
                "page": c["metadata"].get("page", ""),
            }
            for c in top_chunks
        ]

    def format_context(self, chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a context string for the LLM prompt.
        Includes source attribution.
        """
        if not chunks:
            return "No relevant policy information found."

        parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source: {chunk['source']}"
            if chunk.get("page"):
                source_info += f", page {chunk['page']}"
            source_info += "]"
            parts.append(f"--- Context {i} {source_info} ---\n{chunk['text']}")

        return "\n\n".join(parts)


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    retriever = HRRetriever()
    query = "How many casual leaves do employees get per year?"
    print(f"\nQuery: {query}")
    results = retriever.retrieve(query)
    print(f"\nTop {len(results)} chunks after reranking:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['source']}] Score: {r['score']}")
        print(f"   {r['text'][:150]}...")
        print()