# Riverstone Family Health — AI Front-Desk Agent (Demo)

A client-facing demo of an **AI agent** (not a scripted chatbot) embedded on a US
clinic's website. Built with Streamlit + Google Gemini.

## What it demonstrates to a clinic owner

| Capability | How |
|---|---|
| Answers grounded in *their* clinic data | RAG over a markdown knowledge base (semantic search with Gemini embeddings) |
| Books appointments in chat | Gemini function calling → captured leads appear live in the sidebar "Front Desk view" |
| Insurance verification | `check_insurance` tool against the clinic's accepted-plans list |
| Medical-domain safety | No diagnosis, 911 escalation on emergency language, HIPAA-aware data minimization |
| Easy to rebrand per client | Swap `data/*.md` — the index rebuilds automatically (content-hash cache) |

## Quick start

```powershell
pip install -r requirements.txt
copy .env.example .env   # then paste your Gemini API key into .env
streamlit run app.py
```

Or skip the `.env` and paste the key into the sidebar at runtime.

## Demo script (for sales calls)

1. Ask: *"Do you take Blue Cross?"* → grounded answer + insurance tool badge.
2. Ask: *"How much is a visit without insurance?"* → exact self-pay pricing from the KB.
3. Say: *"I'd like to book a sick visit tomorrow morning"* → agent collects name/phone
   conversationally, books it, returns a reference number — and the request appears
   in the **Front Desk view** sidebar. That's the close.
4. Ask something medical (*"what should I take for my headache?"*) → safe refusal +
   offer to book. Shows the guardrails clinic owners worry about.

## Architecture

```
app.py      Streamlit UI (chat, sources expander, front-desk lead view)
agent.py    Gemini 2.5 Flash + system guardrails + RAG context injection
rag.py      Section chunking → gemini-embedding-001 → cosine top-k (numpy, disk-cached)
tools.py    book_appointment / check_insurance / get_current_datetime
data/       Clinic knowledge base (synthetic) + captured appointments.json
```

All clinic data is synthetic — for demonstration only.
