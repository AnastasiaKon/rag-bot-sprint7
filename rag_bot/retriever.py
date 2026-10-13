"""Поиск релевантных чанков в FAISS-индексе.

Запрос кодируется ТОЙ ЖЕ моделью, которой строился индекс (см. build_index.py),
иначе векторы окажутся в разных пространствах и поиск сломается.
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class Hit:
    score: float
    chunk_id: str
    source: str
    title: str
    position: int
    text: str


class Retriever:
    def __init__(self, index_dir: str | Path = "index"):
        index_dir = Path(index_dir)
        stats = json.loads((index_dir / "stats.json").read_text(encoding="utf-8"))
        self.model_name = stats["embedding_model"]
        self.index = faiss.read_index(str(index_dir / "faiss.index"))
        with open(index_dir / "chunks.pkl", "rb") as fh:
            self.chunks = pickle.load(fh)
        self.model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode([text], normalize_embeddings=True,
                                 convert_to_numpy=True).astype("float32")

    def search(self, query: str, k: int = 4) -> list[Hit]:
        scores, ids = self.index.search(self.embed(query), k)
        hits = []
        for s, i in zip(scores[0], ids[0]):
            if i < 0:
                continue
            c = self.chunks[i]
            hits.append(Hit(float(s), c["chunk_id"], c["source"], c["title"],
                            c["position"], c["text"]))
        return hits
