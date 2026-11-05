"""
End-to-end check of person numbers and agent scoping against the staging database.

Creates a team member and a partner number on the Prestige Homes demo firm, sends buyers to each
(this calls the AI), checks who owns each conversation, then checks what staff and an agent can see
and do. It removes what it created. Run from backend/:  python scripts/verify_numbers_and_scoping.py
"""
import sys, asyncio
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
import httpx
import main
from db.database import engine, SessionLocal
from routes.guard import guard
from services.auth import Actor
from sqlalchemy import text

FIRM = "52be1cba-b8d7-4915-a465-564fe90ca667"
OK = []
def check(name, cond, extra=""):
    OK.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

async def go():
    from services import claude, pinecone_svc
    claude.init(); pinecone_svc.init()
    async with SessionLocal() as _db:
        await pinecone_svc.load_resource_catalogue(_db)
    t = httpx.ASGITransport(app=main.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=t, base_url="http://t", timeout=120) as c:
        # people
        r = await c.post("/brokers", json={"firm_id": FIRM, "name": "Karan Mehta", "phone": "9000000090",
                                           "company": "Prestige sales gallery", "kind": "team"})
        check("create team member", r.status_code == 200 and r.json().get("kind") == "team", r.text)
        karan = r.json()["id"]
        r = await c.get(f"/brokers?firm_id={FIRM}")
        ravi = next(b for b in r.json() if b["name"] == "Ravi Kumar")
        check("list shows kind", {b["kind"] for b in r.json()} >= {"partner", "team"})

        # numbers
        r = await c.post("/numbers", json={"firm_id": FIRM, "label": "Karan line", "wa_phone_number_id": "DEMO_KARAN_NUM",
                                           "display_phone": "+91 90000 00090", "person_id": karan})
        check("register number for team member", r.status_code == 200 and r.json()["person_name"] == "Karan Mehta", r.text)
        karan_num = r.json()["id"]
        r = await c.post("/numbers", json={"firm_id": FIRM, "label": "Ravi line", "wa_phone_number_id": "DEMO_RAVI_NUM",
                                           "person_id": ravi["id"]})
        check("register number for partner", r.status_code == 200, r.text)
        ravi_num = r.json()["id"]
        r = await c.post("/numbers", json={"firm_id": FIRM, "label": "dup", "wa_phone_number_id": "DEMO_KARAN_NUM"})
        check("duplicate number id rejected", r.status_code == 400, r.text)
        r = await c.get(f"/numbers?firm_id={FIRM}")
        check("numbers hide the token", all("meta_access_token" not in n for n in r.json()))

        # buyers arrive on different numbers
        async def buyer(phone, number_id, msg):
            body = {"firm_id": FIRM, "phone": phone, "message": msg, "wa_name": "Test " + phone[-4:]}
            if number_id:
                body["number_id"] = number_id
            r = await c.post("/dev/chat", json=body)
            return r.status_code, r.text[:200]

        s1 = await buyer("919000009101", karan_num, "Hi, what is the RERA number?")
        s2 = await buyer("919000009102", ravi_num, "What is the price?")
        s3 = await buyer("919000009103", None, "Is there a payment plan?")
        check("buyers answered", all(s[0] == 200 for s in (s1, s2, s3)), (s1, s2, s3))

        async with SessionLocal() as db:
            rows = (await db.execute(text(
                "select l.phone, l.owner_id::text, l.number_id::text, l.source from stl.leads l "
                "where l.phone in ('919000009101','919000009102','919000009103') order by l.phone"))).all()
            logs = (await db.execute(text(
                "select count(*) from stl.conversation_logs where number_id = :n"), {"n": karan_num})).scalar_one()
        owners = {r[0]: r for r in rows}
        check("lead on Karan's number is owned by Karan", owners["919000009101"][1] == karan and owners["919000009101"][2] == karan_num)
        check("lead on Ravi's number is owned by Ravi", owners["919000009102"][1] == ravi["id"])
        check("lead on main number has no owner", owners["919000009103"][1] is None)
        check("person-number lead is credited as source", owners["919000009101"][3] == "broker")
        check("messages record the number", logs >= 2, logs)

        # staff view
        r = await c.get(f"/dashboard/conversations?firm_id={FIRM}&limit=100")
        phones = {x["phone"] for x in r.json()}
        check("staff sees all conversations", {"919000009101", "919000009102", "919000009103"} <= phones)
        r = await c.get(f"/dashboard/conversations?firm_id={FIRM}&owner_id={karan}")
        mine = r.json()
        check("staff can filter by person", [x["phone"] for x in mine] == ["919000009101"], [x["phone"] for x in mine])
        check("rows carry owner and number names", mine and mine[0]["owner_name"] == "Karan Mehta" and mine[0]["number_label"] == "Karan line")
        lead_a = mine[0]["id"]
        r = await c.get(f"/dashboard/conversations?firm_id={FIRM}&limit=100")
        lead_b = next(x["id"] for x in r.json() if x["phone"] == "919000009102")

        # agent view: Karan
        main.app.dependency_overrides[guard] = lambda: Actor("u1", "karan@x.in", "agent", FIRM, karan, "Karan Mehta")
        r = await c.get(f"/dashboard/conversations?firm_id=00000000-0000-0000-0000-000000000000&owner_id={ravi['id']}&limit=100")
        check("agent sees only own conversations (query ignored)", [x["phone"] for x in r.json()] == ["919000009101"], [x["phone"] for x in r.json()])
        r = await c.get(f"/dashboard/lead/{lead_a}")
        check("agent can open own lead", r.status_code == 200, r.status_code)
        r = await c.get(f"/dashboard/lead/{lead_b}")
        check("agent cannot open someone else's lead", r.status_code == 403, r.status_code)
        r = await c.get(f"/console/lead/{lead_b}/history")
        check("agent cannot read someone else's history", r.status_code == 403, r.status_code)
        r = await c.get(f"/console/lead/{lead_a}/history")
        check("agent can read own history", r.status_code == 200 and len(r.json()) >= 2, r.status_code)
        r = await c.post("/console/pause", json={"lead_id": lead_b, "paused": True})
        check("agent cannot pause someone else's lead", r.status_code == 403, r.status_code)
        r = await c.post("/console/reply", json={"lead_id": lead_b, "session_id": "00000000-0000-0000-0000-000000000000", "phone": "x", "message_text": "hi"})
        check("agent cannot reply on someone else's lead", r.status_code == 403, r.status_code)
        r = await c.get(f"/console/lead/{lead_b}/summary")
        check("agent cannot read someone else's summary", r.status_code == 403, r.status_code)
        for path in (f"/brokers?firm_id={FIRM}", f"/registrations?firm_id={FIRM}", f"/numbers?firm_id={FIRM}",
                     "/firms", "/plans", f"/dashboard/stats?firm_id={FIRM}", f"/dashboard/source-split?firm_id={FIRM}"):
            r = await c.get(path)
            check(f"agent blocked from {path.split('?')[0]}", r.status_code == 403, r.status_code)
        r = await c.get(f"/firms/{FIRM}")
        check("agent sees own firm without secrets", r.status_code == 200 and "meta_access_token" not in r.json() and "plan" not in r.json(), r.text[:120])
        r = await c.get("/firms/17080121-90f7-4589-adda-a4e3f695ab33")
        check("agent cannot open another firm", r.status_code == 403, r.status_code)
        r = await c.get(f"/dashboard/visits?firm_id={FIRM}")
        check("agent visits are limited to own leads", r.status_code == 200 and all(v["lead_id"] for v in r.json()))

        # counselor sees everything
        main.app.dependency_overrides[guard] = lambda: Actor("u2", "c@x.in", "counselor", FIRM, None, "Counselor")
        r = await c.get(f"/dashboard/conversations?firm_id={FIRM}&limit=100")
        check("counselor sees all conversations", {"919000009101", "919000009102", "919000009103"} <= {x["phone"] for x in r.json()})
        r = await c.get(f"/brokers?firm_id={FIRM}")
        check("counselor can manage people", r.status_code == 200)
        main.app.dependency_overrides.clear()

        # cleanup of what this script created
        async with SessionLocal() as db:
            await db.execute(text("delete from stl.conversation_logs where lead_id in (select id from stl.leads where phone like '9190000091%')"))
            await db.execute(text("delete from stl.leads where phone like '9190000091%'"))
            await db.execute(text("delete from stl.firm_numbers where wa_phone_number_id in ('DEMO_KARAN_NUM','DEMO_RAVI_NUM')"))
            await db.execute(text("delete from stl.brokers where phone10 = '9000000090'"))
            await db.commit()
    await engine.dispose()
    print(f"\n{sum(OK)}/{len(OK)} passed")

asyncio.run(go())
