"""
chart_explain.py
----------------
Gemini-powered chart explanation and follow-up question suggestion helpers
for the BI Assistant.

Both helpers use a lightweight dict-based in-session cache so repeated
clicks / rerenders never re-call the API for identical inputs.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

GEMINI_MODEL = "gemini-2.5-flash"


# ─────────────────────────────────────────────
# Internal cache key helper
# ─────────────────────────────────────────────

def _make_key(*parts: str) -> str:
    """Return a short MD5 key from arbitrary string parts."""
    payload = "|".join(str(p) for p in parts)
    return hashlib.md5(payload.encode()).hexdigest()[:16]


# ─────────────────────────────────────────────
# Chart explanation
# ─────────────────────────────────────────────

def explain_chart(
    client: Any,
    chart_title: str = "",
    chart_description: str = "",
    sample_csv: str = "",
    cache_store: Optional[Dict[str, str]] = None,
    model: str = GEMINI_MODEL,
    **kwargs: Any,
) -> str:
    """
    Ask Gemini to explain a chart in 2-3 business-friendly sentences.
    Robust to argument ordering, keyword args, and model name.
    """
    if cache_store is None:
        cache_store = {}

    target_model = model or kwargs.get("gemini_model", GEMINI_MODEL)
    key = _make_key(chart_title, chart_description, sample_csv[:500])
    if key in cache_store:
        return cache_store[key]

    prompt = (
        "You are a Business Intelligence assistant helping a non-technical manager.\n"
        f"Chart title: {chart_title}\n"
        f"Chart description: {chart_description}\n\n"
        "Sample data (CSV):\n"
        f"{sample_csv}\n\n"
        "In 2-3 concise sentences, explain the KEY business takeaway from this chart. "
        "Be specific about values or trends visible in the data. "
        "Do not use jargon. Write for a business manager."
    )

    try:
        resp = client.models.generate_content(model=target_model, contents=prompt)
        result = resp.text.strip()
        cache_store[key] = result
    except Exception as exc:
        result = f"⚠️ Could not generate explanation: {exc}"

    return result


# ─────────────────────────────────────────────
# Follow-up question suggestions
# ─────────────────────────────────────────────

def suggest_followups(
    client: Any,
    answer: str = "",
    data_summary: str = "",
    cache_store: Optional[Dict[str, str]] = None,
    n: int = 3,
    model: str = GEMINI_MODEL,
    **kwargs: Any,
) -> List[str]:
    """
    Ask Gemini to suggest follow-up questions a manager might ask next.
    Robust to argument ordering, keyword args, and model name.
    """
    if cache_store is None:
        cache_store = {}

    target_model = model or kwargs.get("gemini_model", GEMINI_MODEL)
    key = _make_key(answer[:300], data_summary[:300])
    if key in cache_store:
        raw = cache_store[key]
        return _parse_questions(raw)

    prompt = (
        f"You are a Business Intelligence assistant.\n\n"
        f"DATASET SUMMARY:\n{data_summary[:1500]}\n\n"
        f"LATEST AI ANSWER:\n{answer[:800]}\n\n"
        f"Suggest exactly {n} short, concise follow-up questions a business manager might ask next. "
        "Each question must be directly answerable from this dataset. "
        "Output ONLY the questions, one per line, numbered 1. 2. 3. etc. "
        "No preamble, no explanations."
    )

    try:
        resp = client.models.generate_content(model=target_model, contents=prompt)
        raw = resp.text.strip()
    except Exception:
        return []

    cache_store[key] = raw
    return _parse_questions(raw)


def _parse_questions(raw: str) -> List[str]:
    """Parse numbered list output into clean question strings."""
    questions = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ["1.", "2.", "3.", "4.", "1)", "2)", "3)", "1 -", "2 -", "3 -"]:
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        if line:
            questions.append(line)
    return questions[:4]
