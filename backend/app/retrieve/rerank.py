"""EXPERIMENTAL — LLM query expansion and candidate reranking (D-054).

Status: not wired into chat. The Gate 2 experiment showed the reranker still
omitted the expected Q3 passage and cost ~15.6 s/query, so it was rejected in
favour of the title-aware RRF boost (D-061). Kept for reference and future work.

Usage:
    python -m app.retrieve.rerank "swiss cheese model" --k 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import settings
from app.ingest.store import connect
from app.retrieve.search import Hit, search

RERANK_MODEL = "gpt-4o-mini"
CANDIDATES = 40
SNIPPET_CHARS = 420

EXPAND_PROMPT = """You help search an aviation safety, human-factors and quality library.
Rewrite the user's question as 2 alternative search queries that use the vocabulary likely to
appear in textbooks and standards (synonyms, standard terms, abbreviations spelled out).
Keep each query short (under 15 words). Return JSON only: {"queries": ["...", "..."]}."""

RERANK_PROMPT = """You rank library passages for answering an aviation safety / human factors /
quality question. Judge whether each passage actually helps answer the question, using its title,
page and excerpt. Prefer passages that state the concept asked about, not merely mention a keyword.

Return JSON only: {"ranking": [candidate ids in best-first order]}. Include every candidate that is
useful; omit clearly irrelevant ones. Do not invent ids."""


def _completion_json(messages: list[dict], max_tokens: int = 400) -> dict:
    import litellm

    response = litellm.completion(
        model=RERANK_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        api_key=settings.openai_api_key,
        timeout=60,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def expand_queries(question: str) -> list[str]:
    try:
        data = _completion_json(
            [
                {"role": "system", "content": EXPAND_PROMPT},
                {"role": "user", "content": question},
            ],
            max_tokens=200,
        )
        queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        return queries[:2]
    except Exception as exc:  # noqa: BLE001
        print(f"query expansion skipped: {exc}", file=sys.stderr)
        return []


def candidate_pool(conn, question: str, lance_dir: Path | None, use_vectors: bool) -> list[Hit]:
    """Hybrid hits for the question plus expanded queries, merged by first-seen order."""
    pools = [search(conn, question, CANDIDATES, lance_dir, use_vectors)]
    for variant in expand_queries(question):
        try:
            pools.append(search(conn, variant, 10, lance_dir, use_vectors))
        except Exception as exc:  # noqa: BLE001
            print(f"expanded query failed: {exc}", file=sys.stderr)
    seen: set[int] = set()
    merged: list[Hit] = []
    for pool in pools:
        for hit in pool:
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            merged.append(hit)
    return merged[:CANDIDATES]


def rerank(question: str, hits: list[Hit], top_k: int = 5) -> list[Hit]:
    if len(hits) <= 1:
        return hits[:top_k]
    lines = []
    for i, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.text.split())[:SNIPPET_CHARS]
        lines.append(f"[{i}] {hit.title} — p.{hit.page_no} ({hit.collection})\n{snippet}")
    try:
        data = _completion_json(
            [
                {"role": "system", "content": RERANK_PROMPT},
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nCandidates:\n\n" + "\n\n".join(lines),
                },
            ],
            max_tokens=600,
        )
        order = [int(x) for x in data.get("ranking", []) if 1 <= int(x) <= len(hits)]
        ordered: list[Hit] = []
        used: set[int] = set()
        for idx in order:
            if idx in used:
                continue
            used.add(idx)
            ordered.append(hits[idx - 1])
        ordered.extend(hit for i, hit in enumerate(hits, start=1) if i not in used)
        return ordered[:top_k]
    except Exception as exc:  # noqa: BLE001
        print(f"rerank skipped: {exc}", file=sys.stderr)
        return hits[:top_k]


def search_reranked(
    conn,
    question: str,
    k: int = 5,
    lance_dir: Path | None = None,
    use_vectors: bool = True,
    expand: bool = True,
) -> list[Hit]:
    pool = candidate_pool(conn, question, lance_dir, use_vectors) if expand else search(
        conn, question, CANDIDATES, lance_dir, use_vectors
    )
    return rerank(question, pool, k)


def main() -> None:
    parser = argparse.ArgumentParser(prog="aerovault-rerank")
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--db", default=str(Path(settings.data_dir) / "aerovault.db"))
    parser.add_argument("--lance", default=str(Path(settings.data_dir) / "lancedb"))
    parser.add_argument("--no-vectors", action="store_true")
    args = parser.parse_args()

    conn = connect(Path(args.db))
    hits = search_reranked(conn, args.query, args.k, Path(args.lance), not args.no_vectors)
    conn.close()
    print(json.dumps([
        {"rank": i + 1, "title": hit.title, "page": hit.page_no, "score": round(hit.score, 5)}
        for i, hit in enumerate(hits)
    ], indent=2))


if __name__ == "__main__":
    main()
