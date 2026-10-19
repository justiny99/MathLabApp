from __future__ import annotations

import uuid
from typing import Any

from app import db
from app.rag import generate_question
from app.state import generated_questions


def next_question(
    *,
    textbook_id: str | None,
    subject: str | None,
    exclude_ids: list[str],
    force_generate: bool,
) -> dict[str, Any]:
    if not force_generate:
        row = db.next_exercise(
            exclude_ids, textbook_id=textbook_id, subject=subject
        )
        if row:
            return {
                "id": row["id"],
                "source": "extracted",
                "textbook_id": row["textbook_id"],
                "subject": row["subject"],
                "section": row.get("section"),
                "stem_md": row["stem_md"],
                "has_official_answer": bool(row.get("answer_md")),
            }

    generated = generate_question(textbook_id=textbook_id, subject=subject)
    qid = f"gen-{uuid.uuid4()}"
    generated_questions[qid] = {
        "id": qid,
        "source": "generated",
        "textbook_id": textbook_id,
        "subject": subject,
        "section": generated["section"],
        "stem_md": generated["stem_md"],
        "solution_md": generated["solution_md"],
    }
    return {
        "id": qid,
        "source": "generated",
        "textbook_id": textbook_id,
        "subject": subject,
        "section": generated["section"],
        "stem_md": generated["stem_md"],
        "has_official_answer": False,
    }
