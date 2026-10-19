from __future__ import annotations

from app.config import BACKEND_DIR
from app.db import count_exercises
from ingest.load import load_markdown_file


def seed_fixture() -> None:
    if count_exercises(textbook_id="fixture-algebra") > 0:
        return
    path = BACKEND_DIR / "fixtures" / "introductory_algebra.md"
    load_markdown_file(
        path,
        textbook_id="fixture-algebra",
        subject="algebra",
        source_url=None,
    )
