from __future__ import annotations

from ingest.chunk import Chunk, markdown_to_chunks, parse_exercises
from app.ollama_client import OllamaError, chat_json, ping


def extract_chunks(markdown: str, *, use_llm: bool = True) -> list[Chunk]:
    chunks = markdown_to_chunks(markdown)
    has_exercises = any(c.chunk_type == "exercise" for c in chunks)
    if has_exercises or not use_llm:
        return chunks
    status = ping()
    if not (status["reachable"] and status["chat_model_present"]):
        return chunks
    try:
        data = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Extract textbook exercises from the markdown. Return JSON "
                        '{"exercises":[{"stem":"...","answer":null or string,"section":"..."}]}'
                    ),
                },
                {"role": "user", "content": markdown[:12000]},
            ]
        )
        for item in data.get("exercises") or []:
            stem = str(item.get("stem") or "").strip()
            if not stem:
                continue
            answer = item.get("answer")
            answer_s = str(answer).strip() if answer else None
            section = str(item.get("section") or "Exercises")
            chunks.append(
                Chunk(
                    chunk_type="exercise",
                    section=section,
                    text=stem + (f"\nAnswer: {answer_s}" if answer_s else ""),
                    stem=stem,
                    answer=answer_s,
                )
            )
    except OllamaError:
        pass
    return chunks


def exercises_from_section(title: str, body: str) -> list[Chunk]:
    return parse_exercises(title, body)
