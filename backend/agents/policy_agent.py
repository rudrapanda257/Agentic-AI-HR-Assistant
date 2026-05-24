"""
policy_agent.py

This file creates the HR Policy AI Agent using RAG architecture.

Flow:
User Question
    ↓
Retrieve relevant chunks from ChromaDB
    ↓
Build prompt using retrieved context
    ↓
Send prompt to Gemini LLM
    ↓
Generate answer with source citations
"""

# Import system module
import sys

# Import Path class for handling file paths
from pathlib import Path

# Add parent folder path so Python can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import LangChain prompt template class
from langchain_core.prompts import PromptTemplate

# Import output parser to convert LLM output into normal string
from langchain_core.output_parsers import StrOutputParser

# Import custom Gemini LLM wrapper
from llm.gemini_wrapper import GeminiLLM

# Import retriever for searching HR document chunks
from rag.retriever import HRRetriever


# Create prompt template for HR assistant
POLICY_PROMPT = PromptTemplate(

    # Variables dynamically inserted into prompt
    input_variables=["context", "question"],

    # Full prompt sent to Gemini model
    template="""
You are a helpful HR assistant.

# Tell model to answer only from HR documents

# If answer not found, ask user to contact HR

# Mention source document and page number

# Use professional and concise responses

# Insert retrieved document chunks here
{context}

# Insert user question here
{question}

Answer:
""",
)


# Main HR Policy Agent class
class PolicyAgent:

    """
    RAG Pipeline:

    Retriever
        ↓
    Prompt Builder
        ↓
    Gemini LLM
        ↓
    Final Parsed Response
    """

    # Constructor runs when object is created
    def __init__(self):

        # Initialize Gemini LLM model
        self.llm = GeminiLLM()

        # Initialize retriever for vector search
        self.retriever = HRRetriever()

        # Initialize output parser
        self.parser = StrOutputParser()

        # Create LangChain pipeline chain
        # Prompt → LLM → Output Parser
        self.chain = POLICY_PROMPT | self.llm | self.parser

    # Main function to process user question
    def run(self, question: str) -> dict:

        """
        Input:
            User question

        Output:
            AI answer + source citations
        """

        # Step 1:
        # Retrieve most relevant chunks from ChromaDB
        chunks = self.retriever.retrieve(question)

        # Convert retrieved chunks into formatted context text
        context = self.retriever.format_context(chunks)

        # Step 2:
        # Send context + question to Gemini model
        answer = self.chain.invoke({

            # Insert retrieved context into prompt
            "context": context,

            # Insert user question into prompt
            "question": question,
        })

        # Step 3:
        # Build source list for frontend citation display
        sources = [

            # Create source dictionary for each chunk
            {
                "source": c["source"],

                # Get page number if available
                "page": c.get("page", ""),

                # Similarity/relevance score
                "score": c["score"],
            }

            # Loop through all retrieved chunks
            for c in chunks
        ]

        # Return final API response
        return {

            # Remove extra spaces/newlines from answer
            "answer": answer.strip(),

            # Return source citations
            "sources": sources,

            # Mention which agent handled request
            "agent": "policy",
        }


# Run file directly for testing
if __name__ == "__main__":

    # Create PolicyAgent object
    agent = PolicyAgent()

    # Sample test questions
    questions = [
        "How many casual leaves do I get per year?",
        "What is the work from home policy?",
        "How do I apply for sick leave?",
    ]

    # Loop through all questions
    for q in questions:

        # Print question
        print(f"\nQ: {q}")

        # Run agent for current question
        result = agent.run(q)

        # Print generated answer
        print(f"A: {result['answer']}")

        # Print source citations
        print(f"Sources: {result['sources']}")

        # Print separator line
        print("-" * 50)