"""Agent tools exposed to Gemini via automatic function calling.

Each function is a plain Python callable with type hints + docstring — the
google-genai SDK converts these into function declarations and runs the
call/response loop automatically. In production these would hit the clinic's
PMS/EHR scheduling API (e.g. athenahealth, DrChrono); for the demo, appointment
requests are persisted to a JSON file that the sidebar 'Front Desk view' reads."""

import json
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

APPOINTMENTS_PATH = Path(__file__).parent / "data" / "appointments.json"

CLINIC_TZ = ZoneInfo("America/Chicago")

ACCEPTED_PLANS = [
    "Aetna",
    "Blue Cross Blue Shield of Texas",
    "Cigna",
    "UnitedHealthcare",
    "Humana",
    "Medicare",
    "Texas Medicaid",
    "Tricare",
    "Oscar Health",
    "Ambetter",
]

# Per-turn log so the UI can show which tools the agent used.
TOOL_EVENTS: list[str] = []


def _load_appointments() -> list[dict]:
    if APPOINTMENTS_PATH.exists():
        try:
            return json.loads(APPOINTMENTS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save_appointments(items: list[dict]) -> None:
    APPOINTMENTS_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


def get_current_datetime() -> dict:
    """Get the current date, day of week, and time at the clinic (US Central Time).
    Use this to resolve relative dates like 'today', 'tomorrow', or 'next Monday',
    and to check whether the clinic is currently open."""
    TOOL_EVENTS.append("🕐 Checked current date/time")
    now = datetime.now(CLINIC_TZ)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "day_of_week": now.strftime("%A"),
        "time": now.strftime("%I:%M %p"),
        "timezone": "US Central Time (CT)",
    }


def check_insurance(plan_name: str) -> dict:
    """Check whether a specific insurance plan is accepted at Riverstone Family Health.

    Args:
        plan_name: The name of the patient's insurance plan or carrier,
            e.g. 'Blue Cross', 'Cigna', 'Kaiser'.
    """
    TOOL_EVENTS.append(f"🛡️ Verified insurance: {plan_name}")
    needle = plan_name.strip().lower()
    for plan in ACCEPTED_PLANS:
        if needle in plan.lower() or plan.lower() in needle:
            return {
                "accepted": True,
                "matched_plan": plan,
                "note": "Coverage varies by specific plan — patients should confirm "
                        "their plan is in-network before the visit.",
            }
    return {
        "accepted": False,
        "accepted_plans": ACCEPTED_PLANS,
        "note": "Plan not on the accepted list. The patient can call the front desk "
                "at (512) 555-0142 to check, or use transparent self-pay pricing "
                "with a 15% pay-in-full discount.",
    }


def book_appointment(
    full_name: str,
    phone: str,
    reason: str,
    preferred_date: str,
    preferred_time: str,
    visit_type: str = "in-person",
    preferred_provider: str = "next available",
    is_new_patient: bool = True,
) -> dict:
    """Submit an appointment request to the clinic's scheduling system.
    Only call this AFTER collecting the patient's full name, phone number,
    reason for visit, and preferred date and time.

    Args:
        full_name: Patient's full name.
        phone: Patient's phone number for confirmation callback.
        reason: Reason for the visit, e.g. 'annual physical', 'sick visit - flu symptoms'.
        preferred_date: Preferred date in YYYY-MM-DD format.
        preferred_time: Preferred time of day, e.g. '10:00 AM' or 'morning'.
        visit_type: 'in-person' or 'telehealth'.
        preferred_provider: Requested provider name, or 'next available'.
        is_new_patient: Whether this is a new patient to the clinic.
    """
    reference = f"RFH-{secrets.token_hex(3).upper()}"
    record = {
        "reference": reference,
        "full_name": full_name,
        "phone": phone,
        "reason": reason,
        "preferred_date": preferred_date,
        "preferred_time": preferred_time,
        "visit_type": visit_type,
        "preferred_provider": preferred_provider,
        "is_new_patient": is_new_patient,
        "status": "pending confirmation",
        "submitted_at": datetime.now(CLINIC_TZ).strftime("%Y-%m-%d %I:%M %p CT"),
    }
    items = _load_appointments()
    items.append(record)
    _save_appointments(items)
    TOOL_EVENTS.append(f"📅 Appointment request submitted — ref {reference}")
    return {
        "status": "submitted",
        "reference": reference,
        "message": "Appointment request received. Front desk staff will call to "
                   "confirm the exact time slot within business hours. New patients "
                   "should complete intake forms via the patient portal or arrive "
                   "15 minutes early.",
    }


AGENT_TOOLS = [get_current_datetime, check_insurance, book_appointment]
