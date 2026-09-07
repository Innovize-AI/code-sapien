"""PDF quote generation using fpdf2."""
import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

COMPANY_NAME  = os.getenv("COMPANY_NAME", "InnovizeAI")
COMPANY_EMAIL = os.getenv("GMAIL_SENDER", "admin@innovizeai.com")

# India keywords — anything else is treated as international (zero-rated export)
_INDIA_KEYWORDS = {"india", "mumbai", "delhi", "bangalore", "bengaluru", "chennai",
                   "hyderabad", "pune", "kolkata", "ahmedabad", "midc", "noida",
                   "gurugram", "gurgaon", "jnpt", "nhava sheva", "cochin", "kochi"}

# Gulf/UAE → VAT 5%
_VAT_KEYWORDS = {"uae", "dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah",
                 "jebel ali", "dafza", "difc", "qatar", "doha", "bahrain", "oman",
                 "muscat", "kuwait", "riyadh", "saudi", "ksa"}


def _tax_for_location(delivery_location: str | None) -> tuple[str, float]:
    """Return (tax_label, tax_rate) based on delivery location."""
    loc = (delivery_location or "").lower()
    if any(k in loc for k in _INDIA_KEYWORDS):
        return "GST 18%", 0.18
    if any(k in loc for k in _VAT_KEYWORDS):
        return "VAT 5%", 0.05
    # International / export — zero-rated
    return "Tax (Export — Zero Rated)", 0.0


def generate_quote_pdf(record) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        raise RuntimeError("fpdf2 not installed. Run: pip install fpdf2")

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Header band ─────────────────────────────────────────────────────────
    pdf.set_fill_color(79, 70, 229)  # indigo-600
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_y(12)
    pdf.set_x(20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, COMPANY_NAME, ln=True)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(199, 210, 254)  # indigo-200
    quote_ref = f"Quotation · Ref {record.rfq_id[:8].upper()}"
    pdf.cell(0, 6, quote_ref, ln=True)
    pdf.set_text_color(0, 0, 0)

    # ── Meta row ─────────────────────────────────────────────────────────────
    pdf.set_y(48)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    today = date.today().strftime("%d %b %Y")
    pdf.cell(95, 5, f"Date: {today}", ln=False)
    pdf.cell(0, 5, f"Valid until: {_add_days(today, 30)}", ln=True, align="R")
    pdf.ln(6)

    # ── Bill To ──────────────────────────────────────────────────────────────
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(20, pdf.get_y(), 80, 28, "FD")
    pdf.set_xy(25, pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "BILL TO", ln=True)
    pdf.set_x(25)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5, _to_latin1(record.buyer_name or "-"), ln=True)
    pdf.set_x(25)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 4, _to_latin1(record.sender or ""), ln=True)
    if record.delivery_location:
        pdf.set_x(25)
        pdf.cell(0, 4, _to_latin1(record.delivery_location), ln=True)

    # ── Deadline / Details ───────────────────────────────────────────────────
    if record.rfq_deadline:
        pdf.set_xy(115, pdf.get_y() - 16)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 4, "REQUIRED BY", ln=True)
        pdf.set_x(115)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, record.rfq_deadline, ln=True)

    pdf.ln(10)

    # ── Resolve currency once for the whole document ─────────────────────────
    _tax_label, _tax_rate = _tax_for_location(getattr(record, "delivery_location", None))
    # Helvetica only supports Latin-1 — use plain text symbols only
    sym = "Rs." if _tax_rate == 0.18 else "USD "

    # ── Line items table ─────────────────────────────────────────────────────
    line_items   = record.line_items   or []
    line_pricing = record.line_pricing or []
    pricing_map  = {p["line_item_index"]: p for p in line_pricing}

    if line_items:
        # Table header
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 116, 139)
        col_w = [85, 20, 22, 28, 15]
        headers = ["Description", "Qty", "Unit Price", "Subtotal", "Disc"]
        x0 = 20
        pdf.set_x(x0)
        for h, w in zip(headers, col_w):
            pdf.cell(w, 7, h, border="B", fill=True, align="C" if h != "Description" else "L")
        pdf.ln()

        # Rows
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(15, 23, 42)
        for i, item in enumerate(line_items):
            p = pricing_map.get(i)
            pdf.set_x(x0)
            pdf.cell(col_w[0], 7, _trunc(_to_latin1(item.get("description", "")), 52))
            pdf.cell(col_w[1], 7, f"{item.get('quantity','-')} {item.get('unit','')}", align="C")
            pdf.cell(col_w[2], 7, f"{sym}{p['unit_price']:,.2f}" if p else "-", align="R")
            pdf.cell(col_w[3], 7, f"{sym}{p['subtotal']:,.2f}" if p else "-", align="R")
            disc = f"-{int(p['discount_pct']*100)}%" if p and p.get("discount_pct") else "-"
            pdf.cell(col_w[4], 7, disc, align="C")
            pdf.ln()

        # Totals
        pdf.ln(2)
        subtotal    = record.subtotal or record.total or 0.0
        tax_amount  = round(subtotal * _tax_rate, 2)
        grand_total = round(subtotal + tax_amount, 2)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        for label, val in [("Subtotal", subtotal)] + ([(_tax_label, tax_amount)] if _tax_rate > 0 else []):
            pdf.set_x(x0 + sum(col_w[:3]))
            pdf.cell(col_w[3], 6, label, align="L")
            pdf.cell(col_w[4], 6, f"{sym}{val:,.2f}", align="R")
            pdf.ln()
        if _tax_rate == 0:
            pdf.set_x(x0 + sum(col_w[:3]))
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(col_w[3] + col_w[4], 5, "Export supply — zero-rated", align="R")
            pdf.ln()
        # Total row
        pdf.set_fill_color(241, 245, 249)
        pdf.set_x(x0 + sum(col_w[:3]))
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w[3] + col_w[4], 8, f"  Total   {sym}{grand_total:,.2f}", fill=True, align="R")
        pdf.ln()

    elif record.draft_quote:
        # Fallback: convert markdown → plain text then render
        safe_text = _to_latin1(_md_to_plain(record.draft_quote))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5.5, safe_text)

    # ── Freight highlight ─────────────────────────────────────────────────────
    if record.rfq_type == "freight" and record.freight_quote_amount:
        pdf.ln(4)
        pdf.set_fill_color(237, 233, 254)
        pdf.set_draw_color(167, 139, 250)
        pdf.set_xy(20, pdf.get_y())
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(109, 40, 217)
        pdf.cell(0, 10, f"  Freight Quote: {sym}{record.freight_quote_amount:,.2f}  ({record.freight_origin} -> {record.freight_destination})", fill=True, border=1)
        pdf.ln()

    # ── Terms ────────────────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    tax_label, tax_rate = _tax_for_location(getattr(record, "delivery_location", None))
    if tax_rate == 0:
        tax_term = "Export supply — zero-rated. No tax applicable."
    else:
        tax_term = f"{tax_label} applicable extra unless stated."
    terms = [
        ("Payment Terms", "50% advance, balance before dispatch"),
        ("Delivery",      "As per quoted lead time. Transport at actuals."),
        ("Validity",      f"30 days from {today}. Prices subject to change."),
        ("Tax",           tax_term),
    ]
    col = 0
    for label, val in terms:
        if col == 0:
            pdf.set_x(20)
        else:
            pdf.set_x(110)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(30, 5, label + ":", ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0 if col == 1 else 55, 5, val, ln=(col == 1))
        col = (col + 1) % 2

    # ── Footer ────────────────────────────────────────────────────────────────
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Generated by {COMPANY_NAME} RFQ Agent · {COMPANY_EMAIL} · {quote_ref}", align="C")

    return bytes(pdf.output())


def _md_to_plain(text: str) -> str:
    """Convert markdown to clean plain text suitable for fpdf2."""
    try:
        import markdown as _md
        from html.parser import HTMLParser

        class _Stripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts: list[str] = []
                self._block_tags = {"p", "h1", "h2", "h3", "h4", "li", "tr", "hr", "br"}
            def handle_data(self, data):
                self._parts.append(data)
            def handle_starttag(self, tag, attrs):
                if tag in self._block_tags:
                    self._parts.append("\n")
            def get_text(self):
                return "".join(self._parts).strip()

        html = _md.markdown(text, extensions=["tables", "nl2br"])
        s = _Stripper()
        s.feed(html)
        return s.get_text()
    except Exception:
        # Hard fallback: regex strip if markdown lib unavailable
        import re as _re
        t = text
        t = _re.sub(r"^#{1,6}\s+", "", t, flags=_re.MULTILINE)
        t = _re.sub(r"\*\*(.+?)\*\*", r"\1", t)
        t = _re.sub(r"\*(.+?)\*", r"\1", t)
        t = _re.sub(r"`(.+?)`", r"\1", t)
        t = _re.sub(r"\[(.+?)\]\(.+?\)", r"\1", t)
        t = _re.sub(r"^\|.*\|$", "", t, flags=_re.MULTILINE)
        t = _re.sub(r"^\s*[-*]\s+", "* ", t, flags=_re.MULTILINE)
        return t.strip()


_UNICODE_REPLACEMENTS = {
    "–": "-",   # en dash
    "—": "--",  # em dash
    "‘": "'",   # left single quote
    "’": "'",   # right single quote
    "“": '"',   # left double quote
    "”": '"',   # right double quote
    "•": "*",   # bullet
    "₹": "Rs.", # rupee sign
    "…": "...", # ellipsis
    "×": "x",  # multiplication sign
}

def _to_latin1(text: str) -> str:
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _trunc(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n - 1] + "..."


def _add_days(date_str: str, days: int) -> str:
    from datetime import datetime, timedelta
    try:
        d = datetime.strptime(date_str, "%d %b %Y") + timedelta(days=days)
        return d.strftime("%d %b %Y")
    except Exception:
        return ""
