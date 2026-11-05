"""
Parse visit_date strings returned by the signal extractor.

The LLM resolves relative expressions ("this Saturday", "next week Tuesday", "15th")
to YYYY-MM-DD using today's date injected into the prompt. This function just validates
and converts that output to a Python date object.
"""

from datetime import date


def parse_visit_date(raw: str) -> date | None:
    """Parse a YYYY-MM-DD string from the signal extractor. Returns None on failure."""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None
