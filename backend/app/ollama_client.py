from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import settings

JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class OllamaError(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(base_url=settings.ollama_base_url, timeout=180.0)


def ping() -> dict[str, Any]:
    info = {
        "reachable": False,
        "chat_model": settings.chat_model,
        "embed_model": settings.embed_model,
        "chat_model_present": False,
        "embed_model_present": False,
        "tags": [],
    }
    try:
        with _client() as client:
            resp = client.get("/api/tags")
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            info["reachable"] = True
            info["tags"] = models
            info["chat_model_present"] = _model_listed(settings.chat_model, models)
            info["embed_model_present"] = _model_listed(settings.embed_model, models)
    except httpx.HTTPError:
        pass
    return info


def _model_listed(name: str, tags: list[str]) -> bool:
    if name in tags:
        return True
    prefix = name.split(":")[0]
    return any(t == name or t.startswith(prefix + ":") or t == prefix for t in tags)


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    with _client() as client:
        resp = client.post(
            "/api/embed",
            json={"model": settings.embed_model, "input": texts},
        )
        if resp.status_code >= 400:
            raise OllamaError(f"embed failed: {resp.status_code} {resp.text}")
        data = resp.json()
        vectors = data.get("embeddings")
        if not vectors:
            raise OllamaError("embed response missing embeddings")
        return vectors


def chat(messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
    payload: dict[str, Any] = {
        "model": settings.chat_model,
        "messages": messages,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"
    with _client() as client:
        resp = client.post("/api/chat", json=payload)
        if resp.status_code >= 400:
            raise OllamaError(f"chat failed: {resp.status_code} {resp.text}")
        content = resp.json().get("message", {}).get("content", "")
        if not isinstance(content, str):
            raise OllamaError("chat response missing content")
        return content


def chat_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    raw = chat(messages, json_mode=True)
    return parse_json_object(raw)


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = JSON_OBJECT.search(text)
    if not match:
        raise OllamaError(f"could not parse JSON from model output: {text[:400]}")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise OllamaError("JSON output was not an object")
    return data
