#!/usr/bin/env python
"""Build a small arXiv abstract sample corpus.

Usage (examples):
  poetry run python scripts/build_arxiv_sample.py --query "cat:cs.CL OR cat:cs.LG" -n 25 -o research_eval/corpus_raw/arxiv_abstracts.jsonl
  poetry run python scripts/build_arxiv_sample.py --ids 2401.12345 2402.54321 -o research_eval/corpus_raw/arxiv_specific.jsonl

Notes:
- Uses the arXiv API (rate limit ~1 req / 3 sec suggested for large harvests, but small samples fine).
- Stores JSON lines with: id, title, summary, published, updated, authors, categories.
- Does NOT download PDFs (focus on fast retrieval baseline).

Future extensions:
- Add PDF fetch & parsing.
- Add incremental update mode.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, List, Dict, Any

ARXIV_API = "https://export.arxiv.org/api/query"  # export subdomain reduces blocking risk

# Minimal namespace parse (avoid feedparser dependency initially). If reliability becomes an issue, add feedparser.


def fetch_arxiv(query: str, max_results: int = 10, start: int = 0) -> str:
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = ARXIV_API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as resp:  # nosec B310 (trusted host arxiv.org)
        return resp.read().decode("utf-8", errors="replace")


def parse_feed(xml_text: str) -> List[Dict[str, Any]]:
    # Extremely lightweight element scraping; not robust for all cases.
    # We purposely avoid heavy deps; replace with feedparser or lxml if expanding.
    entries: List[Dict[str, Any]] = []
    parts = xml_text.split("<entry>")
    if len(parts) <= 1:
        return entries
    for raw in parts[1:]:
        segment = raw.split("</entry>")[0]
        def extract(tag: str) -> str:
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            if start_tag in segment:
                inner = segment.split(start_tag, 1)[1].split(end_tag, 1)[0]
                return inner.strip()
            return ""
        # id, title, summary, published, updated
        eid = extract("id")
        title = extract("title").replace("\n", " ").strip()
        summary = extract("summary").replace("\n", " ").strip()
        published = extract("published")
        updated = extract("updated")
        # Authors
        authors: List[str] = []
        for a_part in segment.split("<author>")[1:]:
            name = a_part.split("<name>")
            if len(name) > 1:
                nm = name[1].split("</name>")[0].strip()
                if nm:
                    authors.append(nm)
        # Categories
        cats: List[str] = []
        for c_part in segment.split("<category ")[1:]:
            if "term=" in c_part:
                term_part = c_part.split("term=\"")
                if len(term_part) > 1:
                    term = term_part[1].split("\"")[0]
                    cats.append(term)
        entries.append({
            "id": eid,
            "title": title,
            "summary": summary,
            "published": published,
            "updated": updated,
            "authors": authors,
            "categories": cats,
            "source": "arxiv",
            "section": "abstract",
        })
    return entries


def write_jsonl(docs: Iterable[Dict[str, Any]], path: str) -> None:
    """Write documents to JSONL, creating parent directories automatically."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


def fetch_by_ids(ids: List[str]) -> List[Dict[str, Any]]:
    # Combine IDs into OR query; arXiv doesn't have direct ID list param for API but id: search works.
    # If an id lacks prefix, accept as-is.
    or_query = " OR ".join(f"id:{i}" for i in ids)
    xml = fetch_arxiv(or_query, max_results=len(ids))
    return parse_feed(xml)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build small arXiv abstract sample JSONL")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--query", help="arXiv API search_query expression (e.g. 'cat:cs.CL OR cat:cs.LG')")
    g.add_argument("--ids", nargs="+", help="Specific arXiv IDs (e.g. 2401.12345 2402.54321)")
    ap.add_argument("-n", "--num", type=int, default=10, help="Max results (query mode)")
    ap.add_argument("-o", "--output", required=True, help="Output JSONL path")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds after request (use >2 for large runs)")
    args = ap.parse_args()

    if args.ids:
        docs = fetch_by_ids(args.ids)
    else:
        xml = fetch_arxiv(args.query, max_results=args.num)
        docs = parse_feed(xml)
    if not docs:
        print("No documents fetched (check query or IDs).", file=sys.stderr)
        return 1

    write_jsonl(docs, args.output)
    print(f"Wrote {len(docs)} docs to {args.output}")
    if args.sleep > 0:
        time.sleep(args.sleep)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
