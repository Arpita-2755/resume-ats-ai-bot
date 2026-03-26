from __future__ import annotations

import io
import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def parse_text_from_path(path: str | Path) -> str:
    file_path = Path(path)
    return parse_text_from_bytes(file_path.name, file_path.read_bytes())


def parse_text_from_bytes(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return file_bytes.decode("utf-8", errors="ignore").strip()
    if suffix == ".pdf":
        return _parse_pdf(file_bytes).strip()
    if suffix in {".docx", ".docm"}:
        return _parse_docx(file_bytes).strip()
    if suffix == ".doc":
        return _parse_doc(file_bytes).strip()
    # Fall back to text decode for unknown extensions.
    return file_bytes.decode("utf-8", errors="ignore").strip()


def _parse_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _parse_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(lines)


def _parse_doc(file_bytes: bytes) -> str:
    # Best-effort: use antiword if available, otherwise decode plain text fragments.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)
    try:
        try:
            result = subprocess.run(
                ["antiword", str(tmp_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            text = result.stdout.strip()
            if text:
                return text
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        decoded = file_bytes.decode("latin-1", errors="ignore")
        decoded = re.sub(r"[^\x20-\x7E\n\t]", " ", decoded)
        decoded = re.sub(r"\s+", " ", decoded)
        return decoded.strip()
    finally:
        tmp_path.unlink(missing_ok=True)

