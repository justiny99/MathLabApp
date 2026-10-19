from __future__ import annotations

from app.chroma_store import query_chunks
from app.config import settings
from app.db import get_exercise
from app.ollama_client import OllamaError, chat


def retrieve(
    query: str,
    *,
    textbook_id: str | None = None,
    subject: str | None = None,
) -> list[str]:
    try:
        hits = query_chunks(
            query,
            textbook_id=textbook_id,
            subject=subject,
            n_results=settings.retrieve_k,
        )
    except Exception:
        return []
    return [h["document"] for h in hits if h.get("document")]


def format_context(chunks: list[str]) -> str:
    if not chunks:
        return "(no textbook passages retrieved)"
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[Passage {i}]\n{chunk}")
    return "\n\n".join(parts)


def generate_question(
    *,
    textbook_id: str | None,
    subject: str | None,
) -> dict[str, str]:
    scope = subject or textbook_id or "mathematics"
    query = f"core worked examples and definitions for {scope}"
    chunks = retrieve(query, textbook_id=textbook_id, subject=subject)
    context = format_context(chunks)
    data = None
    try:
        from app.ollama_client import chat_json

        data = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You write original practice problems grounded in the given textbook "
                        "passages. Return JSON with keys stem_md, solution_md, section. "
                        "Use markdown math ($...$ / $$...$$). Do not copy an exercise verbatim."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Subject: {subject or 'unspecified'}\n"
                        f"Textbook id: {textbook_id or 'unspecified'}\n\n"
                        f"Passages:\n{context}\n\n"
                        "Create one medium-difficulty problem with a worked solution."
                    ),
                },
            ]
        )
    except OllamaError as exc:
        raise RuntimeError(f"Could not generate a question: {exc}") from exc
    stem = str(data.get("stem_md") or "").strip()
    solution = str(data.get("solution_md") or "").strip()
    if not stem or not solution:
        raise RuntimeError("Model did not return stem_md and solution_md")
    return {
        "stem_md": stem,
        "solution_md": solution,
        "section": str(data.get("section") or "generated"),
    }


def tutor_reply(
    messages: list[dict[str, str]],
    *,
    textbook_id: str | None,
    subject: str | None,
    question_id: str | None,
    work: str | None,
    submitted: bool,
) -> tuple[str, int]:
    user_text = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "help",
    )
    query = user_text
    if question_id:
        ex = get_exercise(question_id)
        if ex:
            query = f"{ex['stem_md']}\n{user_text}"
    chunks = retrieve(query, textbook_id=textbook_id, subject=subject)
    extra = ""
    if question_id:
        ex = get_exercise(question_id)
        if ex:
            extra += f"\nCurrent problem:\n{ex['stem_md']}\n"
            if submitted and ex.get("answer_md"):
                extra += f"Official answer (student already submitted): {ex['answer_md']}\n"
            elif not submitted:
                extra += (
                    "The student has not submitted yet. Do not reveal the final answer. "
                    "You may hint at the next step.\n"
                )
    if work:
        extra += f"\nStudent work so far:\n{work}\n"

    system = (
        "You are a patient math tutor. Use the retrieved textbook passages when relevant. "
        "Explain one step at a time. Prefer questions that unblock the student. "
        "Do not dump a full official solution unless they already submitted or clearly "
        "ask you to check a finished solution."
    )
    prompt_messages = [
        {"role": "system", "content": system},
        {
            "role": "system",
            "content": f"Textbook context:\n{format_context(chunks)}\n{extra}",
        },
        *[m for m in messages if m["role"] in {"user", "assistant"}],
    ]
    reply = chat(prompt_messages)
    return reply, len(chunks)
