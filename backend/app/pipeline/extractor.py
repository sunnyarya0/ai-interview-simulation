import re
from pathlib import Path

import pdfplumber
from docx import Document


def _clean(text: str) -> str:
    # Collapse runs of blank lines and trailing whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(file_path: str) -> str:
    parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(file_path: str) -> str:
    """Extract plain text from a PDF or DOCX resume."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        raw = _extract_pdf(file_path)
    elif ext == ".docx":
        raw = _extract_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return _clean(raw)


if __name__ == "__main__":
    import sys

    print(extract_text(sys.argv[1]))
