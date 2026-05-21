"""
email_agent.py — Gmail Email Agent (Fixed).

Key fixes:
- Removed early_stopping_method="generate" (unsupported)  
- Agent ALWAYS uses draft_email first — never send_email directly
- action_card includes pending=True so UI shows Edit+Send buttons
- Actual send only happens when user clicks Send in the UI
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from llm.gemini_wrapper import GeminiLLM
from mcp_tools.gmail_tools import GMAIL_TOOLS


EMAIL_SYSTEM_PROMPT = PromptTemplate.from_template(
    """You are an HR Email Assistant. Help employees draft professional emails.

TOOLS available:
- list_emails: Check recent inbox emails (input: {{"max_results": 5}})
- draft_email: Compose a draft (to, subject, body) — does NOT send
- send_email: Send immediately (ONLY use if user explicitly says "send now" or "confirm send")

EMAIL WRITING RULES:
1. Write professional, concise emails (under 150 words)
2. For HR topics (leave, WFH, appraisal etc.) use formal but friendly tone
3. Use "I" not "we" for personal requests
4. End with a polite sign-off (e.g., "Best regards, [Your Name]")
5. If recipient email is missing, use a placeholder like "[manager@company.com]"
6. Always include a clear subject line
7. Never leave the subject or body blank or omit them from the action input

IMPORTANT — ALWAYS use draft_email tool first unless user explicitly confirms sending.
The draft_email Action Input MUST be:
{{"to": "email@example.com", "subject": "Subject here", "body": "Full email body here"}}

If the user asks to compose an email, you MUST provide all three fields.
If you do not know the exact recipient address, use "[manager@company.com]".

{tools}

FORMAT — use EXACTLY this format:
Question: the input question
Thought: reasoning  
Action: one of [{tool_names}]
Action Input: valid JSON object
Observation: result
Thought: I now know the final answer
Final Answer: friendly response to user

Previous conversation context:
{chat_history}

Question: {input}
Thought:{agent_scratchpad}"""
)


class EmailAgent:
    """
    ReAct agent for email drafting.
    
    Flow:
      1. Agent calls draft_email → returns draft data
      2. _extract_action_card builds action_card with pending=True
      3. React UI shows Edit + Send buttons
      4. User can edit inline, then clicks Send
      5. /confirm-send-email endpoint does the actual Gmail send
    """

    def __init__(self):
        self.llm = GeminiLLM()
        self.tools = GMAIL_TOOLS

        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=EMAIL_SYSTEM_PROMPT,
        )

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors="Check your output. Use exact format: Action: tool_name, Action Input: valid JSON",
        )

    def run(self, question: str, chat_history: str = "") -> dict:
        try:
            result = self.executor.invoke({
                "input": question,
                "chat_history": chat_history,
            })
            output = result.get("output", "")
            action_card = self._extract_action_card(result)

            return {
                "answer": output,
                "agent": "email",
                "action_card": action_card,
            }

        except Exception as e:
            message = str(e)
            if "draft_emailSchema" in message or ("subject" in message and "body" in message):
                message = (
                    "I couldn't compose the draft because the email subject or body was missing. "
                    "Please ask me to draft an email with a recipient, a subject, and a full message body."
                )
            return {
                "answer": f"I had trouble composing the email: {message}. Please try again.",
                "agent": "email",
                "action_card": None,
            }

    def _extract_action_card(self, result: dict) -> dict | None:
        intermediate = result.get("intermediate_steps", [])
        for action, observation in intermediate:
            if action.tool == "draft_email":
                tool_input = action.tool_input
                obs_data = {}
                try:
                    obs_data = json.loads(observation)
                except Exception:
                    pass

                return {
                    "type": "email",
                    "pending": True,   # <-- user must click Send
                    "to": tool_input.get("to", ""),
                    "subject": tool_input.get("subject", ""),
                    "body": tool_input.get("body", obs_data.get("body", "")),
                    "ready_to_send": True,
                }

            if action.tool == "send_email":
                obs_data = {}
                try:
                    obs_data = json.loads(observation)
                except Exception:
                    pass
                return {
                    "type": "email",
                    "sent": True,
                    "success": obs_data.get("success", False),
                    "message": obs_data.get("message", ""),
                    "to": action.tool_input.get("to", ""),
                    "subject": action.tool_input.get("subject", ""),
                }

        return None