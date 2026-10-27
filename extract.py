"""
extract.py - ЕКСТРАКЦІЯ ФАКТІВ: для кожного чанка просимо Gemini видобути факти за схемою
schema.py. Модель повертає JSON, який відразу перевіряється pydantic.
Результат: output/facts.json (мінімум 30 фактів), кожен факт має джерело (документ, чанк) і цитату.
"""
import json
import os

from config import OUT, ENTITY_TYPES, RELATION_TYPES, EXTRACT_DOCS
from llm import generate_structured
from schema import FactList

PROMPT = """You extract knowledge graph facts from a text about the history of computing.
Rules:
- Extract only facts that are stated explicitly in the text. Do not add outside knowledge.
- Use entity names exactly as written in the text.
- subject_type and object_type must be one of: {etypes}.
- relation must be one of: {rels}.
  designed = X designed/invented/proposed Y; worked_at = X worked at Y;
  built_at = Y was built/located at X; influenced = X influenced Y; collaborated_with = X worked with Y.
- evidence must be an exact sentence copied from the text.
- Return an empty list if there are no such facts.

TEXT:
{text}
"""


def extract_chunk(chunk: dict) -> list[dict]:
    prompt = PROMPT.format(etypes=", ".join(ENTITY_TYPES), rels=", ".join(RELATION_TYPES), text=chunk["text"])
    result: FactList = generate_structured(prompt, FactList)
    out, dropped = [], 0
    for f in result.facts if result else []:
        if f.subject_type not in ENTITY_TYPES or f.object_type not in ENTITY_TYPES or f.relation not in RELATION_TYPES:
            dropped += 1
            continue
        out.append({
            "subject": f.subject.strip(), "subject_type": f.subject_type,
            "relation": f.relation,
            "object": f.object.strip(), "object_type": f.object_type,
            "evidence": f.evidence.strip(),
            "doc_id": chunk["doc_id"], "title": chunk["title"], "chunk_id": chunk["chunk_id"],
        })
    if dropped:
        print(f"    відкинуто {dropped} фактів зі сторонніми типами або зв'язками")
    return out


def extract_all(chunks: list[dict], force: bool = False) -> list[dict]:
    """Видобуває факти по чанках. Прогрес зберігається після кожного чанка
    у output/facts_partial.json, тож після збою можна продовжити з того самого місця."""
    path = os.path.join(OUT, "facts.json")
    partial = os.path.join(OUT, "facts_partial.json")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            facts = json.load(f)
        print(f"[3] facts.json вже є ({len(facts)} фактів), пропускаю. Щоб перезібрати, запустіть з --force")
        return facts
    # Екстракція йде по першому чанку кожного з перших EXTRACT_DOCS документів:
    # так вистачає фактів на 30+ і запитів у межах безкоштовної добової квоти.
    chunks = [c for c in chunks if c["chunk_id"].endswith("_c00")][:EXTRACT_DOCS]
    print(f"[3] Екстракція по {len(chunks)} чанках (перші чанки документів)")
    done_chunks, facts = set(), []
    if os.path.exists(partial) and not force:
        with open(partial, encoding="utf-8") as f:
            saved = json.load(f)
        facts = saved["facts"]
        done_chunks = set(saved["done"])
        print(f"  продовжую: вже оброблено {len(done_chunks)} чанків, фактів {len(facts)}")
    for i, ch in enumerate(chunks, start=1):
        if ch["chunk_id"] in done_chunks:
            continue
        print(f"  чанк {i}/{len(chunks)} {ch['chunk_id']}")
        facts.extend(extract_chunk(ch))
        done_chunks.add(ch["chunk_id"])
        with open(partial, "w", encoding="utf-8") as f:
            json.dump({"done": sorted(done_chunks), "facts": facts}, f, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)
    print(f"[3] Видобуто фактів: {len(facts)}. Файл: output/facts.json")
    return facts
