"""Embedding client: LiteLLM when available, otherwise direct OpenAI HTTP."""

from __future__ import annotations

import json
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
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    return [item["embedding"] for item in data["data"]]


def embed_texts(
    texts: list[str], model: str, api_key: str, batch_size: int = 128
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            vectors.extend(_embed_litellm(batch, model, api_key))
        except ImportError:
            vectors.extend(_embed_http(batch, model, api_key))
    return vectors
