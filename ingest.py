import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.config import ensure_directories, RAW_DIR
from src.document_parser import extract_text
from src.wiki_manager import compile_wiki_page, archive_raw_file

def process_file(filepath):
    print(f"\n[+] Processing new file: {filepath}")
    content = extract_text(filepath)
    if not content:
        print(f"[-] Could not extract readable text from {filepath}.")
        return

    filename = os.path.basename(filepath)
    print("[*] Contacting local Ollama (llama3) for Wiki compilation...")
    
    success = compile_wiki_page(filename, content)
    if success:
        print(f"[+] Wiki page compiled successfully.")
        archive_raw_file(filepath)
        print("[+] Ingestion complete.")

class WatcherHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1) # Ensure file transfer completes before reading
            process_file(event.src_path)

if __name__ == "__main__":
    ensure_directories()
    observer = Observer()
    event_handler = WatcherHandler()
    observer.schedule(event_handler, RAW_DIR, recursive=False)
    observer.start()
    
    print("========================================")
    print(" 🤖 LLM Wiki - Invisible Librarian")
    print("========================================")
    print(f"[*] Watching '{RAW_DIR}/' folder for files (.pdf, .docx, .png, .txt)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ingestion engine...")
        observer.stop()
    observer.join()
