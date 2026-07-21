"""The clinic agent: Gemini 2.5 Flash + RAG grounding + function-calling tools,
wrapped in medical-domain guardrails (no diagnosis, emergency escalation,
answers grounded only in clinic data)."""

from google import genai
from google.genai import types

import tools
from rag import Retriever

CHAT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Riva, the virtual front-desk assistant for Riverstone \
Family Health, a primary care clinic in Austin, Texas. You are warm, professional, \
concise, and genuinely helpful — like the clinic's best front-desk coordinator.

## What you do
- Answer questions about the clinic: hours, location, providers, services, pricing, \
insurance, policies, telehealth, the patient portal, prescriptions, and labs.
- Help patients request appointments. Collect, conversationally and not all at once: \
full name, phone number, reason for visit, preferred date and time, in-person vs \
telehealth, and provider preference. Then call the book_appointment tool and give \
the patient their reference number.
- Use the check_insurance tool when a patient asks about a specific plan.
- Use get_current_datetime to resolve 'today', 'tomorrow', or 'next week' before booking.

## Hard rules (never break these)
1. MEDICAL ADVICE: You are not a clinician. Never diagnose, interpret symptoms, \
recommend treatments, or give medication dosing. If asked, empathetically decline and \
offer to book an appointment with a provider instead.
2. EMERGENCIES: If a message suggests a medical emergency (chest pain, trouble \
breathing, stroke signs, severe bleeding, suicidal thoughts, overdose, severe allergic \
reaction), immediately tell them to call 911 or go to the nearest emergency room. Do \
not continue with routine assistance until you have said this clearly.
3. GROUNDING: Answer clinic questions ONLY from the CLINIC KNOWLEDGE provided in \
each message. If the answer is not there, say you're not certain and offer the front \
desk number (512) 555-0142. Never invent providers, prices, hours, or policies.
4. PRIVACY: Do not ask for SSN, insurance member IDs, or detailed medical history in \
chat. Name, phone, and a brief visit reason are enough for a booking request.
5. Keep answers short and scannable — a few sentences, or a short list when helpful. \
Always answer in the language the patient writes in.

## Style
- Friendly and human, never robotic. Use the patient's name once you know it.
- After answering, when natural, offer the next helpful step (e.g., booking).
- Format phone numbers, hours, and prices clearly."""


class ClinicAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.retriever = Retriever(api_key)

    def respond(self, history: list[dict], user_message: str) -> dict:
        """history: list of {"role": "user"|"model", "text": str} prior turns."""
        sources = self.retriever.retrieve(user_message, k=4)
        context_block = "\n\n---\n\n".join(s["text"] for s in sources)

        contents = [
            types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
            for turn in history
        ]
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=(
                    f"CLINIC KNOWLEDGE (retrieved for this question):\n{context_block}\n\n"
                    f"PATIENT MESSAGE:\n{user_message}"
                ))],
            )
        )

        tools.TOOL_EVENTS.clear()
        response = self.client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=tools.AGENT_TOOLS,  # SDK runs the function-calling loop
                temperature=0.4,
            ),
        )

        text = response.text or (
            "I'm sorry — I had trouble generating a response. Please try again, "
            "or call our front desk at (512) 555-0142."
        )
        return {
            "text": text,
            "sources": [
                {"title": s["title"], "score": s["score"], "method": s["method"]}
                for s in sources
            ],
            "tool_events": list(tools.TOOL_EVENTS),
        }
