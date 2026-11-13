"""Page-aware chunking: ~750-token chunks with overlap, never crossing pages."""

from __future__ import annotations

MAX_CHARS = 3000
OVERLAP = 400


def normalize(text: str) -> str:
    return " ".join(text.split())


def chunk_page(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    text = normalize(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
