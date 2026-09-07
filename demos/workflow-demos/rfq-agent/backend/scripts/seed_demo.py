"""
Seed realistic demo RFQ submissions into rfq_submissions table.

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --clear   # wipe existing records first
"""
import sys, os, argparse, uuid, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
_local = Path(__file__).resolve().parent.parent / ".env"
if _local.exists():
    load_dotenv(_local, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import psycopg
import json
from datetime import datetime, timedelta
import random

DB_SCHEMA = os.getenv("DB_SCHEMA", "rfq")


def _get_conn():
    url = os.getenv("DATABASE_URL", "")
    url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://").replace("postgres://", "postgresql://")
    return psycopg.connect(url)


DEMO_RFQS = [
    # --- Auto-dispatched ---
    {
        "buyer_name": "Manoj Enterprises",
        "sender": "manoj@manojenterprises.in",
        "source": "email",
        "subject": "RFQ - Fasteners and Hardware",
        "category": "industrial_components",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Pune Industrial Area, MIDC",
        "rfq_deadline": "2026-08-20",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.91,
        "total": 7150.0,
        "subtotal": 6483.0,
        "days_ago": 1,
        "line_items": [
            {"description": "M8 Stainless Steel Hex Bolt 50mm", "quantity": 500, "unit": "pcs", "specs": "SS 316"},
            {"description": "M8 Stainless Steel Hex Nut", "quantity": 500, "unit": "pcs", "specs": "SS 316"},
            {"description": "M8 Flat Washer SS", "quantity": 1000, "unit": "pcs", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 8.50, "quantity": 500, "subtotal": 4250.0, "discount_pct": 0.05, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 1, "unit_price": 3.50, "quantity": 500, "subtotal": 1750.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 2, "unit_price": 1.50, "quantity": 1000, "subtotal": 1500.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": """QUOTATION — Q-2026-0047

Date: 03 Aug 2026
Valid Until: 03 Sep 2026

To: Manoj Enterprises
Attn: Manoj
Email: manoj@manojenterprises.in
Delivery: Pune Industrial Area, MIDC

RE: Your RFQ dated 02 Aug 2026

Dear Manoj,

Thank you for your inquiry. We are pleased to submit our quotation for the following items:

| # | Description                     | Qty  | Unit | Unit Price | Subtotal    |
|---|----------------------------------|------|------|------------|-------------|
| 1 | M8 SS 316 Hex Bolt 50mm DIN 931  | 500  | pcs  | ₹8.08      | ₹4,037.50   |
| 2 | M8 SS 316 Hex Nut DIN 934        | 500  | pcs  | ₹3.50      | ₹1,750.00   |
| 3 | M8 SS 304 Flat Washer DIN 125    | 1000 | pcs  | ₹1.50      | ₹1,500.00   |

                                        Subtotal: ₹7,287.50
                                        GST 18%:  ₹1,311.75
                                        TOTAL:    ₹8,599.25

Lead Time: 3 working days
Payment: 50% advance, balance before dispatch
Delivery: Pune MIDC (transport at actuals)

This quotation is valid for 30 days from date of issue.

Regards,
InnovizeAI Procurement
admin@innovizeai.com""",
    },
    {
        "buyer_name": "Rajesh Steel Works",
        "sender": "purchase@rajeshsteel.com",
        "source": "email",
        "subject": "Steel Requirement - August",
        "category": "raw_materials",
        "urgency": "rush",
        "complexity": "auto",
        "delivery_location": "Bhiwandi, Maharashtra",
        "rfq_deadline": "2026-08-10",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.87,
        "total": 312000.0,
        "subtotal": 264407.0,
        "days_ago": 2,
        "line_items": [
            {"description": "MS Plate 6mm 2500x1250mm", "quantity": 40, "unit": "sheets", "specs": "IS 2062 E250"},
            {"description": "MS Angle 50x50x6mm", "quantity": 200, "unit": "meters", "specs": "IS 2062"},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 4200.0, "quantity": 40, "subtotal": 168000.0, "discount_pct": 0.0, "rush_premium_pct": 0.05, "notes": "Rush premium applied"},
            {"line_item_index": 1, "unit_price": 220.0, "quantity": 200, "subtotal": 44000.0, "discount_pct": 0.0, "rush_premium_pct": 0.05, "notes": "Rush premium applied"},
        ],
        "draft_quote": """QUOTATION — Q-2026-0046

Date: 02 Aug 2026 | Valid Until: 02 Sep 2026

To: Rajesh Steel Works | purchase@rajeshsteel.com
Delivery: Bhiwandi, Maharashtra by 10 Aug 2026

Dear Sir/Madam,

| # | Item                        | Qty | Unit   | Unit Price  | Subtotal     |
|---|-----------------------------|-----|--------|-------------|--------------|
| 1 | MS Plate 6mm IS 2062 E250   |  40 | sheets | ₹4,410.00   | ₹1,76,400.00 |
| 2 | MS Angle 50x50x6mm IS 2062  | 200 | mtr    | ₹231.00     | ₹46,200.00   |

Subtotal: ₹2,22,600.00 | GST 18%: ₹40,068.00 | TOTAL: ₹2,62,668.00

Note: 5% rush premium applied. Delivery within 5 working days.
Payment: 50% advance, balance on delivery.

InnovizeAI Procurement | admin@innovizeai.com""",
    },
    {
        "buyer_name": "Delhi Auto Parts",
        "sender": "orders@delhiautoparts.in",
        "source": "whatsapp",
        "subject": "Bearings and Belts Requirement",
        "category": "industrial_components",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Okhla Industrial Estate, Delhi",
        "rfq_deadline": "2026-08-25",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.93,
        "total": 28600.0,
        "subtotal": 24237.0,
        "days_ago": 2,
        "line_items": [
            {"description": "Deep Groove Ball Bearing 6205-2RS", "quantity": 50, "unit": "pcs", "specs": None},
            {"description": "Pillow Block Bearing UCF205", "quantity": 20, "unit": "pcs", "specs": None},
            {"description": "V-Belt A50", "quantity": 30, "unit": "pcs", "specs": "A-section"},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 180.0, "quantity": 50, "subtotal": 9000.0, "discount_pct": 0.05, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 1, "unit_price": 450.0, "quantity": 20, "subtotal": 9000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 2, "unit_price": 220.0, "quantity": 30, "subtotal": 6600.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": "QUOTATION Q-2026-0045 | Delhi Auto Parts | Bearings & Belts | Total: ₹28,600 | Dispatched via WhatsApp",
    },
    {
        "buyer_name": "Coastal Packaging",
        "sender": "rahul@coastalpkg.com",
        "source": "upload",
        "subject": "Monthly Packaging Material Order",
        "category": "packaging",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Navi Mumbai",
        "rfq_deadline": "2026-08-15",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.96,
        "total": 18500.0,
        "subtotal": 15678.0,
        "days_ago": 3,
        "line_items": [
            {"description": "Corrugated Box 30x20x20cm 5-ply", "quantity": 10, "unit": "bundles", "specs": None},
            {"description": "Stretch Wrap Film 500mm", "quantity": 20, "unit": "rolls", "specs": None},
            {"description": "PP Strapping Roll 12mm", "quantity": 5, "unit": "rolls", "specs": None},
            {"description": "BOPP Packing Tape 48mm", "quantity": 3, "unit": "boxes", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 1100.0, "quantity": 10, "subtotal": 11000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 1, "unit_price": 380.0, "quantity": 20, "subtotal": 7600.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 2, "unit_price": 950.0, "quantity": 5, "subtotal": 4750.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 3, "unit_price": 1100.0, "quantity": 3, "subtotal": 3300.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": "QUOTATION Q-2026-0044 | Coastal Packaging | Packaging materials | Total: ₹18,500 | Auto-dispatched",
    },
    {
        "buyer_name": "Punjab Agro Industries",
        "sender": "purchase@punjabagro.in",
        "source": "email",
        "subject": "Welding Consumables RFQ",
        "category": "industrial_components",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Ludhiana, Punjab",
        "rfq_deadline": "2026-08-22",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.89,
        "total": 42800.0,
        "subtotal": 36271.0,
        "days_ago": 3,
        "line_items": [
            {"description": "Welding Electrode E6013 3.15mm", "quantity": 20, "unit": "packs", "specs": "5kg each"},
            {"description": "Cutting Disc 230mm", "quantity": 10, "unit": "boxes", "specs": None},
            {"description": "Grinding Disc 125mm", "quantity": 8, "unit": "boxes", "specs": None},
            {"description": "HSS Drill Bit 10mm", "quantity": 50, "unit": "pcs", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 650.0, "quantity": 20, "subtotal": 13000.0, "discount_pct": 0.05, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 1, "unit_price": 900.0, "quantity": 10, "subtotal": 9000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 2, "unit_price": 850.0, "quantity": 8, "subtotal": 6800.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 3, "unit_price": 85.0, "quantity": 50, "subtotal": 4250.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": "QUOTATION Q-2026-0043 | Punjab Agro Industries | Welding consumables | Total: ₹42,800",
    },
    {
        "buyer_name": "Mehta Trading Co",
        "sender": "mehta@mehtatrading.com",
        "source": "upload",
        "subject": "Lubricants Monthly Requirement",
        "category": "industrial_components",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Surat, Gujarat",
        "rfq_deadline": "2026-08-18",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.94,
        "total": 36400.0,
        "subtotal": 30847.0,
        "days_ago": 4,
        "line_items": [
            {"description": "Hydraulic Oil ISO VG 46 20L", "quantity": 10, "unit": "cans", "specs": None},
            {"description": "Lithium Grease EP-2 1kg", "quantity": 20, "unit": "tins", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 2800.0, "quantity": 10, "subtotal": 28000.0, "discount_pct": 0.03, "rush_premium_pct": 0.0, "notes": "Volume discount"},
            {"line_item_index": 1, "unit_price": 320.0, "quantity": 20, "subtotal": 6400.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": "QUOTATION Q-2026-0042 | Mehta Trading Co | Lubricants | Total: ₹36,400 | Auto-dispatched",
    },
    {
        "buyer_name": "Tech Solutions Pvt Ltd",
        "sender": "it@techsolutionspvt.com",
        "source": "email",
        "subject": "IT Hardware Procurement Q3",
        "category": "it_hardware",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Bangalore, Karnataka",
        "rfq_deadline": "2026-08-30",
        "rfq_type": "product",
        "status": "dispatched",
        "pricing_confidence": 0.88,
        "total": 374000.0,
        "subtotal": 316949.0,
        "days_ago": 4,
        "line_items": [
            {"description": "Laptop Core i5 13th Gen 8GB 512GB", "quantity": 5, "unit": "pcs", "specs": "Business grade"},
            {"description": "UPS 1KVA", "quantity": 5, "unit": "pcs", "specs": "Line interactive"},
            {"description": "WiFi 6 Router", "quantity": 3, "unit": "pcs", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 52000.0, "quantity": 5, "subtotal": 260000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 1, "unit_price": 7500.0, "quantity": 5, "subtotal": 37500.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 2, "unit_price": 6500.0, "quantity": 3, "subtotal": 19500.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": "QUOTATION Q-2026-0041 | Tech Solutions | IT Hardware | Total: ₹3,74,000 | Auto-dispatched",
    },
    # --- Freight dispatched ---
    {
        "buyer_name": "Ravi Logistics",
        "sender": "ravi@ravilogistics.in",
        "source": "whatsapp",
        "subject": "Transport RFQ Mumbai to Delhi",
        "category": "services",
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": "Delhi",
        "rfq_deadline": "2026-08-12",
        "rfq_type": "freight",
        "status": "dispatched",
        "pricing_confidence": 0.85,
        "total": 38500.0,
        "subtotal": 32627.0,
        "days_ago": 1,
        "freight_origin": "Mumbai",
        "freight_destination": "Delhi",
        "freight_cargo_desc": "Steel pipes and structural material",
        "freight_weight_kg": 8000.0,
        "freight_truck_type": "large",
        "freight_distance_km": 1400.0,
        "freight_quote_amount": 38500.0,
        "line_items": [],
        "line_pricing": [],
        "draft_quote": "FREIGHT QUOTE Q-2026-F012 | Ravi Logistics | Mumbai→Delhi | 8 MT steel | Large truck | ₹38,500 incl GST",
    },
    {
        "buyer_name": "Sharma Brothers Transport",
        "sender": "amit.sharma@sharmatransport.com",
        "source": "email",
        "subject": "Heavy Machinery Transport - Hyderabad to Pune",
        "category": "services",
        "urgency": "rush",
        "complexity": "auto",
        "delivery_location": "Pune",
        "rfq_deadline": "2026-08-08",
        "rfq_type": "freight",
        "status": "dispatched",
        "pricing_confidence": 0.82,
        "total": 68000.0,
        "subtotal": 57627.0,
        "days_ago": 2,
        "freight_origin": "Hyderabad",
        "freight_destination": "Pune",
        "freight_cargo_desc": "CNC machine and ancillary equipment",
        "freight_weight_kg": 18000.0,
        "freight_truck_type": "trailer",
        "freight_distance_km": 560.0,
        "freight_quote_amount": 68000.0,
        "line_items": [],
        "line_pricing": [],
        "draft_quote": "FREIGHT QUOTE Q-2026-F011 | Sharma Brothers | Hyderabad→Pune | 18 MT CNC machine | Multi-axle trailer | ₹68,000 incl GST",
    },
    # --- Pending review ---
    {
        "buyer_name": "Sharma Construction Ltd",
        "sender": "procurement@sharmaconstruction.in",
        "source": "email",
        "subject": "Construction Material RFQ - Site #12",
        "category": "raw_materials",
        "urgency": "critical",
        "complexity": "review",
        "delivery_location": "Whitefield, Bangalore",
        "rfq_deadline": "2026-08-06",
        "rfq_type": "product",
        "status": "pending_review",
        "pricing_confidence": 0.62,
        "total": 892000.0,
        "subtotal": 755932.0,
        "days_ago": 1,
        "line_items": [
            {"description": "TMT bars 12mm Fe500", "quantity": 10, "unit": "MT", "specs": "IS 1786"},
            {"description": "Binding wire", "quantity": 50, "unit": "kg", "specs": None},
            {"description": "MS Plate 6mm", "quantity": 20, "unit": "sheets", "specs": None},
        ],
        "line_pricing": [],
        "draft_quote": None,
        "review_notes": "High-value order (₹8.9L) with critical deadline in 3 days. TMT bars not in standard catalog — custom procurement required. Manual approval needed.",
    },
    {
        "buyer_name": "Mumbai Electrical Supplies",
        "sender": "purchase@mumbaielectrical.com",
        "source": "email",
        "subject": "Electrical Panel Components",
        "category": "industrial_components",
        "urgency": "rush",
        "complexity": "review",
        "delivery_location": "Andheri, Mumbai",
        "rfq_deadline": "2026-08-09",
        "rfq_type": "product",
        "status": "pending_review",
        "pricing_confidence": 0.71,
        "total": 156000.0,
        "subtotal": 132203.0,
        "days_ago": 2,
        "line_items": [
            {"description": "Copper Wire 6 sqmm 100m roll", "quantity": 20, "unit": "rolls", "specs": "FR grade"},
            {"description": "AC Contactor 32A", "quantity": 30, "unit": "pcs", "specs": "3P 230V"},
            {"description": "MCB 32A Single Pole", "quantity": 50, "unit": "pcs", "specs": "C-curve"},
            {"description": "Perforated Cable Tray 150x50mm", "quantity": 100, "unit": "meters", "specs": None},
        ],
        "line_pricing": [
            {"line_item_index": 0, "unit_price": 4200.0, "quantity": 20, "subtotal": 84000.0, "discount_pct": 0.0, "rush_premium_pct": 0.05, "notes": "Rush premium"},
            {"line_item_index": 1, "unit_price": 1200.0, "quantity": 30, "subtotal": 36000.0, "discount_pct": 0.0, "rush_premium_pct": 0.05, "notes": "Rush premium"},
            {"line_item_index": 2, "unit_price": 380.0, "quantity": 50, "subtotal": 19000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
            {"line_item_index": 3, "unit_price": 320.0, "quantity": 100, "subtotal": 32000.0, "discount_pct": 0.0, "rush_premium_pct": 0.0, "notes": None},
        ],
        "draft_quote": None,
        "review_notes": "Pricing confidence 71% — copper wire pricing volatile, recommend manual price check before dispatching.",
    },
    {
        "buyer_name": "Hyderabad Cable Industries",
        "sender": "hyd.cables@hci.co.in",
        "source": "upload",
        "subject": "Cable Tray and Conduit RFQ",
        "category": "industrial_components",
        "urgency": "rush",
        "complexity": "review",
        "delivery_location": "Medchal, Hyderabad",
        "rfq_deadline": "2026-08-10",
        "rfq_type": "product",
        "status": "pending_review",
        "pricing_confidence": 0.68,
        "total": 215000.0,
        "subtotal": 182203.0,
        "days_ago": 3,
        "line_items": [
            {"description": "Perforated Cable Tray 150x50mm", "quantity": 500, "unit": "meters", "specs": "GI 1.6mm"},
            {"description": "Copper Wire 2.5 sqmm 100m", "quantity": 30, "unit": "rolls", "specs": None},
        ],
        "line_pricing": [],
        "draft_quote": None,
        "review_notes": "Large order (500m cable tray). Pricing confidence below threshold — current stock uncertain for this quantity. Needs confirmation.",
    },
    {
        "buyer_name": "Phoenix Electronics",
        "sender": "procurement@phoenixelec.com",
        "source": "email",
        "subject": "Network Infrastructure - Data Center Expansion",
        "category": "it_hardware",
        "urgency": "standard",
        "complexity": "review",
        "delivery_location": "Chennai, Tamil Nadu",
        "rfq_deadline": "2026-08-28",
        "rfq_type": "product",
        "status": "pending_review",
        "pricing_confidence": 0.55,
        "total": 540000.0,
        "subtotal": 457627.0,
        "days_ago": 5,
        "line_items": [
            {"description": "Managed Switch 24-Port Gigabit", "quantity": 10, "unit": "pcs", "specs": "VLAN capable"},
            {"description": "UPS 1KVA", "quantity": 10, "unit": "pcs", "specs": None},
            {"description": "WiFi 6 Router", "quantity": 15, "unit": "pcs", "specs": None},
        ],
        "line_pricing": [],
        "draft_quote": None,
        "review_notes": "Managed switches currently out of stock (lead time 14 days). Confidence 55% — cannot auto-fulfill partial order. Manual coordination needed.",
    },
    # --- Processing (in progress) ---
    {
        "buyer_name": "Krishna Engineering Works",
        "sender": "krishna@kewpune.in",
        "source": "whatsapp",
        "subject": None,
        "category": None,
        "urgency": "standard",
        "complexity": "auto",
        "delivery_location": None,
        "rfq_deadline": None,
        "rfq_type": "product",
        "status": "processing",
        "pricing_confidence": 0.0,
        "total": 0.0,
        "subtotal": 0.0,
        "days_ago": 0,
        "line_items": [],
        "line_pricing": [],
        "draft_quote": None,
    },
    # --- Failed ---
    {
        "buyer_name": "Greenfield Pharma",
        "sender": "procurement@greenfield-pharma.com",
        "source": "email",
        "subject": "Lab Equipment - Pharma Grade",
        "category": "other",
        "urgency": "standard",
        "complexity": "review",
        "delivery_location": "Hyderabad Pharma City",
        "rfq_deadline": "2026-08-20",
        "rfq_type": "product",
        "status": "failed",
        "pricing_confidence": 0.0,
        "total": 0.0,
        "subtotal": 0.0,
        "days_ago": 6,
        "line_items": [
            {"description": "SS 316L reactor vessel 50L", "quantity": 2, "unit": "pcs", "specs": "Pharma grade, cGMP"},
            {"description": "Peristaltic pump 100 LPH", "quantity": 1, "unit": "pcs", "specs": None},
        ],
        "line_pricing": [],
        "draft_quote": None,
        "review_notes": None,
        "error": "Parser error: RFQ contains highly specialized pharma-grade equipment not in catalog. Unable to generate quotation automatically.",
    },
]


def seed(clear: bool = False):
    conn = _get_conn()
    cur = conn.cursor()

    if clear:
        cur.execute(f"DELETE FROM {DB_SCHEMA}.rfq_submissions")
        print(f"Cleared existing records from {DB_SCHEMA}.rfq_submissions")

    now = datetime.utcnow()
    inserted = 0

    for rfq in DEMO_RFQS:
        rfq_id = str(uuid.uuid4())
        days_ago = rfq.pop("days_ago", 0)
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 8), minutes=random.randint(0, 59))

        freight_fields = {k: rfq.pop(k, None) for k in [
            "freight_origin", "freight_destination", "freight_cargo_desc",
            "freight_weight_kg", "freight_truck_type", "freight_distance_km",
            "freight_quote_amount", "freight_volume_cbm"
        ]}

        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.rfq_submissions (
                rfq_id, created_at, source, sender, subject,
                buyer_name, buyer_contact, delivery_location, rfq_deadline,
                urgency, complexity, category,
                line_items, catalog_matches, feasibility, unfulfillable_items,
                line_pricing, subtotal, total, pricing_confidence,
                draft_quote, dispatched_at, status, review_notes, error,
                rfq_type,
                freight_origin, freight_destination, freight_cargo_desc,
                freight_weight_kg, freight_volume_cbm, freight_truck_type,
                freight_distance_km, freight_quote_amount
            ) VALUES (
                %(rfq_id)s, %(created_at)s, %(source)s, %(sender)s, %(subject)s,
                %(buyer_name)s, %(buyer_contact)s, %(delivery_location)s, %(rfq_deadline)s,
                %(urgency)s, %(complexity)s, %(category)s,
                %(line_items)s, %(catalog_matches)s, %(feasibility)s, %(unfulfillable_items)s,
                %(line_pricing)s, %(subtotal)s, %(total)s, %(pricing_confidence)s,
                %(draft_quote)s, %(dispatched_at)s, %(status)s, %(review_notes)s, %(error)s,
                %(rfq_type)s,
                %(freight_origin)s, %(freight_destination)s, %(freight_cargo_desc)s,
                %(freight_weight_kg)s, %(freight_volume_cbm)s, %(freight_truck_type)s,
                %(freight_distance_km)s, %(freight_quote_amount)s
            )
        """, {
            "rfq_id": rfq_id,
            "created_at": created_at,
            "dispatched_at": created_at if rfq.get("status") == "dispatched" else None,
            "source": rfq.get("source"),
            "sender": rfq.get("sender"),
            "subject": rfq.get("subject"),
            "buyer_name": rfq.get("buyer_name"),
            "buyer_contact": None,
            "delivery_location": rfq.get("delivery_location"),
            "rfq_deadline": rfq.get("rfq_deadline"),
            "urgency": rfq.get("urgency", "standard"),
            "complexity": rfq.get("complexity", "auto"),
            "category": rfq.get("category"),
            "line_items": json.dumps(rfq.get("line_items", [])),
            "catalog_matches": json.dumps([]),
            "feasibility": json.dumps([]),
            "unfulfillable_items": json.dumps([]),
            "line_pricing": json.dumps(rfq.get("line_pricing", [])),
            "subtotal": rfq.get("subtotal", 0.0),
            "total": rfq.get("total", 0.0),
            "pricing_confidence": rfq.get("pricing_confidence", 0.0),
            "draft_quote": rfq.get("draft_quote"),
            "status": rfq.get("status", "processing"),
            "review_notes": rfq.get("review_notes"),
            "error": rfq.get("error"),
            "rfq_type": rfq.get("rfq_type", "product"),
            **freight_fields,
        })
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\nSeeded {inserted} demo RFQ submissions into {DB_SCHEMA}.rfq_submissions")
    print("Status breakdown:")
    statuses = {}
    for r in DEMO_RFQS:
        s = r.get("status", "processing")
        statuses[s] = statuses.get(s, 0) + 1
    for s, count in sorted(statuses.items()):
        print(f"  {s}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear existing records first")
    args = parser.parse_args()
    seed(clear=args.clear)
