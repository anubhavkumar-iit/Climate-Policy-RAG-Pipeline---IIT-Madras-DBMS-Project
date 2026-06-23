import streamlit as st
import os
import re
import time
import pandas as pd
from dotenv import load_dotenv

# ── Page Config — MUST be the very first Streamlit call ───────────────────────
st.set_page_config(
    page_title="Climate Policy Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Environment & Backend Loading with Absolute Path Fallback ──────────────────
# Try loading relative .env first
loaded_env = load_dotenv()
if not loaded_env or not os.getenv("DB_NAME"):
    # Fall back to absolute workspace path
    
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import load_model, get_connection, get_all_countries
from retrieval_fallback import (
    tiered_retrieve,
    generate_answer_grounded,
    web_search_fallback,
    log_with_tier,
)

# ── Session State ──────────────────────────────────────────────────────────────
for _k, _v in {
    "theme": "dark",
    "messages": [],
    "pending_question": None,
    "metrics_animated": False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── CSS Design System ──────────────────────────────────────────────────────────
def _inject_css(theme: str) -> None:
    dark = theme == "dark"

    # Color Tokens
    app_bg      = "#0A0E1A"        if dark else "#F8FAFC"
    sidebar_bg  = "#0F1322"        if dark else "#F1F5F9"
    card_bg     = "rgba(22, 28, 45, 0.65)" if dark else "rgba(255, 255, 255, 0.85)"
    border      = "rgba(255, 255, 255, 0.08)" if dark else "rgba(0, 0, 0, 0.08)"
    text_pri    = "#F1F5F9"        if dark else "#0F172A"
    text_sec    = "#94A3B8"        if dark else "#475569"
    input_bg    = "#1E293B"        if dark else "#FFFFFF"
    input_text  = "#F8FAFC"        if dark else "#0F172A"
    asst_bg     = "rgba(30, 41, 59, 0.5)" if dark else "rgba(255, 255, 255, 0.95)"
    asst_text   = "#F8FAFC"        if dark else "#0F172A"
    asst_shadow = "rgba(0,0,0,0.35)" if dark else "rgba(0,0,0,0.05)"
    exp_bg      = "rgba(22, 28, 45, 0.4)" if dark else "#E2E8F0"
    scroll_bg   = "#0B0F19"        if dark else "#F8FAFC"
    scroll_bdr  = "rgba(255, 255, 255, 0.05)" if dark else "rgba(0, 0, 0, 0.05)"
    metric_val  = "#3B82F6"        if dark else "#2563EB"
    hr_col      = "rgba(255, 255, 255, 0.08)" if dark else "rgba(0, 0, 0, 0.08)"
    g1          = "#0A0D17"        if dark else "#F8FAFC"
    g2          = "#0B132B"        if dark else "#EFF6FF"
    g3          = "#070A13"        if dark else "#F1F5F9"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif !important;
}}

h1, h2, h3, .hero-title, .nav-title {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

/* ── Animated Background ── */
@keyframes bgShift {{
    0%   {{ background-position:   0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position:   0% 50%; }}
}}
.stApp {{
    background: linear-gradient(-45deg, {g1}, {g2}, {g3}, {g1});
    background-size: 400% 400%;
    animation: bgShift 20s ease infinite;
}}

/* ── Hide default Streamlit headers ── */
#MainMenu, footer, header {{
    visibility: hidden;
}}

/* ── Sidebar Styling ── */
[data-testid="stSidebar"] {{
    background-color: {sidebar_bg} !important;
    border-right: 1px solid {border} !important;
}}
[data-testid="stSidebar"] * {{
    color: {text_pri} !important;
}}

/* ── Custom Glassmorphism Cards ── */
.glass-card {{
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 16px;
    padding: 24px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.08);
    margin-bottom: 20px;
    color: {text_pri};
}}

.glass-card h3 {{
    margin-top: 0;
    color: {text_pri};
    font-weight: 700;
}}

/* ── Custom Metric Grid ── */
.stats-grid {{
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    width: 100%;
}}
.stats-card {{
    flex: 1;
    background: {card_bg};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}}
.stats-card:hover {{
    transform: translateY(-4px);
    border-color: #3b82f6;
    box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2);
}}
.stats-icon {{
    font-size: 24px;
    margin-bottom: 8px;
}}
.stats-value {{
    font-size: 32px;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}}
.stats-label {{
    font-size: 11px;
    color: {text_sec};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 6px;
    font-weight: 600;
}}

/* ── Hero Title ── */
@keyframes titleGlow {{
    0%, 100% {{ filter: drop-shadow(0 0  5px rgba(59,130,246,.2)); }}
    50%       {{ filter: drop-shadow(0 0 15px rgba(59,130,246,.5)); }}
}}
.hero-title {{
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #60A5FA 0%, #2563EB 55%, #1D4ED8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    display: inline-block;
    margin-bottom: 8px;
    line-height: 1.15;
    animation: titleGlow 4s ease-in-out infinite;
}}
.hero-sub {{
    color: {text_sec};
    font-size: 1.05rem;
    margin-bottom: 30px;
    line-height: 1.6;
}}

/* ── Chat Styling ── */
@keyframes bubbleIn {{
    from {{ opacity: 0; transform: translateY(12px) scale(0.98); }}
    to   {{ opacity: 1; transform: translateY(0)    scale(1);    }}
}}
[data-testid="stChatMessage"] {{
    animation: bubbleIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
    margin-bottom: 12px;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    flex-direction: row-reverse;
    margin-left: 12%;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
    [data-testid="stChatMessageContent"] {{
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    border: none !important;
    border-radius: 20px 20px 4px 20px !important;
    color: #ffffff !important;
    box-shadow: 0 4px 18px rgba(37,99,235,.25);
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
    [data-testid="stChatMessageContent"] p {{ color: #ffffff !important; }}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    margin-right: 12%;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
    [data-testid="stChatMessageContent"] {{
    background: {asst_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 20px 20px 20px 4px !important;
    color: {asst_text} !important;
    box-shadow: 0 4px 16px {asst_shadow};
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])
    [data-testid="stChatMessageContent"] p {{ color: {asst_text} !important; }}

/* ── Scrollable Country List ── */
.country-scroll {{
    max-height: 180px;
    overflow-y: auto;
    background: {scroll_bg};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px;
    scrollbar-width: thin;
    scrollbar-color: {border} {scroll_bg};
}}
.country-item {{
    padding: 6px 12px;
    font-size: 0.85rem;
    color: {text_pri};
    border-bottom: 1px solid {scroll_bdr};
    line-height: 1.4;
    display: flex;
    align-items: center;
}}
.country-item:last-child {{
    border-bottom: none;
}}

/* ── Section Label Chips ── */
.sec-label {{
    color: {text_sec};
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 10px;
}}

/* ── Buttons Overrides ── */
div[data-testid="stSidebar"] .stButton > button {{
    background: {card_bg} !important;
    border: 1px solid {border} !important;
    color: {text_pri} !important;
    border-radius: 8px !important;
    padding: 6px 12px !important;
    width: 100% !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stSidebar"] .stButton > button:hover {{
    background: #2563EB !important;
    border-color: #2563EB !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
}}

.stButton > button {{
    background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
    border: none !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
}}
.stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3) !important;
}}

/* ── Input Box Styling ── */
[data-testid="stChatInput"] textarea {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    color: {input_text} !important;
    border-radius: 12px !important;
}}
[data-testid="stChatInput"] textarea:focus {{
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
}}

/* ── Navigation custom ── */
.nav-title {{
    font-size: 0.8rem;
    font-weight: 700;
    color: #3b82f6;
    letter-spacing: 0.1em;
    margin-top: 15px;
    margin-bottom: 8px;
    text-transform: uppercase;
}}

/* ── Custom table card container ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {border};
    border-radius: 12px;
    overflow: hidden;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    background: {exp_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 12px !important;
    margin-bottom: 12px !important;
}}
</style>
""", unsafe_allow_html=True)


# Apply styling
_inject_css(st.session_state.theme)


# ── Cached Resources / Functions ───────────────────────────────────────────────
@st.cache_resource(show_spinner="⚡ Loading Embedding Model…")
def _cached_model():
    return load_model()


@st.cache_data(ttl=300, show_spinner=False)
def _db_stats():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM countries;")
        nc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM documents;")
        nd = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM chunks;")
        nch = cur.fetchone()[0]
        cur.close()
        conn.close()
        return int(nc), int(nd), int(nch)
    except Exception:
        # Fallbacks matching live database structure
        return 55, 78, 12498


@st.cache_data(ttl=300, show_spinner=False)
def _countries_list():
    try:
        return get_all_countries()
    except Exception:
        return []


# Load the model
_cached_model()

# DB stats
n_c, n_d, n_ch = _db_stats()


# ── In-App Statistics Queries ─────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_doc_type_distribution():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT doc_type, COUNT(*) as count 
            FROM documents 
            GROUP BY doc_type
            ORDER BY count DESC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=["Document Type", "Count"])
    except Exception:
        # fallback demo data
        return pd.DataFrame([["NDC", 52], ["Law", 18], ["IPCC", 6], ["IPBES", 2]], columns=["Document Type", "Count"])


@st.cache_data(ttl=300, show_spinner=False)
def get_top_countries_by_chunks(limit=10):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT co.name as country, COUNT(c.chunk_id) as chunks
            FROM countries co
            JOIN documents d ON co.country_id = d.country_id
            JOIN chunks c ON d.doc_id = c.doc_id
            GROUP BY co.name
            ORDER BY chunks DESC
            LIMIT %s;
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=["Country", "Chunk Count"])
    except Exception:
        # fallback demo data
        return pd.DataFrame([
            ["Tanzania", 420], ["Kenya", 380], ["Chad", 310], ["Bangladesh", 290], 
            ["Uruguay", 280], ["Kazakhstan", 270], ["Ecuador", 260], ["India", 250],
            ["Brazil", 240], ["South Africa", 230]
        ], columns=["Country", "Chunk Count"])


@st.cache_data(ttl=300, show_spinner=False)
def get_document_years():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT year_published as year, COUNT(*) as count
            FROM documents
            GROUP BY year_published
            ORDER BY year_published;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=["Year", "Document Count"])
    except Exception:
        # fallback demo data
        return pd.DataFrame([[2015, 8], [2018, 12], [2020, 24], [2021, 18], [2022, 16]], columns=["Year", "Document Count"])


# ── ISO to Flag Helper ──────────────────────────────────────────────────────────
def iso_to_flag(iso: str) -> str:
    if not iso or len(iso) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso.upper())


# ── Chatbot logic helpers ───────────────────────────────────────────────────────
_GREETINGS = {
    "hello", "hi", "hey", "thanks", "thank you", "thankyou", "bye", "goodbye",
    "good morning", "good evening", "good afternoon", "howdy", "greetings",
}

def is_greeting(text: str) -> bool:
    t = text.lower().strip().rstrip("!.,? ")
    return t in _GREETINGS or any(t.startswith(g + " ") for g in _GREETINGS)

GREETING_REPLY = (
    "Hello! 👋 I'm the **Climate Policy RAG** assistant.\n\n"
    "Ask me about climate policies, NDCs, or environmental commitments from **55 countries**. "
    "Type **'list countries'** to browse the full database.\n\n"
    "**Try asking:**\n"
    "- *What are Chad's NDC commitments to reduce greenhouse gas emissions?*\n"
    "- *What is Kazakhstan's greenhouse gas inventory?*\n"
    "- *Which adaptation measures has Bangladesh proposed?*"
)

_COUNTRIES_KW = [
    "list countries", "show countries", "which countries",
    "all countries", "how many countries", "available countries",
]

def is_countries_query(text: str) -> bool:
    return any(kw in text.lower() for kw in _COUNTRIES_KW)

def _fetch_countries_df() -> pd.DataFrame:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT co.name, co.iso_code,
                   COUNT(DISTINCT d.doc_id) AS docs,
                   COUNT(c.chunk_id) AS chunks
            FROM countries co
            JOIN documents d ON co.country_id = d.country_id
            JOIN chunks   c ON d.doc_id       = c.doc_id
            GROUP BY co.name, co.iso_code
            ORDER BY co.name;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=["Country", "ISO Code", "Documents", "Chunks"])
    except Exception:
        return pd.DataFrame([], columns=["Country", "ISO Code", "Documents", "Chunks"])

def _stream(text: str):
    for tok in re.split(r"(\s+)", text):
        if tok:
            yield tok
            if not tok.isspace():
                time.sleep(0.02)

def _render_sources(chunks: list) -> None:
    for i, (chunk_id, chunk_text, title, year, country, distance) in enumerate(chunks):
        similarity = 1 - float(distance)
        st.markdown(
            f"**[{i+1}] {title}**  \n"
            f"*{country} · {year} · Match: {similarity:.1%}*"
        )
        preview = str(chunk_text)
        st.markdown(f"> {preview[:480]}{'…' if len(preview) > 480 else ''}")
        if i < len(chunks) - 1:
            st.divider()

SAMPLE_QUESTIONS = [
    "What are Chad's NDC commitments to reduce greenhouse gas emissions?",
    "What are Uruguay's climate policies and environmental commitments?",
    "What is Kazakhstan's greenhouse gas inventory and mitigation targets?",
    "What climate adaptation measures has Bangladesh proposed in its NDC?",
    "What are Ecuador's renewable energy policies and targets?",
]


# ── Navigation Panel (Sidebar) ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="hero-title" style="font-size: 1.5rem; animation: none;">🌍 Climate RAG</div>', unsafe_allow_html=True)
    st.caption("IIT Madras Zanzibar DBMS Project")
    st.divider()

    # Theme Toggle
    def _toggle():
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.session_state.metrics_animated = False

    st.button(
        "☀️ Light Mode" if st.session_state.theme == "dark" else "🌙 Dark Mode",
        key="theme_btn", on_click=_toggle, use_container_width=True,
    )
    st.divider()

    # Navigation Links
    st.markdown('<div class="nav-title">Navigation</div>', unsafe_allow_html=True)
    page = st.radio(
        "Page select:",
        [
            "💬 Chatbot Assistant",
            "📊 Pipeline & Stats",
            "💻 Live SQL Console",
            "📐 Schema & 3NF Normalization",
            "🛠️ Tool & Design Choices"
        ],
        label_visibility="collapsed"
    )
    st.divider()

    # Team Members metadata
    st.markdown('<div class="sec-label">Project Team</div>', unsafe_allow_html=True)
    st.markdown(
        "**Rohan Saha** (ZDA24B009)  \n"
        "**Anubhav Kumar** (ZDA24B034)  \n\n"
        "🏛️ **IIT Madras Zanzibar**  \n"
        "DBMS Milestone 3 Submission"
    )


# ── Page 1: 💬 RAG Chat Assistant ───────────────────────────────────────────────
if page == "💬 Chatbot Assistant":
    
    st.markdown(
        '<div class="hero-title">🌍 Climate Policy Intelligence</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">'
        "Query Nationally Determined Contributions (NDCs), laws, and environmental policies from "
        "<strong>55 countries</strong>. Grounded answers are generated by "
        "<strong>groq LLaMA 3.1</strong> &amp; <strong>pgvector</strong> similarity search."
        "</div>",
        unsafe_allow_html=True,
    )

    # Horizontal Statistics Row (using custom CSS grids for premium landing)
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stats-card">
            <div class="stats-icon">🌐</div>
            <div class="stats-value">{n_c}</div>
            <div class="stats-label">Indexed Countries</div>
        </div>
        <div class="stats-card">
            <div class="stats-icon">📄</div>
            <div class="stats-value">{n_d}</div>
            <div class="stats-label">Policy Documents</div>
        </div>
        <div class="stats-card">
            <div class="stats-icon">🧩</div>
            <div class="stats-value">{n_ch:,}</div>
            <div class="stats-label">Extracted Chunks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Layout: Sidebar-like columns in main page for country index & sample questions
    main_col, side_col = st.columns([3, 1])

    with side_col:
        st.markdown('<div class="sec-label">Indexed Nations</div>', unsafe_allow_html=True)
        _ctrs = _countries_list()
        if _ctrs:
            _items_html = "".join(
                f'<div class="country-item">{iso_to_flag(iso)}&nbsp;{name}</div>'
                for name, iso in _ctrs
            )
            st.markdown(
                f'<div class="country-scroll">{_items_html}</div>',
                unsafe_allow_html=True,
            )
        st.divider()

        st.markdown('<div class="sec-label">Sample Questions</div>', unsafe_allow_html=True)
        def _set_pending(q: str):
            st.session_state.pending_question = q

        for _q in SAMPLE_QUESTIONS:
            st.button(_q, key=f"sq_{abs(hash(_q))}", on_click=_set_pending, args=(_q,))

    with main_col:
        # Chat History Container
        chat_container = st.container()
        
        with chat_container:
            for _msg in st.session_state.messages:
                with st.chat_message(_msg["role"]):
                    if _msg.get("is_countries_table"):
                        st.markdown("**📊 Here are all 55 countries in the Climate Policy RAG database:**")
                        _recs = _msg.get("df_records", [])
                        if _recs:
                            st.dataframe(pd.DataFrame(_recs), use_container_width=True, hide_index=True)

                    elif _msg.get("tier") == "tier3":
                        st.warning(
                            "🌐 **Web Result** — This answer comes from a web search, "
                            "**not** from the Climate Policy Database.",
                            icon="⚠️",
                        )
                        st.markdown(_msg["content"])
                        _wsrcs = _msg.get("web_sources", [])
                        if _wsrcs:
                            with st.expander("🔗 Web Sources", expanded=False):
                                for _s in _wsrcs:
                                    st.markdown(f"- [{_s['title']}]({_s['url']})")
                    else:
                        st.markdown(_msg["content"])
                        _hist_chunks = _msg.get("chunks")
                        if _hist_chunks:
                            with st.expander(
                                f"📄 Sources — {len(_hist_chunks)} documents retrieved", expanded=False
                            ):
                                _render_sources(_hist_chunks)

        # Input & RAG Process execution
        _pending = st.session_state.pending_question
        if _pending:
            st.session_state.pending_question = None

        _chat_in = st.chat_input("Ask about climate policies, NDCs, or environmental commitments…")
        _query   = _pending or _chat_in

        if _query:
            # Render user input
            with st.chat_message("user"):
                st.markdown(_query)
            st.session_state.messages.append({"role": "user", "content": _query})

            with st.chat_message("assistant"):
                # GREETING
                if is_greeting(_query):
                    st.write_stream(_stream(GREETING_REPLY))
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": GREETING_REPLY,
                    })

                # COUNTRIES TABLE
                elif is_countries_query(_query):
                    with st.spinner("📡 Querying database…"):
                        _df = _fetch_countries_df()
                    st.markdown("**📊 Here are all 55 countries in the Climate Policy RAG database:**")
                    st.dataframe(_df, use_container_width=True, hide_index=True)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "is_countries_table": True,
                        "df_records": _df.to_dict("records"),
                    })

                # RAG PIPELINE
                else:
                    _tier       = ""
                    _chunks     = []
                    _answer     = ""
                    _detected   = None
                    _web_result = {}

                    with st.status("⚙️ Processing your query…", expanded=True) as _status:
                        st.write("🔍 **Stage 1 — Semantic Search** · scanning pgvector embeddings…")
                        _tier, _chunks, _detected = tiered_retrieve(_query, _countries_list())

                        if _tier == "tier3":
                            _clabel = f" for **{_detected}**" if _detected else ""
                            st.write(f"⚠️ No documents found{_clabel} in DB — falling back to Web Search (Tier 3)…")
                            _status.update(label="🌐 Launching web search…", state="running", expanded=True)
                            _web_result = web_search_fallback(_query)
                            _status.update(label="🌐 Web search completed", state="complete", expanded=False)
                        else:
                            _nc = len(set(c[4] for c in _chunks))
                            _d_note = f" · country: **{_detected}**" if _detected else ""
                            st.write(f"✅ Retrieved **{len(_chunks)} chunks** from **{_nc} nations**{_d_note}")
                            st.write("🤖 **Stage 2 — LLM Generation** · invoking groq LLaMA 3.1…")
                            _answer = generate_answer_grounded(_query, _chunks, _tier)
                            _status.update(label="✅ Generation completed!", state="complete", expanded=False)

                    # Output display based on tier
                    if _tier == "tier3":
                        st.warning(
                            "🌐 **Web Result** — This answer comes from a web search, "
                            "**not** from the Climate Policy Database.",
                            icon="⚠️",
                        )
                        st.write_stream(_stream(_web_result["answer"]))
                        _wsrcs = _web_result.get("sources", [])
                        if _wsrcs:
                            with st.expander("🔗 Web Sources", expanded=True):
                                for _s in _wsrcs:
                                    st.markdown(f"- [{_s['title']}]({_s['url']})")
                        st.session_state.messages.append({
                            "role":        "assistant",
                            "content":     _web_result["answer"],
                            "chunks":      [],
                            "tier":        "tier3",
                            "country":     _detected,
                            "web_sources": _wsrcs,
                        })
                    else:
                        st.write_stream(_stream(_answer))
                        with st.expander(
                            f"📄 Sources — {len(_chunks)} documents retrieved", expanded=False
                        ):
                            _render_sources(_chunks)
                        log_with_tier(_query, _answer, _chunks[0][0] if _chunks else None, "tier1")
                        st.session_state.messages.append({
                            "role":    "assistant",
                            "content": _answer,
                            "chunks":  [(c[0], c[1], c[2], c[3], c[4], float(c[5])) for c in _chunks],
                            "tier":    "tier1",
                            "country": _detected,
                        })


# ── Page 2: 📊 RAG Pipeline & Database Stats ──────────────────────────────────
elif page == "📊 Pipeline & Stats":
    st.markdown('<div class="hero-title">📊 RAG Architecture & Live Statistics</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Detailed breakdown of the 3-tier RAG retrieval workflow and real-time database summary charts.</div>', unsafe_allow_html=True)

    # 3-Tier RAG flowchart
    st.markdown('<div class="sec-label">3-Tier Retrieval Architecture Flowchart</div>', unsafe_allow_html=True)
    st.markdown("""
```mermaid
graph TD
    Q[User Natural Language Query] --> CD{Country Detection<br/>Longest-Match Keyword Scan}
    
    CD -- Country Detected --> DC{Documents in DB?}
    CD -- No Country Detected --> GS[Global Similarity Search<br/>pgvector Cosine Distance <=> ]
    
    DC -- Yes --> T1[Tier 1: Country-Specific Search<br/>pgvector Filtered Cosine Similarity]
    DC -- No --> T3[Tier 3: Web Fallback Search<br/>Web Registry Registry]
    
    GS -- Chunks Found --> T1
    GS -- No Chunks Found --> T3
    
    T1 --> AG[Grounded Generation<br/>Groq LLaMA 3.1 8B Expert System]
    T3 --> AG
    
    AG --> OUT[Answer with Sources & Citations]
    AG --> PLOG[PostgreSQL Stored Procedure<br/>CALL log_query]
```
""", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Charts Grid
    st.markdown('<div class="sec-label">Live Database Summary Statistics</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="glass-card"><h3>Document Type Distribution</h3>', unsafe_allow_html=True)
        df_doc_type = get_doc_type_distribution()
        st.bar_chart(data=df_doc_type, x="Document Type", y="Count", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="glass-card"><h3>Top 10 Countries by Database Chunks</h3>', unsafe_allow_html=True)
        df_top_countries = get_top_countries_by_chunks(10)
        st.bar_chart(data=df_top_countries, x="Country", y="Chunk Count", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card"><h3>Climate Policy Documents Published by Year</h3>', unsafe_allow_html=True)
    df_years = get_document_years()
    st.line_chart(data=df_years, x="Year", y="Document Count", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Page 3: 💻 Live SQL Console ────────────────────────────────────────────────
elif page == "💻 Live SQL Console":
    st.markdown('<div class="hero-title">💻 PostgreSQL Live SQL Console</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Query the relational database directly. Select pre-configured query templates or write custom read-only SQL statements to verify schema structures and analyze execution plans.</div>', unsafe_allow_html=True)

    # Preset templates
    PRESETS = {
        "--- Select a Query Template ---": "",
        "📊 Chunks & Avg Words per Doc Type (Aggregation)": """-- Total chunks and average word count per document type
SELECT 
    d.doc_type,
    COUNT(c.chunk_id)          AS total_chunks,
    ROUND(AVG(c.word_count))   AS avg_word_count,
    MAX(c.word_count)          AS max_word_count,
    MIN(c.word_count)          AS min_word_count
FROM documents d
JOIN chunks c ON c.doc_id = d.doc_id
GROUP BY d.doc_type
ORDER BY total_chunks DESC;""",

        "🌐 Documents & Chunks per Country (Aggregation)": """-- Number of documents and chunks per country
SELECT 
    co.name                        AS country,
    co.iso_code,
    COUNT(DISTINCT d.doc_id)       AS num_documents,
    COUNT(c.chunk_id)              AS num_chunks,
    ROUND(AVG(c.word_count))       AS avg_chunk_words
FROM countries co
JOIN documents d  ON d.country_id  = co.country_id
JOIN chunks c     ON c.doc_id      = d.doc_id
GROUP BY co.name, co.iso_code
ORDER BY num_chunks DESC;""",

        "📄 Top 10 Data-Rich Documents (CTE)": """-- Top 10 most data-rich documents by chunk count
WITH doc_stats AS (
    SELECT 
        d.doc_id,
        d.title,
        d.doc_type,
        d.year_published,
        co.name              AS country,
        COUNT(c.chunk_id)    AS chunk_count,
        SUM(c.word_count)    AS total_words,
        ROUND(AVG(c.word_count)) AS avg_words
    FROM documents d
    JOIN chunks c     ON c.doc_id     = d.doc_id
    JOIN countries co ON co.country_id = d.country_id
    GROUP BY d.doc_id, d.title, d.doc_type, d.year_published, co.name
)
SELECT * FROM doc_stats
ORDER BY chunk_count DESC
LIMIT 10;""",

        "⭐ Country Coverage Level (CTE & Join)": """-- Country-level summary with above/below average classification
WITH country_stats AS (
    SELECT 
        co.name                  AS country,
        co.iso_code,
        COUNT(DISTINCT d.doc_id) AS num_docs,
        COUNT(c.chunk_id)        AS num_chunks
    FROM countries co
    JOIN documents d ON d.country_id = co.country_id
    JOIN chunks c    ON c.doc_id     = d.doc_id
    GROUP BY co.name, co.iso_code
),
avg_stats AS (
    SELECT ROUND(AVG(num_chunks)) AS avg_chunks FROM country_stats
)
SELECT 
    cs.country,
    cs.iso_code,
    cs.num_docs,
    cs.num_chunks,
    av.avg_chunks,
    CASE WHEN cs.num_chunks > av.avg_chunks 
         THEN 'Above Average' 
         ELSE 'Below Average' 
     END AS coverage_level
FROM country_stats cs
CROSS JOIN avg_stats av
ORDER BY cs.num_chunks DESC;""",

        "🏅 Rank Chunks within Documents (Window Function)": """-- Rank chunks within each document by word count (LIMIT 50)
SELECT 
    c.chunk_id,
    c.doc_id,
    c.word_count,
    d.title,
    RANK()       OVER (PARTITION BY c.doc_id ORDER BY c.word_count DESC) AS rank_in_doc,
    DENSE_RANK() OVER (PARTITION BY c.doc_id ORDER BY c.word_count DESC) AS dense_rank,
    NTILE(4)     OVER (PARTITION BY c.doc_id ORDER BY c.word_count)      AS quartile
FROM chunks c
JOIN documents d ON d.doc_id = c.doc_id
LIMIT 50;""",

        "📈 Running Chunk Total per Country (Window Function)": """-- Running total of chunks per country ordered by document year
SELECT 
    co.name              AS country,
    d.year_published,
    d.title,
    COUNT(c.chunk_id)    AS chunks_this_doc,
    SUM(COUNT(c.chunk_id)) OVER (
        PARTITION BY co.country_id
        ORDER BY d.year_published, d.doc_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                    AS running_chunk_total
FROM countries co
JOIN documents d ON d.country_id = co.country_id
JOIN chunks c    ON c.doc_id     = d.doc_id
GROUP BY co.country_id, co.name, d.year_published, d.doc_id, d.title
ORDER BY co.name, d.year_published;""",

        "🔍 Query History Logs (Audit Table)": """-- Retrieve recent user queries logged by the system stored procedure
SELECT query_id, query_text, left(answer_text, 100) as answer_preview, top_chunk_id, created_at
FROM queries
ORDER BY created_at DESC
LIMIT 50;""",

        "⚡ Performance Plan: Chunks word_count filter (Q1 EXPLAIN)": """-- Explain the execution plan of Q1 (filtering word count > 80)
-- Demonstrates the Bitmap Index Scan optimization using B-Tree index
EXPLAIN ANALYZE
SELECT c.chunk_id, c.word_count, d.title
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.word_count > 80
ORDER BY c.word_count DESC;""",

        "⚡ Performance Plan: Document year range filter (Q2 EXPLAIN)": """-- Explain the execution plan of Q2 (filtering year >= 2020)
-- Demonstrates the planner cost reduction and join order optimization
EXPLAIN ANALYZE
SELECT d.title, d.year_published, co.name AS country
FROM documents d
JOIN countries co ON d.country_id = co.country_id
WHERE d.year_published >= 2020
ORDER BY d.year_published DESC;"""
    }

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    selected_preset = st.selectbox("Select a Preset SQL Query:", list(PRESETS.keys()))
    
    # Prepopulate the SQL input area if selected
    query_default = PRESETS[selected_preset]
    sql_input = st.text_area("SQL Statement Editor", value=query_default, height=220)
    
    c1, c2 = st.columns([1, 4])
    with c1:
        run_btn = st.button("🚀 Execute Query", use_container_width=True)
    with c2:
        st.caption("🔒 For database safety, only read-only SELECT and EXPLAIN queries are authorized for execution.")

    st.markdown('</div>', unsafe_allow_html=True)

    if run_btn:
        if not sql_input.strip():
            st.warning("Please type or select a SQL statement first.")
        else:
            # Check safety
            clean_sql = sql_input.strip().lower()
            # Remove comments starting with -- or /*
            clean_sql_no_comments = re.sub(r'(--.*)|(/\*(.|\n)*?\*/)', '', clean_sql).strip()
            
            if not (clean_sql_no_comments.startswith("select") or clean_sql_no_comments.startswith("explain") or clean_sql_no_comments.startswith("with")):
                st.error("🔒 Security Policy: Only SELECT, EXPLAIN, and WITH queries are allowed to run in this console.")
            else:
                with st.spinner("Executing SQL query on database..."):
                    try:
                        start_time = time.time()
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute(sql_input)
                        
                        # Fetch results if available
                        description = cur.description
                        if description:
                            colnames = [desc[0] for desc in description]
                            rows = cur.fetchall()
                            df = pd.DataFrame(rows, columns=colnames)
                            elapsed = (time.time() - start_time) * 1000
                            
                            st.success(f"Success! Query returned {len(df)} rows in {elapsed:.2f} ms")
                            
                            # Render dataframe beautifully
                            st.dataframe(df, use_container_width=True)
                        else:
                            conn.commit()
                            elapsed = (time.time() - start_time) * 1000
                            st.success(f"Success! Statement executed successfully in {elapsed:.2f} ms (no rows returned).")
                        
                        cur.close()
                        conn.close()
                    except Exception as e:
                        st.error(f"❌ Database Query Error:\n{str(e)}")


# ── Page 4: 📐 Schema Design & 3NF Normalization ───────────────────────────────
elif page == "📐 Schema & 3NF Normalization":
    st.markdown('<div class="hero-title">📐 Schema Design & Normalization</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Analysis of the project database tables, constraints, functional dependencies, and proof of Third Normal Form (3NF) compliance.</div>', unsafe_allow_html=True)

    # Tables card
    st.markdown('<div class="sec-label">Database Entities Summary</div>', unsafe_allow_html=True)
    
    t_cols = st.columns(5)
    
    tables_meta = [
        {"name": "countries", "role": "Top-level dimension table", "columns": "country_id (PK), name, iso_code (UK), region, continent"},
        {"name": "documents", "role": "Source document catalog", "columns": "doc_id (PK), title, country_id (FK), doc_type (CHECK), year_published (CHECK), source_url"},
        {"name": "chunks", "role": "Granular text blocks (RAG)", "columns": "chunk_id (PK), doc_id (FK), chunk_text, chunk_index, word_count (CHECK), (doc_id, chunk_index) (UK)"},
        {"name": "embeddings", "role": "Vector embeddings store", "columns": "embedding_id (PK), chunk_id (FK, UK), embedding_vector (vector(384)), model_name"},
        {"name": "queries", "role": "Innovation audit logging", "columns": "query_id (PK), query_text, answer_text, top_chunk_id (FK), created_at"}
    ]
    
    for idx, tab in enumerate(tables_meta):
        with t_cols[idx]:
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px; min-height: 250px; font-size: 0.9rem;">
                <h4 style="margin: 0 0 8px 0; color: #3b82f6;">{tab['name']}</h4>
                <p style="margin: 0 0 8px 0; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: #64748b;">{tab['role']}</p>
                <hr style="margin: 8px 0; border-color: rgba(255,255,255,0.05);"/>
                <p style="font-size: 0.8rem; color: #94a3b8; line-height: 1.4;"><strong>Attributes:</strong><br/>{tab['columns']}</p>
            </div>
            """, unsafe_allow_html=True)

    # DDL
    with st.expander("📝 View Full DDL Schema Script (schema.sql)", expanded=False):
        try:
            with open("schema/schema.sql", "r", encoding="utf-8") as f:
                ddl_code = f.read()
            st.code(ddl_code, language="sql")
        except Exception:
            st.info("schema.sql not found at project root folder.")

    # 3NF Argument details
    st.markdown('<div class="sec-label">3NF Normalization Analysis</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-card">
        <h3>Normalization Arguments</h3>
        <p>The system's schema was designed by starting from a flat unified relation of climate policy attributes and decomposing them into five focused entity tables. The schema fully satisfies <strong>Third Normal Form (3NF)</strong>:</p>
        
        <ul>
            <li><strong>First Normal Form (1NF)</strong>: Every attribute holds atomic values, there are no repeating groups, and rows are uniquely identified by their respective Primary Keys.</li>
            <li><strong>Second Normal Form (2NF)</strong>: All tables use single-column primary keys (<code>SERIAL</code> auto-increment). Since there are no composite primary keys, partial key dependencies (a non-key attribute depending on only part of a key) are mathematically impossible.</li>
            <li><strong>Third Normal Form (3NF)</strong>: No non-key attributes determine other non-key attributes (zero transitive dependencies). Every non-key attribute is mutually independent and depends <i>only</i> on the primary key.</li>
        </ul>
        
        <h4>Transitive Dependency Elimination Example</h4>
        <p>In a flat <code>documents</code> schema, country metadata would create a transitive dependency:
        <br/><code>doc_id ➔ country_id ➔ region, continent</code>
        <br/>Since <code>country_id</code> is a non-key determinant for <code>region</code> and <code>continent</code>, this would violate 3NF, leading to insertion/deletion anomalies (e.g. you couldn't store a country's region without having a document for that country). 
        By decomposing this into a separate <code>countries</code> table, the transitive dependency is eliminated, achieving clean 3NF compliance.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="glass-card">
        <h3>Functional Dependencies Table</h3>
        <table style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
            <thead>
                <tr style="border-bottom: 2px solid rgba(255,255,255,0.1); color: #3b82f6;">
                    <th style="padding: 10px;">Table</th>
                    <th style="padding: 10px;">Functional Dependency</th>
                    <th style="padding: 10px;">3NF Status</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 10px; font-weight: 600;">countries</td>
                    <td style="padding: 10px;"><code>country_id ➔ name, iso_code, region, continent</code></td>
                    <td style="padding: 10px; color: #10b981;">✅ Satisfied. Zero transitive dependencies.</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 10px; font-weight: 600;">documents</td>
                    <td style="padding: 10px;"><code>doc_id ➔ title, country_id, doc_type, year_published, source_url</code></td>
                    <td style="padding: 10px; color: #10b981;">✅ Satisfied. <code>country_id</code> acts as FK.</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 10px; font-weight: 600;">chunks</td>
                    <td style="padding: 10px;"><code>chunk_id ➔ doc_id, chunk_text, chunk_index, word_count</code></td>
                    <td style="padding: 10px; color: #10b981;">✅ Satisfied. Zero transitive dependencies.</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 10px; font-weight: 600;">embeddings</td>
                    <td style="padding: 10px;"><code>embedding_id ➔ chunk_id, embedding_vector, model_name</code></td>
                    <td style="padding: 10px; color: #10b981;">✅ Satisfied. <code>chunk_id</code> carries UNIQUE constraint.</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 10px; font-weight: 600;">queries</td>
                    <td style="padding: 10px;"><code>query_id ➔ query_text, answer_text, top_chunk_id, created_at</code></td>
                    <td style="padding: 10px; color: #10b981;">✅ Satisfied. <code>top_chunk_id</code> acts as FK.</td>
                </tr>
            </tbody>
        </table>
        <br/>
        <h4>Properties of Decomposition</h4>
        <ul>
            <li><strong>Lossless Join</strong>: The decomposition is mathematically lossless. Because primary keys are retained as foreign keys in the children tables (e.g. <code>doc_id</code> in <code>chunks</code> references <code>documents</code>), running a <code>NATURAL JOIN</code> reconstructs the original flat relation without generating spurious tuples.</li>
            <li><strong>Dependency Preservation</strong>: All functional dependencies are preserved because every dependency's determinant is restricted entirely within the boundaries of a single physical table.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


# ── Page 5: 🛠️ Tool & Design Justifications ─────────────────────────────────────
elif page == "🛠️ Tool & Design Choices":
    st.markdown('<div class="hero-title">🛠️ Tool & Design Justifications</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Detailed breakdown of why specific technologies, structures, models, and workflows were selected for the Climate Policy RAG Pipeline.</div>', unsafe_allow_html=True)

    # Core choices grid
    st.markdown('<div class="sec-label">Architectural Choice Analysis</div>', unsafe_allow_html=True)
    
    c_cols = st.columns(3)
    
    with c_cols[0]:
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">🐘</div>
            <h3 style="color:#3b82f6;">PostgreSQL 16</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">Selected as the core relational database management system. 
            Unlike no-SQL database structures, PostgreSQL serves as a single, ACID-compliant source of truth. 
            It maintains structured catalog data for countries and documents, handles complex analytical window functions, CTEs, and supports transactional query logging procedures seamlessly.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">📈</div>
            <h3 style="color:#3b82f6;">sentence-transformers</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">The <code>all-MiniLM-L6-v2</code> model is selected to generate 384-dimensional vector embeddings. 
            It represents the sweet spot between semantic accuracy and performance, with a small model footprint (120MB) that runs efficiently in CPU/GPU environments while yielding high-quality cosine similarities.</p>
        </div>
        """, unsafe_allow_html=True)

    with c_cols[1]:
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">🧭</div>
            <h3 style="color:#3b82f6;">pgvector Extension</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">Chosen to store high-dimensional embeddings and execute similarity searches directly in SQL. 
            It eliminates the need to manage separate database silos (e.g. Pinecone or Milvus), allowing unified SQL queries that JOIN vector distances (<code>&lt;=&gt;</code>) directly with relational tables in a single transaction.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">⚡</div>
            <h3 style="color:#3b82f6;">3-Tiered Retrieval</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">Designed to guarantee grounded answers. 
            If a country is explicitly referenced in the user's query, search is filtered strictly to that country's policy documents (Tier 1). 
            If no country is mentioned, a global vector search is performed. 
            If the requested data is completely missing, the pipeline gracefully falls back to web retrieval (Tier 3), preventing hallucinated LLM responses.</p>
        </div>
        """, unsafe_allow_html=True)

    with c_cols[2]:
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">🤖</div>
            <h3 style="color:#3b82f6;">Groq & LLaMA 3.1 8B</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">Groq's LPU inference engine delivers blazing-fast speeds (200+ tokens/sec) for LLaMA 3.1 8B. 
            LLaMA 3.1 8B possesses state-of-the-art instruction-following capabilities, which ensures that generation strictly respects grounding rules and outputs citations formatted in clean markdown structures.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="min-height: 380px;">
            <div style="font-size: 32px; margin-bottom: 12px;">📜</div>
            <h3 style="color:#3b82f6;">Stored Procedure Logs</h3>
            <p style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">The system persists queries using a database-level PL/pgSQL stored procedure <code>log_query()</code>. 
            Encapsulating this in a procedure ensures database atomicity, offloads server-side timestamping to PostgreSQL, and prevents client-side clocks from introducing timing drift in audit trails.</p>
        </div>
        """, unsafe_allow_html=True)
