"""
orchestrator.py — LangGraph Orchestrator.

This is the brain of the system. It:
1. Classifies user intent (policy / calendar / email)
2. Routes to the correct sub-agent node
3. Returns the agent's response with metadata

LangGraph StateGraph:
    [START] → classify_intent → (policy | calendar | email) → [END]

All agent runs are automatically traced in LangSmith.
"""
import sys
from pathlib import Path
from typing import TypedDict, Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm.gemini_wrapper import GeminiLLM
from agents.policy_agent import PolicyAgent
from agents.calendar_agent import CalendarAgent
from agents.email_agent import EmailAgent


# ── State definition ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    """State passed between LangGraph nodes."""
    session_id: str
    user_message: str
    intent: str           # "policy" | "calendar" | "email" | "unknown"
    response: dict        # final agent response


# ── Intent classifier prompt ──────────────────────────────────────────────────
CLASSIFIER_PROMPT = PromptTemplate(
    input_variables=["message"],
    template="""Classify the user's HR-related message into exactly one of these categories:
- policy    → questions about HR policies, leaves, benefits, rules, WFH policy, salary, appraisals
- calendar  → scheduling meetings, checking availability, booking events, cancelling meetings
- email     → drafting emails, sending emails, reading emails, composing messages

User message: {message}

Rules:
- Reply with ONLY ONE WORD: policy, calendar, or email
- No explanation, no punctuation
- If unclear, default to: policy

Category:""",
)


class HROrchestratorGraph:
    """
    LangGraph-based orchestrator.
    
    Usage:
        graph = HROrchestratorGraph()
        result = graph.run("session_123", "How many leaves do I get?")
        # result = {"answer": "...", "agent": "policy", "sources": [...]}
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.classifier_chain = CLASSIFIER_PROMPT | self.llm | StrOutputParser()

        # Initialize sub-agents (lazy — loaded once)
        self._policy_agent = None
        self._calendar_agent = None
        self._email_agent = None

        # Build and compile the graph
        self.graph = self._build_graph()

    # ── Lazy agent loaders ────────────────────────────────────────────────────
    @property
    def policy_agent(self):
        if self._policy_agent is None:
            self._policy_agent = PolicyAgent()
        return self._policy_agent

    @property
    def calendar_agent(self):
        if self._calendar_agent is None:
            self._calendar_agent = CalendarAgent()
        return self._calendar_agent

    @property
    def email_agent(self):
        if self._email_agent is None:
            self._email_agent = EmailAgent()
        return self._email_agent

    # ── LangGraph nodes ───────────────────────────────────────────────────────
    def _classify_intent_node(self, state: AgentState) -> AgentState:
        """Node: classify user intent using the LLM."""
        raw = self.classifier_chain.invoke({"message": state["user_message"]})
        intent = raw.strip().lower()

        # Normalize
        if intent not in ("policy", "calendar", "email"):
            intent = "policy"  # safe default

        return {**state, "intent": intent}

    def _policy_node(self, state: AgentState) -> AgentState:
        """Node: run the Policy RAG agent."""
        result = self.policy_agent.run(state["user_message"])
        return {**state, "response": result}

    def _calendar_node(self, state: AgentState) -> AgentState:
        """Node: run the Calendar agent."""
        result = self.calendar_agent.run(state["user_message"])
        return {**state, "response": result}

    def _email_node(self, state: AgentState) -> AgentState:
        """Node: run the Email agent."""
        result = self.email_agent.run(state["user_message"])
        return {**state, "response": result}

    # ── Router (edge condition) ───────────────────────────────────────────────
    def _route(self, state: AgentState) -> Literal["policy_node", "calendar_node", "email_node"]:
        """Conditional edge: route to agent node based on classified intent."""
        intent_map = {
            "policy": "policy_node",
            "calendar": "calendar_node",
            "email": "email_node",
        }
        return intent_map.get(state["intent"], "policy_node")

    # ── Build graph ───────────────────────────────────────────────────────────
    def _build_graph(self) -> StateGraph:
        """Build and compile the LangGraph StateGraph."""
        builder = StateGraph(AgentState)

        # Add nodes
        builder.add_node("classify_intent", self._classify_intent_node)
        builder.add_node("policy_node", self._policy_node)
        builder.add_node("calendar_node", self._calendar_node)
        builder.add_node("email_node", self._email_node)

        # Add edges
        builder.add_edge(START, "classify_intent")
        builder.add_conditional_edges(
            "classify_intent",
            self._route,
            {
                "policy_node": "policy_node",
                "calendar_node": "calendar_node",
                "email_node": "email_node",
            },
        )
        builder.add_edge("policy_node", END)
        builder.add_edge("calendar_node", END)
        builder.add_edge("email_node", END)

        return builder.compile()

    def run(self, session_id: str, message: str) -> dict:
        """
        Main entry point — run the full orchestration pipeline.
        
        Args:
            session_id: Unique session identifier (for LangSmith tracing)
            message: User's natural language message
        
        Returns:
            {
                "answer": "string response",
                "agent": "policy" | "calendar" | "email",
                "intent": "policy" | "calendar" | "email",
                "sources": [...],         # only for policy agent
                "action_card": {...},     # only for calendar/email agents
            }
        """
        initial_state: AgentState = {
            "session_id": session_id,
            "user_message": message,
            "intent": "",
            "response": {},
        }

        # Run the graph with LangSmith config for tracing
        config = {
            "configurable": {"session_id": session_id},
            "run_name": f"hr_agent_{session_id[:8]}",
        }

        final_state = self.graph.invoke(initial_state, config=config)
        response = final_state.get("response", {})

        # Flatten response for API consumption
        return {
            "answer": response.get("answer", "I'm sorry, I couldn't process that request."),
            "agent": response.get("agent", "unknown"),
            "intent": final_state.get("intent", "unknown"),
            "sources": response.get("sources", []),
            "action_card": response.get("action_card", None),
        }


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    graph = HROrchestratorGraph()

    test_cases = [
        ("session_001", "How many casual leaves do employees get?"),
        ("session_002", "Schedule a meeting with Priya tomorrow at 3pm for 30 mins"),
        ("session_003", "Draft an email to HR asking about my appraisal status"),
    ]

    for session_id, message in test_cases:
        print(f"\n{'='*60}")
        print(f"Message: {message}")
        result = graph.run(session_id, message)
        print(f"Routed to: {result['agent']} agent")
        print(f"Answer: {result['answer'][:200]}...")
        if result.get("sources"):
            print(f"Sources: {[s['source'] for s in result['sources']]}")
        if result.get("action_card"):
            print(f"Action card: {result['action_card']}")