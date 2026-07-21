"""Riverstone Family Health — AI Front-Desk Agent demo.

Run:  streamlit run app.py
Requires GEMINI_API_KEY in a .env file (see .env.example) or pasted in the sidebar.
"""

import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import ClinicAgent
from tools import APPOINTMENTS_PATH

load_dotenv()

st.set_page_config(
    page_title="Riverstone Family Health — AI Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- styling

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Lora:ital,wght@0,600;1,500&display=swap');

    :root {
        --ink:      #0d2b36;
        --navy:     #0f3d4c;
        --teal:     #1c7d8c;
        --teal-lt:  #2196a3;
        --mint:     #4fb3a9;
        --bg-top:   #eef6f6;
        --bg-bot:   #e3eef1;
        --card:     #ffffff;
        --line:     #e1ecee;
        --muted:    #5c7982;
    }

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    .stApp {
        background:
            radial-gradient(1200px 500px at 15% -10%, rgba(33,150,163,0.10), transparent),
            radial-gradient(900px 500px at 100% 0%, rgba(79,179,169,0.10), transparent),
            linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bot) 100%);
    }

    #MainMenu, footer { visibility: hidden; }
    div.block-container { padding-top: 1.6rem; max-width: 900px; }

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(195deg, #0a2c38 0%, #0f3d4c 55%, #124a5a 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] * { color: #e8f1f2 !important; }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12); margin: 1.1rem 0; }
    section[data-testid="stSidebar"] .stTextInput input {
        background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.18);
        border-radius: 8px; color: #fff !important;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.22);
        border-radius: 9px; font-weight: 500; transition: all 0.15s ease;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.18); border-color: rgba(255,255,255,0.35);
    }

    .brand-row { display: flex; align-items: center; gap: 12px; margin-bottom: 2px; }
    .brand-mark {
        width: 42px; height: 42px; border-radius: 12px; flex-shrink: 0;
        background: linear-gradient(135deg, var(--teal-lt), var(--mint));
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; box-shadow: 0 3px 10px rgba(0,0,0,0.25);
    }
    .brand-name { font-weight: 700; font-size: 1.05rem; line-height: 1.2; margin: 0; }
    .brand-sub { font-size: 0.74rem; color: #9fc3ca !important; margin: 0; letter-spacing: 0.02em; }

    .side-info { font-size: 0.85rem; line-height: 1.9; color: #d3e8ea !important; }
    .side-label {
        text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.68rem !important;
        color: #7fb0b8 !important; font-weight: 600; margin-bottom: 6px;
    }

    /* ---------- hero ---------- */
    .clinic-hero {
        background: linear-gradient(135deg, #0c3644 0%, #146475 55%, #1f95a4 100%);
        border-radius: 20px;
        padding: 34px 38px;
        color: white;
        margin-bottom: 22px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 14px 34px rgba(12, 54, 68, 0.28);
    }
    .clinic-hero::after {
        content: ""; position: absolute; top: -60px; right: -60px;
        width: 220px; height: 220px; border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.10), transparent 70%);
    }
    .hero-eyebrow {
        text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.72rem;
        color: #a9e0e2; font-weight: 600; margin-bottom: 8px;
    }
    .clinic-hero h1 {
        color: white; font-family: 'Lora', serif; font-weight: 600;
        font-size: 2.05rem; margin: 0 0 8px 0; letter-spacing: -0.01em;
    }
    .clinic-hero p { color: #d3edee; margin: 0; font-size: 1.03rem; max-width: 560px; line-height: 1.5; }
    .hero-badges { margin-top: 18px; display: flex; flex-wrap: wrap; gap: 8px; }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.12); backdrop-filter: blur(4px);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px; padding: 6px 15px;
        font-size: 0.8rem; color: #ffffff; font-weight: 500;
    }

    /* ---------- chat ---------- */
    div[data-testid="stChatMessage"] {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        box-shadow: 0 2px 10px rgba(15, 61, 76, 0.06);
        margin-bottom: 10px;
        padding: 4px 2px;
    }
    div[data-testid="stChatMessageAvatarUser"] {
        background: linear-gradient(135deg, #345a68, #1d3b46) !important;
    }
    div[data-testid="stChatMessageAvatarCustom"] {
        background: linear-gradient(135deg, var(--teal-lt), var(--mint)) !important;
    }
    [data-testid="stChatInput"] {
        border-radius: 14px; border: 1px solid var(--line);
        box-shadow: 0 2px 10px rgba(15, 61, 76, 0.06);
    }

    .tool-event {
        display: inline-flex; align-items: center; gap: 4px;
        background: #eaf7f0; color: #1a7a48;
        border: 1px solid #c3e9d3; border-radius: 999px;
        padding: 3px 12px; margin: 3px 6px 0 0; font-size: 0.76rem; font-weight: 500;
    }
    .src-label {
        text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.68rem;
        color: var(--muted); font-weight: 600;
    }

    .disclaimer {
        color: var(--muted); font-size: 0.76rem; text-align: center;
        margin-top: 22px; padding-top: 14px; border-top: 1px solid var(--line);
    }

    /* ---------- appointment cards ---------- */
    .appt-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.14);
        border-left: 3px solid var(--mint);
        border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;
        font-size: 0.8rem; line-height: 1.6;
    }
    .appt-ref {
        color: #7fe0d4 !important; font-weight: 700; font-size: 0.78rem;
        letter-spacing: 0.02em;
    }
    .appt-status {
        float: right; font-size: 0.68rem; text-transform: uppercase;
        letter-spacing: 0.04em; color: #f0c987 !important; font-weight: 600;
    }
    .appt-name { font-weight: 600; color: #fff !important; }
    .appt-meta { color: #b9d3d6 !important; font-size: 0.76rem; }

    /* ---------- suggestion chips ---------- */
    div[data-testid="column"] .stButton button {
        background: var(--card); border: 1px solid var(--line);
        border-radius: 12px; padding: 0.6rem 0.8rem; font-size: 0.86rem;
        color: var(--ink); font-weight: 500; text-align: left;
        box-shadow: 0 1px 4px rgba(15,61,76,0.05);
        transition: all 0.15s ease;
    }
    div[data-testid="column"] .stButton button:hover {
        border-color: var(--teal-lt); color: var(--teal);
        box-shadow: 0 4px 12px rgba(33,150,163,0.15);
        transform: translateY(-1px);
    }

    .section-label {
        font-size: 0.78rem; font-weight: 600; color: var(--muted);
        text-transform: uppercase; letter-spacing: 0.08em; margin: 4px 0 10px 2px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- helpers

GREETING = (
    "Hi there! 👋 I'm **Riva**, the virtual assistant for Riverstone Family Health "
    "in Austin, TX. I can answer questions about our services, hours, insurance, "
    "and pricing — and I can help you **book an appointment** right here in chat. "
    "How can I help you today?"
)

SUGGESTED = [
    "📅 Book an appointment",
    "🛡️ Do you take Blue Cross Blue Shield?",
    "💵 What does a visit cost without insurance?",
    "🕐 What are your weekend hours?",
]


def get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key_input") or None


@st.cache_resource(show_spinner="Indexing clinic knowledge base…")
def get_agent(api_key: str) -> ClinicAgent:
    return ClinicAgent(api_key)


def load_appointments() -> list[dict]:
    if APPOINTMENTS_PATH.exists():
        try:
            return json.loads(APPOINTMENTS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


if "messages" not in st.session_state:
    # display roles: "user" / "assistant"; model roles mapped later
    st.session_state.messages = [{"role": "assistant", "text": GREETING}]

# ---------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown(
        """<div class="brand-row">
            <div class="brand-mark">🩺</div>
            <div>
                <p class="brand-name">Riverstone Family Health</p>
                <p class="brand-sub">Primary Care & Family Medicine</p>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """<div class="side-info" style="margin-top:14px">
            📍 4820 Guadalupe St, Suite 200<br>&nbsp;&nbsp;&nbsp;Austin, TX 78751<br>
            📞 (512) 555-0142<br>
            🕐 Mon–Fri 8 AM–5 PM · Sat 9 AM–1 PM
        </div>""",
        unsafe_allow_html=True,
    )
    st.divider()

    if not os.getenv("GEMINI_API_KEY"):
        st.markdown('<p class="side-label">Gemini API Key</p>', unsafe_allow_html=True)
        st.text_input(
            "Gemini API key",
            type="password",
            key="api_key_input",
            label_visibility="collapsed",
            help="Paste a Gemini API key, or set GEMINI_API_KEY in a .env file.",
        )
        st.divider()

    st.markdown('<p class="side-label">🗂️ Front Desk View</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="side-info" style="opacity:0.8">Appointment requests captured live by the AI agent</p>',
        unsafe_allow_html=True,
    )
    appointments = load_appointments()
    if not appointments:
        st.markdown(
            '<p class="side-info" style="opacity:0.6"><i>No requests yet — try booking '
            'one in the chat!</i></p>',
            unsafe_allow_html=True,
        )
    else:
        for appt in reversed(appointments[-5:]):
            st.markdown(
                f"""<div class="appt-card">
                <span class="appt-ref">{appt['reference']}</span>
                <span class="appt-status">{appt['status']}</span>
                <div class="appt-name" style="margin-top:6px">{appt['full_name']}</div>
                <div class="appt-meta">{appt['phone']}</div>
                <div class="appt-meta">{appt['reason']}</div>
                <div class="appt-meta">📅 {appt['preferred_date']} · {appt['preferred_time']} · {appt['visit_type']}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.divider()
    if st.button("🔄 Reset conversation", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "text": GREETING}]
        st.rerun()

    st.markdown(
        '<p class="side-info" style="opacity:0.55; font-size:0.72rem; margin-top:12px">'
        'Demo build — all clinic data shown is synthetic.</p>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------- header

st.markdown("""
<div class="clinic-hero">
    <div class="hero-eyebrow">AI Front Desk Assistant</div>
    <h1>Meet Riva — your clinic, answering itself.</h1>
    <p>An AI agent that answers patient questions, checks insurance, and books
    appointments directly in chat — grounded entirely in Riverstone's own policies,
    24 hours a day.</p>
    <div class="hero-badges">
        <span class="hero-badge">🤖 Real AI agent, not a script</span>
        <span class="hero-badge">📅 Books appointments in chat</span>
        <span class="hero-badge">🔒 HIPAA-aware guardrails</span>
        <span class="hero-badge">🌐 English · Español · 中文</span>
    </div>
</div>
""", unsafe_allow_html=True)

api_key = get_api_key()
if not api_key:
    st.info(
        "👈 **Setup:** paste your Gemini API key in the sidebar (or create a `.env` "
        "file from `.env.example`) to start the demo.",
        icon="🔑",
    )
    st.stop()

# ---------------------------------------------------------------- chat history

for msg in st.session_state.messages:
    avatar = "🩺" if msg["role"] == "assistant" else "🙂"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["text"])
        if msg.get("tool_events"):
            st.markdown(
                "".join(f'<span class="tool-event">{e}</span>' for e in msg["tool_events"]),
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------- suggested chips

pending = None
if len(st.session_state.messages) <= 1:
    st.markdown('<p class="section-label">Try asking</p>', unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTED))
    for col, suggestion in zip(cols, SUGGESTED):
        if col.button(suggestion, use_container_width=True):
            pending = suggestion.split(" ", 1)[1]
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- input & response

user_input = st.chat_input("Ask about services, insurance, pricing — or book a visit…")
prompt = user_input or pending

if prompt:
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user", avatar="🙂"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🩺"):
        with st.spinner("Riva is thinking…"):
            try:
                agent = get_agent(api_key)
                history = [
                    {"role": "model" if m["role"] == "assistant" else "user", "text": m["text"]}
                    for m in st.session_state.messages[:-1]
                ]
                result = agent.respond(history, prompt)
            except Exception as exc:
                result = {
                    "text": "I'm sorry — something went wrong on my end. Please try "
                            "again in a moment, or call our front desk at (512) 555-0142.\n\n"
                            f"`{type(exc).__name__}: {exc}`",
                    "sources": [],
                    "tool_events": [],
                }
        st.markdown(result["text"])
        if result["tool_events"]:
            st.markdown(
                "".join(f'<span class="tool-event">{e}</span>' for e in result["tool_events"]),
                unsafe_allow_html=True,
            )

    st.session_state.messages.append({
        "role": "assistant",
        "text": result["text"],
        "sources": result["sources"],
        "tool_events": result["tool_events"],
    })
    # refresh sidebar Front Desk view if a booking just happened
    if any("Appointment" in e for e in result["tool_events"]):
        st.rerun()

st.markdown(
    '<p class="disclaimer">Riva is an AI assistant and does not provide medical advice. '
    'For emergencies, call 911. All data in this demo is synthetic.</p>',
    unsafe_allow_html=True,
)
