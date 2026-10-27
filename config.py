"""
config.py - НАЛАШТУВАННЯ лаби 2: шляхи, назви моделей, список документів.
"""
import os

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

CORPUS_DIR = os.path.join(HERE, "corpus")          # тексти документів
OUT = os.path.join(HERE, "output")                 # усі результати
os.makedirs(CORPUS_DIR, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

# Пауза між запитами до LLM (безкоштовний ліміт ~15 запитів на хвилину)
SLEEP_BETWEEN_CALLS = 5

CHUNK_WORDS = 800      # розмір чанка в словах
CHUNK_OVERLAP = 100    # перекриття сусідніх чанків, щоб факт не розірвався на межі

EXTRACT_DOCS = 8       # скільки документів іде на екстракцію фактів (по першому чанку кожного)
TOP_N = 5              # скільки чанків повертати при пошуку і в vector-RAG

# Документи корпусу: англійська Вікіпедія (ліцензія CC BY-SA 4.0)
DOCUMENTS = [
    "Charles Babbage",
    "Difference engine",
    "Analytical Engine",
    "Ada Lovelace",
    "Alan Turing",
    "Enigma machine",
    "Bletchley Park",
    "Konrad Zuse",
    "ENIAC",
    "John von Neumann",
]

ENTITY_TYPES = ["Person", "Machine", "Organization", "Place"]
RELATION_TYPES = ["designed", "worked_at", "built_at", "influenced", "collaborated_with"]

# Питання до корпусу (п. 1 завдання)
SIMPLE_QUESTIONS = [
    "Хто спроєктував Analytical Engine?",
    "Де було побудовано ENIAC?",
    "Хто написав першу програму для Analytical Engine?",
]
GLOBAL_QUESTIONS = [
    "Хто є ключовими фігурами в історії ранніх обчислювальних машин і як вони пов'язані між собою?",
    "Які теми повторюються найчастіше в цих документах?",
]

# Запити для порівняння keyword-пошуку і векторного пошуку (п. 3)
SEARCH_QUERIES = [
    "machine that could be programmed with punched cards",
    "who broke the German cipher during the Second World War",
    "1837",
    "Z3",
    "the first computer algorithm",
]
