# Reprocessing Guide (Clean RAG Rebuild)

Status: Draft
Last Updated: 2025-09-21

## Purpose
Provide a reliable, repeatable procedure to wipe contaminated / outdated vector data and re-ingest ebooks using the current raw-text embedding pipeline (and future optional augmentation modes) with validation & troubleshooting steps.

## When To Reprocess
- Switched from summary-based to raw-text embeddings
- Updated chunking logic or tokenizer
- Added / removed major preprocessing filters (e.g., boilerplate removal)
- Found hallucinated concepts embedded in vector store
- Large config changes (embedding model, normalization strategy)

## High-Level Stages
1. Assess current state
2. Backup (optional)
3. Wipe vector DB
4. Re-run processing pipeline per ebook
5. Ingest into RAG store
6. Verify ingestion integrity
7. Run basic retrieval smoke tests
8. Archive run metadata

---
## 1. Assess Current State
Check collection stats (example calls vary by implementation). If you log or expose a CLI, run:
- Count documents
- Sample metadata (ensure fields like `type`, `doc_id`, etc.)

If uncertain about contamination: search for phrases you know only appear in AI-generated summaries (e.g., "In summary," "Overall," "This section describes"). If results surface those artificial patterns frequently, proceed with wipe.

## 2. Optional Backup
If you want a rollback path:
```
cp -r ebook_db ebook_db_backup_$(date +%Y%m%d_%H%M)
```
(Windows PowerShell equivalent – adapt path) Ensure no process is writing during copy.

## 3. Wipe Vector DB
Dry run:
```
poetry run python scripts/reset_rag_db.py --dry-run
```
Force delete (collection-level):
```
poetry run python scripts/reset_rag_db.py --force
```
Full path removal (start fresh):
```
poetry run python scripts/reset_rag_db.py --drop-path --force
```

## 4. Process Ebooks
For each source file (example patterns: `.epub`, `.txt`, `.pdf` if supported):
Invoke your existing pipeline (CLI/REPL). Example conceptual command:
```
poetry run python cli.py process --input path/to/book.epub --out output/
```
Outputs should now include:
- raw_chunks
- raw_text
- (optional) combined_result (legacy)

If using REPL:
```
repl> process path/to/book.epub
```
(Adjust to actual command verbs.)

## 5. Ingest into RAG
Once processed JSON or in-memory object is available:
```
poetry run python cli.py rag add --input processed_output.json
```
Or via REPL:
```
repl> rag add processed_output.json
```
If dual embedding / augmentation modes appear later, ensure mode flag off unless intentionally testing:
```
--summary-mode none
```

## 6. Verify Ingestion Integrity
Programmatic quick checks (pseudo):
- Total vectors ≈ sum(raw_chunk_counts)
- No document text contains disallowed summary boilerplate
- Random sample query yields expected literal sentence fragments

Manual spot test queries:
| Query Type | Example |
|------------|---------|
| Proper noun | Character / term from mid-book |
| Rare object | Specific tool / artifact mentioned once |
| Location | Place name |
| Event recall | "What happens after X?" |

Failure indicators:
- Generic filler retrieval dominating top K
- Duplicated near-identical chunks (over-splitting) – re-check chunking config

## 7. Basic Retrieval Smoke Tests
Construct a minimal JSON file of test queries:
```
[
  {"q": "Main conflict object", "expect_hit": true},
  {"q": "Introductory phrase 'Once upon'", "expect_hit": true}
]
```
Run an ad-hoc script (future harness) to ensure each returns at least one hit.

## 8. Archive Run Metadata
Store a run descriptor (suggested directory: `runs/`):
```
{
  "run_id": "2025-09-21_raw_reset",
  "embedding_model": "<model_name>",
  "chunk_strategy": {"size": 800, "overlap": 80},
  "books": ["book1.epub", "book2.txt"],
  "total_chunks": 1234,
  "vectors": 1234,
  "summary_mode": "none"
}
```
This enables regression comparisons after future improvements.

---
## Troubleshooting
| Symptom | Cause | Action |
|---------|-------|--------|
| Zero results for obvious query | DB path mismatch or ingestion skipped | Confirm config path + collection name |
| Many near-duplicate hits | Over-small chunk size | Increase size / reduce overlap |
| Boilerplate phrases retrieved | Contaminated legacy DB not fully cleared | Use `--drop-path` wipe |
| Memory / disk spike | Duplicate ingestion runs | Deduplicate by `doc_id`; prevent re-add without flag |
| Slow retrieval | Embedding model change or large vector count | Consider enabling approximate index if supported |

## Optional Enhancements (Later)
- Add `scripts/reprocess_all.py` to orchestrate steps 3–7 automatically
- Add a JSON log per book with per-chunk stats (min/max tokens, avg embedding latency)
- Integrate evaluation harness after ingestion to auto-report baseline metrics

## Minimal Success Criteria
- Rebuild completes without errors
- All intended books visible via a listing command
- Random queries return grounded, literal text (no meta-summaries)
- Run metadata artifact stored

---
End of document.
