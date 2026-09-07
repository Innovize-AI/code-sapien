"""Gemini Vision OCR — extracts text from scanned PDFs and images.

Used as fallback when pdfplumber returns insufficient text (image-based PDFs)
and for WhatsApp photo attachments.
"""
import base64
import logging
import os

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = (
    "Extract ALL text and data from this document exactly as it appears. "
    "For tables, preserve the structure using pipe-separated rows (col1 | col2 | col3). "
    "For handwritten text, transcribe as accurately as possible. "
    "Output only the extracted content — no commentary."
)


def extract_from_bytes(data: bytes, mime_type: str = "application/pdf") -> str:
    """Send raw bytes to Gemini Vision and return extracted text."""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set — cannot use vision extractor")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content([
            {"mime_type": mime_type, "data": base64.b64encode(data).decode()},
            _EXTRACT_PROMPT,
        ])
        return response.text.strip()
    except Exception as e:
        logger.error(f"[VISION] Extraction failed: {e}")
        raise


def extract_from_path(file_path: str) -> str:
    """Read a file and send to Gemini Vision. Supports PDF, PNG, JPG, WEBP."""
    from pathlib import Path
    suffix = Path(file_path).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_map.get(suffix, "application/pdf")
    with open(file_path, "rb") as f:
        return extract_from_bytes(f.read(), mime_type)
