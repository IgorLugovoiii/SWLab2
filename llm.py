"""
llm.py - ОБГОРТКА НАД GEMINI: один спільний клієнт, повтори при помилці ліміту (429),
пауза між запитами. Усі інші файли викликають LLM тільки через цей файл.
"""
import hashlib
import json
import os
import time

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, LLM_MODEL, EMBED_MODEL, SLEEP_BETWEEN_CALLS, OUT

CACHE = os.path.join(OUT, "llm_cache.json")  # уже отримані відповіді: повтор запуску не витрачає ліміт

_client = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise SystemExit("Немає ключа. Створіть файл .env і впишіть у ньому GEMINI_API_KEY=ваш_ключ")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _retry(fn, tries: int = 5):
    for attempt in range(1, tries + 1):
        try:
            result = fn()
            time.sleep(SLEEP_BETWEEN_CALLS)
            return result
        except Exception as e:  # noqa: BLE001
            text = str(e)
            if "per day" in text.lower() or "PerDay" in text:
                raise SystemExit("Вичерпано ДОБОВИЙ ліміт запитів Gemini. Прогрес збережено; "
                                 "запустіть python main.py ще раз після скидання квоти.")
            is_retryable = any(code in text for code in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"))
            if attempt == tries or not is_retryable:
                raise
            wait = 30 * attempt
            print(f"    сервер зайнятий або ліміт запитів, чекаю {wait} с (спроба {attempt})")
            time.sleep(wait)


def _cache_load() -> dict:
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_text(prompt: str) -> str:
    cache = _cache_load()
    key = hashlib.sha256((LLM_MODEL + prompt).encode("utf-8")).hexdigest()
    if key in cache:
        return cache[key]
    resp = _retry(lambda: client().models.generate_content(model=LLM_MODEL, contents=prompt))
    text = resp.text or ""
    cache[key] = text
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    return text


def generate_structured(prompt: str, schema):
    """Повертає екземпляр pydantic-моделі schema (структурований вивід)."""
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
    resp = _retry(lambda: client().models.generate_content(model=LLM_MODEL, contents=prompt, config=cfg))
    return resp.parsed


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Ембединги пакетами по 5 текстів з паузою 15 с (ліміт безкоштовного рівня)."""
    vectors = []
    # Безкоштовний ліміт ембедингів: ~30 000 токенів на хвилину, тому малі пакети з паузою
    for i in range(0, len(texts), 5):
        if i:
            time.sleep(15)
        batch = texts[i:i + 5]
        cfg = types.EmbedContentConfig(task_type=task_type)
        resp = _retry(lambda b=batch: client().models.embed_content(model=EMBED_MODEL, contents=b, config=cfg))
        vectors.extend([e.values for e in resp.embeddings])
    return vectors
