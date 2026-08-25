"""
ai_narrative.py
---------------
AI-powered business narrative generator for the BI Assistant.

Sends a rich dataset summary to Gemini and receives a structured
4-section business report: Executive Summary, Key Findings,
Anomalies & Risks, and Recommended Next Steps.

Results are cached per dataset fingerprint (MD5 of shape + columns)
so repeat clicks do not re-call the API.
"""

from __future__ import annotations

import hashlib
from typing import Any


# ─────────────────────────────────────────────
# Cache key
# ─────────────────────────────────────────────

def _narrative_key(data_summary: str, domain: str) -> str:
    payload = f"{domain}|{data_summary[:1000]}"
    return hashlib.md5(payload.encode()).hexdigest()[:16]


# ─────────────────────────────────────────────
# Narrative generator
# ─────────────────────────────────────────────

def generate_narrative(
    client: Any,
    model: str,
    data_summary: str,
    domain: str,
    cache_store: dict[str, str],
) -> dict[str, str]:
    """
    Generate a structured business narrative for the dataset.

    Returns
    -------
    dict with keys: executive_summary, key_findings,
                    anomalies_risks, next_steps
    Empty strings are returned on error.
    """
    key = _narrative_key(data_summary, domain)
    if key in cache_store:
        return _parse_narrative(cache_store[key])

    prompt = f"""You are a senior Business Intelligence analyst writing an executive report.

DOMAIN: {domain}

DATASET SUMMARY:
{data_summary[:3000]}

Write a structured business intelligence report with EXACTLY these four sections,
each starting with the exact header shown:

## Executive Summary
[3-4 sentences: What is this dataset about, its scope, and the single most important insight.]

## Key Findings
[4-6 bullet points starting with •. Each bullet must cite specific numbers from the data.]

## Anomalies & Risks
[3-4 bullet points starting with ⚠. Flag outliers, missing data patterns, unusual values, or business risks.]

## Recommended Next Steps
[3-4 bullet points starting with →. Concrete, actionable recommendations a manager can act on today.]

Be specific, cite actual column names and values. Do not be vague.
"""

    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        raw = resp.text.strip()
        cache_store[key] = raw
        return _parse_narrative(raw)
    except Exception as exc:
        return {
            "executive_summary": f"⚠️ Could not generate narrative: {exc}",
            "key_findings":      "",
            "anomalies_risks":   "",
            "next_steps":        "",
        }


def _parse_narrative(raw: str) -> dict[str, str]:
    """Split raw Gemini output into the four narrative sections."""
    sections = {
        "executive_summary": "",
        "key_findings":      "",
        "anomalies_risks":   "",
        "next_steps":        "",
    }

    markers = {
        "## Executive Summary":       "executive_summary",
        "## Key Findings":            "key_findings",
        "## Anomalies & Risks":       "anomalies_risks",
        "## Recommended Next Steps":  "next_steps",
    }

    current_key = None
    lines: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        matched = False
        for marker, key in markers.items():
            if stripped.startswith(marker):
                if current_key and lines:
                    sections[current_key] = "\n".join(lines).strip()
                current_key = key
                lines = []
                matched = True
                break
        if not matched and current_key is not None:
            lines.append(line)

    if current_key and lines:
        sections[current_key] = "\n".join(lines).strip()

    return sections


# ─────────────────────────────────────────────
# KPI generators (domain-aware)
# ─────────────────────────────────────────────

import numpy as np
import pandas as pd


def compute_smart_kpis(df: pd.DataFrame, domain: str) -> list[dict]:
    """
    Return a list of KPI dicts: {label, value, delta, delta_color}.
    Adapts to domain and available columns.
    """
    kpis: list[dict] = []
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

    # ── Universal KPIs ──────────────────────────────────────────────
    kpis.append({
        "label": "Total Records",
        "value": f"{len(df):,}",
        "delta": None,
        "delta_color": "off",
    })

    total_cells = df.shape[0] * df.shape[1]
    completeness = round(100 * (1 - df.isna().sum().sum() / total_cells), 1) if total_cells else 100
    kpis.append({
        "label": "Data Completeness",
        "value": f"{completeness}%",
        "delta": "complete" if completeness == 100 else f"{100 - completeness:.1f}% missing",
        "delta_color": "normal" if completeness >= 95 else "inverse",
    })

    # ── Finance KPIs ────────────────────────────────────────────────
    if domain == "Finance":
        amount_col = _find_col(num_cols, ["amount", "transaction", "expense", "cost", "balance"])
        if amount_col:
            total = df[amount_col].sum()
            kpis.append({
                "label":       f"Total {amount_col.title()}",
                "value":       _fmt_money(total),
                "delta":       f"Avg {_fmt_money(df[amount_col].mean())}",
                "delta_color": "off",
            })
            kpis.append({
                "label":       "Transactions > Mean",
                "value":       f"{(df[amount_col] > df[amount_col].mean()).sum():,}",
                "delta":       f"{(df[amount_col] > df[amount_col].mean()).mean() * 100:.1f}% of records",
                "delta_color": "off",
            })

        cat_col = _find_col(cat_cols, ["category", "merchant", "type"])
        if cat_col and amount_col:
            top = df.groupby(cat_col)[amount_col].sum().idxmax()
            kpis.append({
                "label":       f"Top {cat_col.title()}",
                "value":       str(top),
                "delta":       _fmt_money(df.groupby(cat_col)[amount_col].sum().max()),
                "delta_color": "off",
            })

    # ── Sales KPIs ──────────────────────────────────────────────────
    elif domain == "Sales":
        rev_col = _find_col(num_cols, ["revenue", "sales", "amount", "profit", "total"])
        if rev_col:
            total = df[rev_col].sum()
            kpis.append({
                "label":       f"Total {rev_col.title()}",
                "value":       _fmt_money(total),
                "delta":       f"Avg {_fmt_money(df[rev_col].mean())} / record",
                "delta_color": "off",
            })

        prod_col = _find_col(cat_cols, ["product", "sku", "item"])
        if prod_col and rev_col:
            top_prod = df.groupby(prod_col)[rev_col].sum().idxmax()
            kpis.append({
                "label":       "Top Product",
                "value":       str(top_prod),
                "delta":       _fmt_money(df.groupby(prod_col)[rev_col].sum().max()),
                "delta_color": "off",
            })

        region_col = _find_col(cat_cols, ["region", "territory", "area", "location"])
        if region_col and rev_col:
            top_region = df.groupby(region_col)[rev_col].sum().idxmax()
            kpis.append({
                "label":       "Top Region",
                "value":       str(top_region),
                "delta":       _fmt_money(df.groupby(region_col)[rev_col].sum().max()),
                "delta_color": "off",
            })

    # ── Generic numeric KPIs ────────────────────────────────────────
    else:
        if num_cols:
            primary = num_cols[0]
            kpis.append({
                "label":       f"Avg {primary.title()}",
                "value":       f"{df[primary].mean():.2f}",
                "delta":       f"Std {df[primary].std():.2f}",
                "delta_color": "off",
            })

    # ── Outlier count ────────────────────────────────────────────────
    if num_cols:
        primary = num_cols[0]
        s = df[primary].dropna()
        if len(s) >= 4:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            outliers = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
            kpis.append({
                "label":       f"Outliers ({primary.title()})",
                "value":       f"{outliers:,}",
                "delta":       f"{outliers / len(s) * 100:.1f}% of values",
                "delta_color": "inverse" if outliers > 0 else "normal",
            })

    return kpis


def _find_col(cols: list[str], keywords: list[str]) -> str | None:
    """Return the first column whose name contains any of the keywords."""
    lower = {c.lower(): c for c in cols}
    for kw in keywords:
        for col_lower, col_orig in lower.items():
            if kw in col_lower:
                return col_orig
    return None


def _fmt_money(val: float) -> str:
    """Format a number as a compact monetary string."""
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.1f}K"
    return f"${val:.2f}"
