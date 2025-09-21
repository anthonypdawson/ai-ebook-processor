# Dual Chunk + Summary Embeddings Design

Status: Draft
Owner: TBD
Last Updated: 2025-09-21

## 1. Problem Statement
Raw chunk embeddings provide factual grounding but can underperform when user queries are phrased abstractly (themes, intent, motivations) that are implicitly present but not lexically expressed. Summaries can bridge this semantic gap but introduce hallucination risk if directly embedded with or instead of raw text.

Goal: Introduce summaries in retrieval to improve recall of abstract / conceptual queries WITHOUT contaminating the vector space with hallucinated or ungrounded claims.

## 2. Core Principles
1. Separation of signals: Raw text vectors remain the canonical factual index.
2. Summaries are additive, not substitutive.
3. Guardrails restrict summary generation (low temperature, coverage checks).
4. Retrieval fusion must be transparent & auditable.
5. Easy rollback: Feature flag disables summary augmentation with zero schema migration.

## 3. Strategies Considered
| Strategy | Description | Pros | Cons | Decision |
|----------|-------------|------|------|----------|
| Concatenate raw+summary | Single embedding (raw text + summary) | Simple | Hallucination bleed; summary dominates | Rejected |
| Replace raw with summary | Only summary stored | Space saving | Loss of fidelity; high risk | Rejected |
| Dual embeddings (raw + summary) | Two vectors per chunk, fused at query time | Flexible; isolation | + storage/latency | Selected |
| Hierarchical (summary → raw) | 2-stage cascade | Efficient narrowing | Complexity | Future option |
| Summary as metadata only | Not embedded | Safe | No semantic gain | Optional |
| Dynamic query expansion | LLM expands query; raw only index | No storage cost | Per-query latency | Later exploration |

## 4. Selected Architecture: Dual Embeddings
For each logical chunk we upsert (up to) two records:
- raw: Original text span
- summary: Guarded, compressed representation

### 4.1 Data Model (Conceptual)
```
ChunkRecord {
  chunk_id: UUID
  doc_id: str
  order: int
  type: 'raw' | 'summary'
  text: str
  token_count: int
  coverage: float | null  # summary only
  source_span: (start_char:int, end_char:int) | null
  created_at: timestamp
  version: int
}
```

### 4.2 Summary Generation Guardrails
- Temperature: <= 0.2
- Max tokens: min(180, ~0.25 * raw_chunk_tokens)
- Coverage ratio: (# unique non-stopword content tokens in summary that occur in raw) / (# unique content tokens in summary) >= 0.65
- Reject if:
  - Coverage below threshold
  - Summary introduces OOV proper nouns (detected via simple capitalized token diff excluding sentence start words)
  - Summary length < 25 tokens (likely trivial) unless chunk itself is small

### 4.3 Prompt Template (Initial)
```
You are a faithful compression engine.
Summarize the following text WITHOUT adding facts, interpretations, motivations, or external knowledge.
Keep concrete nouns, entities, and key actions. No analysis beyond what is explicitly stated.
Text:
"""
{{RAW_CHUNK}}
"""
Return ONLY the summary.
```

### 4.4 Ingestion Flow
1. Chunking step produces `raw_chunks` (already implemented).
2. For each `raw_chunk` (config: `rag.summary_augmentation.mode == 'dual'`):
   - Generate candidate summary
   - Run coverage + OOV checks
   - If passes → store summary record
3. Always store raw record
4. Upsert into Chroma (two documents; differentiate via metadata.type)

### 4.5 Retrieval Flow
```
query_embedding_raw = embed(query)
if mode == 'dual':
  query_embedding_summary = embed(query)  # (optional reuse; same encoder) OR same vector reused

raw_hits = search(collection=raw, k=K_raw)
summary_hits = search(collection=summary, k=K_summary)
merge by chunk_id:
  score = w_raw * sim_raw + w_sum * sim_summary (missing treated as 0)

rerank(optional) top N using cross-encoder on original raw text only
return ranked chunks
```

### 4.6 Scoring Weights (Configurable)
Default:
```
weights:
  raw: 0.7
  summary: 0.3
```
Rationale: Raw retention priority, summary augments recall.

### 4.7 Config Additions
```
rag:
  summary_augmentation:
    mode: none  # none|dual|hierarchical|metadata
    temperature: 0.15
    max_summary_tokens: 180
    coverage_min: 0.65
    weight:
      raw: 0.7
      summary: 0.3
    k:
      raw: 25
      summary: 8
    evaluation:
      enabled: true
      sample_size: 50
```

### 4.8 Logging & Observability
For each ingestion batch:
- total_chunks
- summaries_generated
- summaries_rejected (by reason: coverage, OOV, short)
- avg_coverage, p10/p50/p90 coverage
- latency per summary gen (mean, p95)

At retrieval:
- counts: raw_hits, summary_hits, merged
- blended score components (sampled)
- fallback path if one modality empty

### 4.9 Failure Modes & Mitigations
| Failure | Impact | Mitigation |
|---------|--------|------------|
| Low coverage summary passes | Slight abstraction drift | Tight threshold; evaluate distribution |
| Proper noun hallucination | False retrieval context | OOV filter + periodic audits |
| Storage blowup | Disk pressure | Configurable mode; pruning tool |
| Latency increase | Slower queries | Parallel searches; cap K_summary |
| Weight mis-tuned | Suboptimal ranking | AB compare vs baseline |

### 4.10 Rollout Plan
1. Implement config + dual storage behind `mode=dual`.
2. Add ingestion instrumentation JSON report.
3. Add retrieval fusion + debug flag to print blend math.
4. Offline evaluation script: baseline (raw only) vs dual on saved query set.
5. Tune weights & coverage threshold.
6. Default remains `none` until metrics show improvement.

### 4.11 Evaluation Metrics
- Recall@K (query set with known answer spans)
- MRR / NDCG (if graded relevance dataset prepared)
- Factual answer accuracy (LLM judge with citation verification)
- Latency delta (%)
- Disk usage delta (%)
- Hallucination incidence in answers (manual or LLM critique pass)

### 4.12 Future Extensions
- Hierarchical cascade (chapter → chunk) index
- Adaptive summary regeneration when threshold fails
- Entity graph extraction for faceted filtering
- Compression ensembles (different prompt styles)
- Distillation: train smaller model on accepted summaries

## 5. Minimal Code Changes (Planned)
- `config/config.yml`: add `rag.summary_augmentation` block
- `core/summary.py`: new module with generation + validation
- `rag/system.py`: modify ingestion to branch on mode and upsert dual docs
- `rag/retrieval.py`: new retrieval fusion helper
- `scripts/evaluate_retrieval.py`: baseline vs dual comparison
- `scripts/prune_summaries.py`: optional cleanup if reverting

## 6. Open Questions
- Should we store summary + raw in same collection with metadata filter, or separate logical collections? (Start: same collection; filter by `type`).
- Reuse the same embedding model for summaries? (Yes initially for simplicity.)
- Do we need per-summary embedding dimension normalization to prevent shorter text bias? (Investigate post-MVP.)

## 7. Decision Log
- 2025-09-21: Chose dual embedding approach; deferred hierarchical cascade.

## 8. Success Criteria
Feature considered successful if dual mode yields:
- ≥ +8% relative improvement in Recall@10 on abstract queries
- ≤ 30% query latency increase
- ≤ 2.2x storage growth (expected ~2x)
- No measurable increase in hallucination rate in answer outputs

---
End of document.
