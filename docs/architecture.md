# Architecture

BI Assistant follows a linear pipeline that turns an uploaded CSV into a profiled dashboard and a grounded, natural-language Q&A experience, coordinated through Streamlit's session state.

## System Architecture — Component Flowchart

```mermaid
flowchart TD
    A[User uploads CSV] --> B[Streamlit Frontend]
    B --> C[Pandas Data Loader & Profiler]
    C --> D[Data Summary Generator]
    D --> E[Prompt Builder\nSystem + Context + Query]
    E --> F[Gemini API]
    F --> G[Response Parser & Renderer]
    G --> H[Chat UI + Visualizations]

    B -.- S[(st.session_state\ndf, data_summary, messages\nchart_explanations, followup_cache)]
    C -.- S
    D -.- S
    G -.- S

    B --> FILT[Sidebar Filter Engine]
    FILT --> FILT_DF[filtered_df]
    FILT_DF --> D
    FILT_DF --> H
```

## Q&A Interaction — Sequence Diagram

This diagram shows the full message flow when a user asks a question in the AI Assistant tab.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Streamlit UI
    participant PB as Prompt Builder
    participant GM as Gemini API
    participant RP as Response Parser
    participant SS as st.session_state

    User->>UI: Types question & clicks "Ask Gemini"
    UI->>SS: Append {role: user, content: question}
    UI->>PB: Invoke with (system_prompt, data_summary, question)
    Note over PB: Domain-aware system prompt\n+ filtered or full data summary\n+ user question concatenated
    PB->>GM: generate_content(model="gemini-1.5-flash", prompt)
    GM-->>RP: Raw text response
    RP->>UI: Render answer as chat bubble (st.chat_message)
    RP->>SS: Append {role: assistant, content: answer}

    UI->>GM: suggest_followups(answer, data_summary)
    GM-->>UI: 3 follow-up question strings
    UI->>User: Render clickable suggestion chips

    User->>UI: Clicks a suggestion chip
    UI->>SS: Set pending_question = chip text
    UI->>UI: st.rerun() → auto-fill input
    Note over UI: Form re-submits with\nauto-filled question
```

## Component Overview

- **Streamlit Frontend** — renders the file uploader, KPI cards, charts, chat interface, and data editor.
- **Pandas Data Loader & Profiler** — reads the CSV into a dataframe and computes row/column counts, dtypes, and missing-value statistics.
- **Sidebar Filter Engine** — date-range and category filters that produce a `filtered_df`; all views use this filtered slice when active.
- **Data Summary Generator** (`build_summary`) — condenses the profiled dataframe into a compact text block (column details plus a small sample) suitable for an LLM prompt.
- **Prompt Builder** — combines the domain-aware system prompt, the data summary (filtered or full), and the user's question into a single dynamic prompt.
- **Gemini API** — the `gemini-1.5-flash` model generates grounded answers, chart explanations, follow-up suggestions, and data quality recommendations.
- **Response Parser & Renderer** — extracts the model's text response and displays it as a chat bubble.
- **Chart UI + Visualizations** — 9 Plotly chart types; each rendered chart includes a "💡 Explain chart" button powered by Gemini.
- **st.session_state** — persists `df`, `data_summary`, `messages`, `chart_explanations`, `followup_cache`, and `quality_rec_cache` across reruns.
- **`profiler_utils.py`** — `@st.cache_data` wrappers for heavy computations (correlation, quality stats, descriptive stats); domain detection; system-prompt factory.
- **`chart_explain.py`** — `explain_chart()` and `suggest_followups()` Gemini helpers with in-session dict caching.
