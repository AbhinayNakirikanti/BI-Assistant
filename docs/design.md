# Design Document

## 1. Overview

BI Assistant is a lightweight, AI-augmented business intelligence tool built for non-technical users who need quick insight into a tabular dataset without writing SQL, Pandas, or spreadsheet formulas. Target users include analysts, small business owners, and students who want to upload a CSV (finance, sales, or transaction data) and immediately get a profiled dashboard plus a conversational interface for asking business questions.

## 2. Data Flow

1. The user uploads a CSV file through the Streamlit file uploader.
2. The app validates the file (non-empty, parseable as CSV) and loads it into a Pandas dataframe.
3. The dataframe is profiled: row/column counts, per-column dtype, non-null count, unique count, and missing-value totals.
4. A compact text `data_summary` is generated from the profile plus a small sample of rows.
5. The dataset's domain (personal finance, sales analytics, or generic) is auto-detected from column names, and the appropriate domain-specialist system prompt is selected.
6. KPI cards, a data preview table, descriptive statistics, and 9 Plotly chart types are rendered from the profiled dataframe.
7. Sidebar filters (date range + categorical multi-select) produce a `filtered_df`; all charts, tables, and the AI context use this slice when filters are active.
8. When the user submits a question, the app builds a dynamic prompt combining the domain-aware system prompt, the (filtered) `data_summary`, and the question, then sends it to the Gemini API.
9. The model's response is parsed and rendered as a chat message; Gemini then generates 3 follow-up suggestion chips displayed below the answer.
10. Each chart includes a "💡 Explain chart" button that calls Gemini for a 2-3 sentence business-friendly explanation, cached in session state.
11. The Data Quality tab surfaces missingness, duplicates, zero-variance columns, and outliers; an on-demand AI call generates 3 prioritised data-quality recommendations.
12. If the user edits the data sample, `data_summary` is recomputed from the edited rows so subsequent questions reflect the changes.

## 3. Modules

- **`app.py`** — the single entry point containing all UI sections, session-state wiring, and Gemini calls.
- **`profiler_utils.py`** — `@st.cache_data` wrappers for heavy computations (correlation matrix, zero-variance detection, quality summary, descriptive stats); domain detection from column names; domain-aware system-prompt factory.
- **`chart_explain.py`** — `explain_chart()` and `suggest_followups()` helpers that call Gemini and use a lightweight dict-based in-session cache to avoid redundant API calls.
- **Data summary generator (`build_summary`)** — a pure function that converts a dataframe into a compact, LLM-friendly text block.
- **Prompt builder** — inline logic that concatenates the domain system prompt, data summary, user question, and an optional filter-active note into the final prompt string sent to Gemini.
- **Chat UI renderer** — the loop over `st.session_state["messages"]` that displays prior turns using `st.chat_message`.

## 4. API Integration Strategy

- The Gemini client is configured once at startup using `st.secrets["GEMINI_API_KEY"]` (with `.env` fallback), with `gemini-2.0-flash` as the model.
- Each user question is answered with a single `model.generate_content(prompt)` call inside a `st.form`, which prevents redundant API calls on every widget interaction.
- Chart explanations are generated on button click and stored in `st.session_state.chart_explanations` (a dict keyed by an MD5 hash of the chart description + sample data). Subsequent clicks or re-renders load from the cache instantly.
- Follow-up suggestions are generated immediately after each AI answer and stored in `st.session_state.followup_cache` (keyed by a hash of the answer + summary). Repeated identical Q&A pairs load from cache.
- Data quality recommendations are generated on explicit user request (button click) and stored in `st.session_state.quality_rec_cache` (keyed by dataset fingerprint). They persist until a new file is uploaded.
- All Gemini calls are wrapped in `try/except`; failures are surfaced with `st.error` and also recorded in the chat history so the user sees a clear failure message rather than a crash.
- The system prompt explicitly instructs the model to answer only from the supplied dataset summary and to state when a question cannot be answered from the data, minimising hallucination.

## 5. State Management

`st.session_state` holds the following keys:

| Key | Type | Purpose |
|---|---|---|
| `df` | DataFrame | Current working dataframe loaded from CSV |
| `fname` | str | Uploaded file name; change triggers full reset |
| `summary` | str | Compact text summary for AI prompts; recomputed on editor changes |
| `messages` | list[dict] | Full chat history including system prompt |
| `chart_explanations` | dict | In-session cache for Gemini chart explanations |
| `followup_cache` | dict | In-session cache for follow-up question suggestions |
| `quality_rec_cache` | dict | In-session cache for data quality recommendations |
| `pending_question` | str | Auto-fill value from a clicked suggestion chip |
| `filter_cat_values` | list | Selected category filter values |
| `filter_date_start` | date | Start of active date filter |
| `filter_date_end` | date | End of active date filter |

A new upload (detected via a changed file name) resets all keys so a fresh dataset starts with a clean profile, empty caches, and a new conversation.

`@st.cache_data` (from `profiler_utils.py`) provides cross-session Streamlit-level caching for CPU-heavy operations (correlation matrix, quality summary), keyed by the dataset fingerprint (MD5 of shape + column names). This avoids recomputation on tab switches and widget interactions without a cache miss.

## 6. Future Enhancements

- Support for Excel (`.xlsx`) uploads alongside CSV.
- Natural-language-to-Pandas code generation with sandboxed execution, so answers can be verified against actual computed results rather than the model's summary reasoning alone.
- User authentication and per-user saved datasets/conversation history.
- Downloadable PDF/Word summary reports generated from a session's insights and charts.
- Multi-file upload and join assistant for combining datasets.
- Scheduled data refresh via webhook for live-connected data sources.

---

## 7. Security & Privacy

### API Key Management

- The Gemini API key is loaded exclusively from `st.secrets["GEMINI_API_KEY"]` (for Streamlit Community Cloud) or a `.env` file (for local development via `python-dotenv`).
- **The API key is never hardcoded in source files** and is excluded from version control via `.gitignore` (both `.env` and `.streamlit/secrets.toml` are listed).
- Contributors must not commit API keys in any form — pull requests containing credentials will be rejected.

### Data Handling

- Uploaded CSV data is processed **entirely in memory** (Python/Pandas) within the user's Streamlit session. No data is written to disk, logged, or persisted to any external database or storage service.
- Data sent to the Gemini API is limited to: a compact text summary (column names, dtypes, non-null counts, and a small row sample of ≤ 6 rows). The full dataset is **never transmitted** to the Gemini API.
- Session state is isolated per user session and is cleared automatically when the session ends or a new file is uploaded.

### Limitations & Recommendations

- **Not suitable for sensitive PII without additional safeguards.** If the dataset contains Personally Identifiable Information (names, emails, SSNs, financial account numbers, health records), users should anonymise or pseudonymise the data before uploading.
- **No end-to-end encryption** of the session data beyond what Streamlit and the underlying host provide. For compliance-sensitive workloads, deploy on an internal network or a compliant cloud environment.
- **Model outputs are not guaranteed to be accurate.** The system prompt instructs Gemini to answer only from the supplied data, but large language models can still produce incorrect statements. Always validate AI-generated insights against the raw data before making business decisions.
- **Rate limits** apply to the Gemini API under the free tier. Heavy concurrent use may result in `429 Too Many Requests` errors; these are caught and displayed to the user gracefully.
