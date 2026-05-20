"""
calendar_agent.py — Google Calendar Agent.

Uses LangChain's create_react_agent to let the LLM decide which
calendar tool to call based on the user's natural language request.

Tools: list_events, create_event, delete_event

The agent returns an action_card dict so the React UI can show
a confirmation card before actually booking.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from llm.gemini_wrapper import GeminiLLM
from mcp_tools.calendar_tools import CALENDAR_TOOLS


CALENDAR_SYSTEM_PROMPT = PromptTemplate.from_template(
    """You are an HR Calendar Assistant. Help employees manage their Google Calendar.

Today's date: {today}

You have these tools:
- list_events: Get upcoming calendar events
- If title/date/time/duration are available, directly call create_event tool.
- create_event: Schedule a new meeting (needs: title, date YYYY-MM-DD, start_time HH:MM, duration_minutes, attendee_email)
- delete_event: Cancel an event by event_id

Important rules:
1. For create_event, always extract date/time precisely from user's message
2. Convert relative dates ("tomorrow", "next Monday") to YYYY-MM-DD format using today's date
3. Convert "3pm" to "15:00", "9am" to "09:00"
4. If attendee email not provided, create event without attendee
5. Always confirm what you did
6. If enough information exists, directly create the event using create_event tool
7. Do not repeatedly ask for already provided information

{tools}

Use this exact format:
Question: the input question you must answer
Thought: your reasoning about what to do
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action as a JSON object
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: your friendly response to the user

Previous conversation:
{chat_history}

Question: {input}

IMPORTANT:
- If enough information already exists in previous conversation,
  DO NOT ask again.
- Use available details and execute tools directly.
- Avoid repeated questioning.

Thought:{agent_scratchpad}"""
)


class CalendarAgent:
    """
    ReAct agent that can list, create, and delete calendar events.
    Returns a structured response with optional action_card for UI.
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.tools = CALENDAR_TOOLS

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=CALENDAR_SYSTEM_PROMPT,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,           # logs each tool call — great for debugging
            max_iterations=8,
            early_stopping_method="generate",
            handle_parsing_errors="Check your output and follow exact Action format.",
        )

    def run(self, question: str, chat_history: str = "") -> dict:
        """
        Run the calendar agent.
        
        Returns:
            {
                "answer": "I've prepared the meeting details for your review",
                "agent": "calendar",
                "action_card": {           # only for create/delete actions
                    "type": "calendar",
                    "action": "create",
                    "title": "1:1 with Priya",
                    "date": "2026-05-21",
                    "start_time": "15:00",
                    "duration_minutes": 30,
                    "attendee_email": "priya@company.com"
                }
            }
        """
        today = datetime.now().strftime("%Y-%m-%d (%A)")

        try:
            result = self.executor.invoke({
                "input": question,
                "today": today,
                "chat_history": chat_history,
            })

            output = result.get("output", "")

            # Check if a create_event tool was called — build action card
            action_card = self._extract_action_card(result, question)

            return {
                "answer": output,
                "agent": "calendar",
                "action_card": action_card,
            }

        except Exception as e:
            return {
                "answer": f"I encountered an issue with the calendar: {str(e)}. Please try again.",
                "agent": "calendar",
                "action_card": None,
            }

    def _extract_action_card(self, result: dict, question: str) -> dict | None:
        """
        Parse intermediate steps to find tool calls and build action_card.
        This drives the confirmation card in the React UI.
        """
        intermediate = result.get("intermediate_steps", [])
        for action, observation in intermediate:
            if action.tool == "create_event":
                tool_input = action.tool_input
                obs_data = {}
                try:
                    obs_data = json.loads(observation)
                except Exception:
                    pass

                return {
                    "type": "calendar",
                    "action": "create",
                    "title": tool_input.get("title", ""),
                    "date": tool_input.get("date", ""),
                    "start_time": tool_input.get("start_time", ""),
                    "duration_minutes": tool_input.get("duration_minutes", 30),
                    "attendee_email": tool_input.get("attendee_email", ""),
                    "event_id": obs_data.get("event_id", ""),
                    "success": obs_data.get("success", False),
                }

            if action.tool == "delete_event":
                return {
                    "type": "calendar",
                    "action": "delete",
                    "event_id": action.tool_input.get("event_id", ""),
                }

        return None


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = CalendarAgent()

    print("Test: List events")
    r = agent.run("What meetings do I have in the next 3 days?")
    print(r["answer"])
    print()

    print("Test: Create event")
    r = agent.run("Schedule a 30-minute sync with Rahul tomorrow at 10am")
    print(r["answer"])
    if r.get("action_card"):
        print("Action card:", json.dumps(r["action_card"], indent=2))