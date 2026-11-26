"""BM25 keyword search over an app's knowledge/ folder. No vector database."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from has have in into is it its of on or that the this to was "
    "were will with any all after before then than".split()
)
SUFFIXES = ("ing", "ed", "es", "s")
TEXT_SUFFIXES = (".md", ".txt")


def tokens(text: str) -> list[str]:
    out = []
    for word in TOKEN.findall(text.lower()):
        if word in STOPWORDS or len(word) < 2:
            continue
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        out.append(word)
    return out


@dataclass(frozen=True)
class Passage:
    source: str
    heading: str
    text: str
    title: str = ""


def _split_markdown(source: str, text: str) -> list[Passage]:
    passages, title, heading, lines = [], "", "", []

    def flush():
        body = "\n".join(lines).strip()
        if body:
            passages.append(Passage(source, heading, body, title))

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            flush()
            heading, lines = line.lstrip("# ").strip(), []
            if line.lstrip().startswith("# ") and not title:
                title = heading
        else:
            lines.append(line)
    flush()
    return passages


def _split_text(source: str, text: str) -> list[Passage]:
    return [Passage(source, "", p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()]


class KnowledgeIndex:
    k1 = 1.5
    b = 0.75

    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.docs = [tokens(f"{p.title} {p.heading} {p.text}") for p in passages]
        self.lengths = [len(d) for d in self.docs]
        self.avg = (sum(self.lengths) / len(self.docs)) if self.docs else 0
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.counts = [Counter(d) for d in self.docs]

    @classmethod
    def build(cls, folder: Path | None) -> "KnowledgeIndex":
        passages = []
        if folder and Path(folder).is_dir():
            for path in sorted(Path(folder).rglob("*")):
                if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                source = path.relative_to(folder).as_posix()
                split = _split_markdown if path.suffix.lower() == ".md" else _split_text
                passages.extend(split(source, text))
        return cls(passages)

    def search(self, query: str, k: int = 3) -> list[Passage]:
        terms = set(tokens(query))
        scored = []
        for i, counts in enumerate(self.counts):
            score = 0.0
            for t in terms:
                f = counts.get(t)
                if not f:
                    continue
                norm = f + self.k1 * (1 - self.b + self.b * self.lengths[i] / (self.avg or 1))
                score += self.idf[t] * f * (self.k1 + 1) / norm
            if score > 0:
                scored.append((score, i))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [self.passages[i] for _, i in scored[:k]]
