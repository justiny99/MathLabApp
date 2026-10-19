from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TextbookOut(BaseModel):
    id: str
    title: str
    subject: str
    source_url: str | None = None
    ingest_status: str
    is_fixture: bool


class HealthOut(BaseModel):
    ok: bool
    ollama: dict


class QuestionOut(BaseModel):
    id: str
    source: Literal["extracted", "generated"]
    textbook_id: str | None = None
    subject: str | None = None
    section: str | None = None
    stem_md: str
    has_official_answer: bool = False


class GradeIn(BaseModel):
    question_id: str
    work: str
    source: Literal["extracted", "generated"] = "extracted"


class GradeOut(BaseModel):
    correct: bool
    feedback_md: str
    solution_md: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatIn(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    textbook_id: str | None = None
    subject: str | None = None
    question_id: str | None = None
    work: str | None = None
    submitted: bool = False


class ChatOut(BaseModel):
    reply: str
    used_chunks: int = 0
