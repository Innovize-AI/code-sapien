"""
Generate dummy brochure PDFs for Aparna Constructions demo.

Run from this directory:
    python create_brochures.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import KeepTogether
import os

# ── Brand colours ──────────────────────────────────────────────────────────────
APARNA_MAROON  = HexColor("#8B1A1A")
APARNA_GOLD    = HexColor("#C8922A")
APARNA_DARK    = HexColor("#1A1A1A")
APARNA_GREY    = HexColor("#555555")
APARNA_LIGHT   = HexColor("#F5F0EB")
APARNA_DIVIDER = HexColor("#D4B483")

W, H = A4

# ── Style helpers ──────────────────────────────────────────────────────────────

def styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title",
            fontName="Helvetica-Bold", fontSize=28, textColor=white,
            spaceAfter=6, alignment=TA_CENTER, leading=34),
        "cover_sub": ParagraphStyle("cover_sub",
            fontName="Helvetica", fontSize=13, textColor=HexColor("#F5D9A0"),
            spaceAfter=4, alignment=TA_CENTER),
        "cover_tag": ParagraphStyle("cover_tag",
            fontName="Helvetica-Bold", fontSize=10, textColor=APARNA_GOLD,
            alignment=TA_CENTER, spaceAfter=2),
        "section_head": ParagraphStyle("section_head",
            fontName="Helvetica-Bold", fontSize=14, textColor=APARNA_MAROON,
            spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=10, textColor=APARNA_DARK,
            spaceAfter=5, leading=15),
        "body_bold": ParagraphStyle("body_bold",
            fontName="Helvetica-Bold", fontSize=10, textColor=APARNA_DARK,
            spaceAfter=4, leading=15),
        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=10, textColor=APARNA_DARK,
            spaceAfter=4, leftIndent=12, leading=14,
            bulletIndent=0, bulletFontName="Helvetica"),
        "label": ParagraphStyle("label",
            fontName="Helvetica-Bold", fontSize=9, textColor=APARNA_GREY,
            spaceAfter=1),
        "value": ParagraphStyle("value",
            fontName="Helvetica-Bold", fontSize=12, textColor=APARNA_MAROON,
            spaceAfter=8),
        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=8, textColor=APARNA_GREY,
            alignment=TA_CENTER),
        "rera": ParagraphStyle("rera",
            fontName="Helvetica", fontSize=8, textColor=APARNA_GREY,
            alignment=TA_CENTER, spaceBefore=4),
    }


def divider():
    return HRFlowable(width="100%", thickness=1, color=APARNA_DIVIDER,
                      spaceAfter=10, spaceBefore=4)


def stat_table(pairs, s):
    """Render a 2-column stat grid (label / value)."""
    data = []
    row = []
    for i, (label, value) in enumerate(pairs):
        cell = [Paragraph(label, s["label"]), Paragraph(value, s["value"])]
        row.append(cell)
        if len(row) == 2:
            data.append(row)
            row = []
    if row:
        row.append(["", ""])
        data.append(row)

    t = Table(data, colWidths=[85*mm, 85*mm])
    t.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",  (0, 0), (-1, -1), APARNA_LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [APARNA_LIGHT, white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",(0, 0), (-1, -1), 10),
        ("BOX",         (0, 0), (-1, -1), 0.5, APARNA_DIVIDER),
        ("INNERGRID",   (0, 0), (-1, -1), 0.3, APARNA_DIVIDER),
    ]))
    return t


def header_band(canvas, doc, title, subtitle, tag=None):
    """Draw a full-width maroon header band at the top."""
    canvas.saveState()
    canvas.setFillColor(APARNA_MAROON)
    canvas.rect(0, H - 80*mm, W, 80*mm, fill=1, stroke=0)

    # Gold accent bar
    canvas.setFillColor(APARNA_GOLD)
    canvas.rect(0, H - 83*mm, W, 3*mm, fill=1, stroke=0)

    # Company name
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(HexColor("#F5D9A0"))
    canvas.drawCentredString(W/2, H - 18*mm, "APARNA CONSTRUCTIONS AND ESTATES PVT. LTD.")

    # Project title
    canvas.setFont("Helvetica-Bold", 26)
    canvas.setFillColor(white)
    canvas.drawCentredString(W/2, H - 36*mm, title)

    # Subtitle
    canvas.setFont("Helvetica", 13)
    canvas.setFillColor(HexColor("#F5D9A0"))
    canvas.drawCentredString(W/2, H - 48*mm, subtitle)

    if tag:
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(APARNA_GOLD)
        canvas.drawCentredString(W/2, H - 60*mm, f"● {tag} ●")

    canvas.restoreState()


def footer_band(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(APARNA_MAROON)
    canvas.rect(0, 0, W, 20*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(white)
    canvas.drawCentredString(W/2, 12*mm,
        "Aparna Constructions and Estates Pvt. Ltd.  |  Astral Heights, Road No.1, Banjara Hills, Hyderabad – 500034")
    canvas.drawCentredString(W/2, 7*mm,
        "Sales: 7095333335  |  sales@aparnaconstructions.com  |  www.aparnaconstructions.com")
    canvas.restoreState()


def make_doc(filename, title, subtitle, tag, elements):
    top_margin = 90*mm

    def _header(canvas, doc):
        header_band(canvas, doc, title, subtitle, tag)
        footer_band(canvas, doc)

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        topMargin=top_margin, bottomMargin=28*mm,
        leftMargin=18*mm, rightMargin=18*mm,
    )
    doc.build(elements, onFirstPage=_header, onLaterPages=_header)
    print(f"  Created: {filename}")


# ── Brochure builders ──────────────────────────────────────────────────────────

def cyberzed():
    s = styles()
    el = []

    el.append(Paragraph("Project Overview", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Aparna CyberZed is a new-launch premium residential project at Osman Nagar, Hyderabad — "
        "strategically located in the fast-growing Kokapet-Nallagandla-Financial District corridor. "
        "Three iconic high-rise towers rise S+38/39 floors over a 6.4-acre gated campus, offering "
        "spacious 3 BHK homes designed for the modern professional lifestyle.",
        s["body"]))
    el.append(Spacer(1, 6))

    el.append(stat_table([
        ("Configuration",    "3 BHK"),
        ("Unit Size",        "1,471 – 2,001 Sq. Ft."),
        ("Price",            "₹ 7,999 per Sq. Ft."),
        ("Price Range",      "₹ 1.18 Cr – ₹ 1.60 Cr*"),
        ("Total Units",      "759 Units"),
        ("Towers / Floors",  "3 Towers · S+38/39 Floors"),
        ("Site Area",        "6.4 Acres"),
        ("RERA Number",      "P01100011037"),
    ], s))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Location Advantages", s["section_head"]))
    el.append(divider())
    for point in [
        "Financial District — 15 minutes",
        "HITEC City / Cyber Towers — 20 minutes",
        "Rajiv Gandhi International Airport — 35 minutes via ORR",
        "Outer Ring Road (ORR) access — 5 minutes",
        "Proximity to top schools: DPS, Oakridge, Glendale",
        "Hospitals nearby: Continental, KIMS, Apollo",
        "Osman Nagar is part of the highest capital appreciation zone in Hyderabad (2022–2025: 45% YoY)",
    ]:
        el.append(Paragraph(f"✦  {point}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("Amenities", s["section_head"]))
    el.append(divider())
    amenities = [
        "Grand Clubhouse with Indoor Games",
        "Swimming Pool with Deck",
        "Fully-Equipped Gymnasium",
        "Jogging & Cycling Track",
        "Landscaped Gardens & Water Features",
        "Children's Play Area",
        "Multi-Purpose Sports Court",
        "24×7 Security with CCTV",
        "EV Charging Points",
        "Rooftop Lounge (select towers)",
        "Dedicated Workspace / Co-working Lounge",
        "Visitor Parking",
    ]
    cols = [amenities[:6], amenities[6:]]
    amen_data = [[
        "\n".join(f"✦  {a}" for a in cols[0]),
        "\n".join(f"✦  {a}" for a in cols[1]),
    ]]
    at = Table(amen_data, colWidths=[85*mm, 85*mm])
    at.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    el.append(at)

    el.append(Spacer(1, 10))
    el.append(Paragraph("Payment Plan", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Construction-Linked Plan (most popular): payments linked to construction milestones — "
        "you pay as the building goes up. Home loan disbursement is also linked to milestones, "
        "minimising interest outflow during construction.",
        s["body"]))
    el.append(Paragraph(
        "Bank tie-ups: SBI, HDFC, ICICI, Axis Bank, Kotak Mahindra Bank. "
        "Our team facilitates loan approvals and documentation.",
        s["body"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("* Base price. Registration, stamp duty (~7.5%), GST (5%), and other charges extra.", s["rera"]))
    el.append(Paragraph("RERA: P01100011037  |  Verify at rera.telangana.gov.in", s["rera"]))

    make_doc("cyberzed-brochure.pdf", "APARNA CYBERZED",
             "Osman Nagar, Hyderabad", "NEW LAUNCH · 3 BHK · ₹7,999/Sq.Ft.", el)


def moonstone():
    s = styles()
    el = []

    el.append(Paragraph("Project Overview", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Aparna Moonstone is an ultra-luxury residential township at Gopanpally, Gachibowli — "
        "Hyderabad's most coveted IT and financial address. Spread across 22 acres, 8 towers of "
        "G+44 floors house 2,088 curated residences offering 3 and 4 BHK configurations. "
        "Designed for those who demand the finest, Moonstone defines luxury living in a lush, "
        "green environment within the Township of Tomorrow.",
        s["body"]))
    el.append(Spacer(1, 6))

    el.append(stat_table([
        ("Configuration",    "3 BHK & 4 BHK"),
        ("Unit Size",        "2,166 – 3,140 Sq. Ft."),
        ("Segment",          "Ultra-Luxury"),
        ("Pricing",          "On Request (contact sales)"),
        ("Total Units",      "2,088 Units"),
        ("Towers / Floors",  "8 Towers · G+44 Floors"),
        ("Site Area",        "22 Acres"),
        ("RERA Number",      "P02400009478"),
    ], s))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Location Advantages", s["section_head"]))
    el.append(divider())
    for point in [
        "Gopanpally / Gachibowli — Hyderabad's #1 IT and financial district",
        "Walking distance to major IT campuses (Microsoft, Google, Amazon, Deloitte)",
        "Nanakramguda Financial District — 5 minutes",
        "IKEA Hyderabad — 10 minutes",
        "Inorbit Mall & retail hub — 8 minutes",
        "HITEC City — 20 minutes",
        "Airport via ORR — 30 minutes",
        "Top schools: Glendale, Oakridge, DPS — within 15 minutes",
    ]:
        el.append(Paragraph(f"✦  {point}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("Ultra-Luxury Amenities", s["section_head"]))
    el.append(divider())
    for a in [
        "Grand clubhouse with premium finishes",
        "Olympic-length swimming pool with poolside cabanas",
        "State-of-the-art gymnasium and spa",
        "Rooftop sky lounge with panoramic city views",
        "Landscaped zen gardens and forest walking trails",
        "Private theatre / screening room",
        "Co-working lounge with high-speed connectivity",
        "EV charging infrastructure across all towers",
        "Concierge services post-possession via APMS",
        "Children's indoor and outdoor play zones",
        "Multi-purpose sports hall and tennis court",
        "24×7 three-tier security with CCTV surveillance",
    ]:
        el.append(Paragraph(f"✦  {a}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("RERA: P02400009478  |  Verify at rera.telangana.gov.in", s["rera"]))

    make_doc("moonstone-brochure.pdf", "APARNA MOONSTONE",
             "Gopanpally, Gachibowli, Hyderabad", "ULTRA-LUXURY · 3 & 4 BHK · 22 ACRES", el)


def newlands():
    s = styles()
    el = []

    el.append(Paragraph("Project Overview", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Aparna Newlands is a premium gated community at Tellapur, Hyderabad — a fast-developing "
        "suburb adjacent to Nallagandla and the Financial District. 1,976 homes across 8 "
        "high-rise towers of 42 floors on 14.7 acres. At its heart is one of Hyderabad's largest "
        "clubhouses at 72,865 sq ft, with 10 dedicated sports courts and world-class recreational "
        "facilities — making Newlands a lifestyle community, not just a home.",
        s["body"]))
    el.append(Spacer(1, 6))

    el.append(stat_table([
        ("Configuration",    "2.5 BHK & 3 BHK"),
        ("Unit Size",        "1,475 – 1,991 Sq. Ft."),
        ("Pricing",          "On Request (contact sales)"),
        ("Total Units",      "1,976 Units"),
        ("Towers / Floors",  "8 Towers · 42 Floors"),
        ("Site Area",        "14.7 Acres"),
        ("Clubhouse",        "72,865 Sq. Ft."),
        ("RERA Number",      "P01100007480"),
    ], s))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Location Advantages", s["section_head"]))
    el.append(divider())
    for point in [
        "Tellapur — adjacent to Nallagandla, 10 min from Financial District",
        "Outer Ring Road access — 5 minutes",
        "Sarath City Capital Mall — 15 minutes",
        "IKEA Hyderabad — 15 minutes",
        "Continental and Star Hospitals — 10 minutes",
        "DPS, Oakridge International Schools — 12 minutes",
        "Upcoming Metro connectivity — Tellapur station planned on ORR Metro corridor",
    ]:
        el.append(Paragraph(f"✦  {point}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("Sports & Recreation — 10 Courts", s["section_head"]))
    el.append(divider())
    courts_data = [[
        "✦  Tennis Court\n✦  Badminton Court (2)\n✦  Basketball Court\n✦  Squash Court",
        "✦  Cricket Practice Net\n✦  Skating Rink\n✦  Volleyball Court\n✦  Table Tennis (indoor)",
    ]]
    ct = Table(courts_data, colWidths=[85*mm, 85*mm])
    ct.setStyle(TableStyle([
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    el.append(ct)

    el.append(Spacer(1, 8))
    el.append(Paragraph("Additional Amenities", s["section_head"]))
    el.append(divider())
    for a in [
        "72,865 sq ft Grand Clubhouse — one of Hyderabad's largest",
        "Olympic swimming pool with kids splash zone",
        "Fully-equipped gymnasium and yoga studio",
        "Landscaped gardens with jogging track",
        "Children's adventure play area",
        "Mini-theatre / AV room",
        "24×7 security with CCTV and boom barriers",
        "EV charging points, visitor parking",
    ]:
        el.append(Paragraph(f"✦  {a}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("RERA: P01100007480  |  Verify at rera.telangana.gov.in", s["rera"]))

    make_doc("newlands-brochure.pdf", "APARNA NEWLANDS",
             "Tellapur, Hyderabad", "PREMIUM · 2.5 & 3 BHK · 72,865 SQ FT CLUBHOUSE", el)


def synergy():
    s = styles()
    el = []

    el.append(Paragraph("Project Overview", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Aparna Synergy is the flagship value-luxury community at Gandi Maisamma, north Hyderabad — "
        "one of the city's largest gated projects at 28 acres. 3,345 homes across 15 towers of "
        "G+27 floors. Synergy is built for families — with 15+ child-centric amenities, expansive "
        "open spaces, and a strong community environment. Best price-per-sq-ft in the Aparna portfolio "
        "without compromising on quality or lifestyle.",
        s["body"]))
    el.append(Spacer(1, 6))

    el.append(stat_table([
        ("Configuration",    "2 BHK, 2.5 BHK & 3 BHK"),
        ("Unit Size",        "1,251 – 2,307 Sq. Ft."),
        ("Segment",          "Value Luxury — Best ROI"),
        ("Pricing",          "On Request (contact sales)"),
        ("Total Units",      "3,345 Units"),
        ("Towers / Floors",  "15 Towers · G+27 Floors"),
        ("Site Area",        "28 Acres"),
        ("RERA Number",      "P02200006615"),
    ], s))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Location Advantages", s["section_head"]))
    el.append(divider())
    for point in [
        "Gandi Maisamma — north Hyderabad growth zone near Kompally",
        "Outer Ring Road (ORR) — 10 minutes for city-wide connectivity",
        "Medchal IT corridor — emerging tech employment zone",
        "Schools: Delhi Public School, Sri Chaitanya, Narayana nearby",
        "Hospitals: Yashoda, KIMS, Apollo Spectra — 15 minutes",
        "Best capital appreciation potential in north Hyderabad (2024–2028)",
        "Hyderabad Metro Phase 2 expansion planned in this corridor",
    ]:
        el.append(Paragraph(f"✦  {point}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("15+ Child-Centric Amenities", s["section_head"]))
    el.append(divider())
    for a in [
        "Splash Park and Water Play Zone",
        "Adventure Trail and Rock Climbing Wall",
        "Cricket Practice Academy",
        "Skating Rink",
        "Sand Play Area",
        "Trampoline Zone",
        "Kids' Library and Learning Centre",
        "Outdoor amphitheatre for events",
        "Teen gaming and recreation lounge",
        "Parent seating areas throughout the campus",
    ]:
        el.append(Paragraph(f"✦  {a}", s["bullet"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph(
        "Aparna Synergy — A Higher Standard of Living, Delivered at Unbelievable Value.",
        s["body_bold"]))

    el.append(Spacer(1, 6))
    el.append(Paragraph("RERA: P02200006615  |  Verify at rera.telangana.gov.in", s["rera"]))

    make_doc("synergy-brochure.pdf", "APARNA SYNERGY",
             "Gandi Maisamma, Hyderabad", "VALUE LUXURY · 2/2.5/3 BHK · 28 ACRES · 3,345 HOMES", el)


def payment_plan():
    s = styles()
    el = []

    el.append(Paragraph("Understanding Your Payment Options", s["section_head"]))
    el.append(divider())
    el.append(Paragraph(
        "Aparna Constructions offers flexible payment plans to suit different buyer profiles. "
        "All plans are RERA-compliant with full transparency on milestones and amounts.",
        s["body"]))

    el.append(Spacer(1, 8))
    el.append(Paragraph("Plan 1: Construction-Linked Plan (CLP) — Most Popular", s["body_bold"]))
    el.append(Paragraph(
        "Payments are tied directly to construction milestones. You pay as the building progresses — "
        "minimising interest outflow and aligning your investment with actual progress.",
        s["body"]))
    milestone_data = [
        ["Milestone", "Payment %"],
        ["Booking / EOI", "2%"],
        ["Agreement to Sale", "8% (total 10%)"],
        ["Foundation / Plinth", "10%"],
        ["Each Slab Cast (multiple)", "7.5% × ~8 slabs"],
        ["Brickwork Completion", "5%"],
        ["Plastering Completion", "5%"],
        ["Flooring & Fixtures", "5%"],
        ["Possession (OC + CC)", "5%"],
    ]
    mt = Table(milestone_data, colWidths=[120*mm, 50*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), APARNA_MAROON),
        ("TEXTCOLOR",    (0, 0), (-1, 0), white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("ALIGN",        (1, 0), (1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [APARNA_LIGHT, white]),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("BOX",          (0, 0), (-1, -1), 0.5, APARNA_DIVIDER),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, APARNA_DIVIDER),
    ]))
    el.append(mt)

    el.append(Spacer(1, 12))
    el.append(Paragraph("Plan 2: 20:80 Plan", s["body_bold"]))
    el.append(Paragraph(
        "Pay 20% now (booking + agreement) and 80% at possession. Best for buyers who want to "
        "lock in today's price with minimal cash outflow during construction. Home loan is "
        "taken for the 80% and disbursed at possession. Slight premium on base price applies.",
        s["body"]))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Plan 3: Subvention Scheme (selected projects)", s["body_bold"]))
    el.append(Paragraph(
        "Aparna and the bank together ensure that during construction, EMI is paid by Aparna — "
        "you start paying EMI only after possession. Check with our team for scheme availability "
        "on specific projects.",
        s["body"]))

    el.append(Spacer(1, 10))
    el.append(Paragraph("Home Loan Partner Banks", s["section_head"]))
    el.append(divider())
    banks = [
        ["Bank", "Max LTV", "Processing"],
        ["SBI Home Loans", "Up to 90%", "15–20 days"],
        ["HDFC Bank", "Up to 90%", "10–15 days"],
        ["ICICI Bank", "Up to 85%", "10–15 days"],
        ["Axis Bank", "Up to 90%", "7–12 days"],
        ["Kotak Mahindra Bank", "Up to 85%", "10–14 days"],
    ]
    bt = Table(banks, colWidths=[80*mm, 50*mm, 40*mm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), APARNA_GOLD),
        ("TEXTCOLOR",    (0, 0), (-1, 0), white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [APARNA_LIGHT, white]),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("BOX",          (0, 0), (-1, -1), 0.5, APARNA_DIVIDER),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, APARNA_DIVIDER),
    ]))
    el.append(bt)

    el.append(Spacer(1, 10))
    el.append(Paragraph("Additional Cost Components", s["section_head"]))
    el.append(divider())
    for item in [
        "Stamp Duty: 5% of sale value (Telangana)",
        "Registration: 0.5% of sale value",
        "GST: 5% on under-construction properties (no GST after OC)",
        "Legal/Documentation: Rs 25,000 – Rs 50,000 approx",
        "Maintenance Deposit: 2 years advance (varies by project)",
        "Corpus Fund: One-time (varies by project)",
        "Parking: Covered parking included in some configurations; check per project",
    ]:
        el.append(Paragraph(f"✦  {item}", s["bullet"]))

    el.append(Spacer(1, 8))
    el.append(Paragraph(
        "Our sales team will walk you through the exact breakup for your chosen unit. "
        "Call us at 7095333335 or email sales@aparnaconstructions.com.",
        s["body"]))

    make_doc("payment-plan-guide.pdf", "PAYMENT PLANS",
             "Flexible Options for Every Buyer", "RERA COMPLIANT · BANK APPROVED · TRANSPARENT", el)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Generating Aparna Constructions brochures...\n")
    cyberzed()
    moonstone()
    newlands()
    synergy()
    payment_plan()
    print("\nAll brochures generated.")
