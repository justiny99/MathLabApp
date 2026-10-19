from __future__ import annotations

from typing import Any

import yaml

from app.config import settings
from app.db import upsert_textbook


def load_yaml_textbooks() -> list[dict[str, Any]]:
    raw = yaml.safe_load(settings.textbooks_yaml.read_text(encoding="utf-8")) or {}
    items = raw.get("textbooks") or []
    if not isinstance(items, list):
        raise ValueError("textbooks.yaml must contain a textbooks list")
    return items


def sync_registry() -> None:
    for item in load_yaml_textbooks():
        upsert_textbook(
            textbook_id=item["id"],
            title=item["title"],
            subject=item["subject"],
            source_url=item.get("source_url") or None,
            is_fixture=bool(item.get("fixture")),
        )
