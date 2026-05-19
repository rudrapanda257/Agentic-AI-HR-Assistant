"""
policy_agent.py — RAG-powered HR Policy Agent.

Flow:
    User question
        → retrieve top-3 relevant chunks from ChromaDB (with reranking)
        → build prompt: [system] + [context chunks] + [question]
        → call Gemini LLM
        → return answer + source citations
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.gemini_wrapper import GeminiLLM
from rag.retriever import HRRetriever


POLICY_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a helpful HR assistant. Answer the employee's question based ONLY on the HR policy documents provided below.

Rules:
- Be concise and direct
- If the answer is not in the context, say "I don't have that information in our HR documents. Please contact HR directly."
- Always cite which document/policy your answer comes from
- Use bullet points for multi-part answers
- Be friendly and professional

--- HR Policy Context ---
{context}
--- End of Context ---

Employee Question: {question}

Answer:""",
)


class PolicyAgent:
    """
    RAG chain: retriever → prompt → LLM → parsed output.
    
    Also returns source chunks so the UI can show citation chips.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.retriever = HRRetriever()
        self.parser = StrOutputParser()

        # LangChain LCEL chain
        self.chain = POLICY_PROMPT | self.llm | self.parser

    def run(self, question: str) -> dict:
        """
        Run the policy agent.
        
        Returns:
            {
                "answer": "...",
                "sources": [{"source": "leave-policy.pdf", "page": 4, "score": 0.92}],
                "agent": "policy"
            }
        """
        # Step 1: Retrieve relevant chunks
        chunks = self.retriever.retrieve(question)
        context = self.retriever.format_context(chunks)

        # Step 2: Run the RAG chain
        answer = self.chain.invoke({
            "context": context,
            "question": question,
        })

        # Step 3: Build source list for UI citation chips
        sources = [
            {
                "source": c["source"],
                "page": c.get("page", ""),
                "score": c["score"],
            }
            for c in chunks
        ]

        return {
            "answer": answer.strip(),
            "sources": sources,
            "agent": "policy",
        }


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = PolicyAgent()
    questions = [
        "How many casual leaves do I get per year?",
        "What is the work from home policy?",
        "How do I apply for sick leave?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        result = agent.run(q)
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print("-" * 50)