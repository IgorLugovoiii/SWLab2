"""
manual_check.py - РУЧНА ПЕРЕВІРКА: бере 20 випадкових фактів (фіксований seed, щоб вибірка
відтворювалась) і записує їх у output/manual_check.txt разом з цитатою і тестовим джерелом.
Далі ви відкриваєте файл, читаєте оригінал у corpus\\ і ставите у полі verdict:
  1 - факт правильний, 0 - помилковий, або вказуєте тип помилки:
  пропуск, вигадка, помилка зв'язування.
Потім запустіть:  python manual_check.py --score   і отримаєте частку коректних фактів.
"""
import json
import os
import random
import re
import sys

from config import OUT

PATH = os.path.join(OUT, "manual_check.txt")
SAMPLE = 20


def write_sample(facts: list[dict]) -> None:
    rnd = random.Random(42)
    sample = rnd.sample(facts, min(SAMPLE, len(facts)))
    lines = ["Ручна перевірка. У полі verdict поставте: 1 (правильно), 0 (помилка) і тип помилки, якщо 0.", ""]
    for i, f in enumerate(sample, start=1):
        lines += [
            f"#{i:02d} документ: {f['title']} ({f['chunk_id']})",
            f"  факт: {f['subject']} ({f['subject_type']}) --{f['relation']}--> {f['object']} ({f['object_type']})",
            f"  цитата моделі: {f['evidence']}",
            "  verdict: ",
            "  тип помилки (якщо 0): ",
            "",
        ]
    with open(PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[3b] Вибірка для перевірки: {PATH}")


def score() -> None:
    with open(PATH, encoding="utf-8") as f:
        text = f.read()
    verdicts = re.findall(r"verdict:\s*([01])?", text)
    done = [v for v in verdicts if v in ("0", "1")]
    if not done:
        print("Немає заповнених verdict у manual_check.txt")
        return
    correct = done.count("1")
    print(f"Перевірено: {len(done)}; правильних: {correct}; частка коректних: {correct / len(done):.0%}")
    errors = re.findall(r"тип помилки \(якщо 0\):[ \t]*(\S.*)", text)
    if errors:
        print("Типи помилок, які ви вказали:")
        for e in errors:
            print("  -", e.strip())


if __name__ == "__main__":
    if "--score" in sys.argv:
        score()
    else:
        with open(os.path.join(OUT, "facts.json"), encoding="utf-8") as f:
            write_sample(json.load(f))
