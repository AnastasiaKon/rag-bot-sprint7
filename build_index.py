"""Задание 3. Строит FAISS-индекс по документам knowledge_base/.

Использование:
    python build_index.py                      # индекс в index/
    python build_index.py --query "Who trained Taren Vossmark?"   # + тестовый поиск

Пайплайн:
  1. читаем *.md из knowledge_base/ (и опционально extra-папку, см. --extra);
  2. режем на чанки RecursiveCharacterTextSplitter (~800 символов, перекрытие 120);
  3. считаем эмбеддинги локальной моделью sentence-transformers/all-MiniLM-L6-v2 (384-d);
  4. кладём в FAISS IndexFlatIP (косинусное сходство по нормированным векторам);
  5. рядом сохраняем метаданные чанков (источник, заголовок, позиция, текст).

Важно: индексация = только эмбеддинги. LLM здесь не участвует.
"""
from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"   # https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE = 800        # символов, ~120-180 слов
CHUNK_OVERLAP = 120


def load_documents(dirs: list[Path]) -> list[dict]:
    docs = []
    for d in dirs:
        for f in sorted(d.glob("*.md")) + sorted(d.glob("*.txt")):
            text = f.read_text(encoding="utf-8")
            title = text.splitlines()[0].lstrip("# ").strip() if text else f.stem
            docs.append({"source": str(f), "title": title, "text": text})
    return docs


def make_chunks(docs: list[dict]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n\n", "\n", ". ", " "],
    )
    chunks = []
    for doc in docs:
        pos = 0
        pieces = [p for p in splitter.split_text(doc["text"]) if len(p.strip()) >= 60]
        for i, piece in enumerate(pieces):
            start = doc["text"].find(piece, pos)
            if start < 0:
                start = pos
            chunks.append({
                "chunk_id": f"{Path(doc['source']).stem}#{i}",
                "source": doc["source"],
                "title": doc["title"],
                "position": start,
                "text": piece,
            })
            pos = start + max(1, len(piece) - CHUNK_OVERLAP)
    return chunks


def embed(model: SentenceTransformer, texts: list[str]) -> np.ndarray:
    vecs = model.encode(texts, batch_size=64, show_progress_bar=True,
                        normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")


def build(kb_dirs: list[Path], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    docs = load_documents(kb_dirs)
    chunks = make_chunks(docs)
    model = SentenceTransformer(EMBED_MODEL)
    vecs = embed(model, [c["text"] for c in chunks])

    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    faiss.write_index(index, str(out_dir / "faiss.index"))
    with open(out_dir / "chunks.pkl", "wb") as fh:
        pickle.dump(chunks, fh)

    stats = {
        "embedding_model": EMBED_MODEL,
        "embedding_dim": int(vecs.shape[1]),
        "documents": len(docs),
        "chunks": len(chunks),
        "chunk_size_chars": CHUNK_SIZE,
        "chunk_overlap_chars": CHUNK_OVERLAP,
        "build_seconds": round(time.time() - t0, 1),
        "index_type": "faiss.IndexFlatIP (cosine on normalized vectors)",
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    return stats


def search(out_dir: Path, query: str, k: int = 3) -> list[dict]:
    index = faiss.read_index(str(out_dir / "faiss.index"))
    with open(out_dir / "chunks.pkl", "rb") as fh:
        chunks = pickle.load(fh)
    model = SentenceTransformer(EMBED_MODEL)
    q = embed(model, [query])
    scores, ids = index.search(q, k)
    return [{"score": float(s), **chunks[i]} for s, i in zip(scores[0], ids[0]) if i >= 0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="knowledge_base")
    ap.add_argument("--extra", default=None, help="доп. папка документов (например, data/malicious)")
    ap.add_argument("--out", default="index")
    ap.add_argument("--query", default=None, help="тестовый поисковый запрос после сборки")
    args = ap.parse_args()

    dirs = [Path(args.kb)] + ([Path(args.extra)] if args.extra else [])
    stats = build(dirs, Path(args.out))
    print("\nИндекс собран:", json.dumps(stats, indent=2, ensure_ascii=False))

    if args.query:
        print(f"\nЗапрос: {args.query}")
        for r in search(Path(args.out), args.query):
            print(f"\n[{r['score']:.3f}] {r['title']} ({r['chunk_id']}, pos {r['position']})")
            print(r["text"][:400].replace("\n", " "), "...")


if __name__ == "__main__":
    main()
