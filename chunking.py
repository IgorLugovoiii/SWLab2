"""
chunking.py - РОЗБИТТЯ НА ЧАНКИ: ріже кожен документ на шматки по CHUNK_WORDS слів
з перекриттям CHUNK_OVERLAP. Розмір 800 слів - це кілька абзаців, достатньо контексту,
щоб факт (хто, що, де) лишився в одному чанку. Перекриття 100 слів не дає факту
розірватися на межі двох чанків.
"""
import json
import os

from config import CHUNK_WORDS, CHUNK_OVERLAP, OUT


def chunk_document(doc: dict) -> list[dict]:
    words = doc["text"].split()
    step = CHUNK_WORDS - CHUNK_OVERLAP
    chunks = []
    for n, start in enumerate(range(0, len(words), step)):
        piece = words[start:start + CHUNK_WORDS]
        if not piece:
            break
        chunks.append({
            "chunk_id": f"{doc['id']}_c{n:02d}",
            "doc_id": doc["id"],
            "title": doc["title"],
            "text": " ".join(piece),
        })
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def build_chunks(docs: list[dict]) -> list[dict]:
    chunks = [c for d in docs for c in chunk_document(d)]
    with open(os.path.join(OUT, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"[2] Чанків: {len(chunks)} (по {CHUNK_WORDS} слів, перекриття {CHUNK_OVERLAP}). Файл: output/chunks.json")
    return chunks
