"""
End-to-end RFQ Agent simulation.

Usage:
    python scripts/simulate.py                    # runs all 6 scenarios
    python scripts/simulate.py --scenario 1       # manufacturing (auto-approve)
    python scripts/simulate.py --scenario 2       # electrical rush
    python scripts/simulate.py --scenario 3       # IT procurement
    python scripts/simulate.py --scenario 4       # complex / human review
    python scripts/simulate.py --scenario 5       # freight: full truckload Mumbai→Delhi
    python scripts/simulate.py --scenario 6       # freight: small tempo Bangalore→Pune
"""

import sys
import os
import asyncio
import argparse
import uuid
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pathlib import Path

_wf_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_wf_env)

os.environ.setdefault("PINECONE_INDEX",       "rfq-catalog")
os.environ.setdefault("DB_SCHEMA",            "rfq")
os.environ.setdefault("GEMINI_MODEL",         "gemini-3-flash-preview")
os.environ.setdefault("COMPANY_NAME",         "InnovizeAI")
os.environ.setdefault("REVIEWER_EMAIL",       "admin@innovizeai.com")
os.environ.setdefault("SLACK_REVIEW_CHANNEL", "#rfq-review")
os.environ.setdefault("LANGCHAIN_PROJECT",    "rfq-agent")

from workflow.graph import graph
from workflow.state import RFQState

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    1: {
        "name": "Manufacturing — Standard Hardware Order",
        "expected": "auto-dispatch",
        "rfq": """
From: Rajesh Kumar, Purchase Manager
Company: Bharat Fabricators Pvt Ltd
Contact: rajesh.kumar@bharatfab.com | +91-98765-43210
Delivery: Plot 12, MIDC Industrial Area, Pune 411019
RFQ Deadline: 25 July 2026

Dear Sir/Madam,

We require the following items for our production line. Please quote your best price.

1. M8 Stainless Steel Hex Bolt 50mm — Qty: 500 pcs
2. M8 Stainless Steel Hex Nut — Qty: 500 pcs
3. M8 Stainless Steel Flat Washer — Qty: 1000 pcs
4. Deep Groove Ball Bearing 6205-2RS — Qty: 20 pcs
5. Safety Helmet ISI Marked (Ratchet) — Qty: 25 pcs
6. Nitrile Safety Gloves Size L (Box 100) — Qty: 5 boxes

Payment terms: 30 days credit
Delivery required within 7 days of order confirmation.

Regards,
Rajesh Kumar
""",
    },

    2: {
        "name": "Electrical Contractor — Rush Site Order",
        "expected": "auto-dispatch (rush urgency)",
        "rfq": """
URGENT RFQ — Site work starts 17 July 2026

From: Suresh Electrical Works
Contact: suresh@sureshelectrical.in
Delivery: Site Office, NH-48 Bypass, Bengaluru 560100
Response needed by: 16 July 2026 EOD

We need the following items URGENTLY for an upcoming project:

1. Copper Wire 2.5 sqmm (100m roll) — 30 rolls
2. Copper Wire 6 sqmm (100m roll) — 10 rolls
3. MCB 32A Single Pole C-Curve — 40 pcs
4. AC Contactor 32A 3P 230V Coil — 15 pcs
5. Perforated Cable Tray 150x50mm per meter — 200 meters
6. Safety Shoe Steel Toe Size 8 — 10 pairs
7. Hi-Vis Reflective Safety Vest Size L — 20 pcs

This is a critical requirement. Please confirm availability and earliest delivery.
""",
    },

    3: {
        "name": "IT Procurement — Office Equipment",
        "expected": "auto-dispatch",
        "rfq": """
Request for Quotation — IT Equipment Procurement

Organization: Sunrise Exports Limited
Contact: it.admin@sunriseexports.com
Delivery Address: 4th Floor, DLF Cyber City, Gurugram 122002
Quote validity required: 30 days
RFQ Date: 14 July 2026

We invite quotations for the following IT equipment:

1. Laptop Core i5 13th Gen 8GB 512GB SSD — 15 units
2. UPS 1KVA Line Interactive — 15 units
3. WiFi 6 Router Dual Band — 5 units
4. Managed Switch 24-Port Gigabit — 2 units

All equipment should carry minimum 1-year warranty.
Delivery within 10 working days.
Payment: 100% on delivery against invoice.

Please include GST in your quote.

IT Administrator
Sunrise Exports Limited
""",
    },

    4: {
        "name": "Complex Mixed RFQ — Human Review Expected",
        "expected": "human review queue",
        "rfq": """
RFQ — Multiple Categories, Custom Specs

From: Global Manufacturing Co.
Contact: purchase@globalmfg.com
Delivery: Multiple locations (Pune + Chennai + Delhi warehouses)

Please quote for the following items. Some require custom specifications:

1. MS Plate 6mm 2500x1250mm — 50 sheets
2. SS 304 Pipe 2 inch SCH40 per meter — 500 meters
3. Aluminium Sheet 3mm 2438x1219mm — 30 sheets
4. Deep Groove Ball Bearing 6205-2RS — 200 pcs
5. Pillow Block Bearing UCF205 — 100 pcs
6. Custom fabricated brackets (non-standard, drawings attached) — 500 pcs
7. Industrial grade solvent cleaner, food-safe certified — 100 liters
8. MIG Welding Wire ER70S-6 0.8mm (15kg) — 20 spools
9. Cutting Disc 230x3x22.2mm (Box 25) — 30 boxes
10. Hydraulic Oil ISO VG 46 (20L) — 50 drums
11. Lithium Grease EP-2 (1kg) — 100 tins
12. Specialty high-temp gasket material, 600°C rated, 2mm thick — 200 sqm
13. Conveyor belt, rubber, 600mm wide, custom length 45m — 3 pieces
14. PLC controller Siemens S7-1200 compatible I/O modules — 15 units
15. Custom CNC machined parts as per drawing no. GMC-2026-447 — 100 pcs

Delivery required in 5 days across 3 locations.
Special packaging and third-party inspection required.
Contact for technical specs: engineering@globalmfg.com
""",
    },

    5: {
        "name": "Freight — Full Truckload Mumbai to Delhi",
        "expected": "auto-dispatch (freight quotation)",
        "rfq": """
Hi,

We need to transport machine parts from our Mumbai warehouse to our Delhi plant.
The cargo weighs approximately 8 tons and consists of steel fabricated assemblies.

Please quote for a large truck (full truckload).

Pickup: Bhiwandi, Mumbai (warehouse near NH-48)
Delivery: Okhla Industrial Area Phase 2, New Delhi

We need it delivered within 3 days.

Contact: logistics@techparts.in
Company: TechParts India Pvt Ltd
""",
    },

    6: {
        "name": "Freight — Small Tempo Bangalore to Pune",
        "expected": "auto-dispatch (freight quotation)",
        "rfq": """
Need a small tempo/mini truck to move office equipment.

From: Koramangala, Bangalore
To: Hinjewadi, Pune

Items: 15 office chairs, 8 desks, 5 desktop computers, boxes of stationery
Approx weight: 400 kg

No particular urgency, flexible on date.
Please quote.

- Admin, Startup Hub
""",
    },
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _make_state(scenario: dict) -> RFQState:
    return RFQState(
        rfq_id=str(uuid.uuid4()),
        source="upload",
        sender="simulation@test.com",
        raw_content=scenario["rfq"].strip(),
        attachment_path=None,
        attachment_url=None,
        subject=scenario["name"],
        rfq_type=None,
        line_items=[],
        missing_fields=[],
        buyer_name=None,
        buyer_contact=None,
        delivery_location=None,
        rfq_deadline=None,
        urgency="standard",
        complexity="auto",
        category=None,
        catalog_matches=[],
        feasibility=[],
        unfulfillable_items=[],
        line_pricing=[],
        subtotal=0.0,
        total=0.0,
        pricing_confidence=0.0,
        freight_origin=None,
        freight_destination=None,
        freight_cargo_desc=None,
        freight_weight_kg=None,
        freight_volume_cbm=None,
        freight_truck_type=None,
        freight_distance_km=None,
        freight_quote_amount=None,
        draft_quote=None,
        pdf_path=None,
        status="processing",
        review_notes=None,
        error=None,
    )


def _print_result(scenario_num: int, scenario: dict, result: RFQState):
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  SCENARIO {scenario_num}: {scenario['name']}")
    print(f"  Expected: {scenario['expected']}")
    print(sep)

    print(f"\n  RFQ ID     : {result.get('rfq_id','')[:8].upper()}")
    print(f"  Status     : {result.get('status','').upper()}")
    print(f"  Buyer      : {result.get('buyer_name','—')}")
    print(f"  Urgency    : {result.get('urgency','—')}")
    print(f"  Complexity : {result.get('complexity','—')}")
    print(f"  Category   : {result.get('category','—')}")
    print(f"  Line items : {len(result.get('line_items') or [])}")
    print(f"  Confidence : {result.get('pricing_confidence', 0.0):.0%}")
    print(f"  Total      : ₹{result.get('total', 0.0):,.2f}")

    if result.get("missing_fields"):
        print(f"  Missing    : {', '.join(result['missing_fields'])}")

    if result.get("unfulfillable_items"):
        print(f"  Unfulfillable item indices: {result['unfulfillable_items']}")

    if result.get("review_notes"):
        print(f"\n  Review note: {result['review_notes']}")

    if result.get("error"):
        print(f"\n  ERROR: {result['error']}")

    if result.get("rfq_type") == "freight":
        print(f"\n--- FREIGHT DETAILS ---")
        print(f"  Origin      : {result.get('freight_origin', '—')}")
        print(f"  Destination : {result.get('freight_destination', '—')}")
        print(f"  Cargo       : {result.get('freight_cargo_desc', '—')}")
        print(f"  Weight      : {result.get('freight_weight_kg', '—')} kg")
        print(f"  Truck type  : {result.get('freight_truck_type', '—')}")
        print(f"  Distance    : ~{result.get('freight_distance_km', '—')} km")
        print(f"  Quote       : ₹{result.get('freight_quote_amount', 0.0):,.2f}")
    else:
        print(f"\n--- PRICING BREAKDOWN ---")
        matches = {m["line_item_index"]: m for m in (result.get("catalog_matches") or [])}
        for lp in (result.get("line_pricing") or []):
            i = lp["line_item_index"]
            item = (result.get("line_items") or [])[i] if i < len(result.get("line_items") or []) else {}
            status_icon = "✓" if lp["unit_price"] > 0 else "✗"
            discount = f" -{lp['discount_pct']:.0%}" if lp.get("discount_pct") else ""
            rush = f" +{lp['rush_premium_pct']:.0%} rush" if lp.get("rush_premium_pct") else ""
            print(f"  [{status_icon}] {item.get('description','')[:45]:<45} "
                  f"Qty:{lp['quantity']:>6}  "
                  f"₹{lp['unit_price']:>8,.2f}{discount}{rush}  "
                  f"= ₹{lp['subtotal']:>10,.2f}")

    print(f"\n{'':>57} TOTAL = ₹{result.get('total', 0.0):>10,.2f}")

    if result.get("draft_quote"):
        print(f"\n--- DRAFT QUOTATION (first 800 chars) ---")
        print(result["draft_quote"][:800])
        if len(result["draft_quote"]) > 800:
            print("  [...truncated...]")

    print(f"\n{sep}\n")


async def run_scenario(num: int, scenario: dict):
    print(f"\nRunning scenario {num}: {scenario['name']} ...")
    state = _make_state(scenario)
    config = {"configurable": {"thread_id": state["rfq_id"]}}
    result = await graph.ainvoke(state, config=config)
    _print_result(num, scenario, result)
    return result


async def main(scenario_nums: list[int]):
    for num in scenario_nums:
        scenario = SCENARIOS[num]
        await run_scenario(num, scenario)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Run a specific scenario (default: all)")
    args = parser.parse_args()

    nums = [args.scenario] if args.scenario else [1, 2, 3, 4, 5, 6]
    asyncio.run(main(nums))
