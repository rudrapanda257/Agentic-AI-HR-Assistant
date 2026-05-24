"""
email_agent.py

This file creates the AI Email Agent using ReAct architecture.

Main Flow:
User Request
      ↓
ReAct Agent
      ↓
Thought → Action → Observation
      ↓
draft_email Tool
      ↓
Build action_card
      ↓
Frontend shows Edit + Send buttons
      ↓
User clicks Send
      ↓
/confirm-send-email API
      ↓
Real Gmail Email Sent

Important:
- Agent only drafts email first
- Actual send happens only after user confirmation
"""

# ─────────────────────────────────────────────────────────
# IMPORT SECTION
# This block imports required libraries
# ─────────────────────────────────────────────────────────

# Used for system-level operations
import sys

# Used for JSON parsing
import json

# Used for handling file paths
from pathlib import Path


# Add backend folder into Python import path
# So project modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))


# Import LangChain ReAct agent creator
from langchain.agents import (
    create_react_agent,
    AgentExecutor
)


# Import prompt template builder
from langchain_core.prompts import PromptTemplate


# Import custom Gemini wrapper
from llm.gemini_wrapper import GeminiLLM


# Import Gmail tools
from mcp_tools.gmail_tools import GMAIL_TOOLS


# ─────────────────────────────────────────────────────────
# SYSTEM PROMPT BLOCK
# This prompt controls Email Agent behavior
# ─────────────────────────────────────────────────────────

EMAIL_SYSTEM_PROMPT = PromptTemplate.from_template(

    """
    This prompt teaches the AI:

    - How to write professional emails
    - Which tools are available
    - How ReAct format should work
    - Never send directly without confirmation
    - Always use draft_email first
    """
)


# ─────────────────────────────────────────────────────────
# MAIN EMAIL AGENT CLASS
# Handles AI email drafting workflow
# ─────────────────────────────────────────────────────────

class EmailAgent:

    """
    ReAct-based Email Agent.

    Responsibilities:
    - Draft emails
    - Build UI action cards
    - Prepare email before sending
    """

    # ── INITIALIZATION BLOCK ────────────────────────────

    def __init__(self):

        # Load Gemini LLM
        self.llm = GeminiLLM()


        # Load Gmail tools
        self.tools = GMAIL_TOOLS


        # Create ReAct agent
        agent = create_react_agent(

            # LLM used by agent
            llm=self.llm,

            # Available tools
            tools=self.tools,

            # System instructions
            prompt=EMAIL_SYSTEM_PROMPT,
        )


        # Create AgentExecutor
        # Executes Thought → Action → Observation loop
        self.executor = AgentExecutor(

            # ReAct agent
            agent=agent,

            # Available tools
            tools=self.tools,

            # Print internal reasoning logs
            verbose=True,

            # Maximum ReAct iterations
            max_iterations=5,

            # Handle invalid output formatting
            handle_parsing_errors=
            "Check your output. "
            "Use exact format: "
            "Action: tool_name, "
            "Action Input: valid JSON",
        )


    # ─────────────────────────────────────────────────────
    # MAIN RUN FUNCTION
    # Executes Email Agent workflow
    # ─────────────────────────────────────────────────────

    def run(
        self,
        question: str,
        chat_history: str = ""
    ) -> dict:

        """
        Main email generation pipeline.
        """

        try:

            # Execute ReAct workflow
            result = self.executor.invoke({

                # Current user request
                "input": question,

                # Previous conversation history
                "chat_history": chat_history,
            })


            # Extract final AI response
            output = result.get("output", "")


            # Build frontend action card
            action_card = self._extract_action_card(
                result
            )


            # Return final response
            return {

                # AI-generated response
                "answer": output,

                # Agent type
                "agent": "email",

                # Frontend action card
                "action_card": action_card,
            }

        except Exception as e:

            # Convert error into string
            message = str(e)


            # Handle missing email fields
            if (
                "draft_emailSchema" in message
                or (
                    "subject" in message
                    and "body" in message
                )
            ):

                # User-friendly validation error
                message = (

                    "I couldn't compose the draft "
                    "because subject/body was missing."
                )


            # Return failure response
            return {

                "answer":
                f"I had trouble composing the email: "
                f"{message}. Please try again.",

                "agent": "email",

                "action_card": None,
            }


    # ─────────────────────────────────────────────────────
    # ACTION CARD EXTRACTION BLOCK
    # Converts tool outputs into frontend UI cards
    # ─────────────────────────────────────────────────────

    def _extract_action_card(
        self,
        result: dict
    ) -> dict | None:

        """
        Extract frontend action cards
        from ReAct intermediate steps.
        """

        # Get ReAct execution steps
        intermediate = result.get(
            "intermediate_steps",
            []
        )


        # Loop through all tool actions
        for action, observation in intermediate:


            # ── DRAFT EMAIL TOOL BLOCK ───────────────────

            # If draft_email tool was used
            if action.tool == "draft_email":

                # Tool input data
                tool_input = action.tool_input


                # Store observation data
                obs_data = {}


                try:

                    # Parse JSON observation
                    obs_data = json.loads(
                        observation
                    )

                except Exception:

                    # Ignore parsing errors
                    pass


                # Return frontend email card
                return {

                    # Card type
                    "type": "email",

                    # Email still pending confirmation
                    "pending": True,

                    # Receiver email
                    "to": tool_input.get("to", ""),

                    # Email subject
                    "subject": tool_input.get(
                        "subject",
                        ""
                    ),

                    # Email body
                    "body": tool_input.get(
                        "body",
                        obs_data.get("body", "")
                    ),

                    # Frontend can enable Send button
                    "ready_to_send": True,
                }


            # ── SEND EMAIL TOOL BLOCK ────────────────────

            # If email was actually sent
            if action.tool == "send_email":

                # Store observation data
                obs_data = {}


                try:

                    # Parse JSON observation
                    obs_data = json.loads(
                        observation
                    )

                except Exception:

                    # Ignore parsing errors
                    pass


                # Return sent-status card
                return {

                    # Card type
                    "type": "email",

                    # Email already sent
                    "sent": True,

                    # Gmail success status
                    "success": obs_data.get(
                        "success",
                        False
                    ),

                    # Success/failure message
                    "message": obs_data.get(
                        "message",
                        ""
                    ),

                    # Receiver email
                    "to": action.tool_input.get(
                        "to",
                        ""
                    ),

                    # Email subject
                    "subject": action.tool_input.get(
                        "subject",
                        ""
                    ),
                }


        # Return None if no action card found
        return None