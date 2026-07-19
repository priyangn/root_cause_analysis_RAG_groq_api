import os
import logging
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)


def _get_emergent_classes():
    """Lazy import — emergentintegrations is only available on Emergent platform."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        return LlmChat, UserMessage
    except ImportError:
        return None, None


class BaseAgent:
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.emergent_api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        self.use_groq = bool(self.groq_api_key)

        if not self.groq_api_key and not self.emergent_api_key:
            raise ValueError("GROQ_API_KEY is required (set in backend/.env)")

    async def create_chat(self, system_message: str, session_id: str):
        """For Emergent LLM compatibility (optional fallback)."""
        if not self.use_groq and self.emergent_api_key:
            LlmChat, _ = _get_emergent_classes()
            if LlmChat is None:
                logger.warning("emergentintegrations not installed — Emergent LLM unavailable")
                return None
            chat = LlmChat(
                api_key=self.emergent_api_key,
                session_id=session_id,
                system_message=system_message
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            return chat
        return None

    async def send_message(self, chat_or_system: any, message: str) -> str:
        """Send message with Groq (primary)."""
        try:
            if self.use_groq and self.groq_client:
                system_message = (
                    chat_or_system if isinstance(chat_or_system, str)
                    else "You are a helpful AI assistant."
                )

                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": message}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.7,
                    max_tokens=2000,
                )

                response = chat_completion.choices[0].message.content
                logger.info("Response from Groq")
                return response

            # Optional Emergent fallback (legacy)
            if self.emergent_api_key:
                LlmChat, UserMessage = _get_emergent_classes()
                if LlmChat is None:
                    return "Unable to process request — install emergentintegrations or set GROQ_API_KEY"

                logger.info("Using Emergent LLM (fallback)")
                if isinstance(chat_or_system, str):
                    chat = LlmChat(
                        api_key=self.emergent_api_key,
                        session_id="fallback_session",
                        system_message=chat_or_system
                    )
                    chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
                else:
                    chat = chat_or_system

                user_message = UserMessage(text=message)
                return await chat.send_message(user_message)

            return "Unable to process request — no LLM available"

        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return "Error processing request"
