"""Extract plain text from uploaded resume files (PDF / DOCX / TXT)."""
import io


class UnsupportedFileType(Exception):
    pass


def extract_text(filename: str, content: bytes) -> str:
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        return _extract_pdf(content)
    if name.endswith(".docx"):
        return _extract_docx(content)
    if name.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="ignore")

    raise UnsupportedFileType(
        "Unsupported file type. Use PDF, DOCX, TXT or MD."
    )


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedFileType(
            "PDF support requires the 'pypdf' package."
        ) from exc

    reader = PdfReader(io.BytesIO(content))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts).strip()


def _extract_docx(content: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedFileType(
            "DOCX support requires the 'python-docx' package."
        ) from exc

    document = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs).strip()
