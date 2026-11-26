"""Turn uploaded files into text for the prompt."""
import io
from pathlib import PurePath

MAX_CHARS = 60_000
TEXT_TYPES = (".txt", ".log", ".csv", ".md", ".json")


def extract_text(filename: str, data: bytes) -> str:
    suffix = PurePath(filename).suffix.lower()
    if suffix in TEXT_TYPES:
        text = data.decode("utf-8", errors="replace")
    elif suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError(f"{suffix or 'these'} files are not supported; use .txt, .log, .csv or .pdf")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + f"\n[... cut at {MAX_CHARS} characters]"
    return text
