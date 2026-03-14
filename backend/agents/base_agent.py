import os
import logging
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            raise ValueError("EMERGENT_LLM_KEY not found in environment")
    
    async def create_chat(self, system_message: str, session_id: str):
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        )
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
        return chat
    
    async def send_message(self, chat: LlmChat, message: str) -> str:
        try:
            user_message = UserMessage(text=message)
            response = await chat.send_message(user_message)
            return response
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return "Error processing request"