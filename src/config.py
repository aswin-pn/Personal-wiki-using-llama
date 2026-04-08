import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_API = os.getenv("OLLAMA_API", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3")

# Directories
RAW_DIR = "raw"
WIKI_DIR = "wiki"
WIKI_PAGES_DIR = os.path.join(WIKI_DIR, "pages")
ARCHIVE_DIR = "archive"

def ensure_directories():
    for folder in [RAW_DIR, WIKI_DIR, WIKI_PAGES_DIR, ARCHIVE_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

def load_schema():
    if os.path.exists("schema.md"):
        with open("schema.md", "r") as f:
            return f.read()
    return "Output pure markdown."
