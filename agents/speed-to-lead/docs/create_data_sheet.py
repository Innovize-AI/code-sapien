"""
Generates DWPS_Data_Request.xlsx with 5 tabs for the DWPS admissions team.
Run: python3 docs/create_data_sheet.py
"""

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter

wb = Workbook()

# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY       = "1E3A5F"   # header bg
WHITE      = "FFFFFF"
LIGHT_BLUE = "D6E4F0"   # alternate row / section header bg
YELLOW     = "FFF9C4"   # sample row highlight
ORANGE     = "FFF3CD"   # note / instruction rows
GRAY       = "F2F2F2"   # category header rows in FAQs
BORDER_CLR = "CCCCCC"

thin = Side(style="thin", color=BORDER_CLR)
border = Border(left=thin, right=thin, top=thin, bottom=thin)


def header_font(size=11, bold=True, color=WHITE):
    return Font(name="Calibri", size=size, bold=bold, color=color)


def body_font(size=10, bold=False, color="000000"):
    return Font(name="Calibri", size=size, bold=bold, color=color)


def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)


def center(wrap=False):
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)


def left(wrap=True):
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)


def style_header_row(ws, row, col_count):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = header_font()
        cell.fill = fill(NAVY)
        cell.alignment = center(wrap=True)
        cell.border = border


def style_note_row(ws, row, col_count, bg=ORANGE):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = body_font(bold=False, color="5D4037")
        cell.fill = fill(bg)
        cell.alignment = left()
        cell.border = border


def style_sample_row(ws, row, col_count):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = body_font(color="555555")
        cell.fill = fill(YELLOW)
        cell.alignment = left()
        cell.border = border


def style_empty_row(ws, row, col_count, alt=False):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = body_font()
        cell.fill = fill(LIGHT_BLUE if alt else WHITE)
        cell.alignment = left()
        cell.border = border


def set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def freeze(ws, cell="A2"):
    ws.freeze_panes = cell


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Fee Structure
# ══════════════════════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "1. Fee Structure"
ws1.sheet_view.showGridLines = False

COLS_FEE = 6
headers_fee = [
    "Class Name",
    "Board\n(write: cambridge or cbse)",
    "Fee Per Term (₹)",
    "Number of Terms Per Year",
    "One-Time Admission Fee (₹)",
    "Other Charges (₹ + description)",
]

# Instruction row
ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS_FEE)
ws1["A1"] = (
    "📋  Fill one row per class. If a class has both Cambridge and CBSE, add two rows for that class."
)
style_note_row(ws1, 1, COLS_FEE)
ws1["A1"].alignment = left()
ws1.row_dimensions[1].height = 24

# Header
for col, h in enumerate(headers_fee, 1):
    ws1.cell(row=2, column=col, value=h)
style_header_row(ws1, 2, COLS_FEE)
ws1.row_dimensions[2].height = 36

CLASSES = [
    ("Nursery",  "cambridge"), ("LKG", "cambridge"), ("UKG", "cambridge"),
    ("Class 1",  "cambridge"), ("Class 2", "cambridge"), ("Class 3", "cambridge"),
    ("Class 4",  "cambridge"), ("Class 5", "cambridge"),
    ("Class 6",  "cbse"),      ("Class 7", "cbse"),      ("Class 8", "cbse"),
    ("Class 9",  "cbse"),      ("Class 10", "cbse"),
]

for i, (cls, board) in enumerate(CLASSES):
    row = i + 3
    ws1.cell(row=row, column=1, value=cls)
    ws1.cell(row=row, column=2, value=board)
    ws1.cell(row=row, column=4, value=3)
    alt = i % 2 == 1
    style_empty_row(ws1, row, COLS_FEE, alt=alt)
ws1.row_dimensions[row].height = 18

set_col_widths(ws1, [14, 22, 18, 22, 24, 36])
freeze(ws1, "A3")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Transport / Bus Routes
# ══════════════════════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("2. Transport Routes")
ws2.sheet_view.showGridLines = False

COLS_TR = 4
headers_tr = [
    "Area / Locality",
    "Route Name\n(e.g. Route A)",
    "Morning Pickup Time",
    "Monthly Bus Fee (₹)",
]

ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS_TR)
ws2["A1"] = "📋  Fill one row per area the school bus covers. Add more rows as needed."
style_note_row(ws2, 1, COLS_TR)
ws2["A1"].alignment = left()
ws2.row_dimensions[1].height = 24

for col, h in enumerate(headers_tr, 1):
    ws2.cell(row=2, column=col, value=h)
style_header_row(ws2, 2, COLS_TR)
ws2.row_dimensions[2].height = 36

AREAS = [
    "Miyapur", "Kukatpally", "Gachibowli", "Manikonda", "Kompally",
    "Secunderabad", "Uppal", "LB Nagar", "Dilsukhnagar", "Hayathnagar",
    "ECIL", "Alwal",
]
for i, area in enumerate(AREAS):
    row = i + 3
    ws2.cell(row=row, column=1, value=area)
    style_empty_row(ws2, row, COLS_TR, alt=i % 2 == 1)
# Extra blank rows
for i in range(5):
    row = len(AREAS) + 3 + i
    style_empty_row(ws2, row, COLS_TR, alt=i % 2 == 0)

set_col_widths(ws2, [22, 20, 22, 22])
freeze(ws2, "A3")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FAQs
# ══════════════════════════════════════════════════════════════════════════════
ws3 = wb.create_sheet("3. FAQs")
ws3.sheet_view.showGridLines = False

COLS_FAQ = 3
headers_faq = ["Category", "Question", "Answer (2–3 sentences max)"]

ws3.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS_FAQ)
ws3["A1"] = (
    "📋  Write a short, accurate answer for each question — 2 to 3 sentences max. "
    "Skip any that do not apply. Add more rows at the bottom if needed.  "
    "🟡 Rows already filled in are SAMPLE ANSWERS ONLY — please verify and update them with actual DWPS information."
)
style_note_row(ws3, 1, COLS_FAQ)
ws3["A1"].alignment = left(wrap=True)
ws3.row_dimensions[1].height = 36

for col, h in enumerate(headers_faq, 1):
    ws3.cell(row=2, column=col, value=h)
style_header_row(ws3, 2, COLS_FAQ)
ws3.row_dimensions[2].height = 30

FAQS = [
    # (category_header, [(question, sample_or_blank), ...])
    ("Fees", [
        ("What is the fee for each class?",
         "Saarthi Admission Agent picks this up automatically from the Fee Structure tab — skip this question."),
        ("Are there any charges besides the tuition fee?", ""),
        ("When is the fee due each term?", ""),
        ("Is the admission fee refundable?", ""),
        ("Does DWPS offer scholarships or fee concessions?", ""),
        ("What payment methods are accepted?", ""),
    ]),
    ("Admissions Process", [
        ("What is the minimum age for Nursery / LKG / UKG / Class 1?",
         "Nursery: 3 years. LKG: 4 years. UKG: 5 years. Class 1: 6 years — as of 31st March of the academic year."),
        ("What documents are needed for admission?",
         "Birth certificate, Aadhaar card (child + parent), previous TC, last report card, 2 passport-size photos, address proof."),
        ("Is there an entrance test or interview for the child?", ""),
        ("When do admissions open and close for 2026-27?", ""),
        ("How many seats are available per class?", ""),
        ("How long does the admission process take?", ""),
        ("Can a child join in the middle of the school year?", ""),
    ]),
    ("Curriculum", [
        ("Which boards does DWPS offer — Cambridge or CBSE?",
         "Cambridge from Nursery to Class 5; CBSE from Class 6 to Class 10."),
        ("Why does DWPS switch from Cambridge to CBSE at Class 6?", ""),
        ("What is the medium of instruction?", ""),
        ("What languages are taught? (Hindi / Telugu / Sanskrit?)", ""),
        ("Does DWPS prepare students for JEE or NEET?", ""),
    ]),
    ("Facilities", [
        ("What sports facilities are available? Is there a swimming pool?", ""),
        ("Is there a canteen? Is the food vegetarian?", ""),
        ("Are classrooms equipped with smart boards?", ""),
        ("Is there a library?", ""),
        ("Are there science labs and computer labs?", ""),
        ("Is CCTV installed on campus?", ""),
    ]),
    ("Academic Calendar", [
        ("When does the academic year start?", ""),
        ("How many terms are there in a year?", ""),
        ("When are school exams held?", ""),
        ("When are PTMs (Parent-Teacher Meetings) held?", ""),
    ]),
    ("Contact and Timings", [
        ("What are the school timings for primary and secondary?",
         "Primary (Nursery–Class 5): 8:00 AM to 2:30 PM. Secondary (Class 6–10): 8:00 AM to 3:00 PM. Monday to Saturday."),
        ("Is there school on Saturdays?", ""),
        ("Where is DWPS located? (full address + Google Maps link)", ""),
        ("What is the admissions office phone number?", ""),
        ("What is the admissions office email?", ""),
        ("Who is the admissions coordinator? (name)", ""),
    ]),
    ("Tour and Visit", [
        ("Can parents visit the campus before applying?", ""),
        ("What days and times are campus visits available?", ""),
        ("Do parents need to book an appointment or can they walk in?", ""),
        ("Who should parents ask for when they arrive?", ""),
    ]),
    ("Others", [
        ("What is the student-teacher ratio?", ""),
        ("How many students are in each class section?", ""),
        ("What extracurricular activities are offered?", ""),
        ("What are the Class 10 board exam results / pass percentage?", ""),
        ("Is uniform compulsory? Where can parents buy it?", ""),
        ("Does DWPS have a school app for parents?", ""),
        ("(Add any other questions parents frequently ask)", ""),
    ]),
]

current_row = 3
for category, questions in FAQS:
    # Category header row
    ws3.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=COLS_FAQ)
    cat_cell = ws3.cell(row=current_row, column=1, value=f"  {category}")
    cat_cell.font = Font(name="Calibri", size=10, bold=True, color=NAVY)
    cat_cell.fill = fill(LIGHT_BLUE)
    cat_cell.alignment = left(wrap=False)
    for col in range(1, COLS_FAQ + 1):
        ws3.cell(row=current_row, column=col).border = border
    ws3.row_dimensions[current_row].height = 20
    current_row += 1

    for i, (q, ans) in enumerate(questions):
        ws3.cell(row=current_row, column=1, value=category)
        ws3.cell(row=current_row, column=2, value=q)
        ws3.cell(row=current_row, column=3, value=ans)

        is_sample = bool(ans)
        for col in range(1, COLS_FAQ + 1):
            cell = ws3.cell(row=current_row, column=col)
            cell.border = border
            cell.alignment = left()
            if is_sample:
                cell.font = body_font(color="555555")
                cell.fill = fill(YELLOW)
            else:
                cell.font = body_font()
                cell.fill = fill(WHITE if i % 2 == 0 else LIGHT_BLUE)
        ws3.row_dimensions[current_row].height = 18
        current_row += 1

    current_row += 1  # blank gap between categories

# Legend
legend_row = current_row + 1
ws3.merge_cells(start_row=legend_row, start_column=1, end_row=legend_row, end_column=COLS_FAQ)
ws3.cell(row=legend_row, column=1,
         value="🟡 Yellow rows = sample answers already filled in. "
               "Please verify and update them with actual DWPS information.")
style_note_row(ws3, legend_row, COLS_FAQ, bg=YELLOW)
ws3.cell(row=legend_row, column=1).font = body_font(color="5D4037", bold=True)
ws3.row_dimensions[legend_row].height = 22

set_col_widths(ws3, [22, 52, 60])
freeze(ws3, "A3")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Existing Leads
# ══════════════════════════════════════════════════════════════════════════════
ws4 = wb.create_sheet("4. Existing Leads")
ws4.sheet_view.showGridLines = False

COLS_LD = 5
headers_ld = [
    "Parent Name",
    "WhatsApp Number\n(with +91, e.g. +919876543210)",
    "Child's Grade of Interest",
    "When They Last Contacted",
    "Why They Dropped (if known)",
]

ws4.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS_LD)
ws4["A1"] = (
    "📋  Parents who enquired before but did not convert. "
    "A one-time broadcast message will go out to bring them back. "
    "All new leads after go-live are captured automatically — no need to add them here.  "
    "🟡 The first two rows are SAMPLE DATA ONLY — delete them and replace with actual DWPS leads."
)
style_note_row(ws4, 1, COLS_LD)
ws4["A1"].alignment = left(wrap=True)
ws4.row_dimensions[1].height = 42

for col, h in enumerate(headers_ld, 1):
    ws4.cell(row=2, column=col, value=h)
style_header_row(ws4, 2, COLS_LD)
ws4.row_dimensions[2].height = 36

sample_leads = [
    ("Ramesh Kumar",  "+919876543210", "Class 3",  "March 2026",   "Fees concern"),
    ("Priya Reddy",   "+919988776655", "Nursery",  "January 2026", "School too far"),
]
for i, lead in enumerate(sample_leads):
    row = i + 3
    for col, val in enumerate(lead, 1):
        ws4.cell(row=row, column=col, value=val)
    style_sample_row(ws4, row, COLS_LD)
    ws4.row_dimensions[row].height = 18

for i in range(30):
    row = len(sample_leads) + 3 + i
    style_empty_row(ws4, row, COLS_LD, alt=i % 2 == 1)
    ws4.row_dimensions[row].height = 18

legend_row = len(sample_leads) + 3 + 30 + 1
ws4.merge_cells(start_row=legend_row, start_column=1, end_row=legend_row, end_column=COLS_LD)
ws4.cell(row=legend_row, column=1,
         value="🟡 Yellow rows = sample data. Delete these rows and fill in actual lead data.")
style_note_row(ws4, legend_row, COLS_LD, bg=YELLOW)
ws4.cell(row=legend_row, column=1).font = body_font(color="5D4037", bold=True)
ws4.row_dimensions[legend_row].height = 22

set_col_widths(ws4, [22, 34, 24, 24, 34])
freeze(ws4, "A3")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Documents & Videos
# ══════════════════════════════════════════════════════════════════════════════
ws5 = wb.create_sheet("5. Documents & Videos")
ws5.sheet_view.showGridLines = False

COLS_DOC = 4
headers_doc = [
    "Document / Video",
    "What It Should Cover",
    "When Saarthi Admission Agent Sends It",
    "Link or File Name (fill when ready)",
]

ws5.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS_DOC)
ws5["A1"] = (
    "📋  Share each document via WhatsApp, email, or Google Drive. Scanned copies are fine.  "
    "Fill the last column with the file name or link once shared."
)
style_note_row(ws5, 1, COLS_DOC)
ws5["A1"].alignment = left(wrap=True)
ws5.row_dimensions[1].height = 36

for col, h in enumerate(headers_doc, 1):
    ws5.cell(row=2, column=col, value=h)
style_header_row(ws5, 2, COLS_DOC)
ws5.row_dimensions[2].height = 36

DOCUMENTS = [
    # (name, covers, when_sent, must_have)
    # ── Must have ──────────────────────────────────────────────────────────────
    (
        "Fee Structure 2026-27  ⚠ Separate file required",
        "All classes, all charges — tuition per term, admission fee, transport, uniform, any other charges",
        "When a parent asks about fees or is comparing costs",
        True,
    ),
    (
        "Admissions Process Guide  ⚠ Separate file required",
        "Steps to apply, documents needed, age criteria, deadlines, timeline",
        "When a parent asks how to apply or what documents are needed",
        True,
    ),
    (
        "Curriculum Overview  ⚠ Separate file required",
        "Class-wise subjects, Cambridge and CBSE explained, teaching approach",
        "When a parent asks about subjects, boards, or teaching style",
        True,
    ),
    (
        "School Prospectus 2026-27",
        "School overview, vision, values, achievements, faculty, infrastructure, facilities",
        "Early in the conversation when a parent wants a general overview of the school",
        True,
    ),
    # ── Good to have ───────────────────────────────────────────────────────────
    (
        "Campus Tour Video (YouTube link)",
        "Walkthrough of campus — classrooms, labs, sports ground, facilities",
        "When a parent confirms interest in a visit or books a tour slot",
        False,
    ),
    (
        "Principal's Welcome Video (YouTube link)",
        "School vision, culture, academic philosophy",
        "When a parent asks about the school's values or culture",
        False,
    ),
    (
        "Academic Results / Achievements",
        "Class 10 results, toppers, pass percentage, notable achievements",
        "When a parent asks about academic performance or results",
        False,
    ),
    (
        "Extracurricular Activities",
        "Sports, clubs, arts, robotics, swimming, coaching available",
        "When a parent asks about activities, sports, or after-school programmes",
        False,
    ),
    (
        "Academic Calendar 2026-27",
        "Term dates, exam dates, holidays, PTM schedule",
        "When a parent asks about school dates, holidays, or PTM schedule",
        False,
    ),
    (
        "Transport Route Map",
        "Bus routes, areas covered, pickup points",
        "When a parent asks about bus availability for their area",
        False,
    ),
    (
        "Parent Handbook / School Rules",
        "Uniform, discipline policy, leave rules, late arrival",
        "When a parent asks about school rules, uniform, or discipline policy",
        False,
    ),
    (
        "Scholarship / Fee Concession Policy",
        "Merit scholarships, sports scholarships, sibling discount details",
        "When a parent asks about discounts, scholarships, or fee concessions",
        False,
    ),
    (
        "Faculty and Staff Overview",
        "Teacher qualifications, experience, student-teacher ratio",
        "When a parent asks about teachers or student-teacher ratio",
        False,
    ),
    (
        "Any other brochure / document",
        "Share whatever already exists — no need to create new files",
        "Add a 1-line note on when it should be sent",
        False,
    ),
]

# Section header: Must have
must_row = 3
ws5.merge_cells(start_row=must_row, start_column=1, end_row=must_row, end_column=COLS_DOC)
ws5.cell(row=must_row, column=1, value="  ✅  MUST HAVE")
ws5.cell(row=must_row, column=1).font = Font(name="Calibri", size=10, bold=True, color=WHITE)
ws5.cell(row=must_row, column=1).fill = fill("2E7D32")
ws5.cell(row=must_row, column=1).alignment = left(wrap=False)
for col in range(1, COLS_DOC + 1):
    ws5.cell(row=must_row, column=col).border = border
ws5.row_dimensions[must_row].height = 20

current_row = must_row + 1
good_to_have_started = False

for i, (name, covers, when_sent, must) in enumerate(DOCUMENTS):
    if not must and not good_to_have_started:
        # Insert "Good to have" section header
        ws5.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=COLS_DOC)
        ws5.cell(row=current_row, column=1, value="  ★  GOOD TO HAVE")
        ws5.cell(row=current_row, column=1).font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        ws5.cell(row=current_row, column=1).fill = fill("1565C0")
        ws5.cell(row=current_row, column=1).alignment = left(wrap=False)
        for col in range(1, COLS_DOC + 1):
            ws5.cell(row=current_row, column=col).border = border
        ws5.row_dimensions[current_row].height = 20
        current_row += 1
        good_to_have_started = True

    ws5.cell(row=current_row, column=1, value=name)
    ws5.cell(row=current_row, column=2, value=covers)
    ws5.cell(row=current_row, column=3, value=when_sent)
    ws5.cell(row=current_row, column=4, value="")

    alt = i % 2 == 1
    for col in range(1, COLS_DOC + 1):
        cell = ws5.cell(row=current_row, column=col)
        cell.font = body_font(bold=(col == 1))
        cell.fill = fill(LIGHT_BLUE if alt else WHITE)
        cell.alignment = left()
        cell.border = border
    ws5.row_dimensions[current_row].height = 30
    current_row += 1

set_col_widths(ws5, [38, 46, 52, 30])
freeze(ws5, "A3")


# ── Save ───────────────────────────────────────────────────────────────────────
out_path = "docs/DWPS_Data_Request.xlsx"
wb.save(out_path)
print(f"Saved: {out_path}")
