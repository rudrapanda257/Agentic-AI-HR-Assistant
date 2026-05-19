"""
email_agent.py — Gmail Email Agent.

Flow:
    User says "send email to X about Y"
        → agent drafts a professional email using LLM
        → returns draft as action_card (does NOT send yet)
        → user sees preview card in React UI
        → user clicks "Send" → /confirm-send-email endpoint actually sends

Safety pattern: draft_email tool just returns the content.
Actual sending via send_email only happens from confirm endpoint.
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
    """You are an HR Email Assistant. Help employees draft and send professional emails.

You have these tools:
- list_emails: Check recent inbox emails
- draft_email: Compose an email draft (to, subject, body) — does NOT send, shows preview to user
- send_email: Send an email (only use when user explicitly confirms)

Email writing rules:
1. Always write professional, concise emails
2. For HR-related emails (leave requests, WFH, etc.), use formal but friendly tone
3. Keep emails under 150 words unless detailed explanation needed
4. Use "I" not "we" for personal emails
5. End with a polite sign-off
6. If recipient email not mentioned, use a placeholder like "[manager-email@company.com]"

IMPORTANT: For draft requests, ALWAYS use draft_email tool first.
Never use send_email unless user explicitly says "yes send it" or "confirm send".

{tools}

Use this exact format:
Question: the input question you must answer
Thought: your reasoning
Action: the action to take, must be one of [{tool_names}]
Action Input: the input as a JSON object
Observation: the result
Thought: I now know the final answer
Final Answer: your response to user

Question: {input}
Thought:{agent_scratchpad}"""
)


class EmailAgent:
    """
    ReAct agent for email drafting and sending.
    Returns action_card with draft details for React UI preview.
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
            max_iterations=4,
            handle_parsing_errors=True,
        )

    def run(self, question: str) -> dict:
        """
        Run the email agent.
        
        Returns:
            {
                "answer": "Here's your draft email. Review and click Send when ready.",
                "agent": "email",
                "action_card": {
                    "type": "email",
                    "to": "manager@company.com",
                    "subject": "WFH Request — Friday 23 May",
                    "body": "Hi ...",
                    "ready_to_send": true
                }
            }
        """
        try:
            result = self.executor.invoke({"input": question})
            output = result.get("output", "")
            action_card = self._extract_action_card(result)

            return {
                "answer": output,
                "agent": "email",
                "action_card": action_card,
            }

        except Exception as e:
            return {
                "answer": f"I had trouble composing the email: {str(e)}. Please try again.",
                "agent": "email",
                "action_card": None,
            }

    def _extract_action_card(self, result: dict) -> dict | None:
        """
        Extract draft details from tool call steps → build action_card for UI.
        """
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
                }

        return None


# ── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = EmailAgent()

    print("Test: Draft WFH email")
    r = agent.run("Draft an email to my manager requesting work from home on Friday")
    print(r["answer"])
    if r.get("action_card"):
        card = r["action_card"]
        print(f"\nTo: {card['to']}")
        print(f"Subject: {card['subject']}")
        print(f"Body:\n{card['body']}")