"""
search.py - ПОШУК ПО КОРПУСУ (п. 3):
  1. keyword-пошук: TF-IDF (збіг слів, косинусна подібність);
  2. векторний пошук: ембединги Gemini (gemini-embedding-001) + косинусна подібність.
Порівняння для кількох запитів записується у output/search_comparison.txt.
"""
import json
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from config import OUT, TOP_N, SEARCH_QUERIES
from llm import embed

EMB_PATH = os.path.join(OUT, "chunk_embeddings.npy")


def build_embeddings(chunks: list[dict], force: bool = False) -> np.ndarray:
    if os.path.exists(EMB_PATH) and not force:
        print(f"[4] Ембединги вже є: {EMB_PATH}")
        return np.load(EMB_PATH)
    vecs = np.array(embed([c["text"] for c in chunks], task_type="RETRIEVAL_DOCUMENT"), dtype=np.float32)
    np.save(EMB_PATH, vecs)
    print(f"[4] Ембединги чанків: {vecs.shape}. Файл: output/chunk_embeddings.npy")
    return vecs


def _cos(matrix: np.ndarray, vec: np.ndarray) -> np.ndarray:
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12)
    v = vec / (np.linalg.norm(vec) + 1e-12)
    return m @ v


def vector_search(query: str, chunks: list[dict], vecs: np.ndarray, k: int = TOP_N) -> list[tuple[dict, float]]:
    qv = np.array(embed([query], task_type="RETRIEVAL_QUERY")[0], dtype=np.float32)
    scores = _cos(vecs, qv)
    idx = np.argsort(-scores)[:k]
    return [(chunks[i], float(scores[i])) for i in idx]


def keyword_search(query: str, chunks: list[dict], k: int = TOP_N) -> list[tuple[dict, float]]:
    vec = TfidfVectorizer(stop_words="english", lowercase=True)
    matrix = vec.fit_transform([c["text"] for c in chunks])
    q = vec.transform([query]).toarray()[0]
    m = matrix.toarray()
    scores = _cos(m, q)
    idx = np.argsort(-scores)[:k]
    return [(chunks[i], float(scores[i])) for i in idx]


def _fmt(results) -> str:
    out = []
    for c, s in results:
        out.append(f"    {c['chunk_id']} ({c['title']}) схожість={s:.3f}")
    return "\n".join(out)


def compare(chunks: list[dict], vecs: np.ndarray) -> None:
    lines = []
    for q in SEARCH_QUERIES:
        kw = keyword_search(q, chunks)
        sem = vector_search(q, chunks, vecs)
        block = f"ЗАПИТ: {q}\n  keyword (TF-IDF):\n{_fmt(kw)}\n  векторний (Gemini embeddings):\n{_fmt(sem)}\n"
        lines.append(block)
        print(block)
    with open(os.path.join(OUT, "search_comparison.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[4b] Порівняння пошуків записано у output/search_comparison.txt")
