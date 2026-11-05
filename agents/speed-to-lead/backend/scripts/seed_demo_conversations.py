"""
Run two realistic buyer conversations through the live backend for Aparna Constructions, so the
per-person views have something to show. The AI really replies, from Aparna's ingested knowledge base.

  Meera Joshi   -> a channel partner's line  asks about 3 BHK projects, budget, RERA and loans, books a
                                              visit, then asks for a discount (which goes to a person)
  Rohit Agarwal -> a team member's line       asks about Newlands possession, investment, documents,
                                              and books a visit

It adds two sample people (placeholder mobile numbers 9000000101 and 9000000102, the same two that
seed_aparna_logins.py uses) and one demo WhatsApp number for each (Meta IDs starting DEMO_). Buyer phones use
91900000xxxx. Nothing is sent to WhatsApp.

    python scripts/seed_demo_conversations.py                 # create (skips what already exists)
    python scripts/seed_demo_conversations.py --remove        # delete exactly what this script made

The backend must be running (default http://localhost:8001).
"""

import argparse
import asyncio
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIRM = "Aparna Constructions"
BUYER_PREFIX = "9190000093"          # 919000009301, 919000009302
NUMBER_IDS = ("DEMO_APARNA_PARTNER_LINE", "DEMO_APARNA_TEAM_LINE")
PEOPLE_PHONES = ("9000000101", "9000000102")

SCRIPTS = [
    {
        "buyer": "Meera Joshi", "phone": "919000009301",
        "person": "Aparna Partner", "kind": "partner", "person_phone": "9000000101",
        "person_company": "Sample Realty",
        "number_label": "Partner line", "wa_id": NUMBER_IDS[0],
        "messages": [
            "Hi, I am looking for a 3 BHK in Hyderabad. Which Aparna projects do you have?",
            "Budget is around 1.5 crore. I work in Gachibowli.",
            "Are all your projects RERA registered, and do you help with home loans?",
            "Can I visit this Saturday around 11 AM?",
            "Can you give me a discount if I book this month?",
        ],
    },
    {
        "buyer": "Rohit Agarwal", "phone": "919000009302",
        "person": "Aparna Sales Executive", "kind": "team", "person_phone": "9000000102",
        "person_company": "Aparna sales team",
        "number_label": "Sales team line", "wa_id": NUMBER_IDS[1],
        "messages": [
            "Hello, I want to know about Aparna Newlands in Tellapur. What is the possession timeline?",
            "I am buying for investment. A 2.5 BHK would work for me.",
            "What documents do I need for booking?",
            "Great. Can I come for a site visit on Sunday morning?",
        ],
    },
]


def create(api: str):
    firm = next((f for f in requests.get(f"{api}/firms", timeout=30).json() if f["name"] == FIRM), None)
    if not firm:
        sys.exit(f"Firm not found: {FIRM}")
    fid = firm["id"]
    people = {p["phone"]: p for p in requests.get(f"{api}/brokers", params={"firm_id": fid}, timeout=30).json()}
    numbers = {n["wa_phone_number_id"]: n for n in requests.get(f"{api}/numbers", params={"firm_id": fid}, timeout=30).json()}
    leads = {x["phone"] for x in requests.get(f"{api}/dashboard/conversations",
                                              params={"firm_id": fid, "limit": 100}, timeout=30).json()}

    for s in SCRIPTS:
        if s["phone"] in leads:
            print(f"- {s['buyer']}: already exists, skipped")
            continue
        person = people.get(s["person_phone"])
        if person is None:
            r = requests.post(f"{api}/brokers", timeout=30, json={
                "firm_id": fid, "name": s["person"], "phone": s["person_phone"],
                "company": s["person_company"], "kind": s["kind"]})
            r.raise_for_status()
            person = r.json()
            print(f"+ added {s['kind']} {s['person']}")
        number = numbers.get(s["wa_id"])
        if number is None:
            r = requests.post(f"{api}/numbers", timeout=30, json={
                "firm_id": fid, "label": s["number_label"], "wa_phone_number_id": s["wa_id"],
                "person_id": person["id"]})
            r.raise_for_status()
            number = r.json()
            print(f"+ registered {s['number_label']} for {s['person']}")

        print(f"\n{s['buyer']} -> {s['number_label']} ({s['person']})")
        for msg in s["messages"]:
            r = requests.post(f"{api}/dev/chat", timeout=180, json={
                "firm_id": fid, "phone": s["phone"], "message": msg,
                "wa_name": s["buyer"], "number_id": number["id"]})
            if r.status_code != 200:
                print(f"  ! {r.status_code} {r.text[:120]}")
                break
            d = r.json()
            print(f"  buyer : {msg}")
            print(f"  reply : {(d.get('response') or '').replace(chr(10), ' ')[:160]}   [{d.get('path_taken')}, {d.get('stage')}]")
            time.sleep(1)


async def remove():
    """Delete only what this script created: the two buyers' leads (and their messages, visits,
    follow-ups and summaries), the two demo numbers, and the two sample people if they have no
    login linked in a way the user wants to keep (they are placeholders)."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    from sqlalchemy import text
    from db.database import engine

    async with engine.begin() as c:
        fid = (await c.execute(text("select id from stl.firms where name = :n"), {"n": FIRM})).scalar_one_or_none()
        if fid is None:
            sys.exit(f"Firm not found: {FIRM}")
        ids = [r[0] for r in await c.execute(
            text("select id from stl.leads where firm_id=:f and phone like :p"), {"f": fid, "p": BUYER_PREFIX + "%"})]
        for table in ("followup_schedules", "visits", "conversation_logs", "retrieval_logs",
                      "lead_summaries", "real_estate_profiles", "sessions", "lead_registrations"):
            if ids:
                await c.execute(text(f"delete from stl.{table} where lead_id = any(:ids)"), {"ids": ids})
        if ids:
            await c.execute(text("delete from stl.leads where id = any(:ids)"), {"ids": ids})
        n = await c.execute(text("delete from stl.firm_numbers where firm_id=:f and wa_phone_number_id = any(:w)"),
                            {"f": fid, "w": list(NUMBER_IDS)})
        # A person with a sign-in is kept: the login is tied to that person's ID, and deleting and
        # re-creating them would leave the login pointing at nobody.
        p = await c.execute(text("delete from stl.brokers where firm_id=:f and phone10 = any(:p) and email is null"),
                            {"f": fid, "p": list(PEOPLE_PHONES)})
        print(f"removed {len(ids)} leads, {n.rowcount} numbers, {p.rowcount} sample people")
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8001")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    if a.remove:
        asyncio.run(remove())
    else:
        create(a.api)
