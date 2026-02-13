"""Local KB vector store backed by ChromaDB."""
from __future__ import annotations

import math
import os
import re
from typing import Iterable

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

KB_PATH = os.getenv("CHROMA_PATH", "./backend/chroma_db")
COLLECTION_NAME = "helpdesk_kb"


class SimpleHashEmbedding(EmbeddingFunction[Documents]):
    """Deterministic local embedding without external model downloads."""

    def __call__(self, input: Documents) -> Embeddings:
        vectors: Embeddings = []
        for text in input:
            tokens = re.findall(r"[a-z0-9]+", text.lower())
            dims = [0.0] * 128
            for tok in tokens:
                idx = hash(tok) % 128
                dims[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in dims)) or 1.0
            vectors.append([v / norm for v in dims])
        return vectors


class KBStore:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=KB_PATH)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=SimpleHashEmbedding(),
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, docs: Iterable[dict]) -> None:
        docs = list(docs)
        if not docs:
            return
        self.collection.upsert(
            ids=[str(d["id"]) for d in docs],
            documents=[d["content"] for d in docs],
            metadatas=[{"title": d["title"], "tags": ",".join(d.get("tags", []))} for d in docs],
        )

    def search(self, query: str, k: int = 3) -> list[dict]:
        result = self.collection.query(query_texts=[query], n_results=k)
        docs = []
        for idx, doc in enumerate(result.get("documents", [[]])[0]):
            docs.append(
                {
                    "id": result["ids"][0][idx],
                    "content": doc,
                    "title": result["metadatas"][0][idx].get("title", "KB Article"),
                    "distance": result["distances"][0][idx],
                    "tags": result["metadatas"][0][idx].get("tags", ""),
                }
            )
        return docs
