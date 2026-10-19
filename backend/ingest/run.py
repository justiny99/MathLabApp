from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import get_textbook, init_db  # noqa: E402
from app.registry import load_yaml_textbooks, sync_registry  # noqa: E402
from app.seed import seed_fixture  # noqa: E402
from ingest.crawl import crawl_to_raw  # noqa: E402
from ingest.load import load_markdown_file  # noqa: E402


def ingest_one(textbook_id: str) -> None:
    book = get_textbook(textbook_id)
    if not book:
        raise SystemExit(f"Unknown textbook id: {textbook_id}")
    if book.get("is_fixture"):
        seed_fixture()
        print(f"Loaded fixture {textbook_id}")
        return
    url = book.get("source_url")
    if not url:
        raise SystemExit(
            f"{textbook_id} has no source_url in textbooks.yaml; add a link first."
        )
    path = crawl_to_raw(textbook_id, url)
    stats = load_markdown_file(
        path,
        textbook_id=textbook_id,
        subject=book["subject"],
        source_url=url,
    )
    print(f"Ingested {textbook_id}: {stats}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest textbooks into SQLite + Chroma")
    parser.add_argument("--id", help="Textbook id from textbooks.yaml")
    parser.add_argument("--all", action="store_true", help="Ingest every book that has a URL")
    parser.add_argument("--fixture", action="store_true", help="Reload the fixture algebra book")
    args = parser.parse_args()

    init_db()
    sync_registry()

    if args.fixture or (args.id == "fixture-algebra"):
        from app import db

        db.delete_exercises_for_textbook("fixture-algebra")
        seed_fixture()
        print("Fixture reloaded")
        return
    if args.id:
        ingest_one(args.id)
        return
    if args.all:
        for item in load_yaml_textbooks():
            if item.get("fixture"):
                continue
            if not item.get("source_url"):
                print(f"Skipping {item['id']} (no URL)")
                continue
            ingest_one(item["id"])
        return
    parser.print_help()


if __name__ == "__main__":
    main()
