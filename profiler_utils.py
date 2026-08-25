"""
profiler_utils.py
-----------------
Cached data-profiling helpers, dataset-domain detection, and
domain-aware system-prompt factory for the BI Assistant.
"""

from __future__ import annotations

import hashlib
from typing import List

import numpy as np
import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────
# Domain detection
# ─────────────────────────────────────────────

_FINANCE_SIGNALS = {
    "amount", "balance", "transaction", "merchant", "category",
    "debit", "credit", "expense", "income", "payment", "account",
    "spend", "budget", "transfer", "currency",
}

_SALES_SIGNALS = {
    "sales", "revenue", "profit", "margin", "product", "region",
    "territory", "quota", "discount", "order", "units", "sku",
    "customer", "deal", "pipeline", "forecast", "conversion",
}


def detect_domain(columns: List[str]) -> str:
    """Return 'finance', 'sales', or 'generic' based on column-name overlap."""
    lower = {c.lower() for c in columns}
    # Also split on common separators so 'order_id' matches 'order'
    tokens: set[str] = set()
    for col in lower:
        tokens.update(col.replace("_", " ").replace("-", " ").split())

    finance_score = len(tokens & _FINANCE_SIGNALS)
    sales_score   = len(tokens & _SALES_SIGNALS)

    if finance_score == 0 and sales_score == 0:
        return "generic"
    return "finance" if finance_score >= sales_score else "sales"


# ─────────────────────────────────────────────
# Domain-aware system prompts
# ─────────────────────────────────────────────

_PROMPTS = {
    "finance": """\
You are a Finance Analytics Copilot — an expert in personal finance and transaction analysis.
You have deep knowledge of budgeting, spending patterns, cash flow, and financial health metrics.

Rules:
- Ground every answer in the actual data shown. Never guess or hallucinate figures.
- For numeric questions, describe your aggregation logic clearly (sum, mean, group-by, etc.).
- If the data is insufficient to answer, say so explicitly.
- Format answers with bullet points, markdown tables, or code blocks as appropriate.
- Include concise pandas code when it clarifies your reasoning.
- Keep answers actionable for a non-technical finance user: highlight anomalies, trends, and risks.
- Flag unusually large transactions, high-spend categories, or suspicious patterns proactively.
""",
    "sales": """\
You are a Sales BI Copilot — an expert in sales analytics, revenue operations, and go-to-market strategy.
You understand pipelines, quotas, regional performance, product mix, and revenue forecasting.

Rules:
- Ground every answer in the actual data shown. Never guess or hallucinate figures.
- For numeric questions, describe your aggregation logic clearly (sum, mean, group-by, etc.).
- If the data is insufficient to answer, say so explicitly.
- Format answers with bullet points, markdown tables, or code blocks as appropriate.
- Include concise pandas code when it clarifies your reasoning.
- Keep answers actionable for a sales manager: highlight top performers, laggards, and growth opportunities.
- Proactively surface quota attainment gaps, regional outliers, and product concentration risks.
""",
    "generic": """\
You are a Business Analytics Assistant — a senior BI analyst with broad expertise in business data.
You can handle any domain: operations, logistics, HR, marketing, or general tabular datasets.

Rules:
- Ground every answer in the actual data shown. Never guess or hallucinate figures.
- For numeric questions, describe your aggregation logic clearly (sum, mean, group-by, etc.).
- If the data is insufficient to answer, say so explicitly.
- Format answers with bullet points, markdown tables, or code blocks as appropriate.
- Include concise pandas code when it clarifies your reasoning.
- Keep answers concise, business-friendly, and immediately actionable.
""",
}

_DOMAIN_LABELS = {
    "finance": "💳 Personal Finance",
    "sales":   "📈 Sales Analytics",
    "generic": "🗂 Business Analytics",
}


def get_system_prompt(domain: str) -> str:
    """Return the domain-appropriate system prompt."""
    return _PROMPTS.get(domain, _PROMPTS["generic"])


def get_domain_label(domain: str) -> str:
    """Return a human-readable domain label with emoji."""
    return _DOMAIN_LABELS.get(domain, _DOMAIN_LABELS["generic"])


# ─────────────────────────────────────────────
# Dataset fingerprint (for cache keys)
# ─────────────────────────────────────────────

def compute_data_fingerprint(df: pd.DataFrame) -> str:
    """
    Return a short hex string that changes when the dataset shape or
    column names change.  Used as a cache-buster key.
    """
    signature = f"{df.shape}|{'|'.join(df.columns.tolist())}"
    return hashlib.md5(signature.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────
# Cached heavy computations
# ─────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def compute_correlation(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Return the Pearson correlation matrix for numeric columns.
    Cached per dataset fingerprint so re-renders are instant.
    """
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(num_cols) < 2:
        return pd.DataFrame()
    return df[num_cols].corr().round(2)


@st.cache_data(show_spinner=False)
def compute_zero_variance_cols(_df_hash: str, df: pd.DataFrame) -> list[str]:
    """Return a list of column names that have zero or near-zero variance."""
    zero_var = []
    for col in df.columns:
        if df[col].dropna().nunique() <= 1:
            zero_var.append(col)
    return zero_var


@st.cache_data(show_spinner=False)
def compute_quality_summary(_df_hash: str, df: pd.DataFrame) -> dict:
    """
    Return a dict with:
      - missing_pct: dict {col: pct}
      - duplicate_count: int
      - zero_variance_cols: list[str]
      - overall_completeness: float
    """
    total_cells = df.shape[0] * df.shape[1] or 1
    missing_per_col = {
        col: round(df[col].isna().mean() * 100, 2)
        for col in df.columns
        if df[col].isna().any()
    }
    dup_count = int(df.duplicated().sum())
    zv_cols   = compute_zero_variance_cols(_df_hash, df)
    completeness = round((1 - df.isna().sum().sum() / total_cells) * 100, 1)

    return {
        "missing_pct":          missing_per_col,
        "duplicate_count":      dup_count,
        "zero_variance_cols":   zv_cols,
        "overall_completeness": completeness,
    }


@st.cache_data(show_spinner=False)
def compute_descriptive_stats(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    """Return extended descriptive statistics (with skewness & kurtosis)."""
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    if not num_cols:
        return pd.DataFrame()
    desc = df[num_cols].describe().T.round(3)
    desc["skewness"] = df[num_cols].skew().round(3)
    desc["kurtosis"] = df[num_cols].kurt().round(3)
    return desc
