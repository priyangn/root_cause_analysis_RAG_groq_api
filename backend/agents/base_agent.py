import os
import logging
import asyncio
import time
from typing import List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# Prefer current Groq production models; fall back if one is unavailable / rate-limited.
DEFAULT_GROQ_MODELS = [
    os.environ.get("GROQ_MODEL", "").strip() or "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
]


def _get_emergent_classes():
    """Lazy import — emergentintegrations is only available on Emergent platform."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        return LlmChat, UserMessage
    except ImportError:
        return None, None


def _unique_models() -> List[str]:
    seen = set()
    out = []
    for m in DEFAULT_GROQ_MODELS:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


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

    def _groq_complete(self, messages: list, model: str) -> str:
        kwargs = {
            "messages": messages,
            "model": model,
            "temperature": 0.7,
        }
        # Newer Groq models prefer max_completion_tokens; keep max_tokens as fallback.
        try:
            chat_completion = self.groq_client.chat.completions.create(
                **kwargs,
                max_completion_tokens=1500,
            )
        except TypeError:
            chat_completion = self.groq_client.chat.completions.create(
                **kwargs,
                max_tokens=1500,
            )
        return (chat_completion.choices[0].message.content or "").strip()

    def _call_groq_with_fallback(self, messages: list) -> str:
        last_error = None
        for model in _unique_models():
            for attempt in range(2):
                try:
                    text = self._groq_complete(messages, model)
                    if text:
                        logger.info("Response from Groq model=%s", model)
                        return text
                    last_error = RuntimeError(f"Empty response from {model}")
                except Exception as e:
                    last_error = e
                    err = str(e).lower()
                    logger.warning("Groq model=%s attempt=%s failed: %s", model, attempt + 1, e)
                    # Brief pause on rate limits before retry / next model
                    if "rate" in err or "429" in err or "tpm" in err:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    break  # try next model for non-rate errors
        raise RuntimeError(str(last_error) if last_error else "Groq request failed")

    async def send_message(
        self,
        chat_or_system,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> str:
        """Send message with Groq (primary). history: optional prior [{role, content}]."""
        try:
            if self.use_groq and self.groq_client:
                system_message = (
                    chat_or_system if isinstance(chat_or_system, str)
                    else "You are a helpful AI assistant."
                )

                # Keep API payload simple: system + one user message.
                # Embed prior turns in text to avoid role-alternation API errors.
                user_content = message
                if history:
                    lines = []
                    for turn in history[-6:]:
                        role = (turn.get("role") or "").strip().lower()
                        content = (turn.get("content") or "").strip()
                        if role in ("user", "assistant") and content:
                            label = "User" if role == "user" else "Assistant"
                            lines.append(f"{label}: {content[:1500]}")
                    if lines:
                        user_content = (
                            "Previous conversation:\n"
                            + "\n".join(lines)
                            + "\n\nCurrent question:\n"
                            + message
                        )

                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_content},
                ]

                response = await asyncio.to_thread(self._call_groq_with_fallback, messages)
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
            err = str(e)
            if "401" in err or "invalid" in err.lower() and "api" in err.lower():
                return (
                    "Chat AI is not authorized (check GROQ_API_KEY on causesense-api). "
                    "Update the key in Render Environment and redeploy."
                )
            if "429" in err or "rate" in err.lower():
                return (
                    "The AI service is rate-limited right now. "
                    "Please wait about a minute and ask again."
                )
            if "model" in err.lower():
                return (
                    "The configured Groq model is unavailable. "
                    "Set GROQ_MODEL=openai/gpt-oss-20b on causesense-api and redeploy."
                )
            return (
                "I could not reach the AI service just now. "
                "Please try again in a moment. If this keeps happening, "
                "check GROQ_API_KEY and usage limits in the Groq console."
            )
