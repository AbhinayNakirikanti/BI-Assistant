"""
config.py
---------
Centralized configuration and constants for the BI Assistant.
All tuneable values live here — never scattered across modules.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# App Identity
# ─────────────────────────────────────────────
APP_NAME        = "BI Assistant"
APP_VERSION     = "2.0.0"
APP_DESCRIPTION = "AI-powered Business Intelligence Platform"
APP_AUTHOR      = "MirAI School of Technology"

# ─────────────────────────────────────────────
# Gemini Configuration
# ─────────────────────────────────────────────
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_TIMEOUT_S  = int(os.getenv("GEMINI_TIMEOUT_S", "30"))

# ─────────────────────────────────────────────
# Data Limits
# ─────────────────────────────────────────────
MAX_UPLOAD_MB         = int(os.getenv("MAX_UPLOAD_MB", "200"))
LARGE_DATASET_ROWS    = int(os.getenv("LARGE_DATASET_ROWS", "100_000"))
SAMPLE_ROWS_DEFAULT   = int(os.getenv("SAMPLE_ROWS_DEFAULT", "50_000"))
PREVIEW_ROWS          = int(os.getenv("PREVIEW_ROWS", "100"))
CORRELATION_MAX_COLS  = int(os.getenv("CORRELATION_MAX_COLS", "25"))
AI_SUMMARY_ROWS       = int(os.getenv("AI_SUMMARY_ROWS", "8"))

# ─────────────────────────────────────────────
# Chart / Visual
# ─────────────────────────────────────────────
PALETTE = [
    "#F7B731", "#FF6B35", "#A78BFA", "#60A5FA",
    "#4ADE80", "#F472B6", "#34D399", "#FB923C",
    "#22D3EE", "#E879F9", "#86EFAC", "#FCA5A5",
]
PLOTLY_TEMPLATE = "plotly_dark"
DARK_BG         = "rgba(0,0,0,0)"

# ─────────────────────────────────────────────
# Colors (semantic)
# ─────────────────────────────────────────────
COLOR_AMBER  = "#F7B731"
COLOR_ORANGE = "#FF6B35"
COLOR_VIOLET = "#A78BFA"
COLOR_GREEN  = "#4ADE80"
COLOR_RED    = "#F87171"
COLOR_BLUE   = "#60A5FA"

# ─────────────────────────────────────────────
# Domain Detection Signals
# ─────────────────────────────────────────────
FINANCE_SIGNALS = {
    "revenue", "profit", "income", "expense", "cost",
    "balance", "salary", "budget", "transaction", "amount",
    "debit", "credit", "payment", "spend", "cash", "invoice",
}
SALES_SIGNALS = {
    "customer", "product", "region", "sales", "order",
    "quantity", "discount", "segment", "merchant", "deal",
    "pipeline", "quota", "territory", "sku", "conversion",
}

DOMAIN_LABELS = {
    "Finance":          "💳 Finance Analytics",
    "Sales":            "📈 Sales Analytics",
    "General Business": "🗂 Business Analytics",
}
DOMAIN_COLORS = {
    "Finance":          "#60A5FA",
    "Sales":            "#4ADE80",
    "General Business": "#A78BFA",
}

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent
ASSETS_DIR = ROOT_DIR / "assets"
DOCS_DIR   = ROOT_DIR / "docs"
