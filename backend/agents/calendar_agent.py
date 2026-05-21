"""
calendar_agent.py — Google Calendar Agent (Fixed).

Key fixes:
- Removed early_stopping_method="generate" (unsupported in this LangChain version)
- Much stricter date/time extraction prompt
- Returns action_card with pending=True so UI shows Edit+Create buttons
- Calendar event is NOT created until user clicks Create in the UI
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from llm.gemini_wrapper import GeminiLLM
from mcp_tools.calendar_tools import CALENDAR_TOOLS


CALENDAR_SYSTEM_PROMPT = PromptTemplate.from_template(
    """You are an HR Calendar Assistant. Help employees manage their Google Calendar.

Today's date and time: {today}

AVAILABLE TOOLS:
- list_events: Get upcoming calendar events (input: {{"days_ahead": 7}})
- create_event: Schedule a new calendar event
- delete_event: Cancel an event by event_id

STRICT DATE/TIME RULES — follow these exactly:
1. "today" = {today_date}
2. "tomorrow" = {tomorrow_date}
3. Always output date as YYYY-MM-DD and time as HH:MM (24h)
4. "2pm" → "14:00", "3pm" → "15:00", "10am" → "10:00", "9am" → "09:00"
5. "1 hour" → duration_minutes: 60, "30 min" → duration_minutes: 30, "2 hours" → duration_minutes: 120
6. If no duration given, default to 30 minutes
7. If no attendee email given, omit attendee_email field

IMPORTANT — for create_event, Action Input MUST include all required fields:
{{"title": "...", "date": "YYYY-MM-DD", "start_time": "HH:MM", "duration_minutes": 30}}

{tools}

FORMAT — use EXACTLY this format, nothing else:
Question: the input question
Thought: reasoning
Action: one of [{tool_names}]
Action Input: valid JSON object
Observation: result
Thought: I now know the final answer
Final Answer: friendly response

Previous conversation context:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}"""
)


class CalendarAgent:
    """
    ReAct agent for calendar management.
    
    IMPORTANT CHANGE: create_event tool is called to VALIDATE the data
    and build the action_card, but the actual Google Calendar API call
    is deferred to the /confirm-book-event endpoint (when user clicks Create).
    
    To support this, we use a DRY_RUN mode where create_event returns
    the event data without actually calling Google API.
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
            verbose=True,
            max_iterations=6,
            handle_parsing_errors="Check your output. Use exact format: Action: tool_name, Action Input: valid JSON",
        )

    def run(self, question: str, chat_history: str = "") -> dict:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d (%A) %H:%M")
        today_date = now.strftime("%Y-%m-%d")
        tomorrow_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            result = self.executor.invoke({
                "input": question,
                "today": today,
                "today_date": today_date,
                "tomorrow_date": tomorrow_date,
                "chat_history": chat_history,
            })

            output = result.get("output", "")
            action_card = self._extract_action_card(result)

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

    def _extract_action_card(self, result: dict) -> dict | None:
        intermediate = result.get("intermediate_steps", [])
        for action, observation in intermediate:
            if action.tool == "create_event":
                tool_input = action.tool_input
                obs_data = {}
                try:
                    obs_data = json.loads(observation)
                except Exception:
                    pass

                # Build action card — UI will show Edit + Create buttons
                # pending=True means the user still needs to click Create
                return {
                    "type": "calendar",
                    "action": "create",
                    "pending": True,   # <-- NEW: user must click Create
                    "title": tool_input.get("title", ""),
                    "date": tool_input.get("date", ""),
                    "start_time": tool_input.get("start_time", ""),
                    "duration_minutes": tool_input.get("duration_minutes", 30),
                    "attendee_email": tool_input.get("attendee_email", ""),
                    "description": tool_input.get("description", ""),
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