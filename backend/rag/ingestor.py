"""
ingestor.py

This file builds the RAG knowledge base.

Main Pipeline:
PDF/TXT Documents
        ↓
Load Documents
        ↓
Split into Chunks
        ↓
Convert Chunks into Embedding Vectors
        ↓
Store in ChromaDB

Run this file whenever new HR documents are added.
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports all required Python libraries
# ─────────────────────────────────────────────────────────

# Used for folder and OS operations
import os

# Used for system-level operations
import sys

# Used for handling file paths safely
from pathlib import Path


# Add backend folder to Python import path
# So we can import config/settings files
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import project settings from config.py
from config import settings


# Import ChromaDB vector database library
import chromadb

# Import ChromaDB configuration class
from chromadb.config import Settings as ChromaSettings

# Import Sentence Transformer embedding model
from sentence_transformers import SentenceTransformer

# Import LangChain text chunking algorithm
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Import document loaders for PDF and TXT files
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
)


# ─────────────────────────────────────────────────────────
# DOCUMENT DIRECTORY SETUP
# This block defines where HR documents are stored
# ─────────────────────────────────────────────────────────

# Path to backend/rag/docs folder
DOCS_DIR = Path(__file__).parent / "docs"


# ─────────────────────────────────────────────────────────
# DOCUMENT LOADING FUNCTION
# This block loads all HR documents
# ─────────────────────────────────────────────────────────

def load_documents():

    """
    Load all PDF and TXT files from docs folder.
    """

    # Check if docs folder exists
    if not DOCS_DIR.exists():

        # Show error if folder missing
        print(f"❌ docs/ directory not found at {DOCS_DIR}")

        # Tell user to create folder
        print("   Create it and add your HR PDF/TXT files.")

        # Stop program execution
        sys.exit(1)


    # Find all PDF and TXT files
    doc_files = list(DOCS_DIR.glob("*.pdf")) + list(DOCS_DIR.glob("*.txt"))


    # Check if folder contains documents
    if not doc_files:

        # Show error if no files found
        print(f"❌ No PDF or TXT files found in {DOCS_DIR}")

        # Tell user where to place documents
        print("   Add HR policy documents to backend/rag/docs/")

        # Stop program
        sys.exit(1)


    # Print loading message
    print(f"\n📂 Loading documents from {DOCS_DIR}")


    # Store all loaded document pages
    all_docs = []


    # Loop through every file
    for file_path in doc_files:

        # Print current file name
        print(f"   Loading: {file_path.name}")

        try:

            # If file is PDF
            if file_path.suffix == ".pdf":

                # Use PDF loader
                loader = PyPDFLoader(str(file_path))

            else:

                # Use text loader for TXT files
                loader = TextLoader(str(file_path), encoding="utf-8")


            # Extract document content
            docs = loader.load()


            # Add source filename into metadata
            for doc in docs:

                # Store original file name
                doc.metadata["source_file"] = file_path.name


            # Add loaded pages into all_docs list
            all_docs.extend(docs)

        except Exception as e:

            # Skip corrupted or problematic files
            print(f"   ⚠️  Skipping {file_path.name}: {e}")


    # Print total loaded pages
    print(f"✅ Loaded {len(all_docs)} document pages")


    # Return all loaded documents
    return all_docs


# ─────────────────────────────────────────────────────────
# DOCUMENT CHUNKING FUNCTION
# This block splits documents into smaller chunks
# ─────────────────────────────────────────────────────────

def chunk_documents(docs):

    """
    Split large documents into smaller chunks.
    """

    # Print chunking configuration
    print(
        f"\n✂️  Splitting into chunks "
        f"(size={settings.chunk_size}, "
        f"overlap={settings.chunk_overlap})"
    )


    # Create RecursiveCharacterTextSplitter object
    splitter = RecursiveCharacterTextSplitter(

        # Maximum chunk size
        chunk_size=settings.chunk_size,

        # Shared text between chunks
        chunk_overlap=settings.chunk_overlap,

        # Preferred splitting order
        separators=["\n\n", "\n", ". ", " ", ""],

        # Measure chunk size using character length
        length_function=len,
    )


    # Split documents into chunks
    chunks = splitter.split_documents(docs)


    # Print total chunk count
    print(f"✅ Created {len(chunks)} chunks")


    # Return chunks
    return chunks


# ─────────────────────────────────────────────────────────
# EMBEDDING + CHROMADB STORAGE FUNCTION
# This block converts chunks into vectors
# and stores them in ChromaDB
# ─────────────────────────────────────────────────────────

def embed_and_store(chunks):

    """
    Convert chunks into embeddings
    and store inside ChromaDB.
    """

    # Print embedding model name
    print(f"\n🔢 Loading embedding model: {settings.embedding_model}")


    # Inform first-time download
    print("   (First run downloads model — later runs use cache)")


    # Load sentence transformer model
    model = SentenceTransformer(settings.embedding_model)


    # ── CHROMADB INITIALIZATION BLOCK ───────────────────

    # Get ChromaDB storage folder path
    db_path = settings.chroma_db_path


    # Create DB folder if missing
    os.makedirs(db_path, exist_ok=True)


    # Print DB connection message
    print(f"\n🗃️  Connecting to ChromaDB at {db_path}")


    # Create persistent ChromaDB client
    client = chromadb.PersistentClient(

        # DB storage location
        path=db_path,

        # Disable telemetry
        settings=ChromaSettings(anonymized_telemetry=False),
    )


    # Delete old collection if already exists
    # Helps re-create clean embeddings during re-ingestion
    try:

        # Delete existing collection
        client.delete_collection(settings.chroma_collection_name)

        # Print success message
        print("   Cleared existing collection")

    except Exception:

        # Ignore error if collection does not exist
        pass


    # Create new ChromaDB collection
    collection = client.create_collection(

        # Collection name
        name=settings.chroma_collection_name,

        # Use cosine similarity for vector comparison
        metadata={"hnsw:space": "cosine"},
    )


    # ── PREPARE DATA BLOCK ──────────────────────────────

    # Extract text content from chunks
    texts = [c.page_content for c in chunks]


    # Extract metadata from chunks
    metadatas = [c.metadata for c in chunks]


    # Create unique chunk IDs
    ids = [f"chunk_{i}" for i in range(len(chunks))]


    # Batch size for embedding processing
    batch_size = 64


    # Print embedding progress message
    print(
        f"\n📊 Embedding {len(chunks)} chunks "
        f"in batches of {batch_size}..."
    )


    # ── BATCH EMBEDDING LOOP ────────────────────────────

    # Process chunks batch-by-batch
    for start in range(0, len(chunks), batch_size):

        # Batch ending index
        end = min(start + batch_size, len(chunks))


        # Current batch texts
        batch_texts = texts[start:end]


        # Current batch metadata
        batch_meta = metadatas[start:end]


        # Current batch IDs
        batch_ids = ids[start:end]


        # Convert batch text into embedding vectors
        embeddings = model.encode(

            # Input texts
            batch_texts,

            # Hide progress bar
            show_progress_bar=False

        ).tolist()


        # Store embeddings inside ChromaDB
        collection.add(

            # Original chunk texts
            documents=batch_texts,

            # 384-dimensional vectors
            embeddings=embeddings,

            # Metadata like source file/page
            metadatas=batch_meta,

            # Unique IDs
            ids=batch_ids,
        )


        # Print stored batch range
        print(f"   Stored chunks {start}–{end}")


    # Print final success message
    print(f"\n✅ Ingestion complete!")


    # Print total stored chunks
    print(f"   {len(chunks)} chunks stored in ChromaDB")


    # Print DB storage location
    print(f"   DB location: {os.path.abspath(db_path)}")


    # Inform user ingestion is complete
    print("\n💡 You can now run the FastAPI server and start chatting!")


# ─────────────────────────────────────────────────────────
# MAIN EXECUTION BLOCK
# This block runs when file is executed directly
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Load HR documents
    docs = load_documents()

    # Split documents into chunks
    chunks = chunk_documents(docs)

    # Generate embeddings and store in ChromaDB
    embed_and_store(chunks)