"""
exports.py
----------
Multi-format export helpers for the BI Assistant.

Supports:
  - Excel (.xlsx)  with multiple sheets
  - JSON           structured metadata + data
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────
# Excel Export
# ─────────────────────────────────────────────

def to_excel_bytes(
    df: pd.DataFrame,
    stats_df: pd.DataFrame | None = None,
    quality_dict: dict[str, Any] | None = None,
    corr_df: pd.DataFrame | None = None,
    narrative: str = "",
    file_name: str = "dataset",
) -> bytes:
    """
    Build a multi-sheet Excel workbook and return it as bytes.

    Sheets produced:
      1. Data         — the (filtered) dataset
      2. Statistics   — numeric describe + skew + kurtosis
      3. Data Quality — missing-value report + duplicate count
      4. Correlation  — Pearson correlation matrix (numeric cols)
      5. AI Report    — AI-generated narrative (if provided)
      6. Info         — Export metadata
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb  = writer.book
        fmt = _excel_formats(wb)

        # ── Sheet 1: Data ────────────────────────────────────────────
        df.to_excel(writer, sheet_name="Data", index=False, startrow=1)
        ws = writer.sheets["Data"]
        ws.write(0, 0, f"Dataset Export — {file_name}", fmt["title"])
        ws.set_column(0, len(df.columns) - 1, 18)

        # ── Sheet 2: Statistics ──────────────────────────────────────
        if stats_df is not None and not stats_df.empty:
            stats_df.to_excel(writer, sheet_name="Statistics")
            ws2 = writer.sheets["Statistics"]
            ws2.write(0, 0, "Descriptive Statistics", fmt["title"])

        # ── Sheet 3: Data Quality ────────────────────────────────────
        if quality_dict:
            _write_quality_sheet(writer, wb, fmt, quality_dict, df)

        # ── Sheet 4: Correlation ─────────────────────────────────────
        if corr_df is not None and not corr_df.empty:
            corr_df.to_excel(writer, sheet_name="Correlation")
            ws4 = writer.sheets["Correlation"]
            ws4.write(0, 0, "Pearson Correlation Matrix", fmt["title"])

        # ── Sheet 5: AI Report ───────────────────────────────────────
        if narrative.strip():
            ws5 = wb.add_worksheet("AI Report")
            writer.sheets["AI Report"] = ws5
            ws5.write(0, 0, "AI Business Narrative", fmt["title"])
            ws5.set_column(0, 0, 100)
            for i, line in enumerate(narrative.split("\n"), start=2):
                ws5.write(i, 0, line, fmt["body"])

        # ── Sheet 6: Info ────────────────────────────────────────────
        ws6 = wb.add_worksheet("Info")
        writer.sheets["Info"] = ws6
        ws6.write(0, 0, "Export Information", fmt["title"])
        ws6.set_column(0, 1, 30)
        info_rows = [
            ("File Name", file_name),
            ("Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Total Rows", len(df)),
            ("Total Columns", len(df.columns)),
            ("Missing Values", int(df.isna().sum().sum())),
            ("Duplicate Rows", int(df.duplicated().sum())),
        ]
        for i, (k, v) in enumerate(info_rows, start=2):
            ws6.write(i, 0, k, fmt["header"])
            ws6.write(i, 1, v, fmt["body"])

    return output.getvalue()


def _write_quality_sheet(
    writer: pd.ExcelWriter,
    wb: Any,
    fmt: dict,
    quality_dict: dict[str, Any],
    df: pd.DataFrame,
) -> None:
    ws = wb.add_worksheet("Data Quality")
    writer.sheets["Data Quality"] = ws
    ws.set_column(0, 3, 25)
    ws.write(0, 0, "Data Quality Report", fmt["title"])

    summary_rows = [
        ("Total Rows",        quality_dict.get("rows", len(df))),
        ("Total Columns",     quality_dict.get("columns", len(df.columns))),
        ("Missing Values",    quality_dict.get("missing_count", 0)),
        ("Completeness",      f"{quality_dict.get('completeness', 100):.2f}%"),
        ("Duplicate Rows",    quality_dict.get("duplicate_count", 0)),
    ]
    for i, (k, v) in enumerate(summary_rows, start=2):
        ws.write(i, 0, k,    fmt["header"])
        ws.write(i, 1, str(v), fmt["body"])

    # Missing by column
    missing_by_col = quality_dict.get("missing_by_column", pd.Series(dtype=float))
    if hasattr(missing_by_col, "items"):
        ws.write(9, 0, "Column", fmt["header"])
        ws.write(9, 1, "Missing %", fmt["header"])
        for j, (col, pct) in enumerate(missing_by_col.items(), start=10):
            ws.write(j, 0, col, fmt["body"])
            ws.write(j, 1, float(pct), fmt["body"])


def _excel_formats(wb: Any) -> dict:
    title = wb.add_format({
        "bold": True, "font_size": 13,
        "font_color": "#F7B731", "font_name": "Calibri",
    })
    header = wb.add_format({
        "bold": True, "font_size": 10,
        "font_color": "#FFFFFF", "font_name": "Calibri",
        "bg_color": "#1a1a1a",
    })
    body = wb.add_format({
        "font_size": 10, "font_color": "#cccccc",
        "font_name": "Calibri",
    })
    return {"title": title, "header": header, "body": body}


# ─────────────────────────────────────────────
# JSON Export
# ─────────────────────────────────────────────

def to_json_bytes(df: pd.DataFrame, metadata: dict[str, Any] | None = None) -> bytes:
    """
    Serialize dataset + optional metadata to a structured JSON bytes object.
    NaN / Inf values are converted to None for JSON compliance.
    """
    clean_df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

    payload = {
        "metadata": {
            "exported_at":   datetime.now().isoformat(),
            "rows":          len(df),
            "columns":       len(df.columns),
            "column_names":  df.columns.tolist(),
            "dtypes":        {c: str(t) for c, t in df.dtypes.items()},
            **(metadata or {}),
        },
        "data": clean_df.to_dict(orient="records"),
    }

    return json.dumps(payload, indent=2, default=str).encode("utf-8")
