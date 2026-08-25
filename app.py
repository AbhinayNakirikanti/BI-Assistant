import hashlib
import io
import os
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    genai = None

from ai_narrative import compute_smart_kpis, generate_narrative, _narrative_key, _parse_narrative
from exports import to_excel_bytes, to_json_bytes


# -------------------------------------------------
# Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="BI Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PALETTE = [
    "#F7B731", "#FF6B35", "#A78BFA", "#60A5FA",
    "#4ADE80", "#F472B6", "#34D399", "#FB923C",
]

PLOTLY_TEMPLATE = "plotly_dark"
DARK_BG = "rgba(0,0,0,0)"


# -------------------------------------------------
# Styling
# -------------------------------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@1,400;1,700&display=swap');

        /* ── Global ─────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── App background ─────────────────────── */
        .stApp {
            background-color: #07070a;
            background-image:
                radial-gradient(ellipse 90% 60% at 50% -15%,
                    rgba(247, 183, 49, 0.08) 0%, transparent 65%),
                radial-gradient(ellipse 50% 40% at 90% 80%,
                    rgba(255, 107, 53, 0.06) 0%, transparent 55%),
                radial-gradient(ellipse 45% 35% at 5%  70%,
                    rgba(167, 139, 250, 0.05) 0%, transparent 50%);
            color: #e8e8e8;
        }

        /* ── Sidebar ────────────────────────────── */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0c0c10 0%, #0a0a0d 100%) !important;
            border-right: 1px solid rgba(255,255,255,0.06) !important;
        }
        [data-testid="stSidebar"] * {
            font-family: 'Inter', sans-serif !important;
        }

        /* ── Tabs ───────────────────────────────── */
        [data-testid="stTabs"] [role="tablist"] {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.07) !important;
            border-radius: 14px !important;
            padding: 5px !important;
            gap: 4px !important;
        }
        [data-testid="stTabs"] [role="tab"] {
            border-radius: 10px !important;
            color: #555 !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            padding: 0.45rem 1.1rem !important;
            transition: all 0.25s ease !important;
            letter-spacing: 0.01em !important;
        }
        [data-testid="stTabs"] [role="tab"]:hover {
            color: #aaa !important;
            background: rgba(255,255,255,0.04) !important;
        }
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #FF6B35 0%, #F7B731 100%) !important;
            color: #07070a !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 12px rgba(247,183,49,0.25) !important;
        }

        /* ── Metric cards ───────────────────────── */
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 14px;
            padding: 1.2rem 1.4rem;
            transition: all 0.3s ease;
            backdrop-filter: blur(12px);
        }
        div[data-testid="stMetric"]:hover {
            border-color: rgba(247,183,49,0.35);
            box-shadow: 0 0 24px rgba(247,183,49,0.07), 0 4px 20px rgba(0,0,0,0.3);
            transform: translateY(-2px);
        }
        div[data-testid="stMetric"] label {
            color: #4a4a4a !important;
            font-size: 0.68rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
        }
        div[data-testid="stMetricValue"] {
            color: #fff !important;
            font-size: 1.85rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }
        div[data-testid="stMetricDelta"] { color: #FF6B35 !important; }

        /* ── Hero ───────────────────────────────── */
        .hero {
            padding: 2.5rem 0 2rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 2rem;
        }
        .hero h1 {
            font-size: 2.9rem;
            font-weight: 800;
            color: #fff;
            letter-spacing: -0.04em;
            line-height: 1.1;
            margin: 0 0 0.5rem;
        }
        .hero h1 em {
            font-family: 'Playfair Display', serif;
            font-style: italic;
            background: linear-gradient(90deg, #FF6B35, #F7B731, #FFD580);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .hero p {
            color: #4a4a4a;
            font-size: 0.98rem;
            margin: 0;
        }
        .hero-badges {
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 20px;
            padding: 0.25rem 0.8rem;
            font-size: 0.72rem;
            color: #666;
            font-weight: 500;
            letter-spacing: 0.02em;
        }

        /* ── Section labels ─────────────────────── */
        .section-title {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            color: #F7B731;
            margin: 2rem 0 1rem;
        }
        .section-title::after {
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(255,255,255,0.05);
        }

        /* ── Buttons ────────────────────────────── */
        .stButton > button {
            background: linear-gradient(135deg, #FF6B35, #F7B731) !important;
            color: #07070a !important;
            border: none !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            letter-spacing: 0.01em !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 10px rgba(247,183,49,0.2) !important;
        }
        .stButton > button:hover {
            opacity: 0.88 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 18px rgba(247,183,49,0.3) !important;
        }
        .stDownloadButton > button {
            background: rgba(255,255,255,0.05) !important;
            color: #ccc !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 9px !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            transition: all 0.2s ease !important;
        }
        .stDownloadButton > button:hover {
            border-color: rgba(247,183,49,0.4) !important;
            color: #F7B731 !important;
            background: rgba(247,183,49,0.06) !important;
        }
        .stFormSubmitButton > button {
            background: linear-gradient(135deg, #FF6B35, #F7B731) !important;
            color: #07070a !important;
            border: none !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 10px rgba(247,183,49,0.2) !important;
        }

        /* ── Inputs & selects ───────────────────── */
        .stTextInput input, .stTextArea textarea {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-radius: 9px !important;
            color: #e8e8e8 !important;
            font-family: 'Inter', sans-serif !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: rgba(247,183,49,0.45) !important;
            box-shadow: 0 0 0 3px rgba(247,183,49,0.08) !important;
        }

        /* ── File uploader ──────────────────────── */
        [data-testid="stFileUploader"] {
            background: rgba(247,183,49,0.03) !important;
            border: 1.5px dashed rgba(247,183,49,0.22) !important;
            border-radius: 14px !important;
            transition: border-color 0.3s ease !important;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: rgba(247,183,49,0.5) !important;
        }
        [data-testid="stFileUploader"] section button {
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            color: #fff !important;
            font-size: 0.75rem !important;
            letter-spacing: normal !important;
        }

        /* ── Chat messages ──────────────────────── */
        [data-testid="stChatMessage"] {
            background: rgba(255,255,255,0.025) !important;
            border: 1px solid rgba(255,255,255,0.06) !important;
            border-radius: 14px !important;
            margin-bottom: 0.6rem !important;
            backdrop-filter: blur(8px) !important;
        }

        /* ── Expanders ──────────────────────────── */
        [data-testid="stExpander"] {
            background: rgba(255,255,255,0.025) !important;
            border: 1px solid rgba(255,255,255,0.07) !important;
            border-radius: 12px !important;
        }

        /* ── Dataframes ─────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        /* ── Alerts ─────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 10px !important;
        }

        /* ── Scrollbar ──────────────────────────── */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #07070a; }
        ::-webkit-scrollbar-thumb { background: #222; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #F7B731; }

        /* ── Filter active badge ────────────────── */
        .filter-active-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: rgba(247,183,49,0.1);
            border: 1px solid rgba(247,183,49,0.3);
            border-radius: 20px;
            padding: 0.3rem 0.9rem;
            font-size: 0.72rem;
            color: #F7B731;
            font-weight: 600;
            letter-spacing: 0.03em;
            animation: pulse-glow 2.5s ease-in-out infinite;
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(247,183,49,0.18); }
            50%       { box-shadow: 0 0 10px 3px rgba(247,183,49,0.08); }
        }

        /* ── Sidebar branding ───────────────────── */
        .sb-brand {
            padding: 1.2rem 0 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 0.8rem;
        }
        .sb-brand-name {
            font-size: 1.2rem;
            font-weight: 800;
            color: #fff;
            letter-spacing: -0.03em;
            line-height: 1;
        }
        .sb-brand-name em {
            font-family: 'Playfair Display', serif;
            font-style: italic;
            background: linear-gradient(90deg, #FF6B35, #F7B731);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .sb-brand-sub {
            font-size: 0.65rem;
            color: #333;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-top: 0.25rem;
        }
        .sb-file-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 10px;
            padding: 0.8rem 1rem;
            margin: 0.5rem 0;
        }
        .sb-file-label {
            font-size: 0.6rem;
            font-weight: 700;
            color: #F7B731;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .sb-file-name {
            font-size: 0.78rem;
            color: #ddd;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .sb-file-meta {
            font-size: 0.68rem;
            color: #444;
            margin-top: 0.2rem;
        }
        .sb-status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 0.4rem;
        }
        .sb-status-online  { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
        .sb-status-offline { background: #f87171; box-shadow: 0 0 6px #f87171; }

        /* ── Footer ─────────────────────────────── */
        .app-footer {
            margin-top: 5rem;
            padding: 2rem 0 1.5rem;
            border-top: 1px solid rgba(255,255,255,0.04);
            text-align: center;
            color: #252525;
            font-size: 0.72rem;
            letter-spacing: 0.05em;
        }
        .app-footer span { color: #F7B731; }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()



# -------------------------------------------------
# General Helpers
# -------------------------------------------------
def section_title(title: str) -> None:
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )


def dataframe_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def plot_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        title=dict(text=title, x=0, font=dict(size=16)),
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(color="#cfcfcf"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    return fig


def get_gemini_client() -> Any:
    if genai is None:
        return None

    api_key = None

    # 1. Check user input in session state
    if st.session_state.get("manual_gemini_api_key"):
        api_key = str(st.session_state.manual_gemini_api_key).strip()

    # 2. Check Streamlit secrets (check direct keys and nested sections)
    if not api_key:
        try:
            for k in ["GEMINI_API_KEY", "gemini_api_key", "GOOGLE_API_KEY", "google_api_key", "GEMINI_KEY"]:
                if k in st.secrets:
                    api_key = str(st.secrets[k]).strip()
                    break
            if not api_key:
                for section in st.secrets:
                    try:
                        sec_val = st.secrets[section]
                        if isinstance(sec_val, dict) or hasattr(sec_val, "get"):
                            for k in ["GEMINI_API_KEY", "gemini_api_key", "GOOGLE_API_KEY", "google_api_key", "api_key"]:
                                if k in sec_val:
                                    api_key = str(sec_val[k]).strip()
                                    break
                    except Exception:
                        pass
                    if api_key:
                        break
        except Exception:
            pass

    # 3. Check environment variables
    if not api_key:
        for k in ["GEMINI_API_KEY", "gemini_api_key", "GOOGLE_API_KEY", "google_api_key"]:
            val = os.getenv(k)
            if val:
                api_key = str(val).strip()
                break

    if not api_key:
        return None

    # Clean any quotes or extra whitespace
    api_key = api_key.strip("'\"").strip()
    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.session_state["gemini_error"] = str(e)
        return None


# -------------------------------------------------
# Data Handling
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "latin-1"]

    for encoding in encodings:
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError:
            continue

    return pd.read_csv(io.BytesIO(file_bytes))


def detect_date_columns(df: pd.DataFrame, threshold: float = 0.8) -> list[str]:
    date_columns = []

    for col in df.select_dtypes(include=["object", "string"]).columns:
        values = df[col].dropna()

        if values.empty:
            continue

        parsed = pd.to_datetime(values, errors="coerce")

        if parsed.notna().mean() >= threshold:
            date_columns.append(col)

    return date_columns


def detect_domain(columns: list[str]) -> str:
    names = " ".join(col.lower() for col in columns)

    finance_terms = [
        "revenue", "profit", "income", "expense", "cost",
        "balance", "salary", "budget", "transaction",
    ]
    sales_terms = [
        "customer", "product", "region", "sales", "order",
        "quantity", "discount", "segment", "merchant",
    ]

    if any(word in names for word in finance_terms):
        return "Finance"

    if any(word in names for word in sales_terms):
        return "Sales"

    return "General Business"


def build_ai_summary(df: pd.DataFrame, sample_rows: int = 8) -> str:
    lines = [
        f"Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns.",
        "",
        "Column profile:",
    ]

    for col in df.columns:
        lines.append(
            f"- {col}: dtype={df[col].dtype}, "
            f"non_null={df[col].notna().sum()}, "
            f"unique={df[col].nunique(dropna=True)}"
        )

    lines.extend(
        [
            "",
            "Sample rows:",
            df.head(sample_rows).to_csv(index=False),
        ]
    )

    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    total_cells = df.shape[0] * df.shape[1]
    missing_count = int(df.isna().sum().sum())

    missing_by_column = (
        (df.isna().mean() * 100)
        .round(2)
        .sort_values(ascending=False)
    )

    zero_variance = [
        col for col in df.columns
        if df[col].nunique(dropna=False) <= 1
    ]

    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_count": missing_count,
        "completeness": round(
            100 * (1 - missing_count / total_cells), 2
        ) if total_cells else 100.0,
        "duplicate_count": int(df.duplicated().sum()),
        "missing_by_column": missing_by_column,
        "zero_variance_columns": zero_variance,
    }


@st.cache_data(show_spinner=False)
def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.select_dtypes(include=np.number)

    if numeric.empty:
        return pd.DataFrame()

    result = numeric.describe().T
    result["skewness"] = numeric.skew()
    result["kurtosis"] = numeric.kurt()
    return result.round(3)


@st.cache_data(show_spinner=False)
def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.select_dtypes(include=np.number)

    if numeric.shape[1] < 2:
        return pd.DataFrame()

    return numeric.corr().round(2)


def iqr_outlier_stats(series: pd.Series) -> tuple[int, float]:
    series = series.dropna()

    if len(series) < 4:
        return 0, 0.0

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return 0, 0.0

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    count = int(((series < lower) | (series > upper)).sum())
    percentage = round((count / len(series)) * 100, 2)

    return count, percentage


def apply_filters(
    df: pd.DataFrame,
    date_column: str | None,
    date_range: tuple | None,
    category_column: str | None,
    categories: list,
) -> pd.DataFrame:
    filtered = df.copy()

    if date_column and date_range and len(date_range) == 2:
        parsed_dates = pd.to_datetime(
            filtered[date_column],
            errors="coerce",
        )

        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)

        filtered = filtered[
            (parsed_dates >= start_date) &
            (parsed_dates < end_date)
        ]

    if category_column and categories:
        filtered = filtered[
            filtered[category_column].isin(categories)
        ]

    return filtered


# -------------------------------------------------
# Session State
# -------------------------------------------------
def init_state(file_id: str, df: pd.DataFrame) -> None:
    if st.session_state.get("file_id") != file_id:
        st.session_state.file_id = file_id
        st.session_state.raw_df = df.copy()
        st.session_state.messages = []
        st.session_state.edited_sample = df.head(20).copy()
        st.session_state.narrative_cache = {}
        st.session_state.narrative_raw = ""

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "narrative_cache" not in st.session_state:
        st.session_state.narrative_cache = {}
    if "narrative_raw" not in st.session_state:
        st.session_state.narrative_raw = ""


# -------------------------------------------------
# Sidebar
# -------------------------------------------------
def sidebar_filters(df: pd.DataFrame, file_name: str = "", file_size_kb: float = 0.0) -> tuple[pd.DataFrame, bool]:
    with st.sidebar:
        # Brand header
        st.markdown(
            """
            <div class="sb-brand">
              <div class="sb-brand-name">📊 BI <em>Assistant</em></div>
              <div class="sb-brand-sub">Business Intelligence Platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # File info card (shown after upload)
        if file_name:
            st.markdown(
                f"""
                <div class="sb-file-card">
                  <div class="sb-file-label">Loaded Dataset</div>
                  <div class="sb-file-name">📄 {file_name}</div>
                  <div class="sb-file-meta">{len(df):,} rows &nbsp;·&nbsp; {len(df.columns)} cols &nbsp;·&nbsp; {file_size_kb:.1f} KB</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            '<hr style="border-color:rgba(255,255,255,0.05);margin:0.8rem 0">',
            unsafe_allow_html=True,
        )
        section_title("Filters")

        date_columns = detect_date_columns(df)
        category_columns = df.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        selected_date_col = None
        selected_date_range = None

        if date_columns:
            selected_date_col = st.selectbox(
                "Date column",
                options=["None"] + date_columns,
            )

            if selected_date_col == "None":
                selected_date_col = None
            else:
                parsed = pd.to_datetime(
                    df[selected_date_col],
                    errors="coerce",
                ).dropna()

                if not parsed.empty:
                    selected_date_range = st.date_input(
                        "Date range",
                        value=(parsed.min().date(), parsed.max().date()),
                        min_value=parsed.min().date(),
                        max_value=parsed.max().date(),
                    )

        selected_category_col = None
        selected_categories = []

        if category_columns:
            selected_category_col = st.selectbox(
                "Category column",
                options=["None"] + category_columns,
            )

            if selected_category_col == "None":
                selected_category_col = None
            else:
                choices = sorted(
                    df[selected_category_col]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                selected_categories = st.multiselect(
                    "Select categories",
                    options=choices,
                )

                if selected_categories:
                    df = df.copy()
                    df[selected_category_col] = (
                        df[selected_category_col].astype(str)
                    )

        filtered = apply_filters(
            df=df,
            date_column=selected_date_col,
            date_range=selected_date_range,
            category_column=selected_category_col,
            categories=selected_categories,
        )

        is_filtered = len(filtered) != len(df)

        if is_filtered:
            st.markdown(
                f'<div class="filter-active-badge">⚡ {len(filtered):,} of {len(df):,} rows</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<hr style="border-color:rgba(255,255,255,0.05);margin:0.8rem 0">',
            unsafe_allow_html=True,
        )
        section_title("AI Status")

        client = get_gemini_client()
        if client:
            st.markdown(
                '<div style="display:flex;align-items:center;font-size:.75rem;color:#4ade80;font-weight:600">'
                '<span class="sb-status-dot sb-status-online"></span> Gemini Connected</div>',
                unsafe_allow_html=True,
            )
            with st.expander("⚙️ API Key Settings", expanded=False):
                new_key = st.text_input(
                    "Update Gemini Key",
                    type="password",
                    placeholder="Paste new AIzaSy... key",
                    key="update_key_input",
                )
                if new_key:
                    st.session_state.manual_gemini_api_key = new_key.strip()
                    st.rerun()
        else:
            st.markdown(
                '<div style="display:flex;align-items:center;font-size:.75rem;color:#f87171;font-weight:600">'
                '<span class="sb-status-dot sb-status-offline"></span> Gemini Offline</div>',
                unsafe_allow_html=True,
            )
            st.caption("Paste your API key below to activate:")
            manual_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="AIzaSy...",
                key="sidebar_key_input",
                help="Get a free key from https://aistudio.google.com",
            )
            if manual_key:
                st.session_state.manual_gemini_api_key = manual_key.strip()
                st.rerun()

            if st.session_state.get("gemini_error"):
                st.error(f"Error: {st.session_state['gemini_error']}", icon="⚠️")

        st.markdown(
            '<p style="font-size:0.6rem;color:#1e1e1e;text-align:center;margin-top:2rem;letter-spacing:0.06em">'
            'MirAI School of Technology · Capstone Project</p>',
            unsafe_allow_html=True,
        )

    return filtered, is_filtered


# -------------------------------------------------
# Tabs
# -------------------------------------------------
def render_overview(df: pd.DataFrame, is_filtered: bool, domain: str = "General Business") -> None:
    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isna().sum().sum())
    completeness = (
        100 * (1 - missing / total_cells)
        if total_cells else 100
    )

    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
    categorical_columns = df.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    # ── Smart Domain-Aware KPIs ───────────────────────────────────
    section_title(f"Smart KPIs — {domain}")
    kpis = compute_smart_kpis(df, domain)
    n_cols = min(len(kpis), 4)
    kpi_cols = st.columns(n_cols)
    for i, kpi in enumerate(kpis[:4]):
        kpi_cols[i].metric(
            label=kpi["label"],
            value=kpi["value"],
            delta=kpi.get("delta"),
            delta_color=kpi.get("delta_color", "off"),
        )
    if len(kpis) > 4:
        kpi_cols2 = st.columns(min(len(kpis) - 4, 4))
        for i, kpi in enumerate(kpis[4:]):
            kpi_cols2[i % 4].metric(
                label=kpi["label"],
                value=kpi["value"],
                delta=kpi.get("delta"),
                delta_color=kpi.get("delta_color", "off"),
            )

    if is_filtered:
        st.markdown(
            f'<div style="margin:.5rem 0"><span class="filter-active-badge">⚡ Filtered — {len(df):,} rows shown</span></div>',
            unsafe_allow_html=True,
        )

    # ── Data Preview ────────────────────────────────────────
    section_title("Data Preview")
    st.dataframe(df.head(100), use_container_width=True)

    # ── Descriptive Statistics ──────────────────────────────
    section_title("Descriptive Statistics")
    stats = numeric_summary(df)
    if stats.empty:
        st.info("No numeric columns are available.")
    else:
        st.dataframe(stats, use_container_width=True)

    # ── Column Metadata ──────────────────────────────────
    with st.expander("📋 Column Metadata"):
        metadata = pd.DataFrame(
            {
                "Column": df.columns,
                "Data type": df.dtypes.astype(str).values,
                "Non-null": [df[col].notna().sum() for col in df.columns],
                "Unique": [df[col].nunique(dropna=True) for col in df.columns],
                "Missing %": [
                    round(df[col].isna().mean() * 100, 2)
                    for col in df.columns
                ],
            }
        )
        st.dataframe(metadata, use_container_width=True, hide_index=True)

    # ── Column Deep Profiler ──────────────────────────────
    with st.expander("🔬 Column Deep Profiler"):
        sel_col = st.selectbox(
            "Select a column to profile",
            df.columns.tolist(),
            key="col_profiler",
        )
        if sel_col:
            series = df[sel_col]
            cp1, cp2, cp3, cp4 = st.columns(4)
            cp1.metric("Non-null",  f"{series.notna().sum():,}")
            cp2.metric("Null",      f"{series.isna().sum():,}")
            cp3.metric("Unique",    f"{series.nunique(dropna=True):,}")
            cp4.metric("Null %",    f"{series.isna().mean()*100:.1f}%")

            if pd.api.types.is_numeric_dtype(series):
                cp5, cp6, cp7, cp8 = st.columns(4)
                cp5.metric("Min",  f"{series.min():.4g}")
                cp6.metric("Max",  f"{series.max():.4g}")
                cp7.metric("Mean", f"{series.mean():.4g}")
                cp8.metric("Std",  f"{series.std():.4g}")
                h1, h2 = st.columns(2)
                with h1:
                    fig_h = px.histogram(df, x=sel_col, nbins=40, color_discrete_sequence=PALETTE)
                    st.plotly_chart(plot_layout(fig_h, f"Distribution — {sel_col}"), use_container_width=True)
                with h2:
                    fig_b = px.box(df, y=sel_col, color_discrete_sequence=PALETTE)
                    st.plotly_chart(plot_layout(fig_b, f"Box Plot — {sel_col}"), use_container_width=True)

                # IQR outlier stats
                count, pct = iqr_outlier_stats(series)
                st.markdown(
                    f'<div style="font-size:.8rem;color:#aaa;margin:.5rem 0">⚠️ <strong style="color:#F87171">{count:,} outliers</strong> detected ({pct:.1f}% of values) using IQR method</div>',
                    unsafe_allow_html=True,
                )

            else:
                vc = series.value_counts().head(20).reset_index()
                vc.columns = [sel_col, "Count"]
                p1, p2 = st.columns(2)
                with p1:
                    fig_bar = px.bar(vc, x=sel_col, y="Count", color_discrete_sequence=PALETTE)
                    st.plotly_chart(plot_layout(fig_bar, f"Top 20 Values — {sel_col}"), use_container_width=True)
                with p2:
                    fig_pie = px.pie(vc.head(10), names=sel_col, values="Count",
                                     color_discrete_sequence=PALETTE, hole=0.4)
                    st.plotly_chart(plot_layout(fig_pie, f"Share — {sel_col}"), use_container_width=True)
                st.dataframe(vc, use_container_width=True, hide_index=True)

    # ── Export ──────────────────────────────────────────
    section_title("Export")
    e1, e2, e3 = st.columns(3)

    with e1:
        st.download_button(
            "⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="bi_export.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with e2:
        try:
            q_summary   = quality_summary(df)
            stats_excel = numeric_summary(df)
            corr_excel  = correlation_matrix(df)
            narrative_text = st.session_state.get("narrative_raw", "")
            excel_bytes = to_excel_bytes(
                df=df,
                stats_df=stats_excel,
                quality_dict=q_summary,
                corr_df=corr_excel,
                narrative=narrative_text,
                file_name="bi_export",
            )
            st.download_button(
                "⬇ Download Excel (multi-sheet)",
                data=excel_bytes,
                file_name="bi_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"Excel export unavailable: {e}")

    with e3:
        json_bytes = to_json_bytes(df, metadata={"domain": domain})
        st.download_button(
            "⬇ Download JSON",
            data=json_bytes,
            file_name="bi_export.json",
            mime="application/json",
            use_container_width=True,
        )



def render_visualizations(df: pd.DataFrame) -> None:
    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
    categorical_columns = df.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    chart_type = st.selectbox(
        "Chart type",
        [
            "Histogram",
            "Bar Chart",
            "Pie / Donut",
            "Scatter Plot",
            "Box Plot",
            "Correlation Heatmap",
            "Line Chart",
            "Waterfall Chart",
            "Funnel Chart",
            "Calendar Heatmap",
        ],
    )

    if chart_type == "Histogram":
        if not numeric_columns:
            st.warning("No numeric columns found.")
            return

        col1, col2, col3 = st.columns(3)
        value_col = col1.selectbox("Numeric column", numeric_columns)
        bins = col2.slider("Bins", 5, 100, 30)
        color_col = col3.selectbox(
            "Color by",
            ["None"] + categorical_columns,
        )

        fig = px.histogram(
            df,
            x=value_col,
            nbins=bins,
            color=None if color_col == "None" else color_col,
            color_discrete_sequence=PALETTE,
        )
        st.plotly_chart(
            plot_layout(fig, f"Distribution of {value_col}"),
            use_container_width=True,
        )

    elif chart_type == "Bar Chart":
        if not numeric_columns or not categorical_columns:
            st.warning(
                "A bar chart requires at least one numeric and one category column."
            )
            return

        col1, col2, col3, col4 = st.columns(4)
        category = col1.selectbox("Category", categorical_columns)
        value = col2.selectbox("Value", numeric_columns)
        aggregation = col3.selectbox(
            "Aggregation",
            ["sum", "mean", "median", "count", "max", "min"],
        )
        top_n = col4.slider("Top N", 5, 50, 15)

        grouped = (
            df.groupby(category, dropna=False)[value]
            .agg(aggregation)
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index()
        )

        fig = px.bar(
            grouped,
            x=category,
            y=value,
            color=value,
            color_continuous_scale=["#FF6B35", "#F7B731"],
        )
        fig.update_layout(coloraxis_showscale=False)

        st.plotly_chart(
            plot_layout(
                fig,
                f"Top {top_n} {category} by {aggregation}({value})",
            ),
            use_container_width=True,
        )

    elif chart_type == "Pie / Donut":
        if not categorical_columns:
            st.warning("No category columns found.")
            return

        col1, col2, col3 = st.columns(3)
        category = col1.selectbox("Category", categorical_columns)
        hole = col2.slider("Donut size", 0.0, 0.7, 0.45, 0.05)
        top_n = col3.slider("Top categories", 3, 30, 10)

        counts = (
            df[category]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .head(top_n)
            .reset_index()
        )
        counts.columns = [category, "Count"]

        fig = px.pie(
            counts,
            names=category,
            values="Count",
            hole=hole,
            color_discrete_sequence=PALETTE,
        )

        st.plotly_chart(
            plot_layout(fig, f"Distribution of {category}"),
            use_container_width=True,
        )

    elif chart_type == "Scatter Plot":
        if len(numeric_columns) < 2:
            st.warning("A scatter plot requires at least two numeric columns.")
            return

        col1, col2, col3 = st.columns(3)
        x_col = col1.selectbox("X axis", numeric_columns, index=0)
        y_col = col2.selectbox("Y axis", numeric_columns, index=1)
        color_col = col3.selectbox(
            "Color by",
            ["None"] + categorical_columns,
        )

        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=None if color_col == "None" else color_col,
            color_discrete_sequence=PALETTE,
            opacity=0.75,
        )

        st.plotly_chart(
            plot_layout(fig, f"{y_col} vs {x_col}"),
            use_container_width=True,
        )

    elif chart_type == "Box Plot":
        if not numeric_columns:
            st.warning("No numeric columns found.")
            return

        col1, col2 = st.columns(2)
        value_col = col1.selectbox("Numeric column", numeric_columns)
        group_col = col2.selectbox(
            "Group by",
            ["None"] + categorical_columns,
        )

        fig = px.box(
            df,
            x=None if group_col == "None" else group_col,
            y=value_col,
            color=None if group_col == "None" else group_col,
            color_discrete_sequence=PALETTE,
            points="outliers",
        )

        st.plotly_chart(
            plot_layout(fig, f"Box Plot: {value_col}"),
            use_container_width=True,
        )

    elif chart_type == "Correlation Heatmap":
        corr = correlation_matrix(df)

        if corr.empty:
            st.warning("At least two numeric columns are required.")
            return

        fig = go.Figure(
            go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.index,
                text=corr.values,
                texttemplate="%{text}",
                colorscale="RdYlGn",
                zmin=-1,
                zmax=1,
            )
        )

        st.plotly_chart(
            plot_layout(fig, "Correlation Heatmap"),
            use_container_width=True,
        )

    elif chart_type == "Line Chart":
        if not numeric_columns:
            st.warning("No numeric columns found.")
            return

        date_columns = detect_date_columns(df)
        x_choices = ["Row Number"] + date_columns + numeric_columns

        col1, col2 = st.columns(2)
        x_col = col1.selectbox("X axis", x_choices)
        y_cols = col2.multiselect(
            "Y columns",
            numeric_columns,
            default=numeric_columns[: min(2, len(numeric_columns))],
        )

        if not y_cols:
            st.info("Select at least one Y column.")
            return

        plot_df = df.copy()

        if x_col == "Row Number":
            plot_df["Row Number"] = np.arange(1, len(plot_df) + 1)

        fig = px.line(
            plot_df,
            x=x_col,
            y=y_cols,
            color_discrete_sequence=PALETTE,
        )

        st.plotly_chart(
            plot_layout(fig, "Line Chart"),
            use_container_width=True,
        )

    elif chart_type == "Waterfall Chart":
        if not numeric_columns or not categorical_columns:
            st.warning("A waterfall chart requires at least one numeric and one category column.")
            return
        col1, col2, col3 = st.columns(3)
        cat  = col1.selectbox("Category column", categorical_columns, key="wf_cat")
        val  = col2.selectbox("Value column",    numeric_columns,     key="wf_val")
        agg  = col3.selectbox("Aggregation", ["sum", "mean", "count"], key="wf_agg")
        grouped = df.groupby(cat)[val].agg(agg).reset_index()
        grouped.columns = [cat, val]
        grouped = grouped.sort_values(val, ascending=False)
        measures = ["relative"] * len(grouped)
        fig = go.Figure(go.Waterfall(
            x=grouped[cat],
            y=grouped[val],
            measure=measures,
            connector={"line": {"color": "rgba(255,255,255,0.2)"}},
            increasing={"marker": {"color": PALETTE[0]}},
            decreasing={"marker": {"color": "#F87171"}},
            totals={   "marker": {"color": PALETTE[2]}},
            texttemplate="%{y:.2s}",
            textposition="outside",
        ))
        st.plotly_chart(plot_layout(fig, f"Waterfall — {agg}({val}) by {cat}"), use_container_width=True)

    elif chart_type == "Funnel Chart":
        if not numeric_columns or not categorical_columns:
            st.warning("A funnel chart requires at least one numeric and one category column.")
            return
        col1, col2 = st.columns(2)
        stage = col1.selectbox("Stage column (categories)", categorical_columns, key="fn_stage")
        value = col2.selectbox("Value column",              numeric_columns,     key="fn_val")
        funnel_df = df.groupby(stage)[value].sum().reset_index()
        funnel_df.columns = [stage, value]
        funnel_df = funnel_df.sort_values(value, ascending=False)
        fig = px.funnel(
            funnel_df,
            x=value,
            y=stage,
            color_discrete_sequence=PALETTE,
        )
        st.plotly_chart(plot_layout(fig, f"Funnel — {value} by {stage}"), use_container_width=True)

    elif chart_type == "Calendar Heatmap":
        date_cols = detect_date_columns(df)
        if not date_cols or not numeric_columns:
            st.warning("A calendar heatmap requires a date column and a numeric column.")
            return
        col1, col2 = st.columns(2)
        date_col = col1.selectbox("Date column",  date_cols,     key="cal_date")
        val_col  = col2.selectbox("Value column", numeric_columns, key="cal_val")
        tmp = df[[date_col, val_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col])
        tmp["date"] = tmp[date_col].dt.date
        daily = tmp.groupby("date")[val_col].sum().reset_index()
        daily.columns = ["date", val_col]
        daily["date"] = pd.to_datetime(daily["date"])
        daily["week"]    = daily["date"].dt.isocalendar().week.astype(int)
        daily["weekday"] = daily["date"].dt.day_name()
        daily["month"]   = daily["date"].dt.strftime("%b %Y")
        fig = px.density_heatmap(
            daily,
            x="week",
            y="weekday",
            z=val_col,
            color_continuous_scale=["#1a1a2e", PALETTE[0], PALETTE[1]],
            nbinsx=52,
        )
        fig.update_layout(yaxis={"categoryorder": "array",
                                  "categoryarray": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]})
        st.plotly_chart(plot_layout(fig, f"Calendar Heatmap — {val_col}"), use_container_width=True)


def render_quality(df: pd.DataFrame) -> None:
    summary = quality_summary(df)
    missing_pct = summary["missing_by_column"]

    section_title("Data Completeness")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{summary['rows']:,}")
    col2.metric("Missing values", f"{summary['missing_count']:,}")
    col3.metric("Duplicate rows", f"{summary['duplicate_count']:,}")
    col4.metric("Completeness", f"{summary['completeness']:.2f}%")

    missing_table = pd.DataFrame(
        {
            "Column": missing_pct.index,
            "Missing %": missing_pct.values,
            "Missing count": [
                df[column].isna().sum()
                for column in missing_pct.index
            ],
        }
    )

    missing_with_values = missing_table[
        missing_table["Missing count"] > 0
    ]

    if missing_with_values.empty:
        st.success("No missing values found.")
    else:
        fig = px.bar(
            missing_with_values,
            x="Column",
            y="Missing %",
            color="Missing %",
            color_continuous_scale=["#F7B731", "#F87171"],
        )
        fig.update_layout(coloraxis_showscale=False)

        st.plotly_chart(
            plot_layout(fig, "Missing Values by Column"),
            use_container_width=True,
        )

        st.dataframe(
            missing_with_values,
            use_container_width=True,
            hide_index=True,
        )

    section_title("Outlier Detection")

    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()

    if not numeric_columns:
        st.info("No numeric columns available for IQR outlier detection.")
    else:
        outliers = []

        for col in numeric_columns:
            count, percentage = iqr_outlier_stats(df[col])
            outliers.append(
                {
                    "Column": col,
                    "Outliers": count,
                    "Outlier %": percentage,
                }
            )

        outlier_df = pd.DataFrame(outliers).sort_values(
            "Outliers",
            ascending=False,
        )

        fig = px.bar(
            outlier_df,
            x="Column",
            y="Outlier %",
            color="Outlier %",
            color_continuous_scale=["#F7B731", "#F87171"],
        )
        fig.update_layout(coloraxis_showscale=False)

        st.plotly_chart(
            plot_layout(fig, "IQR Outliers by Column"),
            use_container_width=True,
        )
        st.dataframe(outlier_df, use_container_width=True, hide_index=True)

    if summary["zero_variance_columns"]:
        section_title("Columns With No Variation")
        st.warning(
            "These columns have one or fewer unique values: "
            + ", ".join(summary["zero_variance_columns"])
        )


def render_narrative(df: pd.DataFrame, domain: str) -> None:
    """Render the AI Business Narrative generator panel."""
    client = get_gemini_client()
    section_title("AI Business Narrative")

    if client is None:
        st.warning(
            "Gemini is not configured. Add GEMINI_API_KEY to your .env file "
            "or Streamlit secrets."
        )
        return

    st.markdown(
        '<p style="color:#555;font-size:.88rem;margin-top:-.5rem;margin-bottom:1rem">'  
        'One-click executive report: Executive Summary · Key Findings · Anomalies · Next Steps'
        '</p>',
        unsafe_allow_html=True,
    )

    col_btn, col_clear = st.columns([4, 1])
    with col_btn:
        gen_btn = st.button("🤖 Generate Insights Report", use_container_width=True)
    with col_clear:
        clear_btn = st.button("🗑 Clear", use_container_width=True)

    if clear_btn:
        st.session_state.narrative_cache = {}
        st.session_state.narrative_raw = ""
        st.rerun()

    if gen_btn:
        data_summary = build_ai_summary(df)
        with st.spinner("✨ Gemini is writing your business report…"):
            narrative = generate_narrative(
                client=client,
                model=GEMINI_MODEL,
                data_summary=data_summary,
                domain=domain,
                cache_store=st.session_state.narrative_cache,
            )
            # Persist raw text for Excel export
            key = _narrative_key(data_summary, domain)
            st.session_state.narrative_raw = st.session_state.narrative_cache.get(key, "")
        _render_narrative_cards(narrative)

    elif st.session_state.get("narrative_cache"):
        # Re-render cached narrative without re-calling API
        data_summary = build_ai_summary(df)
        key = _narrative_key(data_summary, domain)
        if key in st.session_state.narrative_cache:
            narrative = _parse_narrative(st.session_state.narrative_cache[key])
            _render_narrative_cards(narrative)
        else:
            st.info("Click \"Generate Insights Report\" to create an AI business narrative for this dataset.")
    else:
        st.info("Click \"Generate Insights Report\" to create an AI business narrative for this dataset.")


def _render_narrative_cards(narrative: dict) -> None:
    """Render the four narrative sections as styled glassmorphism cards."""
    card_base = (
        "background:rgba(255,255,255,0.03);"
        "border:1px solid rgba(255,255,255,0.07);"
        "border-radius:14px;padding:1.4rem 1.6rem;margin-bottom:1rem"
    )
    sections = [
        ("📋 Executive Summary", narrative.get("executive_summary", ""), "#60A5FA"),
        ("🔍 Key Findings",      narrative.get("key_findings",      ""), "#4ADE80"),
        ("⚠️ Anomalies & Risks", narrative.get("anomalies_risks",   ""), "#F87171"),
        ("→ Next Steps",         narrative.get("next_steps",        ""), "#F7B731"),
    ]
    for title, content, color in sections:
        if not content.strip():
            continue
        st.markdown(
            f'<div style="{card_base};border-left:3px solid {color}">'
            f'<div style="font-size:.68rem;font-weight:700;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{color};margin-bottom:.7rem">{title}</div>'
            f'<div style="font-size:.88rem;color:#bbb;line-height:1.75;white-space:pre-line">{content}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_ai_assistant(df: pd.DataFrame, is_filtered: bool) -> None:
    client = get_gemini_client()

    section_title("AI Assistant")

    if client is None:
        st.warning(
            "Gemini is not configured. Add GEMINI_API_KEY to your .env file "
            "or Streamlit secrets."
        )
        return

    domain = detect_domain(df.columns.tolist())

    st.caption(
        f"Detected domain: {domain}"
        + (" · AI answers use the filtered dataset." if is_filtered else "")
    )

    if st.button("🗑 Clear chat"):
        st.session_state.messages = []
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask a business question about the uploaded data..."
    )

    if not question:
        return

    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    context = build_ai_summary(df)

    prompt = f"""
You are a concise business intelligence assistant.

Business domain: {domain}

Use only the dataset profile and sample below.
If the information is not sufficient, clearly say so.
Do not invent exact statistics not present in the supplied data.
Focus on practical business interpretation.

DATASET CONTEXT:
{context}

USER QUESTION:
{question}
"""

    with st.chat_message("assistant"):
        with st.spinner("Analyzing dataset..."):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )

                answer = getattr(response, "text", None)

                if not answer:
                    answer = (
                        "Gemini did not return a usable text response. "
                        "Please try again."
                    )

            except Exception as exc:
                answer = f"Gemini request failed: {exc}"

        st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )


def render_editor(df: pd.DataFrame) -> None:
    section_title("Editable Data Sample")

    st.caption(
        "This editor works on the first 20 rows only. "
        "Download the sample after making changes."
    )

    edited = st.data_editor(
        st.session_state.edited_sample,
        use_container_width=True,
        num_rows="fixed",
        key="data_editor",
    )

    st.session_state.edited_sample = edited

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "⬇ Download edited sample",
            data=edited.to_csv(index=False).encode("utf-8"),
            file_name="edited_sample.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        if st.button("Reset sample"):
            st.session_state.edited_sample = df.head(20).copy()
            st.rerun()

    numeric_columns = edited.select_dtypes(include=np.number).columns.tolist()

    if numeric_columns:
        section_title("Edited Sample Statistics")
        st.dataframe(
            edited[numeric_columns].describe().T.round(3),
            use_container_width=True,
        )


# -------------------------------------------------
# Footer Helper
# -------------------------------------------------
def _render_footer() -> None:
    st.markdown(
        """
        <div class="app-footer">
          Built with <span>Streamlit</span> + <span>Gemini</span>
          &nbsp;·&nbsp; MirAI School of Technology Capstone
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------
# Main Application
# -------------------------------------------------
def main() -> None:
    domain_str = ""

    # Upload lives in sidebar (hidden label so branding shows cleanly)
    with st.sidebar:
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            label_visibility="collapsed",
        )

    if uploaded_file is None:
        # Landing hero — no data yet
        st.markdown(
            """
            <div class="hero">
              <h1>Business <em>Intelligence</em> Platform</h1>
              <p>Upload your dataset · Explore deep insights · Ask anything with Gemini AI</p>
              <div class="hero-badges">
                <span class="hero-badge">📊 Smart Charts</span>
                <span class="hero-badge">🔍 Data Quality</span>
                <span class="hero-badge">🤖 AI Q&amp;A</span>
                <span class="hero-badge">⚡ Real-time Filters</span>
                <span class="hero-badge">💡 Chart Explanations</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(
                """
                <div style="text-align:center;padding:4.5rem 2rem;
                    background:rgba(255,255,255,0.02);
                    border:1.5px dashed rgba(247,183,49,0.2);
                    border-radius:18px;margin-top:1.5rem">
                  <div style="font-size:3.5rem;margin-bottom:1rem">📂</div>
                  <div style="font-size:1.25rem;font-weight:700;color:#fff;
                      letter-spacing:-0.02em;margin-bottom:0.4rem">Drop your dataset here</div>
                  <div style="color:#383838;font-size:0.88rem">
                    Upload a CSV using the sidebar to get started</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        sidebar_filters(pd.DataFrame())
        _render_footer()
        return

    file_bytes = uploaded_file.getvalue()
    file_id = dataframe_hash(file_bytes)

    try:
        raw_df = load_csv(file_bytes)
    except Exception as exc:
        st.error(f"Could not read the CSV file: {exc}")
        return

    if raw_df.empty:
        st.error("The uploaded CSV contains no rows.")
        return

    raw_df.columns = [
        str(col).strip() if str(col).strip() else f"Unnamed_{i}"
        for i, col in enumerate(raw_df.columns)
    ]

    init_state(file_id, raw_df)

    domain_str   = detect_domain(raw_df.columns.tolist())
    file_size_kb = round(len(file_bytes) / 1024, 1)

    # Large dataset guard
    if len(raw_df) > 100_000:
        st.warning(
            f"Large dataset detected — {len(raw_df):,} rows. "
            f"Filters and sampling recommended for best performance.",
        )

    filtered_df, is_filtered = sidebar_filters(
        raw_df,
        file_name=uploaded_file.name,
        file_size_kb=file_size_kb,
    )

    if filtered_df.empty:
        st.warning("No rows match the selected filters. Adjust or clear them.")
        return

    # Hero (data loaded)
    st.markdown(
        f"""
        <div class="hero">
          <h1>Business <em>Intelligence</em> Platform</h1>
          <p>Exploring <strong style="color:#ddd">{uploaded_file.name}</strong>
             &nbsp;&middot;&nbsp; {len(filtered_df):,} rows &nbsp;&middot;&nbsp;
             {len(filtered_df.columns)} columns
             {'&nbsp;&middot;&nbsp; <span style="color:#F7B731">&#9889; Filtered</span>' if is_filtered else ''}
          </p>
          <div class="hero-badges">
            <span class="hero-badge">&#127991; Domain: {domain_str}</span>
            <span class="hero-badge">&#128202; Smart Charts</span>
            <span class="hero-badge">&#129302; Gemini AI</span>
            <span class="hero-badge">&#128193; Multi-format Export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        overview_tab,
        charts_tab,
        quality_tab,
        narrative_tab,
        ai_tab,
        editor_tab,
    ) = st.tabs(
        [
            "\U0001f4ca Overview",
            "\U0001f4c8 Visualizations",
            "\U0001f50d Data Quality",
            "\U0001f4dd AI Narrative",
            "\U0001f916 AI Assistant",
            "\u270f\ufe0f Data Editor",
        ]
    )

    with overview_tab:
        render_overview(filtered_df, is_filtered, domain=domain_str)

    with charts_tab:
        render_visualizations(filtered_df)

    with quality_tab:
        render_quality(filtered_df)

    with narrative_tab:
        render_narrative(filtered_df, domain=domain_str)

    with ai_tab:
        render_ai_assistant(filtered_df, is_filtered)

    with editor_tab:
        render_editor(raw_df)

    _render_footer()


if __name__ == "__main__":
    main()