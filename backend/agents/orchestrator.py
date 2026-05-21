"""
orchestrator.py — LangGraph Orchestrator (Fixed).

Key fixes:
- Loads real chat history from SQLite and passes it to calendar/email agents
- chat_history is formatted as readable string of last N messages
- Agents can see prior context so multi-turn conversations work
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
from memory.session_store import get_history


# ── State definition ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    session_id: str
    user_message: str
    intent: str
    chat_history: str
    response: dict


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


def _format_history(session_id: str, limit: int = 6) -> str:
    """
    Load last N messages from SQLite and format as readable context string.
    Returns empty string if no history.
    """
    try:
        messages = get_history(session_id, limit=limit)
        if not messages:
            return ""

        lines = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:300]  # truncate long messages
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
    except Exception:
        return ""


class HROrchestratorGraph:
    """
    LangGraph-based orchestrator with real session history.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.classifier_chain = CLASSIFIER_PROMPT | self.llm | StrOutputParser()

        self._policy_agent = None
        self._calendar_agent = None
        self._email_agent = None

        self.graph = self._build_graph()

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

    def _classify_intent_node(self, state: AgentState) -> AgentState:
        raw = self.classifier_chain.invoke({"message": state["user_message"]})
        intent = raw.strip().lower()
        if intent not in ("policy", "calendar", "email"):
            intent = "policy"
        return {**state, "intent": intent}

    def _policy_node(self, state: AgentState) -> AgentState:
        result = self.policy_agent.run(state["user_message"])
        return {**state, "response": result}

    def _calendar_node(self, state: AgentState) -> AgentState:
        result = self.calendar_agent.run(
            question=state["user_message"],
            chat_history=state["chat_history"],
        )
        return {**state, "response": result}

    def _email_node(self, state: AgentState) -> AgentState:
        result = self.email_agent.run(
            question=state["user_message"],
            chat_history=state["chat_history"],
        )
        return {**state, "response": result}

    def _route(self, state: AgentState) -> Literal["policy_node", "calendar_node", "email_node"]:
        intent_map = {
            "policy": "policy_node",
            "calendar": "calendar_node",
            "email": "email_node",
        }
        return intent_map.get(state["intent"], "policy_node")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(AgentState)
        builder.add_node("classify_intent", self._classify_intent_node)
        builder.add_node("policy_node", self._policy_node)
        builder.add_node("calendar_node", self._calendar_node)
        builder.add_node("email_node", self._email_node)
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
        # Load real chat history from DB
        chat_history = _format_history(session_id, limit=8)

        initial_state: AgentState = {
            "session_id": session_id,
            "user_message": message,
            "intent": "",
            "chat_history": chat_history,
            "response": {},
        }

        config = {
            "configurable": {"session_id": session_id},
            "run_name": f"hr_agent_{session_id[:8]}",
        }

        final_state = self.graph.invoke(initial_state, config=config)
        response = final_state.get("response", {})

        return {
            "answer": response.get("answer", "I'm sorry, I couldn't process that request."),
            "agent": response.get("agent", "unknown"),
            "intent": final_state.get("intent", "unknown"),
            "sources": response.get("sources", []),
            "action_card": response.get("action_card", None),
        }