#!/usr/bin/env python
"""Scientific / Technical Retrieval Evaluation Harness (Skeleton)

Goal: Provide baseline retrieval metrics (Recall@K, MRR, SectionCoverage) on a curated research corpus.

Current Status: Skeleton. Fill in TODO sections to integrate with project RAG system.

Example usage:
  poetry run python scripts/eval_retrieval_science.py \
    --queries research_eval/queries/sample_queries.jsonl \
    --gold research_eval/gold/sample_spans.jsonl \
    --k 5 --k 10 \
    --run-id $(date +%Y%m%d)_baseline_raw \
    --out research_eval/runs/$(date +%Y%m%d)_baseline_raw.json

Input formats (JSONL):
  Query line: {"query_id": 1, "text": "What is contrastive pretraining?", "expected_sections": ["abstract"], "answerable": true}
  Gold span: {"span_id": "d1_s4", "doc_id": "doc1", "section": "methods", "text": "We fine-tune ..."}

Integration TODO:
  - Implement `perform_search` to call existing RAG retrieval (import from rag/system if available)
  - Decide how to map retrieved chunks to doc_id + section (metadata fields)

Metrics definitions:
  Recall@K: Any gold span's doc appears in top K retrieved chunks (doc-level) OR exact span text match if indexing supports it.
  MRR: Reciprocal rank of first gold doc among retrieved.
  SectionCoverage: At least one retrieved chunk comes from any expected section.

Outputs a JSON artifact with aggregate + per-query stats.
"""
from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Iterable, Tuple, Optional, Set

# --- Data Structures -----------------------------------------------------------------

@dataclass
class Query:
    query_id: int
    text: str
    expected_sections: List[str]
    answerable: bool

@dataclass
class GoldSpan:
    span_id: str
    doc_id: str
    section: str
    text: str

@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    section: str
    score: float

# --- Parsing Helpers -----------------------------------------------------------------

def read_jsonl(path: str, loader) -> List[Any]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append(loader(obj))
    return out


def load_query(obj: Dict[str, Any]) -> Query:
    return Query(
        query_id=int(obj["query_id"]),
        text=obj["text"],
        expected_sections=obj.get("expected_sections", []),
        answerable=bool(obj.get("answerable", True)),
    )


def load_gold(obj: Dict[str, Any]) -> GoldSpan:
    return GoldSpan(
        span_id=obj["span_id"],
        doc_id=obj["doc_id"],
        section=obj.get("section", "other"),
        text=obj["text"],
    )

# --- Retrieval Integration Placeholder ------------------------------------------------

# TODO: integrate with actual RAG system.
# For now, we provide a stub that returns empty to avoid accidental misuse.

def perform_search(query: str, k: int) -> List[RetrievedChunk]:  # pragma: no cover - placeholder
    # Replace with import + call into existing retrieval.
    # Example expected shape filled with dummy content:
    # return [RetrievedChunk(chunk_id="c1", doc_id="doc1", section="methods", score=0.82)]
    return []

# --- Metric Computation ---------------------------------------------------------------

def compute_metrics(
    queries: List[Query],
    gold_spans: List[GoldSpan],
    ks: List[int],
) -> Dict[str, Any]:
    gold_by_query_doc: Dict[int, Set[str]] = {}
    gold_sections_by_query: Dict[int, Set[str]] = {}

    # Without explicit mapping query->gold spanning we infer by naive text match OR future mapping file.
    # For MVP assume all gold spans are globally relevant; refine later with explicit mapping file.
    # TODO: add optional mapping input.
    all_gold_docs = {g.doc_id for g in gold_spans}
    all_gold_sections = {g.section for g in gold_spans}

    per_query = []

    mrr_ranks: List[int] = []
    recall_counts: Dict[int, int] = {k: 0 for k in ks}
    section_coverage_counts: Dict[int, int] = {k: 0 for k in ks}

    for q in queries:
        retrieved: List[RetrievedChunk] = perform_search(q.text, max(ks))
        doc_ids_order = [r.doc_id for r in retrieved]
        sections_order = [r.section for r in retrieved]

        # MRR doc-level: first gold doc rank
        rank = None
        for idx, d in enumerate(doc_ids_order):
            if d in all_gold_docs:
                rank = idx + 1
                break
        if rank is not None:
            mrr_ranks.append(rank)

        # Recall@K (doc-level)
        for k in ks:
            top_docs = set(doc_ids_order[:k])
            if top_docs & all_gold_docs:
                recall_counts[k] += 1
            # Section coverage: expected vs actual (approximate)
            if q.expected_sections:
                top_sections = set(sections_order[:k])
                if top_sections & set(q.expected_sections):
                    section_coverage_counts[k] += 1

        per_query.append({
            "query_id": q.query_id,
            "rank_first_gold": rank,
            **{f"gold_hit@{k}": (rank is not None and rank <= k) for k in ks},
        })

    total = len(queries)
    metrics: Dict[str, Any] = {}
    if mrr_ranks:
        metrics["mrr"] = sum(1.0 / r for r in mrr_ranks) / len(queries)
    for k in ks:
        metrics[f"recall_at_{k}"] = recall_counts[k] / total
        metrics[f"section_cov_at_{k}"] = section_coverage_counts[k] / total

    return {"metrics": metrics, "per_query": per_query}

# --- Main CLI ------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate retrieval on research corpus (skeleton)")
    ap.add_argument("--queries", required=True, help="Path to queries JSONL")
    ap.add_argument("--gold", required=True, help="Path to gold spans JSONL")
    ap.add_argument("--k", action="append", type=int, default=[5], help="K values (repeatable)")
    ap.add_argument("--run-id", required=True, help="Run identifier string")
    ap.add_argument("--out", required=True, help="Output JSON path")
    args = ap.parse_args()

    ks = sorted(set(args.k))
    queries = read_jsonl(args.queries, load_query)
    gold = read_jsonl(args.gold, load_gold)

    result = compute_metrics(queries, gold, ks)
    artifact = {
        "run_id": args.run_id,
        "ks": ks,
        **result,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2)
    print(f"Wrote results to {args.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
