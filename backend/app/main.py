from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.grade import grade_submission
from app.ollama_client import ping
from app.quiz import next_question
from app.rag import tutor_reply
from app.registry import sync_registry
from app.schemas import (
    ChatIn,
    ChatOut,
    GradeIn,
    GradeOut,
    HealthOut,
    QuestionOut,
    TextbookOut,
)
from app.seed import seed_fixture


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    sync_registry()
    seed_fixture()
    yield


app = FastAPI(title="MathProblemApp", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/api/health", response_model=HealthOut)
def health() -> HealthOut:
    ollama = ping()
    return HealthOut(ok=True, ollama=ollama)


@app.get("/api/subjects")
def subjects() -> list[str]:
    return db.list_subjects()


@app.get("/api/textbooks", response_model=list[TextbookOut])
def textbooks(subject: str | None = None) -> list[TextbookOut]:
    rows = db.list_textbooks(subject)
    return [
        TextbookOut(
            id=r["id"],
            title=r["title"],
            subject=r["subject"],
            source_url=r.get("source_url"),
            ingest_status=r["ingest_status"],
            is_fixture=bool(r["is_fixture"]),
        )
        for r in rows
    ]


@app.get("/api/questions/next", response_model=QuestionOut)
def questions_next(
    subject: str | None = None,
    textbook_id: str | None = None,
    exclude: str = "",
    generate: bool = Query(False),
) -> QuestionOut:
    exclude_ids = [x for x in exclude.split(",") if x]
    try:
        payload = next_question(
            textbook_id=textbook_id,
            subject=subject,
            exclude_ids=exclude_ids,
            force_generate=generate,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return QuestionOut(**payload)


@app.post("/api/grade", response_model=GradeOut)
def grade(body: GradeIn) -> GradeOut:
    try:
        result = grade_submission(body.question_id, body.work, body.source)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GradeOut(**result)


@app.post("/api/chat", response_model=ChatOut)
def chat_endpoint(body: ChatIn) -> ChatOut:
    try:
        reply, used = tutor_reply(
            [m.model_dump() for m in body.messages],
            textbook_id=body.textbook_id,
            subject=body.subject,
            question_id=body.question_id,
            work=body.work,
            submitted=body.submitted,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatOut(reply=reply, used_chunks=used)
