import os
import logging
import asyncio
import time
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# Prefer largest Llama on Groq first, then smaller Llama / other fallbacks.
# Override primary with GROQ_MODEL if set.
_DEFAULT_LLAMA = "llama-3.3-70b-versatile"  # ~70B — largest Llama currently on Groq free/dev


def _unique_models() -> List[str]:
    preferred = os.environ.get("GROQ_MODEL", "").strip() or _DEFAULT_LLAMA
    candidates = [
        preferred,
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    ]
    seen = set()
    out = []
    for m in candidates:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _primary_and_fallback_models() -> Tuple[str, List[str]]:
    models = _unique_models()
    primary = models[0]
    fallbacks = models[1:]
    return primary, fallbacks



def _load_groq_keys() -> List[str]:
    """Collect Groq keys from GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEYS."""
    keys: List[str] = []
    seen = set()

    def add(raw: Optional[str]) -> None:
        if not raw:
            return
        for part in raw.replace(";", ",").split(","):
            k = part.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)

    add(os.environ.get("GROQ_API_KEY"))
    add(os.environ.get("GROQ_API_KEY_2"))
    add(os.environ.get("GROQ_API_KEYS"))
    return keys


def _get_emergent_classes():
    """Lazy import — emergentintegrations is only available on Emergent platform."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        return LlmChat, UserMessage
    except ImportError:
        return None, None


def _is_retryable(err: Exception) -> bool:
    text = str(err).lower()
    return any(
        token in text
        for token in (
            "429",
            "rate",
            "tpm",
            "quota",
            "timeout",
            "503",
            "502",
            "overloaded",
            "capacity",
        )
    )


def _is_auth_error(err: Exception) -> bool:
    text = str(err).lower()
    return any(token in text for token in ("401", "403", "invalid api key", "unauthorized", "forbidden"))


class BaseAgent:
    def __init__(self):
        self.groq_keys = _load_groq_keys()
        self.emergent_api_key = os.environ.get("EMERGENT_LLM_KEY")
        self.use_groq = bool(self.groq_keys)
        # Keep first key as attribute for any legacy callers
        self.groq_api_key = self.groq_keys[0] if self.groq_keys else None
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None

        if not self.groq_keys and not self.emergent_api_key:
            raise ValueError("GROQ_API_KEY is required (set in backend/.env or Render)")

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
                system_message=system_message,
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            return chat
        return None

    def _groq_complete(self, client: Groq, messages: list, model: str) -> str:
        kwargs = {
            "messages": messages,
            "model": model,
            "temperature": 0.7,
        }
        try:
            chat_completion = client.chat.completions.create(
                **kwargs,
                max_completion_tokens=1500,
            )
        except TypeError:
            chat_completion = client.chat.completions.create(
                **kwargs,
                max_tokens=1500,
            )
        return (chat_completion.choices[0].message.content or "").strip()

    def _try_once(self, client: Groq, messages: list, model: str, key_label: str):
        """Returns (text|None, error|None, auth_failed: bool)."""
        try:
            text = self._groq_complete(client, messages, model)
            if text:
                logger.info("Groq OK model=%s %s", model, key_label)
                return text, None, False
            return None, RuntimeError(f"Empty response from {model}"), False
        except Exception as e:
            logger.warning("Groq fail model=%s %s: %s", model, key_label, e)
            return None, e, _is_auth_error(e)

    def _call_groq_with_fallback(self, messages: list) -> str:
        """
        Failover order:
          1) Preferred Llama model with key changeovers:
             key1 → key2 → key1 → key2  (two full changeover rounds)
          2) If that still fails, try other free-tier models with the same
             key rotation (one pass per model: key1 → key2 → …).
        Auth-failed keys are skipped for the rest of the request.
        """
        if not self.groq_keys:
            raise RuntimeError("No Groq API keys configured")

        primary, fallback_models = _primary_and_fallback_models()
        last_error: Optional[Exception] = None
        dead_keys = set()

        def active_keys():
            return [
                (i, k)
                for i, k in enumerate(self.groq_keys)
                if i not in dead_keys
            ]

        def try_model_with_key_rounds(model: str, rounds: int) -> Optional[str]:
            nonlocal last_error
            for round_num in range(1, rounds + 1):
                keys = active_keys()
                if not keys:
                    break
                logger.info(
                    "Groq key-round %s/%s model=%s keys=%s",
                    round_num,
                    rounds,
                    model,
                    len(keys),
                )
                for key_index, api_key in keys:
                    key_label = f"key#{key_index + 1}"
                    client = Groq(api_key=api_key)
                    text, err, auth_failed = self._try_once(
                        client, messages, model, key_label
                    )
                    if text:
                        return text
                    if err is not None:
                        last_error = err
                    if auth_failed:
                        dead_keys.add(key_index)
                        logger.error(
                            "Groq auth failed for %s — skipping this key",
                            key_label,
                        )
                        continue
                    if err is not None and _is_retryable(err):
                        time.sleep(1.0)
            return None

        # Phase 1: preferred model, two changeover rounds (key1↔key2 twice)
        text = try_model_with_key_rounds(primary, rounds=2)
        if text:
            return text

        # Phase 2: other free-tier models (one key pass each)
        for model in fallback_models:
            text = try_model_with_key_rounds(model, rounds=1)
            if text:
                return text

        raise RuntimeError(str(last_error) if last_error else "Groq request failed")

    async def send_message(
        self,
        chat_or_system,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> str:
        """Send message with Groq (primary). history: optional prior [{role, content}]."""
        try:
            if self.use_groq:
                system_message = (
                    chat_or_system
                    if isinstance(chat_or_system, str)
                    else "You are a helpful AI assistant."
                )

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

                return await asyncio.to_thread(self._call_groq_with_fallback, messages)

            if self.emergent_api_key:
                LlmChat, UserMessage = _get_emergent_classes()
                if LlmChat is None:
                    return (
                        "Unable to process request — set GROQ_API_KEY "
                        "(and optionally GROQ_API_KEY_2) on the API service"
                    )

                logger.info("Using Emergent LLM (fallback)")
                if isinstance(chat_or_system, str):
                    chat = LlmChat(
                        api_key=self.emergent_api_key,
                        session_id="fallback_session",
                        system_message=chat_or_system,
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
            if "401" in err or ("invalid" in err.lower() and "api" in err.lower()):
                return (
                    "Chat AI is not authorized (check GROQ_API_KEY / GROQ_API_KEY_2). "
                    "Update keys in Render Environment and redeploy."
                )
            if "429" in err or "rate" in err.lower():
                return (
                    "Both Groq API keys appear rate-limited right now. "
                    "Please wait about a minute and ask again."
                )
            if "model" in err.lower():
                return (
                    "The configured Groq Llama model is unavailable. "
                    "Set GROQ_MODEL=llama-3.3-70b-versatile on causesense-api and redeploy."
                )
            return (
                "I could not reach the AI service just now. "
                "Please try again in a moment. If this keeps happening, "
                "check GROQ_API_KEY / GROQ_API_KEY_2 and usage limits in the Groq console."
            )
