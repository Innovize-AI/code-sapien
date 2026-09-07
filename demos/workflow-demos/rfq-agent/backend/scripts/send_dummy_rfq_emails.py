"""
Send realistic dummy RFQ emails to the configured Gmail inbox.
Each email represents a different industry / document type and includes
one or more attachments (Excel BOQ, PDF quote request, plain text).

Usage:
    python scripts/send_dummy_rfq_emails.py              # send all 6 scenarios
    python scripts/send_dummy_rfq_emails.py --index 2   # send just scenario #2 (0-based)
    python scripts/send_dummy_rfq_emails.py --list       # print scenario list

Requirements (already in env):  openpyxl, reportlab, smtplib (stdlib)
"""
import argparse
import io
import os
import smtplib
import sys
import textwrap
from datetime import date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── env ──────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
_local = Path(__file__).resolve().parent.parent / ".env"
if _local.exists():
    load_dotenv(_local, override=True)

GMAIL_USER     = os.getenv("GMAIL_USER", "").strip().strip('"')
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "").strip().strip('"')


# ── attachment builders ───────────────────────────────────────────────────────

def make_excel_boq(rows: list[dict], sheet_name: str = "BOQ") -> bytes:
    """Create an Excel BOQ with columns: Item Ref, Description, Unit, Qty, Remarks."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    headers = ["Item Ref", "Description", "Unit", "Qty", "Brand / Spec", "Remarks"]

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for r, row in enumerate(rows, 2):
        ws.cell(row=r, column=1, value=row.get("ref", f"ITEM-{r-1:03d}"))
        ws.cell(row=r, column=2, value=row["description"])
        ws.cell(row=r, column=3, value=row.get("unit", "NOS"))
        ws.cell(row=r, column=4, value=row.get("qty", 1))
        ws.cell(row=r, column=5, value=row.get("spec", "As per spec"))
        ws.cell(row=r, column=6, value=row.get("remarks", ""))

    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["E"].width = 25

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_excel_lane_bid(lanes: list[dict]) -> bytes:
    """Freight/logistics lane bid sheet."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lane Bids"

    fill = PatternFill("solid", fgColor="00548B")
    font = Font(color="FFFFFF", bold=True)
    headers = ["Lane #", "Origin", "Destination", "Mode", "Equipment / Container",
               "Frequency (monthly)", "Incoterm", "Target Rate (USD)", "Remarks"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")

    for r, lane in enumerate(lanes, 2):
        ws.cell(row=r, column=1, value=lane.get("lane_no", r - 1))
        ws.cell(row=r, column=2, value=lane["origin"])
        ws.cell(row=r, column=3, value=lane["destination"])
        ws.cell(row=r, column=4, value=lane.get("mode", "Sea"))
        ws.cell(row=r, column=5, value=lane.get("equipment", "20' FCL"))
        ws.cell(row=r, column=6, value=lane.get("freq", 4))
        ws.cell(row=r, column=7, value=lane.get("incoterm", "FOB"))
        ws.cell(row=r, column=8, value=lane.get("target_rate", ""))
        ws.cell(row=r, column=9, value=lane.get("remarks", ""))

    for col in ["B", "C", "E"]:
        ws.column_dimensions[col].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def make_pdf_rfq(title: str, company: str, contact: str, items: list[dict],
                 notes: str = "", deadline: str = "") -> bytes:
    """Create a PDF RFQ document using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>From:</b> {company}", styles["Normal"]))
    story.append(Paragraph(f"<b>Contact:</b> {contact}", styles["Normal"]))
    if deadline:
        story.append(Paragraph(f"<b>Quote Required By:</b> {deadline}", styles["Normal"]))
    story.append(Spacer(1, 6*mm))

    table_data = [["#", "Description", "Qty", "Unit", "Specification"]]
    for i, item in enumerate(items, 1):
        table_data.append([
            str(i),
            item["description"],
            str(item.get("qty", 1)),
            item.get("unit", "NOS"),
            item.get("spec", ""),
        ])

    tbl = Table(table_data, colWidths=[10*mm, 75*mm, 20*mm, 20*mm, 45*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)

    if notes:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("<b>Notes & Terms:</b>", styles["Normal"]))
        for line in notes.split("\n"):
            story.append(Paragraph(f"• {line.strip()}", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()


def make_excel_stores_requisition(items: list[dict], vessel: str, port: str) -> bytes:
    """Marine stores requisition sheet with IMPA codes."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stores Req"

    ws["A1"] = "STORES REQUISITION"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Vessel: {vessel}"
    ws["A3"] = f"Port of Delivery: {port}"
    ws["A4"] = f"Date Required: {(date.today() + timedelta(days=7)).strftime('%d-%b-%Y')}"
    ws.append([])

    fill = PatternFill("solid", fgColor="003366")
    font = Font(color="FFFFFF", bold=True)
    headers = ["IMPA Code", "ISSA Code", "Description", "Unit", "Qty Required", "Last Price (USD)", "Remarks"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=6, column=col, value=h)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")

    for r, item in enumerate(items, 7):
        ws.cell(row=r, column=1, value=item.get("impa", ""))
        ws.cell(row=r, column=2, value=item.get("issa", ""))
        ws.cell(row=r, column=3, value=item["description"])
        ws.cell(row=r, column=4, value=item.get("unit", "EA"))
        ws.cell(row=r, column=5, value=item.get("qty", 1))
        ws.cell(row=r, column=6, value=item.get("last_price", ""))
        ws.cell(row=r, column=7, value=item.get("remarks", ""))

    ws.column_dimensions["C"].width = 35
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── email scenarios ───────────────────────────────────────────────────────────

DEADLINE = (date.today() + timedelta(days=5)).strftime("%d %b %Y")

SCENARIOS = [

    # 1. Manufacturing — Excel BOQ
    {
        "subject": f"RFQ – Electrical Panel Components | Deadline {DEADLINE}",
        "from_name": "Ahmed Al-Rashidi",
        "from_email": "ahmed.rashidi@gulfelectro.ae",
        "body": textwrap.dedent(f"""
            Dear Supplier,

            Please find attached our Bill of Quantities for electrical panel components
            required for the Al Quoz Industrial Park expansion project.

            We require firm unit prices, lead times, and country of origin for each item.
            Delivery to: Jebel Ali Free Zone, Dubai, UAE.
            Quote validity: 30 days.
            Deadline for submission: {DEADLINE}

            Kindly confirm receipt and revert with your best offer.

            Best regards,
            Ahmed Al-Rashidi
            Procurement Manager — Gulf Electro Industries LLC
            Tel: +971 4 885 6600
        """).strip(),
        "attachments": [
            {
                "filename": "BOQ_Electrical_Components_GEI.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "data_fn": lambda: make_excel_boq([
                    {"ref": "EL-001", "description": "MCB 32A Single Pole 10kA", "unit": "NOS", "qty": 120, "spec": "Schneider / ABB / Legrand", "remarks": "Type C curve"},
                    {"ref": "EL-002", "description": "MCCB 250A 3P 36kA", "unit": "NOS", "qty": 24, "spec": "Schneider EasyPact or equiv.", "remarks": "Fixed type"},
                    {"ref": "EL-003", "description": "Earth Leakage Circuit Breaker 40A 30mA", "unit": "NOS", "qty": 60, "spec": "IEC 61008 compliant"},
                    {"ref": "EL-004", "description": "Busbar Copper 100A 3-Phase", "unit": "MTR", "qty": 80, "spec": "99.9% pure copper"},
                    {"ref": "EL-005", "description": "DIN Rail 35mm Top Hat 1000mm", "unit": "PCS", "qty": 200, "spec": "Galvanised steel"},
                    {"ref": "EL-006", "description": "Terminal Block 4mm² Grey", "unit": "PCS", "qty": 500, "spec": "Phoenix or Wago"},
                    {"ref": "EL-007", "description": "Surge Protection Device Type 2", "unit": "NOS", "qty": 30, "spec": "IEC 61643-11"},
                    {"ref": "EL-008", "description": "Panel Enclosure 800×600×200 IP65", "unit": "NOS", "qty": 12, "spec": "Rittal or Schneider"},
                ], sheet_name="BOQ – Q3 2026"),
            }
        ],
    },

    # 2. Logistics / Freight — Excel lane bid
    {
        "subject": "Request for Quotation – Ocean Freight Rates | Dubai–India Lanes | Q4 2026",
        "from_name": "Priya Nair",
        "from_email": "priya.nair@transindialogistics.com",
        "body": textwrap.dedent(f"""
            Hi,

            We are inviting competitive freight rate quotes for our Q4 2026 import/export lanes
            between UAE and India. Please complete the attached rate sheet and return by {DEADLINE}.

            Scope of Quote:
            - FCL and LCL rates
            - Validity: October – December 2026
            - Include all origin charges, B/L fees, and destination THC separately

            For questions contact: priya.nair@transindialogistics.com | +91 98765 43210

            Regards,
            Priya Nair
            Head of Procurement — Trans India Logistics Pvt. Ltd.
        """).strip(),
        "attachments": [
            {
                "filename": "Lane_Bid_Sheet_Q4_2026.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "data_fn": lambda: make_excel_lane_bid([
                    {"lane_no": 1, "origin": "Jebel Ali, UAE", "destination": "Nhava Sheva (JNPT), India",
                     "mode": "Sea", "equipment": "20' FCL", "freq": 8, "incoterm": "FOB", "target_rate": 350},
                    {"lane_no": 2, "origin": "Jebel Ali, UAE", "destination": "Nhava Sheva (JNPT), India",
                     "mode": "Sea", "equipment": "40'HC FCL", "freq": 8, "incoterm": "FOB", "target_rate": 550},
                    {"lane_no": 3, "origin": "Jebel Ali, UAE", "destination": "Chennai, India",
                     "mode": "Sea", "equipment": "20' FCL", "freq": 4, "incoterm": "CFR", "target_rate": 400},
                    {"lane_no": 4, "origin": "Nhava Sheva, India", "destination": "Jebel Ali, UAE",
                     "mode": "Sea", "equipment": "40'HC FCL", "freq": 6, "incoterm": "FOB", "target_rate": 480},
                    {"lane_no": 5, "origin": "Dubai, UAE", "destination": "Delhi (ICD Tughlakabad), India",
                     "mode": "Air", "equipment": "Palletised cargo", "freq": 2, "incoterm": "EXW", "target_rate": "Per kg"},
                ]),
            }
        ],
    },

    # 3. Marine / Vessel supplies — Excel stores requisition
    {
        "subject": "Urgent Stores Requisition – MV Sea Phoenix | Port Hamad Arrival 3 days",
        "from_name": "Capt. Suresh Menon",
        "from_email": "suresh.menon@alphashipping.com",
        "body": textwrap.dedent(f"""
            Dear Chandler / Supplier,

            MV SEA PHOENIX (IMO 9456782) is arriving Port Hamad, Qatar in approximately 72 hours.
            Please quote immediately for the attached stores requisition.

            Vessel particulars:
              Type: Bulk Carrier | GRT: 28,500 | Flag: Panama
              ETA Port Hamad: {(date.today() + timedelta(days=3)).strftime('%d-%b-%Y')}

            Delivery must be alongside vessel at berth. Please confirm availability and quote
            by return. We require confirmation within 24 hours.

            Masters' instructions: No substitutions without prior approval.

            Rgds,
            Capt. Suresh Menon
            Master — MV Sea Phoenix
            Alpha Shipping & Trading Co.
            suresh.menon@alphashipping.com | +974 5512 3398
        """).strip(),
        "attachments": [
            {
                "filename": "Stores_Req_MV_SeaPhoenix.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "data_fn": lambda: make_excel_stores_requisition([
                    {"impa": "471033", "issa": "710.10", "description": "Engine Oil SAE 40 CD/CF (Drum 208L)", "unit": "DRM", "qty": 4, "last_price": 420},
                    {"impa": "471066", "issa": "710.30", "description": "Hydraulic Oil ISO VG 46 (Drum 208L)", "unit": "DRM", "qty": 2, "last_price": 380},
                    {"impa": "451150", "issa": "451.10", "description": "Grease Multipurpose NLGI 2 (18kg Pail)", "unit": "PCS", "qty": 6, "last_price": 85},
                    {"impa": "310174", "issa": "310.20", "description": "Safety Helmet White EN 397", "unit": "EA", "qty": 12, "last_price": 18},
                    {"impa": "310218", "issa": "310.25", "description": "Safety Boots Steel Toe S3 (Size 42)", "unit": "PAIR", "qty": 6, "last_price": 55},
                    {"impa": "150150", "issa": "150.10", "description": "Paint Anti-Corrosive Primer Red (20L)", "unit": "TIN", "qty": 8, "last_price": 95},
                    {"impa": "150380", "issa": "150.40", "description": "Paint Anti-Fouling (20L)", "unit": "TIN", "qty": 10, "last_price": 210},
                    {"impa": "232450", "issa": "232.10", "description": "Welding Electrode E6013 3.2mm (5kg box)", "unit": "BOX", "qty": 20, "last_price": 22},
                    {"impa": "614200", "issa": "614.10", "description": "Toilet Paper 2-ply Roll (48 pack)", "unit": "PKT", "qty": 10, "last_price": 28},
                    {"impa": "614350", "issa": "614.30", "description": "Liquid Dish Soap 5L Can", "unit": "CAN", "qty": 8, "last_price": 14},
                ], vessel="MV Sea Phoenix", port="Port Hamad, Qatar"),
            }
        ],
    },

    # 4. Construction — PDF with items table
    {
        "subject": f"RFQ – HVAC Equipment Supply | Mall Expansion Project | {DEADLINE}",
        "from_name": "Omar Khalil",
        "from_email": "omar.khalil@constructpro.ae",
        "body": textwrap.dedent(f"""
            Dear Vendor,

            Please find attached our RFQ for HVAC equipment required for the
            Ibn Battuta Mall East Wing Expansion, Dubai.

            Project timeline: Installation commences 01 Oct 2026.
            Delivery deadline: {DEADLINE}
            Delivery address: Ibn Battuta Mall Logistics Gate C, Jebel Ali, Dubai.

            Submission requirements:
            1. Itemised unit pricing in USD
            2. Technical datasheets for each item
            3. Lead time from purchase order
            4. Warranty terms

            Please send your offer to omar.khalil@constructpro.ae

            Omar Khalil | Senior Procurement Engineer
            ConstructPro International | Dubai Investment Park
            T: +971 4 220 4400
        """).strip(),
        "attachments": [
            {
                "filename": "RFQ_HVAC_MallExpansion_IBB.pdf",
                "content_type": "application/pdf",
                "data_fn": lambda: make_pdf_rfq(
                    title="RFQ – HVAC Equipment Supply",
                    company="ConstructPro International, Dubai",
                    contact="Omar Khalil | omar.khalil@constructpro.ae | +971 4 220 4400",
                    deadline=DEADLINE,
                    items=[
                        {"description": "Air Handling Unit 20,000 CFM", "qty": 4, "unit": "NOS", "spec": "Carrier / Trane / York"},
                        {"description": "Fan Coil Unit 4-pipe 1200 CFM", "qty": 60, "unit": "NOS", "spec": "Ceiling Concealed"},
                        {"description": "Chilled Water Pump 150 GPM 30m head", "qty": 8, "unit": "NOS", "spec": "Grundfos / Armstrong"},
                        {"description": "VAV Box with DDC Controller", "qty": 40, "unit": "NOS", "spec": "Siemens or equiv."},
                        {"description": "Duct Insulation Armaflex 25mm", "qty": 2500, "unit": "SQM", "spec": "Class O fire rated"},
                        {"description": "GI Ductwork Medium Pressure", "qty": 1800, "unit": "KG", "spec": "SMACNA standard"},
                        {"description": "Refrigerant R410A (11.3kg cylinder)", "qty": 30, "unit": "CYL", "spec": "Virgin refrigerant"},
                    ],
                    notes="All equipment to carry GCC conformity mark.\nPrices inclusive of delivery to site.\nQuote validity minimum 30 days.",
                ),
            }
        ],
    },

    # 5. Mixed email (no attachment — body-only RFQ)
    {
        "subject": "Quick Enquiry – Safety PPE Restock | Urgent",
        "from_name": "Ravi Sharma",
        "from_email": "ravi.sharma@industrialworks.in",
        "body": textwrap.dedent(f"""
            Hi,

            We need to urgently restock the following PPE items for our fabrication yard.
            Please send best prices and availability by {DEADLINE}.

            Items required:
            - Safety helmets (white, EN 397): 50 nos
            - Safety goggles (clear lens, anti-scratch): 100 nos
            - Leather welding gloves: 80 pairs
            - High-visibility vest (XL, Class 2): 60 nos
            - Ear plugs (disposable, NRR 33): 1000 pairs
            - Safety harness full body (EN 361): 20 nos
            - Steel toe safety boots (sizes 41–44): 30 pairs

            Delivery to: Industrial Works Ltd, MIDC Pune – 411026
            Payment: 30 days credit on approved PO.

            Please confirm if you can supply and quote with HSN codes for GST purposes.

            Regards,
            Ravi Sharma | Purchase Executive
            Industrial Works Ltd | +91 98201 55678
        """).strip(),
        "attachments": [],
    },

    # 6. Two attachments: PDF RFQ + Excel pricing template
    {
        "subject": "RFQ – IT Hardware Refresh Programme Q3 2026 | Due date: " + DEADLINE,
        "from_name": "Fatima Al-Sayed",
        "from_email": "fatima.alsayed@mena-tech.com",
        "body": textwrap.dedent(f"""
            Dear IT Hardware Vendor,

            MENA Tech Solutions is carrying out a quarterly hardware refresh for 3 offices
            across Dubai, Abu Dhabi, and Riyadh.

            Please review the attached RFQ document and complete the Pricing Template
            (Excel) with your best unit prices. Return both documents by {DEADLINE}.

            Scope: Laptops, monitors, docking stations, and peripherals.
            Budget indicative: USD 180,000.

            Vendors must be authorised resellers of quoted brands.
            Include warranty, SLA, and on-site support terms.

            Queries: fatima.alsayed@mena-tech.com

            Fatima Al-Sayed
            IT Procurement Lead — MENA Tech Solutions
            P.O. Box 45678, Dubai Media City, UAE
        """).strip(),
        "attachments": [
            {
                "filename": "RFQ_IT_Hardware_Refresh_Q3_2026.pdf",
                "content_type": "application/pdf",
                "data_fn": lambda: make_pdf_rfq(
                    title="IT Hardware Refresh – RFQ Q3 2026",
                    company="MENA Tech Solutions, Dubai Media City",
                    contact="Fatima Al-Sayed | fatima.alsayed@mena-tech.com",
                    deadline=DEADLINE,
                    items=[
                        {"description": "Business Laptop 14\" Intel i7 13th Gen, 16GB RAM, 512GB SSD", "qty": 75, "unit": "NOS", "spec": "Dell Latitude / HP EliteBook / Lenovo ThinkPad"},
                        {"description": "27\" 4K IPS Monitor USB-C", "qty": 80, "unit": "NOS", "spec": "Dell / LG / HP"},
                        {"description": "Universal Docking Station Thunderbolt 4", "qty": 75, "unit": "NOS", "spec": "Dell WD22 or equiv."},
                        {"description": "Wireless Keyboard & Mouse Combo", "qty": 75, "unit": "SET", "spec": "Logitech MX / Microsoft"},
                        {"description": "USB-C 65W Travel Charger", "qty": 80, "unit": "NOS", "spec": "Compatible with supplied laptops"},
                        {"description": "Laptop Bag 14\" Padded", "qty": 75, "unit": "NOS", "spec": "Branded or unbranded"},
                    ],
                    notes="3-year on-site warranty mandatory.\nAll prices in USD CIF Dubai.\nDelivery within 21 days of PO.",
                ),
            },
            {
                "filename": "Pricing_Template_IT_Hardware_Q3_2026.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "data_fn": lambda: make_excel_boq([
                    {"ref": "IT-001", "description": "Business Laptop 14\" i7/16GB/512GB", "unit": "NOS", "qty": 75, "spec": "Dell / HP / Lenovo", "remarks": "Fill unit price →"},
                    {"ref": "IT-002", "description": "27\" 4K IPS Monitor USB-C",         "unit": "NOS", "qty": 80, "spec": "Dell / LG / HP",    "remarks": "Fill unit price →"},
                    {"ref": "IT-003", "description": "Docking Station Thunderbolt 4",      "unit": "NOS", "qty": 75, "spec": "Dell WD22 / equiv.", "remarks": "Fill unit price →"},
                    {"ref": "IT-004", "description": "Wireless Keyboard & Mouse Combo",    "unit": "SET", "qty": 75, "spec": "Logitech / Microsoft","remarks": "Fill unit price →"},
                    {"ref": "IT-005", "description": "USB-C 65W Travel Charger",           "unit": "NOS", "qty": 80, "spec": "Compatible",         "remarks": "Fill unit price →"},
                    {"ref": "IT-006", "description": "Laptop Bag 14\" Padded",             "unit": "NOS", "qty": 75, "spec": "Any",                "remarks": "Fill unit price →"},
                ], sheet_name="Pricing Template"),
            },
        ],
    },
]


# ── SMTP sender ───────────────────────────────────────────────────────────────

def send_scenario(scenario: dict, to_email: str, dry_run: bool = False):
    msg = MIMEMultipart()
    msg["Subject"] = scenario["subject"]
    msg["From"]    = f"{scenario['from_name']} <{scenario['from_email']}>"
    msg["To"]      = to_email

    msg.attach(MIMEText(scenario["body"], "plain"))

    for att in scenario.get("attachments", []):
        data = att["data_fn"]()
        part = MIMEBase(*att["content_type"].split("/"))
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=att["filename"])
        msg.attach(part)

    if dry_run:
        attach_names = [a["filename"] for a in scenario.get("attachments", [])]
        print(f"  [DRY RUN] Would send: {scenario['subject']}")
        print(f"            Attachments: {attach_names or 'none'}")
        return

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASSWORD)
        smtp.sendmail(scenario["from_email"], to_email, msg.as_bytes())

    attach_names = [a["filename"] for a in scenario.get("attachments", [])]
    print(f"  ✓ Sent: {scenario['subject'][:70]}")
    if attach_names:
        print(f"    Attachments: {', '.join(attach_names)}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Send dummy RFQ emails with attachments")
    parser.add_argument("--to",      default=GMAIL_USER, help="Recipient email (default: GMAIL_USER)")
    parser.add_argument("--index",   type=int, default=None, help="Send only scenario at this index (0-based)")
    parser.add_argument("--list",    action="store_true", help="List scenarios and exit")
    parser.add_argument("--dry-run", action="store_true", help="Build emails but don't send")
    args = parser.parse_args()

    if args.list:
        for i, s in enumerate(SCENARIOS):
            atts = [a["filename"] for a in s.get("attachments", [])]
            print(f"  [{i}] {s['subject'][:65]}")
            print(f"       From: {s['from_name']} <{s['from_email']}>")
            print(f"       Attachments: {', '.join(atts) if atts else 'none (body only)'}")
            print()
        return

    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("ERROR: GMAIL_USER and GMAIL_PASSWORD must be set in .env")
        sys.exit(1)

    to = args.to or GMAIL_USER
    print(f"Sending to: {to}\n")

    targets = [SCENARIOS[args.index]] if args.index is not None else SCENARIOS
    for scenario in targets:
        send_scenario(scenario, to, dry_run=args.dry_run)

    print(f"\nDone. {len(targets)} email(s) sent.")


if __name__ == "__main__":
    main()
