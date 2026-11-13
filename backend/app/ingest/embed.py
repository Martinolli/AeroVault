"""Embedding client: LiteLLM when available, otherwise direct OpenAI HTTP.

Requests are batched by estimated tokens (default 15k) to stay under low
per-minute limits, and retried with exponential backoff on 429s.
"""

from __future__ import annotations

import json
import time
import urllib.request


def _embed_litellm(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    from litellm import embedding

    resp = embedding(model=model, input=texts, api_key=api_key)
    out: list[list[float]] = []
    for item in resp.data:
        vector = item["embedding"] if isinstance(item, dict) else item.embedding
        out.append(list(vector))
    return out


def _embed_http(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.load(resp)
    return [item["embedding"] for item in data["data"]]


def _embed_batch(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    try:
        import litellm  # noqa: F401

        return _embed_litellm(texts, model, api_key)
    except ImportError:
        return _embed_http(texts, model, api_key)


def _iter_batches(texts: list[str], max_tokens: int, max_items: int):
    batch: list[str] = []
    tokens = 0
    for text in texts:
        t = max(1, len(text) // 4)
        if batch and (tokens + t > max_tokens or len(batch) >= max_items):
            yield batch
            batch, tokens = [], 0
        batch.append(text)
        tokens += t
    if batch:
        yield batch


def embed_texts(
    texts: list[str],
    model: str,
    api_key: str,
    batch_size: int = 64,
    max_batch_tokens: int = 15000,
    retries: int = 6,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for batch in _iter_batches(texts, max_batch_tokens, batch_size):
        for attempt in range(retries):
            try:
                vectors.extend(_embed_batch(batch, model, api_key))
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == retries - 1:
                    raise
                wait = min(65, 5 * 2**attempt)
                print(f"  embedding retry {attempt + 1}/{retries} in {wait}s: {str(exc)[:160]}", flush=True)
                time.sleep(wait)
    return vectors
