"""Chat safety guardrails for CauseSense assistant.

Keeps answers scoped to root-cause analysis, uploaded datasets, and outcomes.
Politely declines politics, current affairs, explicit content, and other off-topic asks.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

DECLINE_MESSAGE = (
    "I can only help with CauseSense topics: your uploaded datasets, "
    "root-cause analysis results, anomalies, ML findings, and related technical questions. "
    "Please ask something about your analysis or data — I’m not able to discuss "
    "politics, current affairs, personal topics, or anything outside that scope."
)

CHAT_SYSTEM_PROMPT = """You are CauseSense AI for industrial machine failure and root-cause analysis (RCA).

Discuss only: uploaded datasets, anomalies, hypotheses, ML results, causal factors, reports, and related maintenance troubleshooting.
Refuse politics, news, celebrities, explicit content, hate, illegal activity, and unrelated advice.
Follow-ups about the same analysis are allowed. Keep answers concise unless asked for detail.
"""

# High-signal off-topic / unsafe patterns (heuristic pre-filter before calling the LLM)
_EXPLICIT_PATTERNS = [
    r"\b(porn|pornography|xxx|nude|nudes|onlyfans|hentai|nsfw)\b",
    r"\b(sex\s*chat|sexual\s*act|erotic|fetish)\b",
    r"\b(child\s*porn|underage\s*sex|csam)\b",
]

_OFFTOPIC_PATTERNS = [
    r"\b(politic|election|president|prime\s*minister|congress|parliament|democrat|republican|bjp|congress\s*party)\b",
    r"\b(war\s*in|ukraine|gaza|israel|hamas|nato\s*policy)\b",
    r"\b(stock\s*tips?|crypto\s*pump|bitcoin\s*price|lottery)\b",
    r"\b(celebrity|bollywood|hollywoodwood|gossip|horoscope|astrology)\b",
    r"\b(who\s+will\s+win|latest\s+news|breaking\s+news|current\s+affairs)\b",
]

_ALLOWED_HINTS = [
    r"\b(analy|anomaly|anomalies|dataset|csv|excel|upload|root\s*cause|failure|machine|sensor|ml|model|shap|hypothesis|causal|report|vibration|temperature|rpm|maintenance|rca|dashboard|feature|importance|confidence)\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def check_message_allowed(message: str) -> Tuple[bool, Optional[str]]:
    """
    Returns (allowed, decline_reason_message).
    If allowed is False, decline_reason_message should be shown to the user.
    """
    text = (message or "").strip()
    if not text:
        return False, "Please enter a question about your analysis or uploaded data."

    if len(text) > 4000:
        return False, "Your message is too long. Please ask a shorter question about your analysis."

    if _matches_any(text, _EXPLICIT_PATTERNS):
        return False, DECLINE_MESSAGE

    # Off-topic political / current-affairs heuristics
    if _matches_any(text, _OFFTOPIC_PATTERNS) and not _matches_any(text, _ALLOWED_HINTS):
        return False, DECLINE_MESSAGE

    return True, None


def build_chat_prompt(user_message: str, analysis_context: str) -> str:
    return (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"Analysis context:\n{analysis_context}\n\n"
        f"User question:\n{user_message}\n\n"
        "Answer only if the question is within scope. Otherwise refuse briefly using the rules above."
    )
