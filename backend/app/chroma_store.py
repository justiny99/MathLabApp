from __future__ import annotations

from typing import Any

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import settings
from app.ollama_client import embed


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    def name(self) -> str:
        return "ollama-nomic"

    def __call__(self, input: Documents) -> Embeddings:
        return embed(list(input))


_client: chromadb.PersistentClient | None = None
_embedder = OllamaEmbeddingFunction()


def chroma_path() -> str:
    path = settings.data_dir / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=chroma_path())
    return _client


def collection():
    return client().get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=_embedder,
        metadata={"hnsw:space": "cosine"},
    )


def delete_textbook_chunks(textbook_id: str) -> None:
    col = collection()
    try:
        col.delete(where={"textbook_id": textbook_id})
    except Exception:
        existing = col.get(where={"textbook_id": textbook_id})
        ids = existing.get("ids") or []
        if ids:
            col.delete(ids=ids)


def upsert_chunks(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    if not ids:
        return
    collection().upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_chunks(
    text: str,
    *,
    textbook_id: str | None = None,
    subject: str | None = None,
    n_results: int | None = None,
) -> list[dict[str, Any]]:
    where: dict[str, Any] | None = None
    clauses: list[dict[str, Any]] = []
    if textbook_id:
        clauses.append({"textbook_id": textbook_id})
    if subject:
        clauses.append({"subject": subject})
    if len(clauses) == 1:
        where = clauses[0]
    elif len(clauses) > 1:
        where = {"$and": clauses}

    kwargs: dict[str, Any] = {
        "query_texts": [text],
        "n_results": n_results or settings.retrieve_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    col = collection()
    if col.count() == 0:
        return []
    result = col.query(**kwargs)
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    out: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        out.append(
            {
                "id": ids[i] if i < len(ids) else "",
                "document": doc,
                "metadata": metas[i] if i < len(metas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )
    return out
