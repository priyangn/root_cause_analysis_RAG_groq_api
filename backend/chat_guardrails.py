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

You have access to the full analysis context covering:
- Overview (project, status, root cause, confidence, evidence, actions)
- Hypotheses (titles, probabilities, evidence)
- Anomalies (parameters, values, thresholds, severity)
- Charts / visualizations (correlations, feature importance, time-series signals)
- ML results (exact model names and accuracies)
- Uploaded data (file names, table statistics, document excerpts from manuals/PDFs/Word)

Discuss only those topics and related maintenance troubleshooting.
Refuse politics, news, celebrities, explicit content, hate, illegal activity, and unrelated advice.

CRITICAL FACTUAL RULES:
- Use ONLY facts from "Analysis context". Do not invent model names, accuracies, anomaly values, hypotheses, or file contents.
- When asked about ML, quote exact model_name and accuracy from context.
- When asked about uploaded data or manuals, use data_summary / document_excerpts / uploaded_files.
- If something is missing from context, say it is not available in the current analysis — do not guess.
- Keep answers concise unless asked for more detail.
"""

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
    r"\b(analy|anomaly|anomalies|dataset|csv|excel|upload|manual|pdf|docx|column|row|root\s*cause|failure|machine|sensor|ml|model|shap|hypothesis|causal|report|vibration|temperature|rpm|maintenance|rca|dashboard|feature|importance|confidence|accuracy|chart|correlation|overview)\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def check_message_allowed(message: str) -> Tuple[bool, Optional[str]]:
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
        if n != n:
            return value
        return round(n, 2)
    except (TypeError, ValueError):
        return value


def build_analysis_context(analysis: Optional[Dict[str, Any]]) -> str:
    """Factual context from all dashboard tabs + uploaded data (must match UI)."""
    if not analysis:
        return "No analysis selected — answer generally about RCA workflow only if relevant."

    lines: List[str] = [
        "=== OVERVIEW ===",
        f"Project: {analysis.get('project_name') or 'N/A'}",
        f"Status: {analysis.get('status') or 'unknown'}",
        f"Progress: {analysis.get('progress', 0)}%",
        f"Current step: {analysis.get('current_step') or 'N/A'}",
    ]

    root_cause = analysis.get("root_cause") or {}
    if root_cause:
        conf = _round2((root_cause.get("confidence_score") or 0) * 100)
        lines.append("Root cause:")
        lines.append(f"- Statement: {root_cause.get('root_cause') or 'Not determined'}")
        lines.append(f"- Confidence: {conf}%")
        evidence = root_cause.get("evidence") or []
        if evidence:
            lines.append("- Evidence: " + "; ".join(str(e) for e in evidence[:6]))
        actions = root_cause.get("preventive_actions") or []
        if actions:
            lines.append("- Preventive actions: " + "; ".join(str(a) for a in actions[:6]))
    else:
        lines.append("Root cause: not available yet")

    # Uploaded files + data summary
    lines.append("=== UPLOADED DATA ===")
    uploaded = analysis.get("uploaded_files") or []
    if uploaded:
        for f in uploaded[:10]:
            lines.append(
                f"- File={f.get('name')}, has_text={f.get('has_text')}, has_table={f.get('has_table')}"
            )
    else:
        file_ids = analysis.get("file_ids") or []
        lines.append(f"- Linked file_ids count: {len(file_ids)}")

    summary = analysis.get("data_summary") or {}
    if isinstance(summary, dict) and summary:
        lines.append(
            f"Table summary: total_records={summary.get('total_records')}, "
            f"parameters={summary.get('parameters')}"
        )
        stats = summary.get("statistics") or {}
        for col, st in list(stats.items())[:15]:
            if isinstance(st, dict):
                lines.append(
                    f"- Column {col}: mean={_round2(st.get('mean'))}, "
                    f"std={_round2(st.get('std'))}, min={_round2(st.get('min'))}, "
                    f"max={_round2(st.get('max'))}"
                )
        ai_ex = summary.get("ai_analysis_excerpt")
        if ai_ex:
            lines.append(f"Data AI note: {str(ai_ex)[:1500]}")
    else:
        lines.append("Table summary: not stored for this analysis (re-run analysis to refresh).")

    excerpts = analysis.get("document_excerpts") or []
    if excerpts:
        lines.append("Document / manual excerpts (from uploaded PDF/Word/TXT):")
        for ex in excerpts[:3]:
            lines.append(f"--- File: {ex.get('file')} ---")
            lines.append(str(ex.get("excerpt") or "")[:3500])
    else:
        lines.append("Document excerpts: none (no PDF/Word/TXT text extracted, or older analysis).")

    knowledge = analysis.get("knowledge_insights") or ""
    if knowledge:
        lines.append("Knowledge-base insights:")
        lines.append(str(knowledge)[:2500])

    # Hypotheses
    hypotheses = analysis.get("hypotheses") or []
    lines.append(f"=== HYPOTHESES ({len(hypotheses)}) ===")
    for h in hypotheses[:8]:
        prob = _round2((h.get("probability") or 0) * 100)
        lines.append(f"- Title: {h.get('title')}")
        lines.append(f"  Probability: {prob}%")
        lines.append(f"  Description: {h.get('description') or ''}")
        hev = h.get("evidence") or []
        if hev:
            lines.append("  Evidence: " + "; ".join(str(e) for e in hev[:5]))

    # Anomalies
    anomalies = analysis.get("anomalies") or []
    lines.append(f"=== ANOMALIES ({len(anomalies)}) ===")
    for a in anomalies[:15]:
        lines.append(
            f"- Parameter={a.get('parameter')}, value={_round2(a.get('value'))}, "
            f"threshold={_round2(a.get('threshold'))}, severity={a.get('severity')}, "
            f"timestamp={a.get('timestamp') or 'N/A'}"
        )

    # Charts
    lines.append("=== CHARTS / VISUALIZATIONS ===")
    viz = analysis.get("visualizations") or {}
    fi_chart = viz.get("feature_importance") or []
    if fi_chart:
        lines.append("Feature importance chart:")
        for row in fi_chart[:12]:
            lines.append(
                f"- {row.get('parameter')}: importance={_round2(row.get('importance'))}"
            )
    corr = viz.get("correlation") or {}
    corr_list = corr.get("correlations") if isinstance(corr, dict) else None
    if corr_list:
        lines.append("Top parameter correlations:")
        sorted_corr = sorted(
            corr_list,
            key=lambda x: abs(float(x.get("correlation") or 0)),
            reverse=True,
        )
        for c in sorted_corr[:12]:
            lines.append(
                f"- {c.get('param1')} ↔ {c.get('param2')}: "
                f"correlation={_round2(c.get('correlation'))}"
            )
    ts = viz.get("time_series") or []
    if ts:
        sample = ts[0] if isinstance(ts[0], dict) else {}
        cols = [k for k in sample.keys() if k != "time"]
        lines.append(f"Time-series series available: {cols[:10]}")
        lines.append(f"Time-series points stored: {len(ts)}")
        # last few points for a sense of recent values
        for point in ts[-3:]:
            if isinstance(point, dict):
                compact = {
                    k: _round2(v) if k != "time" else v
                    for k, v in list(point.items())[:8]
                }
                lines.append(f"- Recent point: {compact}")
    if not fi_chart and not corr_list and not ts:
        lines.append("No chart data available yet.")

    # ML
    ml_results = analysis.get("ml_results") or []
    lines.append(
        f"=== ML RESULTS ({len(ml_results)} model(s)) — USE THESE EXACT NAMES AND ACCURACIES ==="
    )
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
                f"{k}={_round2((v or 0) * 100)}%" for k, v in list(fi.items())[:5]
            )
            lines.append(f"  top features: {top}")
        cm = m.get("confusion_matrix") or {}
        if cm:
            lines.append(
                "  confusion_matrix: "
                f"TN={cm.get('true_negative')}, FP={cm.get('false_positive')}, "
                f"FN={cm.get('false_negative')}, TP={cm.get('true_positive')}"
            )

    # Causal
    causal = analysis.get("causal_analysis")
    lines.append("=== CAUSAL ANALYSIS ===")
    if isinstance(causal, list) and causal:
        for c in causal[:12]:
            if isinstance(c, dict):
                lines.append(
                    f"- {c.get('parameter')}: importance={_round2(c.get('importance'))}, "
                    f"causality_score={_round2(c.get('causality_score'))}"
                )
            else:
                lines.append(f"- {c}")
    elif isinstance(causal, dict) and causal:
        try:
            lines.append(json.dumps(causal, default=str)[:2500])
        except Exception:
            lines.append(str(causal)[:2500])
    else:
        lines.append("No causal analysis stored.")

    return "\n".join(lines)


def build_chat_prompt(user_message: str, analysis_context: str) -> str:
    return (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"Analysis context:\n{analysis_context}\n\n"
        f"User question:\n{user_message}\n\n"
        "Answer using only the Analysis context. "
        "Cover Overview, Hypotheses, Anomalies, Charts, ML, and Uploaded data when relevant. "
        "For ML, use exact model_name and accuracy values from the context."
    )
