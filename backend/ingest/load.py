from __future__ import annotations

import hashlib
from pathlib import Path

from app import db
from app.chroma_store import delete_textbook_chunks, upsert_chunks
from app.db import set_ingest_status
from ingest.chunk import Chunk
from ingest.extract import extract_chunks


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return digest


def upsert_content(
    *,
    textbook_id: str,
    subject: str,
    source_url: str | None,
    markdown: str,
    replace: bool = True,
    use_llm_extract: bool = True,
) -> dict[str, int]:
    chunks = extract_chunks(markdown, use_llm=use_llm_extract)
    if replace:
        db.delete_exercises_for_textbook(textbook_id)
        try:
            delete_textbook_chunks(textbook_id)
        except Exception:
            pass

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    exercise_count = 0
    narrative_count = 0

    for index, chunk in enumerate(chunks):
        chunk_id = f"{textbook_id}-{chunk.chunk_type}-{_stable_id(chunk.section, chunk.text)}"
        if chunk.chunk_type == "exercise" and chunk.stem:
            exercise_id = f"{textbook_id}-ex-{_stable_id(chunk.stem)}"
            db.insert_exercise(
                exercise_id=exercise_id,
                textbook_id=textbook_id,
                subject=subject,
                stem_md=chunk.stem,
                answer_md=chunk.answer,
                section=chunk.section,
                source_url=source_url,
                chunk_id=chunk_id,
            )
            exercise_count += 1
        else:
            narrative_count += 1
        ids.append(chunk_id)
        documents.append(chunk.text)
        metadatas.append(
            {
                "textbook_id": textbook_id,
                "subject": subject,
                "section": chunk.section,
                "source_url": source_url or "",
                "chunk_type": chunk.chunk_type,
                "index": index,
            }
        )

    chroma_ok = 0
    try:
        upsert_chunks(ids, documents, metadatas)
        chroma_ok = len(ids)
    except Exception:
        chroma_ok = 0

    status = "ingested" if exercise_count or chroma_ok else "empty"
    set_ingest_status(textbook_id, status)
    return {
        "exercises": exercise_count,
        "narrative_chunks": narrative_count,
        "chroma_upserted": chroma_ok,
    }


def load_markdown_file(
    path: Path,
    *,
    textbook_id: str,
    subject: str,
    source_url: str | None,
) -> dict[str, int]:
    markdown = path.read_text(encoding="utf-8")
    return upsert_content(
        textbook_id=textbook_id,
        subject=subject,
        source_url=source_url,
        markdown=markdown,
        use_llm_extract=False,
    )
