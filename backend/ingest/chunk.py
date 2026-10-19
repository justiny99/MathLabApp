from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
EXERCISE_START = re.compile(
    r"^(?:#{1,6}\s+)?(?:exercises?|problems?|practice)\b",
    re.IGNORECASE,
)
NUMBERED = re.compile(r"^(\d+)[.)]\s+(.*)$")
ANSWER = re.compile(r"^\*\*Answer:\*\*\s*(.*)$", re.IGNORECASE)


@dataclass
class Chunk:
    chunk_type: str  # narrative | exercise
    section: str
    text: str
    stem: str | None = None
    answer: str | None = None


def split_sections(markdown: str) -> list[tuple[str, str]]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    sections: list[tuple[str, list[str]]] = [("(intro)", [])]
    current = sections[0][1]
    title = "(intro)"
    for line in lines:
        m = HEADING.match(line.strip())
        if m and len(m.group(1)) <= 3:
            title = m.group(2).strip()
            sections.append((title, []))
            current = sections[-1][1]
            continue
        current.append(line)
    return [(name, "\n".join(body).strip()) for name, body in sections if "\n".join(body).strip()]


def parse_exercises(section_title: str, body: str) -> list[Chunk]:
    lines = body.split("\n")
    items: list[Chunk] = []
    current: dict[str, str] | None = None
    collecting_stem = False

    def flush() -> None:
        nonlocal current
        if current and current.get("stem"):
            items.append(
                Chunk(
                    chunk_type="exercise",
                    section=section_title,
                    text=current["stem"]
                    + (
                        f"\nAnswer: {current['answer']}"
                        if current.get("answer")
                        else ""
                    ),
                    stem=current["stem"].strip(),
                    answer=(current.get("answer") or "").strip() or None,
                )
            )
        current = None

    for raw in lines:
        line = raw.rstrip()
        numbered = NUMBERED.match(line.strip())
        if numbered:
            flush()
            current = {"stem": numbered.group(2).strip(), "answer": ""}
            collecting_stem = True
            continue
        ans = ANSWER.match(line.strip())
        if ans and current is not None:
            current["answer"] = ans.group(1).strip()
            collecting_stem = False
            continue
        if current is not None and collecting_stem and line.strip():
            current["stem"] += "\n" + line.strip()
    flush()
    return items


def markdown_to_chunks(markdown: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for title, body in split_sections(markdown):
        is_exercise_section = bool(EXERCISE_START.search(title))
        if is_exercise_section:
            exercises = parse_exercises(title, body)
            if exercises:
                chunks.extend(exercises)
                continue
        exercises = parse_exercises(title, body)
        narrative = body
        if exercises:
            chunks.extend(exercises)
            # keep remaining prose as narrative
            narrative = NUMBERED.split(body, maxsplit=1)[0].strip()
        if narrative:
            pieces = _window(narrative, max_chars=1200)
            for piece in pieces:
                chunks.append(
                    Chunk(chunk_type="narrative", section=title, text=piece)
                )
    return chunks


def _window(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) + 2 > max_chars:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}".strip()
    if buf:
        out.append(buf)
    return out
