"""Text extraction + sliding window chunker."""

import re
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CHUNK_MIN = 300
CHUNK_MAX = 500
OVERLAP = 80


def extract_text(file_bytes: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return file_bytes.decode("utf-8", errors="replace")
    if suffix == ".docx":
        return _extract_docx(file_bytes)
    if suffix == ".pdf":
        return _extract_pdf(file_bytes)
    raise ValueError(f"Unsupported format: {suffix}")


def _extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(BytesIO(data))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    result = "\n\n".join(paragraphs)
    if len(result) >= 100:
        return result
    # Fallback: raw XML (WPS, text boxes)
    with zipfile.ZipFile(BytesIO(data)) as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    texts = [e.text.strip() for e in root.iter(f"{{{DOCX_NS}}}t") if e.text and e.text.strip()]
    return "\n".join(texts)


def _extract_pdf(data: bytes) -> str:
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    pages = [p.get_text("text").strip() for p in doc if p.get_text("text").strip()]
    doc.close()
    return "\n\n".join(pages)


def sliding_window(text: str) -> list[dict]:
    """Split long text into overlapping chunks. Each chunk gets an index and text."""
    chunks: list[dict] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + CHUNK_MAX, len(text))

        # Try to break at a natural boundary (sentence end, newline) within range
        if end < len(text):
            best = end
            for brk in ["\n\n", "\n", "。", ". ", "? ", "！", "! "]:
                pos = text.rfind(brk, start + CHUNK_MIN, end)
                if pos > 0:
                    best = pos + len(brk)
                    break
            end = best

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"id": f"sw-{idx+1:04d}", "text": chunk_text})
            idx += 1

        if end >= len(text):
            break
        start = end - OVERLAP

    return chunks
