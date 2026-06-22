"""Load and chunk the curated markdown knowledge base."""
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"
_MAX_CHARS = 700


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _chunk(text: str) -> list[str]:
    """Split a doc into paragraph-ish chunks, merging up to ~_MAX_CHARS."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if para.startswith("#"):  # drop standalone markdown headings
            continue
        if not buf:
            buf = para
        elif len(buf) + len(para) + 2 <= _MAX_CHARS:
            buf += "\n\n" + para
        else:
            chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return chunks


def load_chunks() -> list[dict]:
    """Return [{title, text, source}] for every chunk of every corpus file."""
    chunks: list[dict] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _first_heading(text) or path.stem
        for piece in _chunk(text):
            chunks.append({"title": title, "text": piece, "source": path.name})
    return chunks
