"""
PDF text extraction — Phase 7A.

`extract_pdf_text(pdf_bytes) -> str` pulls plain text from a PDF (resumes are
text-based PDFs). Uses pypdf — lightweight, pure-Python, Lambda-friendly.

Used at resume-upload time: download the uploaded PDF from S3 → extract text →
embed (utils.embeddings.vectorize_text) → store on the resumes row.
"""

import io

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes. Returns concatenated page text (stripped).
    Raises ValueError if no extractable text (e.g. a scanned/image-only PDF).
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt.strip())
    text = "\n\n".join(parts).strip()
    if not text:
        raise ValueError("No extractable text found in PDF (scanned/image-only?)")
    return text
