"""
ingestor.py — RAG Ingestion Pipeline.

Pipeline:
    HR docs (PDF/TXT) → load → chunk → embed → store in ChromaDB

Run this ONCE after adding documents:
    cd backend && python rag/ingestor.py

Re-run only when you add/change documents.
"""
import os
import sys
from pathlib import Path

# Add backend/ to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
)


DOCS_DIR = Path(__file__).parent / "docs"


def load_documents():
    """Load all PDF and TXT files from the docs/ directory."""
    if not DOCS_DIR.exists():
        print(f"❌ docs/ directory not found at {DOCS_DIR}")
        print("   Create it and add your HR PDF/TXT files.")
        sys.exit(1)

    doc_files = list(DOCS_DIR.glob("*.pdf")) + list(DOCS_DIR.glob("*.txt"))

    if not doc_files:
        print(f"❌ No PDF or TXT files found in {DOCS_DIR}")
        print("   Add HR policy documents to backend/rag/docs/")
        sys.exit(1)

    print(f"\n📂 Loading documents from {DOCS_DIR}")
    all_docs = []

    for file_path in doc_files:
        print(f"   Loading: {file_path.name}")
        try:
            if file_path.suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
            else:
                loader = TextLoader(str(file_path), encoding="utf-8")

            docs = loader.load()

            # Tag each doc with its source filename
            for doc in docs:
                doc.metadata["source_file"] = file_path.name

            all_docs.extend(docs)
        except Exception as e:
            print(f"   ⚠️  Skipping {file_path.name}: {e}")

    print(f"✅ Loaded {len(all_docs)} document pages")
    return all_docs


def chunk_documents(docs):
    """
    Split documents into chunks.
    
    Strategy: RecursiveCharacterTextSplitter tries to split at
    paragraph → sentence → word boundaries, preserving context.
    
    chunk_size=512, chunk_overlap=50 is a good balance for HR docs.
    Larger overlap = better context preservation, slower retrieval.
    """
    print(f"\n✂️  Splitting into chunks (size={settings.chunk_size}, overlap={settings.chunk_overlap})")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} chunks")
    return chunks


def embed_and_store(chunks):
    """
    Embed all chunks with all-MiniLM-L6-v2 and store in ChromaDB.
    
    all-MiniLM-L6-v2:
    - 384-dimensional embeddings
    - ~80MB download (cached after first run)
    - Fast: ~14k sentences/second on CPU
    - Free, runs locally
    """
    print(f"\n🔢 Loading embedding model: {settings.embedding_model}")
    print("   (First run downloads ~80MB — subsequent runs use cache)")

    model = SentenceTransformer(settings.embedding_model)

    # ── Init ChromaDB ──────────────────────────────────────────────────────
    db_path = settings.chroma_db_path
    os.makedirs(db_path, exist_ok=True)

    print(f"\n🗃️  Connecting to ChromaDB at {db_path}")
    client = chromadb.PersistentClient(
        path=db_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    # Delete existing collection so we get a clean slate on re-ingest
    try:
        client.delete_collection(settings.chroma_collection_name)
        print("   Cleared existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},  # cosine similarity
    )

    # ── Embed + store in batches ───────────────────────────────────────────
    batch_size = 64
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"\n📊 Embedding {len(chunks)} chunks in batches of {batch_size}...")

    for start in range(0, len(chunks), batch_size):
        end = min(start + batch_size, len(chunks))
        batch_texts = texts[start:end]
        batch_meta = metadatas[start:end]
        batch_ids = ids[start:end]

        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()

        collection.add(
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        print(f"   Stored chunks {start}–{end}")

    print(f"\n✅ Ingestion complete! {len(chunks)} chunks stored in ChromaDB")
    print(f"   DB location: {os.path.abspath(db_path)}")
    print("\n💡 You can now run the FastAPI server and start chatting!")


if __name__ == "__main__":
    docs = load_documents()
    chunks = chunk_documents(docs)
    embed_and_store(chunks)