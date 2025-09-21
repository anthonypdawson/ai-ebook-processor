# Research Evaluation Playbook

Status: Draft
Last Updated: 2025-09-21

## Purpose
Provide a lightweight, reproducible method to evaluate retrieval and answer synthesis performance on a small, curated scientific / technical document corpus (simulating researcher behavior) without immediately investing in large-scale parsing.

## 1. Corpus Composition Strategy
Aim for a **balanced 40–60 document set** spanning abstract difficulty and section structure.

Recommended mix:
| Source | Count | Rationale |
|--------|-------|-----------|
| arXiv abstracts (STEM mix) | 15 | Fast ingestion, semantic variety |
| ACL Anthology NLP full papers | 10 | Method/dataset extraction |
| PubMed Central OA (methods-heavy) | 10 | Procedural & sectioned text |
| PLOS review / survey papers | 5–10 | High-level synthesis queries |
| Long-form (≥10k tokens) | 2–3 | Stress multi-chunk continuity |

### License Hygiene
Store license in metadata. Include only permissive OA (CC-BY, CC0) for full-text. arXiv usage: abstracts & PDFs are fine for research use; respect terms.

## 2. Acquisition Quick Start
| Source | Approach | Minimal Tooling |
|--------|----------|-----------------|
| arXiv | API: title+abstract only | HTTP + JSON parse |
| ACL Anthology | Manual select recent conference papers | Simple PDF → text (PyPDF2) |
| PMC OA | Download small OA tarball | JATS XML parse (lxml) |
| PLOS | Use TDM endpoint | Basic requests |

Defer: GROBID, S2ORC, OpenAlex enrichment until baseline established.

## 3. Parsing & Chunking Guidelines
- Use section headers as hard boundaries (Abstract, Introduction, Methods, Results, Discussion, Conclusion, Related Work).
- Target 512–800 token chunks; avoid mixing unrelated sections.
- For small sections (<120 tokens), merge with neighbor if same logical phase (e.g., “Limitations” + “Future Work”).
- Replace tables/figures with placeholders: `[TABLE]`, `[FIGURE]`.
- Normalize whitespace; preserve equations as inline text where legible.

## 4. Metadata Schema (Suggested)
```
{
  "doc_id": str,
  "source": "arxiv|acl|pmc|plos",
  "title": str,
  "year": int|null,
  "section": str,            # abstract|introduction|methods|results|discussion|conclusion|other
  "authors": [str],
  "license": str|null,
  "categories": [str],
  "tokens": int,
  "version": 1
}
```
Add later: citation_count, concept_tags, dataset_names.

## 5. Query Taxonomy (Target ~50 Queries)
| Type | Example | Section Bias |
|------|---------|--------------|
| Definitional | "What is contrastive pretraining?" | Abstract / Intro |
| Method Steps | "How is data filtered before training?" | Methods |
| Hyperparameters | "What learning rate schedule is used?" | Methods |
| Comparison | "How do diffusion models differ from GANs?" | Intro / Discussion |
| Result Interpretation | "Why does accuracy plateau?" | Discussion |
| Limitations | "What limitations are acknowledged?" | Discussion / Conclusion |
| Dataset Properties | "What languages are in the corpus?" | Methods |
| Timeline / Adoption | "When did large-scale instruction tuning emerge?" | Intro / Related |
| Ablation Focus | "Which component most affected performance?" | Results |
| Citation-based | "Which prior work introduced the baseline?" | Intro / Related |
| Abbreviation Expansion | "What does SNR weighting mean here?" | Methods |
| Unanswerable (control) | "What license governs the hidden dataset?" | N/A |

Mark each query with metadata:
```
{
  "query_id": int,
  "text": str,
  "expected_sections": [str],
  "difficulty": 1|2|3,
  "answerable": bool
}
```

## 6. Gold Construction (Minimal Viable)
Pick 10 full papers. For each:
- Extract 3–5 factual spans (exact sentences) across methods, results, limitations.
Aggregate into a gold JSON:
```
{
  "gold_spans": [
    {"doc_id": "acl2024_paper1", "section": "methods", "text": "We fine-tune using ..."}
  ]
}
```
Map queries to one or more span IDs where applicable.

## 7. Metrics (Initial Set)
| Metric | Definition |
|--------|------------|
| Recall@K | Any gold span retrieved within top K chunks |
| MRR | Mean reciprocal rank over answerable queries |
| SectionCoverage | % queries where at least one expected section appears in top K |
| UnanswerablePrecision | % unanswerable queries with no fabricated answer produced |
| AnswerGroundingRate | % answer sentences with at least one cited source chunk |

Later: NDCG, hallucination rate via LLM judge.

## 8. Evaluation Flow (Pseudo)
```
for query in queries:
  hits = rag.search(query.text, k=K)
  gold = gold_map[query.id]
  record metrics...
(optional) answer = answer_llm(hits)
(optional) judge = judge_llm(answer, hits)
```
Persist a run JSON:
```
{
  "run_id": "2025-09-21_baseline_raw",
  "config": {...},
  "metrics": {...},
  "per_query": [...]
}
```

## 9. Anti-Hallucination Answer Prompt (Template)
```
You answer scientific questions ONLY from provided context chunks.
If a fact is not present verbatim, reply: "Not explicitly stated in the provided sources." 
After each claim, add [CITATION:chunk_id].
Return concise factual sentences. No speculation.
```

## 10. Incremental Roadmap
1. Build small arXiv abstract set
2. Add ACL + PMC subset
3. Create 20 queries + 10 gold spans → baseline metrics
4. Expand to 50 queries + 40 gold spans
5. Introduce dual embeddings (if enabled) → comparative run
6. Add snapshot: `runs/2025-XX-YY/` storing artifacts

## 11. Directory Suggestions
```
research_eval/
  corpus_raw/
  corpus_parsed/
  gold/
  queries/
  runs/
```

## 12. Potential Scripts (Future)
| Script | Purpose |
|--------|---------|
| build_arxiv_sample.py | Fetch & store abstracts |
| parse_acl_pdfs.py | Extract + section split |
| build_queries.py | Generate starter query JSON |
| eval_retrieval_science.py | Run retrieval metrics |
| compare_runs.py | Regression detection |

## 13. Expansion Triggers
Add heavier tooling only if:
- Need citation graph features (→ S2ORC / GROBID)
- Need formula semantic parsing (→ LaTeX extraction)
- Need concept clustering (→ entity linking pass)

## 14. Success Criteria (Phase 1)
- Corpus assembled (<1 working day effort)
- ≥20 queries with gold spans
- Baseline metrics computed & stored deterministically
- Clear delta tracking plan for future embedding strategies

## 15. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| PDF noise degrades embeddings | Strip repeated headers/footers; drop references section initially |
| Gold span bias | Spread spans across multiple sections and difficulty tiers |
| Overfitting queries to first corpus | Add unanswerable + high-level conceptual queries |
| Hallucinated numeric claims | Strict answer prompt + citation requirement |

## 16. Future Enhancements
- Per-section re-ranking
- Hybrid sparse + dense retrieval (BM25 + embeddings)
- Query difficulty automatic classifier
- Active learning loop to expand gold set

---
End of document.
