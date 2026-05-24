"""
orchestrator.py

This file is the main LangGraph orchestrator.

Purpose:
- Detect user intent
- Route request to correct agent
- Pass chat history to agents
- Return final response

Main Flow:
User Message
      ↓
Intent Classification
      ↓
Route to Correct Agent
 ┌────────┼────────┐
 ↓        ↓        ↓
Policy  Calendar  Email
 Agent    Agent    Agent
      ↓
Final Response

Special Feature:
- Loads real chat history from SQLite
- Enables multi-turn conversations
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports required libraries
# ─────────────────────────────────────────────────────────

# Used for system-level operations
import sys

# Used for file path handling
from pathlib import Path

# Used for defining strict data types
from typing import TypedDict, Literal


# Add backend folder to Python path
# Allows importing project modules
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import LangGraph workflow classes
from langgraph.graph import (
    StateGraph,
    START,
    END
)


# Import LangChain prompt template
from langchain_core.prompts import PromptTemplate


# Import output parser
from langchain_core.output_parsers import StrOutputParser


# Import Gemini LLM wrapper
from llm.gemini_wrapper import GeminiLLM


# Import all agents
from agents.policy_agent import PolicyAgent
from agents.calendar_agent import CalendarAgent
from agents.email_agent import EmailAgent


# Import SQLite history loader
from memory.session_store import get_history


# ─────────────────────────────────────────────────────────
# STATE DEFINITION BLOCK
# This defines shared workflow state
# ─────────────────────────────────────────────────────────

class AgentState(TypedDict):

    """
    Shared workflow memory/state.
    Passed between all LangGraph nodes.
    """

    # Current session ID
    session_id: str

    # User message/question
    user_message: str

    # Detected intent
    intent: str

    # Previous conversation history
    chat_history: str

    # Final agent response
    response: dict


# ─────────────────────────────────────────────────────────
# INTENT CLASSIFIER PROMPT BLOCK
# This prompt decides which agent to use
# ─────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = PromptTemplate(

    # Dynamic input variables
    input_variables=["message"],

    # Prompt sent to Gemini
    template="""

Classify user message into one category:

policy
calendar
email

Examples:
- Leave questions → policy
- Schedule meeting → calendar
- Send mail → email

Rules:
- Return ONLY ONE WORD
- No explanation

User message:
{message}

Category:
""",
)


# ─────────────────────────────────────────────────────────
# CHAT HISTORY FORMATTER BLOCK
# Loads previous conversation from SQLite
# ─────────────────────────────────────────────────────────

def _format_history(session_id: str, limit: int = 6) -> str:

    """
    Load previous chat messages
    and convert them into readable text.
    """

    try:

        # Load messages from SQLite
        messages = get_history(
            session_id,
            limit=limit
        )


        # Return empty string if no history
        if not messages:
            return ""


        # Store formatted chat lines
        lines = []


        # Loop through messages
        for msg in messages:

            # Convert role into readable label
            role = (
                "User"
                if msg["role"] == "user"
                else "Assistant"
            )


            # Limit message length
            content = msg["content"][:300]


            # Create readable history line
            lines.append(f"{role}: {content}")


        # Join all messages into one string
        return "\n".join(lines)

    except Exception:

        # Return empty history if error occurs
        return ""


# ─────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR CLASS
# Controls workflow routing and execution
# ─────────────────────────────────────────────────────────

class HROrchestratorGraph:

    """
    Main LangGraph orchestrator.
    """

    # ── INITIALIZATION BLOCK ────────────────────────────

    def __init__(self):

        # Load Gemini LLM
        self.llm = GeminiLLM()


        # Create intent classification chain
        # Prompt → Gemini → String Output
        self.classifier_chain = (

            CLASSIFIER_PROMPT
            | self.llm
            | StrOutputParser()
        )


        # Lazy-loaded agent placeholders
        self._policy_agent = None
        self._calendar_agent = None
        self._email_agent = None


        # Build LangGraph workflow
        self.graph = self._build_graph()


    # ─────────────────────────────────────────────────────
    # AGENT LOADING BLOCKS
    # Lazy loads agents only when needed
    # ─────────────────────────────────────────────────────

    @property
    def policy_agent(self):

        # Load PolicyAgent only once
        if self._policy_agent is None:
            self._policy_agent = PolicyAgent()

        return self._policy_agent


    @property
    def calendar_agent(self):

        # Load CalendarAgent only once
        if self._calendar_agent is None:
            self._calendar_agent = CalendarAgent()

        return self._calendar_agent


    @property
    def email_agent(self):

        # Load EmailAgent only once
        if self._email_agent is None:
            self._email_agent = EmailAgent()

        return self._email_agent


    # ─────────────────────────────────────────────────────
    # INTENT CLASSIFICATION NODE
    # Detects which agent should handle request
    # ─────────────────────────────────────────────────────

    def _classify_intent_node(
        self,
        state: AgentState
    ) -> AgentState:

        # Send user message to classifier LLM
        raw = self.classifier_chain.invoke({

            # Current user message
            "message": state["user_message"]
        })


        # Clean and normalize output
        intent = raw.strip().lower()


        # Fallback to policy if invalid intent
        if intent not in (
            "policy",
            "calendar",
            "email"
        ):
            intent = "policy"


        # Return updated state
        return {
            **state,
            "intent": intent
        }


    # ─────────────────────────────────────────────────────
    # POLICY AGENT NODE
    # Executes policy RAG agent
    # ─────────────────────────────────────────────────────

    def _policy_node(
        self,
        state: AgentState
    ) -> AgentState:

        # Run policy agent
        result = self.policy_agent.run(

            # User question
            state["user_message"]
        )


        # Return updated state
        return {
            **state,
            "response": result
        }


    # ─────────────────────────────────────────────────────
    # CALENDAR AGENT NODE
    # Executes calendar agent
    # ─────────────────────────────────────────────────────

    def _calendar_node(
        self,
        state: AgentState
    ) -> AgentState:

        # Run calendar agent
        result = self.calendar_agent.run(

            # User question
            question=state["user_message"],

            # Previous conversation history
            chat_history=state["chat_history"],
        )


        # Return updated state
        return {
            **state,
            "response": result
        }


    # ─────────────────────────────────────────────────────
    # EMAIL AGENT NODE
    # Executes email agent
    # ─────────────────────────────────────────────────────

    def _email_node(
        self,
        state: AgentState
    ) -> AgentState:

        # Run email agent
        result = self.email_agent.run(

            # User question
            question=state["user_message"],

            # Previous conversation history
            chat_history=state["chat_history"],
        )


        # Return updated state
        return {
            **state,
            "response": result
        }


    # ─────────────────────────────────────────────────────
    # ROUTING BLOCK
    # Chooses next graph node
    # ─────────────────────────────────────────────────────

    def _route(
        self,
        state: AgentState
    ) -> Literal[
        "policy_node",
        "calendar_node",
        "email_node"
    ]:

        # Intent → node mapping
        intent_map = {

            "policy": "policy_node",
            "calendar": "calendar_node",
            "email": "email_node",
        }


        # Return matching node
        return intent_map.get(
            state["intent"],
            "policy_node"
        )


    # ─────────────────────────────────────────────────────
    # GRAPH BUILDING BLOCK
    # Creates LangGraph workflow
    # ─────────────────────────────────────────────────────

    def _build_graph(self) -> StateGraph:

        # Create graph object
        builder = StateGraph(AgentState)


        # Add graph nodes
        builder.add_node(
            "classify_intent",
            self._classify_intent_node
        )

        builder.add_node(
            "policy_node",
            self._policy_node
        )

        builder.add_node(
            "calendar_node",
            self._calendar_node
        )

        builder.add_node(
            "email_node",
            self._email_node
        )


        # Workflow start point
        builder.add_edge(
            START,
            "classify_intent"
        )


        # Conditional routing logic
        builder.add_conditional_edges(

            # Source node
            "classify_intent",

            # Routing function
            self._route,

            # Possible destinations
            {
                "policy_node": "policy_node",
                "calendar_node": "calendar_node",
                "email_node": "email_node",
            },
        )


        # End workflow after agent execution
        builder.add_edge("policy_node", END)
        builder.add_edge("calendar_node", END)
        builder.add_edge("email_node", END)


        # Compile graph into executable workflow
        return builder.compile()


    # ─────────────────────────────────────────────────────
    # MAIN RUN FUNCTION
    # Executes complete workflow
    # ─────────────────────────────────────────────────────

    def run(
        self,
        session_id: str,
        message: str
    ) -> dict:

        # Load previous chat history
        chat_history = _format_history(
            session_id,
            limit=8
        )


        # Create initial workflow state
        initial_state: AgentState = {

            "session_id": session_id,
            "user_message": message,
            "intent": "",
            "chat_history": chat_history,
            "response": {},
        }


        # LangGraph execution config
        config = {

            "configurable": {
                "session_id": session_id
            },

            "run_name": f"hr_agent_{session_id[:8]}",
        }


        # Execute LangGraph workflow
        final_state = self.graph.invoke(
            initial_state,
            config=config
        )


        # Extract final response
        response = final_state.get(
            "response",
            {}
        )


        # Return formatted API response
        return {

            # Final AI answer
            "answer": response.get(
                "answer",
                "I'm sorry, I couldn't process that request."
            ),

            # Which agent handled request
            "agent": response.get(
                "agent",
                "unknown"
            ),

            # Detected intent
            "intent": final_state.get(
                "intent",
                "unknown"
            ),

            # Document sources
            "sources": response.get(
                "sources",
                []
            ),

            # Optional frontend action card
            "action_card": response.get(
                "action_card",
                None
            ),
        }