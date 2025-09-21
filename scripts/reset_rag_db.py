#!/usr/bin/env python
"""Utility script to wipe the existing RAG (Chroma) database.

WARNING: This deletes ALL embedded ebook documents. Use before reprocessing
with raw text ingestion.

Usage (from project root):
    poetry run python scripts/reset_rag_db.py --db-path ebook_db --collection ebooks

If you want a dry run:
    poetry run python scripts/reset_rag_db.py --dry-run
"""
import argparse
import os
import shutil
import sys

try:
    import chromadb
except ImportError:
    print("chromadb not installed. Install with: poetry add chromadb")
    sys.exit(1)


def wipe_collection(db_path: str, collection: str, dry_run: bool = False):
    client = chromadb.PersistentClient(path=db_path)
    try:
        coll = client.get_collection(collection)
    except Exception:
        print(f"Collection '{collection}' not found. Nothing to do.")
        return

    if dry_run:
        count = coll.count()
        print(f"[DRY-RUN] Would delete {count} documents from collection '{collection}'.")
        return

    # Delete via IDs in batches (safer than nuking DB path if future collections exist)
    results = coll.get()
    ids = results.get('ids', [])
    if not ids:
        print("Collection already empty.")
        return
    print(f"Deleting {len(ids)} documents from '{collection}' ...")
    coll.delete(ids=ids)
    print("Done.")


def wipe_db_path(db_path: str, confirm: bool, dry_run: bool):
    if dry_run:
        print(f"[DRY-RUN] Would remove directory {db_path}")
        return
    if not os.path.exists(db_path):
        print("Database path does not exist.")
        return
    if not confirm:
        print("Refusing to remove path without --force. Use --force to confirm.")
        return
    shutil.rmtree(db_path)
    print(f"Removed directory {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Reset / wipe RAG database")
    parser.add_argument('--db-path', default='ebook_db', help='Chroma persistence path')
    parser.add_argument('--collection', default='ebooks', help='Collection name to wipe')
    parser.add_argument('--drop-path', action='store_true', help='Also remove entire database directory')
    parser.add_argument('--force', action='store_true', help='Confirm destructive action')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen without deleting')
    args = parser.parse_args()

    if args.drop_path:
        wipe_db_path(args.db_path, confirm=args.force, dry_run=args.dry_run)
    else:
        wipe_collection(args.db_path, args.collection, dry_run=args.dry_run)

    print("Completed reset operation.")

if __name__ == '__main__':
    main()
