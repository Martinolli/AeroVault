"""Benchmark runner: reads 6_Retrieval_Benchmark.md, runs the 25 questions.

Usage:
    python -m app.retrieve.benchmark --benchmark /app/Project_Documents/6_Retrieval_Benchmark.md \
        --out /data/benchmark_results.csv [--expected /data/benchmark_expected.csv] [--no-vectors]

Expected CSV (optional, filled after manual page confirmation):
    qnum,doc_contains,page
    1,HFACS,42
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import time
from pathlib import Path

from app.config import settings
from app.ingest.store import connect

from .search import search


def parse_questions(md_path: Path) -> list[dict]:
    questions: list[dict] = []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        questions.append({
            "num": int(cells[0]),
            "question": cells[1],
            "collection": cells[2],
            "doc_hint": cells[3],
            "answerable": cells[2] not in ("—", "-", ""),
        })
    return questions


def load_expected(path: Path) -> dict[int, tuple[str, int | None]]:
    out: dict[int, tuple[str, int | None]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            page = row.get("page", "").strip()
            out[int(row["qnum"])] = (row["doc_contains"].strip().lower(), int(page) if page else None)
    return out


def is_match(hit, doc_contains: str, page: int | None) -> bool:
    doc_ok = doc_contains in hit.title.lower() or doc_contains in hit.rel_path.lower()
    page_ok = page is None or hit.page_no == page
    return doc_ok and page_ok


def main() -> None:
    parser = argparse.ArgumentParser(prog="aerovault-benchmark")
    parser.add_argument("--benchmark", default="/docs/6_Retrieval_Benchmark.md")
    parser.add_argument("--out", default="/data/benchmark_results.csv")
    parser.add_argument("--expected", default=None)
    parser.add_argument("--db", default=str(Path(settings.data_dir) / "aerovault.db"))
    parser.add_argument("--lance", default=str(Path(settings.data_dir) / "lancedb"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--no-vectors", action="store_true")
    args = parser.parse_args()

    questions = parse_questions(Path(args.benchmark))
    expected = load_expected(Path(args.expected)) if args.expected else {}
    conn = connect(Path(args.db))

    rows = []
    ranks: list[int | None] = []
    latencies: list[float] = []
    for q in questions:
        t0 = time.time()
        hits = search(conn, q["question"], args.k, Path(args.lance), not args.no_vectors)
        latency = time.time() - t0
        latencies.append(latency)

        rank = None
        if q["num"] in expected:
            doc_contains, page = expected[q["num"]]
            for i, hit in enumerate(hits, start=1):
                if is_match(hit, doc_contains, page):
                    rank = i
                    break
            if q["answerable"]:
                ranks.append(rank)

        for i, hit in enumerate(hits, start=1):
            rows.append({
                "qnum": q["num"], "question": q["question"], "rank": i,
                "title": hit.title, "page": hit.page_no, "source": hit.source,
                "score": round(hit.score, 5), "text": hit.text[:300].replace("\n", " "),
                "latency_s": round(latency, 2),
            })
        print(f"Q{q['num']:2d} top: {hits[0].title[:60] if hits else 'NO HITS'} "
              f"p.{hits[0].page_no if hits else '-'}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["qnum"])
        writer.writeheader()
        writer.writerows(rows)
    conn.close()

    summary: dict = {
        "questions": len(questions),
        "scored": len(ranks),
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "results_csv": str(out),
    }
    if ranks:
        top1 = sum(1 for r in ranks if r == 1)
        top5 = sum(1 for r in ranks if r and r <= 5)
        mrr = sum((1.0 / r) for r in ranks if r) / len(ranks)
        summary.update({
            "top1_accuracy": round(top1 / len(ranks), 3),
            "top5_recall": round(top5 / len(ranks), 3),
            "mrr": round(mrr, 3),
            "gate2_pass": (top5 / len(ranks)) >= 0.8,
        })
    else:
        summary["note"] = "No --expected mapping yet; fill pages and re-run to score."
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
