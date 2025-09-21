# Research Evaluation Assets

This directory holds inputs and outputs for the scientific / technical retrieval evaluation workflow.

## Structure
- `queries/` : Query sets (`*.jsonl` or `*.json`) describing evaluation queries and metadata.
- `gold/` : Gold factual spans / references used for recall metrics.
- `runs/` : Result artifacts from evaluation harness executions.

## File Conventions
### Query File Example (`queries/sample_queries.jsonl`)
One JSON per line:
```
{"query_id": 1, "text": "What is contrastive pretraining?", "expected_sections": ["abstract", "introduction"], "difficulty": 1, "answerable": true}
```

### Gold Spans Example (`gold/sample_spans.jsonl`)
```
{"span_id": "acl2024_p1_s3", "doc_id": "acl2024_p1", "section": "methods", "text": "We fine-tune the model using ..."}
```

### Run Artifact (`runs/2025-09-21_baseline_raw.json`)
```
{
  "run_id": "2025-09-21_baseline_raw",
  "config": {"embedding_model": "sentence-transformers/all-MiniLM-L6-v2"},
  "metrics": {"recall_at_5": 0.62, "mrr": 0.44},
  "per_query": [
    {"query_id": 1, "gold_hit@5": true, "rank": 3, "hit_doc_ids": ["arxiv:1234.5678"]}
  ]
}
```

## Workflow Summary
1. Populate a small corpus (e.g. with `scripts/build_arxiv_sample.py`).
2. Create initial query + gold span files.
3. Run evaluation harness (future script) to compute metrics.
4. Store run artifact & compare over time.

---
End of file.
