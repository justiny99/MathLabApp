from __future__ import annotations

import re
from typing import Any

from app import db
from app.ollama_client import OllamaError, chat_json
from app.state import generated_questions

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def cheap_check(work: str, answer: str) -> bool | None:
    if not answer.strip():
        return None
    if _normalize(work) == _normalize(answer):
        return True
    work_nums = _NUM.findall(work.replace(",", ""))
    ans_nums = _NUM.findall(answer.replace(",", ""))
    if work_nums and ans_nums:
        try:
            return abs(float(work_nums[-1]) - float(ans_nums[-1])) < 1e-6
        except ValueError:
            return None
    return None


def grade_submission(question_id: str, work: str, source: str) -> dict[str, Any]:
    stem = ""
    solution = ""
    if source == "generated":
        item = generated_questions.get(question_id)
        if not item:
            raise KeyError("generated question expired; request a new one")
        stem = item["stem_md"]
        solution = item["solution_md"]
    else:
        row = db.get_exercise(question_id)
        if not row:
            raise KeyError("unknown exercise")
        stem = row["stem_md"]
        solution = row.get("answer_md") or ""

    cheap = cheap_check(work, solution) if solution else None
    feedback = ""
    correct = bool(cheap) if cheap is not None else False
    try:
        data = chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Grade the student's work. Return JSON with keys "
                        "correct (boolean) and feedback_md (string). "
                        "Be fair to equivalent forms. Point out the first mistake. "
                        "Do not introduce new problems."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Problem:\n{stem}\n\n"
                        f"Reference solution/answer:\n{solution or '(none stored)'}\n\n"
                        f"Student work:\n{work or '(empty)'}\n"
                    ),
                },
            ]
        )
        correct = bool(data.get("correct"))
        feedback = str(data.get("feedback_md") or "").strip()
        if cheap is True:
            correct = True
    except OllamaError:
        if cheap is True:
            correct = True
            feedback = "Matches the stored answer (Ollama grader unavailable)."
        elif cheap is False:
            correct = False
            feedback = (
                "Does not match the stored answer, and the local grader is unavailable."
            )
        else:
            correct = False
            feedback = "Ollama is unavailable, so this submission could not be graded."

    return {
        "correct": correct,
        "feedback_md": feedback,
        "solution_md": solution or None,
    }
