"""Extract structured text from Excel and CSV files for RFQ parsing."""
import csv
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_excel(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _extract_csv_file(file_path)
    elif suffix in (".xlsx", ".xlsm"):
        return _extract_xlsx(file_path)
    elif suffix == ".xls":
        return _extract_xls(file_path)
    else:
        raise ValueError(f"Unsupported spreadsheet format: {suffix}")


def extract_excel_bytes(data: bytes, filename: str) -> str:
    """Extract text from raw bytes (used for email attachments)."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return _extract_csv_bytes(data)
    elif suffix in (".xlsx", ".xlsm"):
        return _extract_xlsx_bytes(data)
    elif suffix == ".xls":
        return _extract_xls_bytes(data)
    else:
        raise ValueError(f"Unsupported spreadsheet format: {suffix}")


# -- XLSX ------------------------------------------------------------------

def _extract_xlsx(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return _extract_xlsx_bytes(f.read())


def _extract_xlsx_bytes(data: bytes) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        parts.append(f"[Sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


# -- XLS (legacy) ----------------------------------------------------------

def _extract_xls(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return _extract_xls_bytes(f.read())


def _extract_xls_bytes(data: bytes) -> str:
    try:
        import xlrd
        wb = xlrd.open_workbook(file_contents=data)
        parts = []
        for sheet in wb.sheets():
            parts.append(f"[Sheet: {sheet.name}]")
            for row_idx in range(sheet.nrows):
                cells = [str(sheet.cell_value(row_idx, col)) for col in range(sheet.ncols)]
                if any(c.strip() for c in cells):
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except ImportError:
        raise RuntimeError(
            ".xls format requires the 'xlrd' package. "
            "Install it with: pip install xlrd  OR save the file as .xlsx"
        )


# -- CSV -------------------------------------------------------------------

def _extract_csv_file(file_path: str) -> str:
    with open(file_path, newline="", encoding="utf-8-sig", errors="replace") as f:
        return _parse_csv(f)


def _extract_csv_bytes(data: bytes) -> str:
    text = data.decode("utf-8-sig", errors="replace")
    return _parse_csv(io.StringIO(text))


def _parse_csv(f) -> str:
    reader = csv.reader(f)
    rows = []
    for row in reader:
        if any(cell.strip() for cell in row):
            rows.append(" | ".join(row))
    return "\n".join(rows)
