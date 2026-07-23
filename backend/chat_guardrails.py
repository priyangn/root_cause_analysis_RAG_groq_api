"""Chat safety guardrails for CauseSense assistant.

Keeps answers scoped to root-cause analysis, uploaded datasets, and outcomes.
Politely declines politics, current affairs, explicit content, and other off-topic asks.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

DECLINE_MESSAGE = (
    "I can only help with CauseSense topics: your uploaded datasets, "
    "root-cause analysis results, anomalies, ML findings, and related technical questions. "
    "Please ask something about your analysis or data — I’m not able to discuss "
    "politics, current affairs, personal topics, or anything outside that scope."
)

CHAT_SYSTEM_PROMPT = """You are CauseSense AI for industrial machine failure and root-cause analysis (RCA).

Discuss only: uploaded datasets, anomalies, hypotheses, ML results, causal factors, reports, and related maintenance troubleshooting.
Refuse politics, news, celebrities, explicit content, hate, illegal activity, and unrelated advice.

CRITICAL FACTUAL RULES:
- Use ONLY the facts in "Analysis context" below. Do not invent model names, accuracies, anomaly values, or hypotheses.
- When asked about ML models, quote the exact model_name and accuracy from the context (accuracy as percent with 2 decimals if helpful).
- If the context does not contain an answer, say you do not have that detail in the current analysis results — do not guess.
- Keep answers concise unless asked for more detail. Follow-ups about the same analysis are allowed.
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
    r"\b(analy|anomaly|anomalies|dataset|csv|excel|upload|root\s*cause|failure|machine|sensor|ml|model|shap|hypothesis|causal|report|vibration|temperature|rpm|maintenance|rca|dashboard|feature|importance|confidence|accuracy|random\s*forest|xgboost|gradient)\b",
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

    if _matches_any(text, _OFFTOPIC_PATTERNS) and not _matches_any(text, _ALLOWED_HINTS):
        return False, DECLINE_MESSAGE

    return True, None


def _round2(value: Any) -> Any:
    try:
        n = float(value)
        if n != n:  # NaN
            return value
        return round(n, 2)
    except (TypeError, ValueError):
        return value


def build_analysis_context(analysis: Optional[Dict[str, Any]]) -> str:
    """Build a factual context block from the stored analysis (must match dashboard tabs)."""
    if not analysis:
        return "No analysis selected — answer generally about RCA workflow only if relevant."

    lines: List[str] = [
        f"Project: {analysis.get('project_name') or 'N/A'}",
        f"Status: {analysis.get('status') or 'unknown'}",
        f"Progress: {analysis.get('progress', 0)}%",
    ]

    root_cause = analysis.get("root_cause") or {}
    if root_cause:
        conf = _round2((root_cause.get("confidence_score") or 0) * 100)
        lines.append("Root cause summary:")
        lines.append(f"- Statement: {root_cause.get('root_cause') or 'Not determined'}")
        lines.append(f"- Confidence: {conf}%")
        evidence = root_cause.get("evidence") or []
        if evidence:
            lines.append("- Evidence: " + "; ".join(str(e) for e in evidence[:5]))
        actions = root_cause.get("preventive_actions") or []
        if actions:
            lines.append("- Preventive actions: " + "; ".join(str(a) for a in actions[:5]))

    anomalies = analysis.get("anomalies") or []
    lines.append(f"Anomalies detected: {len(anomalies)}")
    for a in anomalies[:12]:
        lines.append(
            f"- Parameter={a.get('parameter')}, value={_round2(a.get('value'))}, "
            f"threshold={_round2(a.get('threshold'))}, severity={a.get('severity')}, "
            f"timestamp={a.get('timestamp') or 'N/A'}"
        )

    hypotheses = analysis.get("hypotheses") or []
    lines.append(f"Hypotheses: {len(hypotheses)}")
    for h in hypotheses[:8]:
        prob = _round2((h.get("probability") or 0) * 100)
        lines.append(
            f"- Title={h.get('title')}, probability={prob}%, "
            f"description={h.get('description') or ''}"
        )

    ml_results = analysis.get("ml_results") or []
    lines.append(f"ML validation results ({len(ml_results)} model(s)) — USE THESE EXACT NAMES AND ACCURACIES:")
    if not ml_results:
        lines.append("- No ML results available for this analysis.")
    for m in ml_results:
        name = m.get("model_name") or "Unknown"
        acc = m.get("accuracy")
        acc_pct = _round2((acc or 0) * 100) if acc is not None else "N/A"
        lines.append(f"- model_name={name}, accuracy={acc_pct}% (raw={_round2(acc)})")
        fi = m.get("feature_importance") or {}
        if fi:
            top = ", ".join(
                f"{k}={_round2((v or 0) * 100)}%"
                for k, v in list(fi.items())[:5]
            )
            lines.append(f"  top features: {top}")
        cm = m.get("confusion_matrix") or {}
        if cm:
            lines.append(
                "  confusion_matrix: "
                f"TN={cm.get('true_negative')}, FP={cm.get('false_positive')}, "
                f"FN={cm.get('false_negative')}, TP={cm.get('true_positive')}"
            )

    causal = analysis.get("causal_analysis") or {}
    if causal:
        # Keep compact JSON for causal factors if present
        try:
            compact = json.dumps(causal, default=str)[:2500]
            lines.append(f"Causal analysis (excerpt): {compact}")
        except Exception:
            lines.append("Causal analysis: available (see dashboard)")

    viz = analysis.get("visualizations") or {}
    fi_chart = viz.get("feature_importance") or []
    if fi_chart:
        lines.append("Feature importance chart points:")
        for row in fi_chart[:10]:
            lines.append(
                f"- {row.get('parameter')}: importance={_round2(row.get('importance'))}"
            )

    return "\n".join(lines)


def build_chat_prompt(user_message: str, analysis_context: str) -> str:
    return (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"Analysis context:\n{analysis_context}\n\n"
        f"User question:\n{user_message}\n\n"
        "Answer using only the Analysis context facts above. "
        "For ML questions, list the exact model_name and accuracy values from the context."
    )
