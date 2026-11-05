"""
Seed demo data for the broker registry: one project, four channel partners, a ledger with a
broker-vs-broker conflict and a broker-vs-existing-lead conflict, and leads from ads, brokers
and organic so the source split has something to show.

All client phone numbers use the 91900000xxxx range (not real people). Safe to re-run with
--reset, which removes only the rows this script created.

    python scripts/seed_broker_demo.py --firm "Prestige Homes"
    python scripts/seed_broker_demo.py --firm "Prestige Homes" --reset
"""

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from sqlalchemy import delete, select  # noqa: E402

from db.database import SessionLocal, engine  # noqa: E402
from db.models import (  # noqa: E402
    Broker, ConversationLog, Firm, Lead, LeadRegistration, Project, Visit,
)
from services import broker_registry as reg  # noqa: E402

DEMO_PREFIX = "91900000"
NOW = datetime.now(timezone.utc)


def ago(**kw) -> datetime:
    return NOW - timedelta(**kw)


async def wipe(db, firm):
    leads = list((await db.execute(select(Lead.id).where(
        Lead.firm_id == firm.id, Lead.phone.like(f"{DEMO_PREFIX}%")))).scalars())
    await db.execute(delete(LeadRegistration).where(LeadRegistration.firm_id == firm.id))
    if leads:
        await db.execute(delete(Visit).where(Visit.lead_id.in_(leads)))
        await db.execute(delete(ConversationLog).where(ConversationLog.lead_id.in_(leads)))
        await db.execute(delete(Lead).where(Lead.id.in_(leads)))
    from db.models import FirmNumber
    await db.execute(delete(FirmNumber).where(FirmNumber.firm_id == firm.id,
                                              FirmNumber.wa_phone_number_id.like("DEMO_%")))
    await db.execute(delete(Broker).where(Broker.firm_id == firm.id))
    await db.execute(delete(Project).where(Project.firm_id == firm.id))
    await db.commit()


async def make_lead(db, firm, phone, name, *, when, ad=None, broker=None, project=None,
                    reply_seconds=None, visit_in_days=None):
    lead = Lead(
        firm_id=firm.id, phone=phone, wa_name=name, lead_name=name, lead_type=firm.vertical,
        ctwa_source_id=ad, broker_id=broker.id if broker else None,
        project_id=project.id if project else None, lead_status="active",
        source="broker" if broker else ("ad" if ad else "organic"),
        created_at=when, last_active=when,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    if reply_seconds is not None:
        db.add(ConversationLog(firm_id=firm.id, lead_id=lead.id, direction="inbound",
                               sender_type="lead", message_text="Hi, price and floor plan please",
                               created_at=when))
        db.add(ConversationLog(firm_id=firm.id, lead_id=lead.id, direction="outbound",
                               sender_type="ai", message_text="Hello, here are the details.",
                               path_taken="knowledge",
                               created_at=when + timedelta(seconds=reply_seconds)))
    if visit_in_days is not None:
        db.add(Visit(firm_id=firm.id, lead_id=lead.id,
                     visit_date=date.today() + timedelta(days=visit_in_days)))
    await db.commit()
    return lead


async def main(firm_name: str, do_reset: bool):
    async with SessionLocal() as db:
        firm = (await db.execute(select(Firm).where(Firm.name == firm_name))).scalar_one_or_none()
        if firm is None:
            sys.exit(f"Firm not found: {firm_name}")
        if firm.vertical != "real_estate":
            sys.exit("The broker demo needs a real estate firm")
        if do_reset:
            await wipe(db, firm)
            print("removed previous demo rows")
        elif (await db.execute(select(Project).where(Project.firm_id == firm.id))).first():
            sys.exit("This firm already has projects. Re-run with --reset to replace the demo data.")

        project = Project(
            firm_id=firm.id, name="Prestige Skyline", location="Kokapet, Hyderabad",
            rera_number="P02400004521", possession_date=date(2028, 12, 31),
            starting_price="Rs. 1.45 Cr onwards for 3 BHK, all-in cost shared on request",
            payment_plan="10% on booking, construction-linked after that",
            bank_tieups="SBI, HDFC, ICICI, Axis", validity_days=60)
        db.add(project)
        await db.commit()
        await db.refresh(project)

        people = [
            ("Ravi Kumar", "Sri Sai Realty", "9000000001", "A/TS/00231"),
            ("Anitha Rao", "Rao Property Advisors", "9000000002", "A/TS/00488"),
            ("Imran Shaik", "Charminar Estates", "9000000003", "A/TS/00712"),
            ("Lakshmi Devi", "Devi Homes", "9000000004", "A/TS/00905"),
        ]
        brokers = {}
        for name, company, phone, rera in people:
            b = await reg.create_broker(db, firm.id, name, phone, company=company,
                                        rera_agent_no=rera)
            brokers[name.split()[0]] = b

        async def register(broker, client_phone, client_name, when, **kw):
            return await reg.register_client(
                db, firm=firm, broker=broker, client_phone10=client_phone[-10:],
                client_name=client_name, project=project, registered_at=when,
                check_existing_lead=False, **kw)

        # Ledger via broker WhatsApp
        suresh = await register(brokers["Ravi"], "9100000011", "Suresh Reddy", ago(days=3, hours=2))
        await register(brokers["Anitha"], "9100000011", "Suresh Reddy", ago(days=1, hours=5))  # conflict
        await register(brokers["Imran"], "9100000012", "Meena Iyer", ago(days=2, hours=1))
        await register(brokers["Lakshmi"], "9100000013", "Karthik Varma", ago(days=5))
        await register(brokers["Ravi"], "9100000015", "Farah Khan", ago(hours=20))

        # A buyer who came from an ad first, then a broker registers the same person
        priya = await make_lead(db, firm, DEMO_PREFIX + "0014", "Priya Nair", when=ago(days=6),
                                ad="ad_kokapet_3bhk", project=project, reply_seconds=22)
        await register(brokers["Imran"], "9000000014", "Priya Nair", ago(days=4),
                       existing_lead_at=priya.created_at)

        # Leads by source for the split
        ad_latencies = [18, 24, 31, 27, 22, 40]
        for i, sec in enumerate(ad_latencies):
            await make_lead(db, firm, f"{DEMO_PREFIX}02{i:02d}", f"Ad lead {i + 1}",
                            when=ago(days=i + 1, hours=i), ad="ad_kokapet_3bhk", project=project,
                            reply_seconds=sec, visit_in_days=2 if i in (1, 4) else None)
        for i, (who, sec) in enumerate([("Ravi", 21), ("Ravi", 26), ("Anitha", 19),
                                        ("Lakshmi", 33)]):
            lead = await make_lead(db, firm, f"{DEMO_PREFIX}03{i:02d}", f"Broker lead {i + 1}",
                                   when=ago(days=i + 2), broker=brokers[who], project=project,
                                   reply_seconds=sec, visit_in_days=3 if i in (0, 2) else None)
            await reg.register_client(
                db, firm=firm, broker=brokers[who], client_phone10=lead.phone[-10:],
                client_name=lead.lead_name, project=project, method="coded_link",
                lead_id=lead.id, registered_at=lead.created_at, check_existing_lead=False)
        for i, sec in enumerate([29, 36]):
            await make_lead(db, firm, f"{DEMO_PREFIX}04{i:02d}", f"Organic lead {i + 1}",
                            when=ago(days=i + 3), project=project, reply_seconds=sec)

        n = (await db.execute(select(LeadRegistration).where(
            LeadRegistration.firm_id == firm.id))).scalars().all()
        open_c = [r for r in n if r.conflict_state == "open"]
        print(f"seeded firm={firm.name}: 1 project, {len(brokers)} brokers, "
              f"{len(n)} registrations, {len(open_c)} open conflicts")
        print("broker codes:", {k: v.code for k, v in brokers.items()})
        _ = suresh
    await engine.dispose()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--firm", default="Prestige Homes")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.firm, a.reset))
