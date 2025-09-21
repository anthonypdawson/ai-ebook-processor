# Hallucination Mitigation & Grounded Summarization Plan

Status: Draft (Phase 1)
Last Updated: 2025-09-21

## Motivation
Current summaries (see `output/ebook_processing_results_*.json`) display fabricated plot elements, invented quotes, repeated boilerplate (“Here is a concise summary...”), and claims about parts of the book not included in the truncated context. This undermines trust in downstream RAG usage, evaluation, and user-facing features.

## Core Problems Identified
| Issue | Cause | Impact |
|-------|-------|--------|
| Truncation bias | Only first ~10k chars passed into `create_book_summary` | Model extrapolates missing middle/end |
| Generative prompt | Analyst-style prompt invites speculation | Hallucinated themes, invented quotes |
| No evidence binding | Model not forced to cite chunks | unverifiable claims |
| Temperature default (0.7) | High diversity settings | Drifts away from source |
| Single-pass monolith | No structured fact extraction step | Mixed granularity + repetition |
| No uncertainty channel | Model forced to “produce” | Fewer admissions of unknown |
| No evaluation tooling | Hard to detect regression | Hidden accuracy decay |

## Design Goals
1. Ground every claim in surfaced evidence (chunk index referencing).
2. Make hallucination *expensive* by requiring explicit source links or UNKNOWN.
3. Provide structured intermediate data (entities, events, locations) for reuse.
4. Preserve a “classic” mode for legacy loose summaries.
5. Enable incremental adoption (Phase 1 → Phase 3).

## Phased Approach
### Phase 1 (Quick Wins)
- Add config keys:
  - `processing.summary_mode: classic|strict`
  - `processing.summary_max_chars: 12000`
  - `processing.summary_temperature: 0.15`
  - `processing.require_citations: true`
- Implement `create_grounded_summary(chunks, metadata)` producing JSON:
```jsonc
{
  "coverage_percent": 78,
  "claims": [ {"text": "Diary format established early", "sources": [0]}, ...],
  "characters": [ {"name": "John", "first_chunk": 0}],
  "locations": ["San Antonio"],
  "potential_themes": ["survival"],
  "uncertain": ["Cause of outbreak"],
  "notes": ["Content beyond processed range not summarized"]
}
```
- Summary renderer converts structured JSON → human readable + disclaimer.
- Fallback: if coverage < 50% mark summary as PARTIAL.
- Enforce: no quotes unless **exactly** present verbatim in a chunk.

### Phase 2 (Structured Extraction Pipeline)
1. Per-chunk pass (low temp) → extract:
   - characters (canonical form)
   - events (verb phrase + subject) limited N
   - time markers / temporal progression
   - locations
2. Aggregator merges & deduplicates (Levenshtein / case-insensitive).
3. Timeline builder: early / mid / late arcs based on first appearance distribution.
4. Theme candidate detection: terms appearing in ≥2 non-adjacent chunks.
5. Final summarizer consumes structured store only (not raw narrative) → reduces drift.

### Phase 3 (Verification & Evaluation)
- Add optional “verification pass”: ask model to list speculative / weakly grounded claims; remove or tag.
- Add heuristic evaluation script `scripts/evaluate_summary.py`:
  - Token overlap ratio (claims tokens ∩ source tokens / claims tokens)
  - Entity hallucination rate: entities not present in source text vocabulary
  - UNKNOWN usage rate (should not be 0 in partial coverage)
  - Quote validation (reject fabricated quotes)
- Optional embedding-based entailment check (future).

## Prompt (Strict Mode Draft)
```
SYSTEM: You produce STRICT GROUNDED SUMMARIES.
RULES:
- Only use supplied EVIDENCE CHUNKS.
- Each claim MUST append sources like [c:12] or multiple [c:7,15].
- If unavailable: write UNKNOWN (do NOT guess or generalize).
- Do NOT fabricate dialogue or quotations.
- Only propose a theme if supported by ≥2 distinct chunks.
- Output valid JSON (UTF-8, no trailing commas) with keys: coverage_percent, claims, characters, locations, potential_themes, uncertain, notes.

EVIDENCE (each chunk shows index):
{EVIDENCE}
```

## Integration Points
| File | Change |
|------|--------|
| `ai_ebook_processor/models/ollama.py` | Add `create_grounded_summary` + adapt existing `create_book_summary` dispatch |
| `ai_ebook_processor/core/pipeline.py` | When `summary_mode == strict`, build chunk sample set & call grounded summary |
| `config/config.yml` | Add new config defaults |
| `README.md` | Add “Accuracy / Grounded Mode” section |
| `scripts/evaluate_summary.py` | New evaluation utility |

## Configuration Additions (proposed defaults)
```yaml
processing:
  summary_mode: strict
  summary_max_chars: 12000
  summary_temperature: 0.15
  require_citations: true
```

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Longer processing time | Allow classic mode fallback | 
| Model JSON malformation | Add lightweight JSON repair (single retry) |
| Over-fragmented claims | Post-merge adjacent claims with identical source sets |
| Excess UNKNOWN | Raise coverage or widen chunk sampling |

## Acceptance Criteria (Phase 1)
- Setting `summary_mode: strict` produces JSON+rendered summary with citations.
- No fabricated quotes detected (heuristic scan for quotes not in concatenated evidence).
- If only early 20% of book processed, summary flagged PARTIAL.
- Temperature observed ≤ configured value in request options.

## Migration / Cleanup Steps (Existing Contaminated DB)

If you previously ingested books using summary-derived `combined_result` content:

1. Stop any running processes using the RAG DB.
2. (Optional dry run) List what would be deleted:
  ```bash
  poetry run python scripts/reset_rag_db.py --dry-run
  ```
3. Wipe only collection contents (preserves path structure):
  ```bash
  poetry run python scripts/reset_rag_db.py --force
  ```
4. Or wipe entire persistence directory (fresh start):
  ```bash
  poetry run python scripts/reset_rag_db.py --drop-path --force
  ```
5. Reprocess ebooks using page-aware method where possible or standard pipeline (now emits `raw_chunks`).
6. Re-add to RAG via CLI / REPL `add` command (will now embed raw canonical text).
7. (Optional) Run evaluation script once added (future `scripts/evaluate_summary.py`).

### Verifying Clean Re-ingestion
After reprocessing, query the collection and ensure documents no longer contain boilerplate like "Here is a concise summary" and that rare proper nouns from the source appear in vector store.

## Future Enhancements
- Retrieval-assisted late-stage summary by sampling representative centroid chunks.
- Confidence scoring via entailment LLM on each claim.
- Diff-based re-summarization for updated books (hash change).

## Open Questions
- Should partial coverage auto-disable theme inference? (Likely yes if <40% coverage.)
- Persist structured extraction results for reuse in RAG answers? (Recommended.)

---
**Next Step:** Implement Phase 1 (config keys + grounded summary function + dispatch) then add evaluation script.
