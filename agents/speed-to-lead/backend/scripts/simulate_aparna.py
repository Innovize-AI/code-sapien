"""
Aparna Constructions — Conversation Simulator
Calls the LangGraph graph directly (no WhatsApp send).

Modes:
  --auto          Claude plays the lead automatically (reactive, no typing needed)
  (no flag)       You type each message after reading the AI's reply

Flags:
  --output <path>  Save printed output to a file (in addition to stdout)
  --save-db        Persist lead, session, conversation logs, and retrieval logs to the DB

Usage:
    poetry run python scripts/simulate_aparna.py --scenario 1         # interactive
    poetry run python scripts/simulate_aparna.py --scenario 1 --auto  # fully automated
    poetry run python scripts/simulate_aparna.py --scenario 1 --auto --turns 8
    poetry run python scripts/simulate_aparna.py --scenario 1 --auto --turns 8 --output results/s1.txt
    poetry run python scripts/simulate_aparna.py --scenario 1 --auto --save-db

Scenarios:
    1. Fresh lead       — blank state, discovery stage
    2. Researcher       — qualification stage, asks detailed questions
    3. Fence-sitter     — qualified (3BHK, 1Cr-2Cr), raises objections
    4. CTWA ad click    — clicked CyberZed 3BHK ad, config pre-filled
    5. Wrong fit        — low budget (~35-40L), out-of-range lead
    6. Portfolio seeker — wants to see projects and styles first
    7. Visit management — visit already booked, tests reschedule/cancel
"""

import asyncio
import argparse
import os
import sys
import textwrap
from copy import deepcopy
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from services import claude, pinecone_svc, supabase_svc
from workflow.state import LeadState, default_state
from workflow.graph import lead_agent_graph
from workflow.stage import advance_stage

FIRM_ID   = "1791a3db-8a5a-4680-b6cd-f3a2c714ca1a"
FIRM_NAME = "Aparna Constructions"
FIRM_CTA  = "free site visit (cab arranged)"
VERTICAL  = "real_estate"

# Populated from DB in main() before any scenario runs
_firm_contact_phone: str | None = None
_firm_contact_email: str | None = None

SEP  = "─" * 70
SEP2 = "═" * 70

# Output file handle — set when --output is given
_out_file = None


def _emit(text: str = "") -> None:
    """Print to stdout and optionally to the output file."""
    print(text)
    if _out_file:
        _out_file.write(text + "\n")
        _out_file.flush()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _wrap(text: str, prefix: str) -> str:
    lines = text.strip().split("\n")
    out = []
    for line in lines:
        if line.strip():
            out.append(textwrap.fill(line, width=68,
                                     initial_indent=prefix,
                                     subsequent_indent=" " * len(prefix)))
        else:
            out.append("")
    return "\n".join(out)


def _print_reply(response: str, state: LeadState) -> None:
    _emit()
    _emit(_wrap(response, "  AI  : "))
    path  = state.get("path_taken", "—")
    stage = state.get("stage", "—")
    score = state.get("knowledge_top_score")
    res   = state.get("resource_to_attach")
    score_str = f"{score:.3f}" if score else "—"
    suffix = ""
    if res:
        suffix = f"  [RESOURCE attached: {res['id']} ({res['type']})]"
    _emit(f"\n  [turn={state.get('turn_count',0)}  stage={stage}  path={path}  score={score_str}]{suffix}\n")


def _make_state(phone: str, wa_name: str = "Test Lead", **overrides) -> LeadState:
    s = default_state(phone, wa_name)
    s["firm_id"]                = FIRM_ID
    s["firm_vertical"]          = VERTICAL
    s["firm_display_name"]      = FIRM_NAME
    s["firm_visit_cta"]         = FIRM_CTA
    s["firm_meta_access_token"] = None
    s["firm_contact_phone"]     = _firm_contact_phone
    s["firm_contact_email"]     = _firm_contact_email
    s["lead_id"]                = "00000000-0000-0000-0000-000000000001"
    s["session_id"]             = "00000000-0000-0000-0000-000000000002"
    s["lead_status"]            = "new"
    s["ai_paused"]              = False
    for k, v in overrides.items():
        s[k] = v
    return s


async def _send(state: LeadState, message: str, db=None) -> tuple[str, LeadState]:
    from agents.tools import _db_ctx

    state = deepcopy(state)
    state["message_text"] = message
    state["message_type"] = "text"

    if db is not None:
        _db_ctx.set(db)

    result: LeadState = await lead_agent_graph.ainvoke(state)
    result = await advance_stage(result)

    response = result.get("response_text") or ""

    history = list(result.get("history", []))
    history.append({"role": "user",      "content": message})
    history.append({"role": "assistant", "content": response})
    result["history"]    = history[-16:]
    result["turn_count"] = result.get("turn_count", 0) + 1

    return response, result


# ── DB persistence helpers ─────────────────────────────────────────────────────

async def _setup_db_records(db, scenario_n: int, scenario_title: str) -> tuple[str, str]:
    """Create (or reuse) a sim lead and a fresh session. Returns (lead_id, session_id)."""
    from db import crud
    from db.models import Lead, Session
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession

    phone = f"+SIM{scenario_n:03d}"

    lead = await crud.get_or_create_lead(
        db, phone, firm_id=FIRM_ID, wa_name=scenario_title
    )
    # Mark as simulation source so it's easy to filter in the dashboard
    await db.execute(
        update(Lead).where(Lead.id == lead.id).values(source="simulation")
    )
    await db.commit()

    # Always start a fresh session for each simulation run
    session = Session(
        lead_id=lead.id,
        firm_id=FIRM_ID,
        context={},
        stage="discovery",
        turn_count=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return str(lead.id), str(session.id)


def _uuid(val):
    from uuid import UUID
    return UUID(val) if isinstance(val, str) else val


async def _db_log_turn(
    db,
    state: LeadState,
    message: str,
    response: str,
    turn_number: int,
) -> None:
    """Log inbound lead message + outbound AI reply + retrieval record."""
    from db import crud

    lead_id    = _uuid(state["lead_id"])
    session_id = _uuid(state["session_id"])

    await crud.log_message(
        db,
        session_id=session_id,
        lead_id=lead_id,
        firm_id=FIRM_ID,
        direction="inbound",
        sender_type="lead",
        message_text=message,
        turn_number=turn_number,
    )

    if response:
        await crud.log_message(
            db,
            session_id=session_id,
            lead_id=lead_id,
            firm_id=FIRM_ID,
            direction="outbound",
            sender_type="ai",
            message_text=response,
            path_taken=state.get("path_taken"),
            pinecone_score=state.get("knowledge_top_score"),
            resource_sent=(state.get("resource_to_attach") or {}).get("id"),
            turn_number=turn_number,
        )

    if state.get("path_taken") in ("knowledge", "portfolio", "fallback"):
        await crud.log_retrieval(db, state)


async def _db_save_session(db, state: LeadState) -> None:
    from db import crud

    lead_id = _uuid(state["lead_id"])

    await crud.save_session(db, state)

    # Sync lead name + vertical profile
    lead_sync: dict = {}
    for field in ("lead_name", "lead_type"):
        if state.get(field):
            lead_sync[field] = state[field]
    if lead_sync:
        await crud.update_lead(db, lead_id, lead_sync)

    profile_fields: dict = {}
    if state.get("config"):         profile_fields["config"] = state["config"]
    if state.get("budget_bracket"): profile_fields["budget_bracket"] = state["budget_bracket"]
    if profile_fields:
        await crud.upsert_real_estate_profile(db, lead_id, profile_fields)

    if state.get("visit_date_captured") and state.get("visit_date"):
        from utils.date_parser import parse_visit_date
        parsed = parse_visit_date(state["visit_date"])
        if parsed:
            await crud.upsert_visit(
                db,
                lead_id=lead_id,
                visit_date=parsed,
                firm_id=FIRM_ID,
                visit_time_slot=state.get("visit_time_slot"),
            )
            await crud.update_lead(db, lead_id, {"lead_status": "visit_scheduled"})


# ── Scenario definitions (initial state only) ──────────────────────────────────

SCENARIOS = {
    1: {
        "title":       "Fresh Lead",
        "description": "Blank state — discovery stage. Play any kind of lead from the start.",
        "state":       lambda: _make_state("+SIM001", wa_name="Priya"),
    },
    2: {
        "title":       "Researcher",
        "description": "Qualification stage. Lead has shown interest but not yet given budget/config.",
        "state":       lambda: _make_state("+SIM002", wa_name="Kiran",
                           stage="qualification"),
    },
    3: {
        "title":       "Fence-Sitter",
        "description": "Qualified: 3BHK, 1Cr-2Cr. At consideration — play someone raising objections.",
        "state":       lambda: _make_state("+SIM003", wa_name="Rajesh",
                           stage="consideration",
                           config="3BHK", config_captured=True,
                           budget_bracket="1Cr-2Cr", budget_captured=True),
    },
    4: {
        "title":       "CTWA Ad Click",
        "description": "Lead clicked a CyberZed 3BHK ad. Config + location pre-filled from ad.",
        "state":       lambda: _make_state("+SIM004", wa_name="Sneha",
                           ctwa_config="3BHK", ctwa_location="Osman Nagar",
                           config="3BHK", config_captured=True),
    },
    5: {
        "title":       "Wrong Fit",
        "description": "Play a lead with budget ~35-40L. Test how the agent handles out-of-range.",
        "state":       lambda: _make_state("+SIM005", wa_name="Suresh"),
    },
    6: {
        "title":       "Portfolio Seeker",
        "description": "Lead wants to see projects, images, and style comparisons first.",
        "state":       lambda: _make_state("+SIM006", wa_name="Divya"),
    },
    7: {
        "title":       "Visit Management",
        "description": "Visit already booked for Saturday 10am. Test reschedule or cancel.",
        "state":       lambda: _make_state("+SIM007", wa_name="Arjun",
                           stage="conversion",
                           config="3BHK", config_captured=True,
                           budget_bracket="1Cr-2Cr", budget_captured=True,
                           lead_name="Arjun", name_captured=True,
                           visit_date="2026-09-13", visit_time_slot="10am",
                           visit_date_captured=True),
    },
}


# ── Auto-lead (Gemini plays the lead) ─────────────────────────────────────────

_AUTO_LEAD_PERSONAS = {
    1: (
        "You are Priya. First time buying a flat, a bit nervous about the whole process. "
        "You want a 3BHK somewhere near Financial District. Budget is roughly 1.2 cr, give or take. "
        "You don't know much about RERA or payment plans. "
        "You're interested but need some hand-holding."
    ),
    2: (
        "You are Kiran. You've bought property before and you do your homework. "
        "You care about RERA registration, exact possession dates, and how the payment schedule works. "
        "You're not in a rush. You won't book a visit until you've got the facts. "
        "Budget is around 1.5-2 cr, you're open to 3BHK in Osman Nagar or Gachibowli area."
    ),
    3: (
        "You are Rajesh. You like CyberZed but you're on the fence. "
        "You've heard builder delays are common. Also not sure if you'll get a good home loan. "
        "You'll come around if they answer your doubts, but you need to be convinced."
    ),
    4: (
        "You are Sneha. You saw an ad for CyberZed and clicked it on a whim. "
        "You want to know the price quickly — you have roughly 1 cr to spend. "
        "If it's too expensive you'll ask about cheaper options nearby."
    ),
    5: (
        "You are Suresh. You're looking for a 2BHK anywhere in Hyderabad. "
        "Your max budget is 35-40 lakhs. You genuinely don't know this is too low for this developer. "
        "When they say they start at 90 lakhs, you'll be surprised and ask if there's anything cheaper."
    ),
    6: (
        "You are Divya. You're not ready to commit to anything yet. "
        "You want to see photos, compare styles, understand what's luxury vs standard. "
        "Budget is 1.5-2.5 cr, open to 3BHK or 4BHK. "
        "You'll keep asking for brochures and photos rather than agreeing to a visit."
    ),
    7: (
        "You are Arjun. You already booked a site visit for Saturday at 10am but something came up at work. "
        "You want to shift it to Sunday. You're committed to visiting, just need to change the day."
    ),
}

async def _auto_lead_reply(persona: str, conversation: list[dict]) -> str:
    """Use Gemini Flash to generate the next lead message."""
    from google import genai
    from google.genai import types as _gtypes
    import random

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    last_agent = next(
        (m["content"] for m in reversed(conversation) if m["role"] == "assistant"),
        None
    )

    if last_agent:
        prompt = (
            f"You are a home buyer: {persona}\n\n"
            f"The real estate agent just messaged you:\n\"{last_agent}\"\n\n"
            "Reply as this buyer on WhatsApp. Rules:\n"
            "- Max 1-2 short sentences. Never more.\n"
            "- Occasionally two questions is fine, but they should feel natural together, not like a checklist.\n"
            "- Sound like a real person texting, not a survey response.\n"
            "- Use casual language: 'ok', 'yeah', 'hmm', 'btw', 'tbh' where natural.\n"
            "- Typos and informal grammar are fine (e.g. 'wats the price', 'sounds gd').\n"
            "- Do NOT write full formal sentences with multiple clauses.\n"
            "- React to what they said. Don't introduce a new topic out of nowhere.\n"
            "Output ONLY the message text, nothing else."
        )
    else:
        prompt = (
            f"You are a home buyer: {persona}\n\n"
            "Send your very first WhatsApp message to a real estate developer. "
            "Make it short and natural — one or two sentences max, like a real person texting. "
            "Output ONLY the message, nothing else."
        )

    resp = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config=_gtypes.GenerateContentConfig(
            max_output_tokens=300,
            temperature=0.85,
            thinking_config=_gtypes.ThinkingConfig(thinking_budget=0),
        ),
    )
    text = resp.text.strip() if resp.text else None
    if not text:
        fallbacks = [
            "What are the price ranges for 3BHK?",
            "Can you share more details about the projects?",
            "I'm interested. Can I visit the site?",
            "Okay, sounds good.",
            "What's the RERA status?",
        ]
        return random.choice(fallbacks)
    return text


# ── Chat loop ──────────────────────────────────────────────────────────────────

async def run_scenario(
    n: int,
    auto: bool = False,
    max_turns: int = 10,
    save_db: bool = False,
) -> None:
    sc = SCENARIOS[n]
    state = sc["state"]()

    _emit(f"\n{SEP2}")
    _emit(f"  Scenario {n}: {sc['title']}")
    _emit(f"  {sc['description']}")
    _emit(f"{SEP2}")
    _emit(f"  Initial stage : {state.get('stage', 'discovery')}")
    if state.get("config"):         _emit(f"  Config        : {state['config']}")
    if state.get("budget_bracket"): _emit(f"  Budget        : {state['budget_bracket']}")
    if state.get("visit_date"):     _emit(f"  Visit date    : {state['visit_date']} {state.get('visit_time_slot','')}")
    if auto:
        _emit(f"  Mode: AUTO — Claude plays the lead ({max_turns} turns max)\n")
    else:
        _emit(f"  Mode: INTERACTIVE — type each message. Enter 'q' to quit.\n")

    db = None
    if save_db:
        from db.database import SessionLocal
        _db_session = SessionLocal()
        db = await _db_session.__aenter__()
        lead_id, session_id = await _setup_db_records(db, n, sc["title"])
        state["lead_id"]   = lead_id
        state["session_id"] = session_id
        state["lead_status"] = "new"
        _emit(f"  [DB] lead={lead_id[:8]}...  session={session_id[:8]}...\n")

    lead_convo: list[dict] = []
    turn = 1

    try:
        while True:
            if auto:
                if turn > max_turns:
                    _emit(f"  [max turns ({max_turns}) reached]")
                    break
                print(f"  Generating lead message (turn {turn})...", end="\r")
                msg = await _auto_lead_reply(_AUTO_LEAD_PERSONAS.get(n, _AUTO_LEAD_PERSONAS[1]), lead_convo)
                _emit(f"  Lead : {msg}                                    ")
            else:
                try:
                    msg = input(f"  You (turn {turn}): ").strip()
                except (EOFError, KeyboardInterrupt):
                    _emit("\n  Exiting.")
                    break
                if msg.lower() in ("q", "quit", "exit", ""):
                    break

            _emit(f"  {SEP}")
            print("  AI thinking...", end="\r")

            response, state = await _send(state, msg, db=db)
            print("                ", end="\r")
            _print_reply(response, state)

            if save_db and db is not None:
                await _db_log_turn(db, state, msg, response, turn)
                await _db_save_session(db, state)

            lead_convo.append({"role": "user",      "content": msg})
            lead_convo.append({"role": "assistant",  "content": response})

            turn += 1

    finally:
        if db is not None:
            await _db_session.__aexit__(None, None, None)

    _emit(f"\n  Final state:")
    _emit(f"    stage      : {state.get('stage', '—')}")
    _emit(f"    lead_name  : {state.get('lead_name') or '—'}")
    _emit(f"    config     : {state.get('config') or '—'}")
    _emit(f"    budget     : {state.get('budget_bracket') or '—'}")
    _emit(f"    visit_date : {state.get('visit_date') or '—'}")
    _emit(f"{SEP2}\n")


# ── Entry point ────────────────────────────────────────────────────────────────

async def main(
    scenario: int | None,
    auto: bool = False,
    turns: int = 10,
    output: str | None = None,
    save_db: bool = False,
) -> None:
    global _out_file

    if output:
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        _out_file = open(output, "w", encoding="utf-8")

    try:
        claude.init()
        pinecone_svc.init()
        supabase_svc.init()

        # Load resource catalogue + firm contact details (normally done by pipeline on startup)
        from db.database import SessionLocal
        from services.pinecone_svc import load_resource_catalogue
        from db.models import Firm
        from sqlalchemy import select
        from uuid import UUID as _UUID

        global _firm_contact_phone, _firm_contact_email
        async with SessionLocal() as _db:
            await load_resource_catalogue(_db, firm_id=FIRM_ID)
            _row = await _db.execute(
                select(Firm.contact_phone, Firm.contact_email).where(Firm.id == _UUID(FIRM_ID))
            )
            _r = _row.first()
            if _r:
                _firm_contact_phone = _r.contact_phone
                _firm_contact_email = _r.contact_email

        _emit(f"\n{SEP2}")
        _emit(f"  Aparna Constructions — Speed-to-Lead Simulator")
        _emit(f"  Firm   : {FIRM_NAME}  ({FIRM_ID})")
        _emit(f"  Vertical: {VERTICAL}")
        _emit(f"{SEP2}")

        if scenario:
            if scenario not in SCENARIOS:
                _emit(f"  Unknown scenario {scenario}. Choose 1-{len(SCENARIOS)}.")
                sys.exit(1)
            await run_scenario(scenario, auto=auto, max_turns=turns, save_db=save_db)
            return

        # Scenario picker
        _emit("\n  Scenarios:")
        for n, sc in SCENARIOS.items():
            _emit(f"    {n}. {sc['title']} — {sc['description']}")

        _emit()
        try:
            choice = input("  Pick a scenario (1-7): ").strip()
            n = int(choice)
            if n not in SCENARIOS:
                raise ValueError
        except (ValueError, EOFError, KeyboardInterrupt):
            _emit("  Invalid choice. Exiting.")
            sys.exit(1)

        await run_scenario(n, auto=auto, max_turns=turns, save_db=save_db)

    finally:
        if _out_file:
            _out_file.close()
            print(f"\n  Output saved to: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, default=None,
                        help="Scenario number (1-7). Omit to pick interactively.")
    parser.add_argument("--auto", action="store_true",
                        help="Gemini plays the lead automatically (no typing needed).")
    parser.add_argument("--turns", type=int, default=10,
                        help="Max turns in auto mode (default: 10).")
    parser.add_argument("--output", type=str, default=None,
                        help="Save output to this file path (e.g. results/scenario1.txt).")
    parser.add_argument("--save-db", action="store_true",
                        help="Persist lead, session, and conversation logs to the database.")
    args = parser.parse_args()
    asyncio.run(main(
        args.scenario,
        auto=args.auto,
        turns=args.turns,
        output=args.output,
        save_db=args.save_db,
    ))
