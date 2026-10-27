"""
corpus.py - КОРПУС: завантажує статті з англійської Вікіпедії і зберігає їх як текстові файли.
Тексти беруться з відкритого джерела (CC BY-SA 4.0). Посилання на кожну статтю записуються в output/sources.json.
Служебні розділи (References, See also тощо) відрізаються, щоб у тексті лишився лише зміст.
"""
import json
import os
import re
import urllib.parse
import urllib.request

from config import CORPUS_DIR, OUT, DOCUMENTS

API = "https://en.wikipedia.org/w/api.php"
CUT_MARKERS = ["\n== See also ==", "\n== References ==", "\n== Notes ==", "\n== External links ==", "\n== Further reading =="]


def fetch_article(title: str) -> str:
    params = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": 1,
        "titles": title, "format": "json", "redirects": 1,
    })
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "lab2-corpus/1.0 (student lab)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    page = next(iter(data["query"]["pages"].values()))
    return page.get("extract", "")


def clean(text: str) -> str:
    cut = len(text)
    for marker in CUT_MARKERS:
        i = text.find(marker)
        if i != -1:
            cut = min(cut, i)
    text = text[:cut]
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_corpus(force: bool = False) -> list[dict]:
    """Повертає список документів: {id, title, url, path, words}."""
    docs, sources = [], []
    for i, title in enumerate(DOCUMENTS, start=1):
        fname = f"{i:02d}_{re.sub(r'[^A-Za-z0-9]+', '_', title).strip('_')}.txt"
        path = os.path.join(CORPUS_DIR, fname)
        if force or not os.path.exists(path):
            text = clean(fetch_article(title))
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  завантажено: {title}")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        docs.append({"id": f"doc{i:02d}", "title": title, "url": url, "path": path,
                     "words": len(text.split()), "text": text})
        sources.append({"id": f"doc{i:02d}", "title": title, "url": url,
                        "license": "CC BY-SA 4.0", "words": len(text.split())})
    with open(os.path.join(OUT, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    total = sum(d["words"] for d in docs)
    print(f"[1] Корпус: {len(docs)} документів, разом {total} слів. Джерела: output/sources.json")
    return docs


if __name__ == "__main__":
    build_corpus()
