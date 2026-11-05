"""
Ingest knowledge documents into Pinecone (knowledge namespace).

Supports text PDFs via PyMuPDF. OCR for scanned PDFs uses Claude Vision.

Usage:
    poetry run python scripts/seed_pinecone_knowledge.py --docs-dir ../docs/knowledge

Each PDF is chunked by words (500-word chunks, 50-word overlap).
Metadata: source (filename), doc_type (from filename prefix), vertical.

Filename convention:
    interior_pricing.pdf   → doc_type=interior, vertical=interior
    re_pricing.pdf         → doc_type=real_estate, vertical=real_estate
    general_faq.pdf        → doc_type=general, vertical=both
"""

import argparse
import asyncio
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import fitz  # PyMuPDF
from services import claude, pinecone_svc

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
MIN_TEXT_CHARS = 50


def _vertical_from_name(name: str) -> str:
    n = name.lower()
    if n.startswith("interior") or n.startswith("id_"):
        return "interior"
    if n.startswith("re_") or n.startswith("real_estate"):
        return "real_estate"
    return "both"


def _doc_type_from_name(name: str) -> str:
    n = name.lower()
    if "pricing" in n:   return "pricing"
    if "process" in n:   return "process"
    if "faq" in n:       return "faq"
    if "project" in n:   return "project"
    if "timeline" in n:  return "timeline"
    return "knowledge"


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + size]))
        i += size - overlap
    return chunks


async def ocr_page_claude(page) -> str:
    """Use Claude Vision to extract text from a scanned page."""
    import base64
    import anthropic
    from config import settings

    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    b64 = base64.b64encode(img_bytes).decode()

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": b64},
                },
                {"type": "text", "text": "Extract all text from this page. Output only the text, no commentary."},
            ],
        }],
    )
    return response.content[0].text.strip()


async def process_pdf(path: str, vertical: str, doc_type: str) -> list[dict]:
    filename = os.path.basename(path)
    doc = fitz.open(path)
    all_chunks: list[dict] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if len(text) < MIN_TEXT_CHARS:
            print(f"  Page {page_num}: text too short ({len(text)} chars) — running OCR")
            text = await ocr_page_claude(page)

        for i, chunk in enumerate(chunk_text(text)):
            chunk_id = hashlib.md5(f"{filename}_{page_num}_{i}".encode()).hexdigest()[:16]
            all_chunks.append({
                "id":       chunk_id,
                "text":     chunk,
                "source":   filename,
                "doc_type": doc_type,
                "vertical": vertical,
            })

    doc.close()
    return all_chunks


async def main(docs_dir: str) -> None:
    claude.init()
    pinecone_svc.init()

    pdfs = [f for f in os.listdir(docs_dir) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"No PDFs found in {docs_dir}")
        return

    total = 0
    for pdf in sorted(pdfs):
        path = os.path.join(docs_dir, pdf)
        name = os.path.splitext(pdf)[0]
        vertical = _vertical_from_name(name)
        doc_type = _doc_type_from_name(name)

        print(f"\n{pdf} ({vertical}, {doc_type})")
        chunks = await process_pdf(path, vertical, doc_type)
        if chunks:
            await pinecone_svc.upsert_knowledge(chunks)
            print(f"  → Upserted {len(chunks)} chunks")
            total += len(chunks)

    print(f"\nDone. Total chunks: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="../docs/knowledge")
    args = parser.parse_args()
    asyncio.run(main(args.docs_dir))
