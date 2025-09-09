import os
import logging
import threading
from src.database import init_mysql_database, save_interaction
from src.models import initialize_models
from src.indexing import initial_scan_and_index, save_index, force_reindex
from src.rag import answer_query, add_user_knowledge
from src.file_watcher import start_file_watcher_background

from dotenv import load_dotenv
load_dotenv()

# ---------------- CONFIG ----------------
KNOWLEDGE_DIR = "./knowledge"
INDEX_PATH = "faiss_index"
LLM_MODEL_NAME = "QuantFactory--Meta-Llama-3-8B-Instruct-GGUF/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"         
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "utsav1424"),
    "database": os.getenv("DB_NAME", "synthcerebrum"),
    "port": os.getenv("DB_PORT", 3306)
}
# ---------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def interactive_loop():
    print("\n--- Offline RAG System ---")
    print("Commands: 'exit', 'watch' (start watcher), 'add' (add new knowledge), 'save' (save index), 'reindex' (force re-index), or type a question.")
    while True:
        try:
            q = input("\nYour input: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not q:
            continue
        if q.lower() == "exit":
            break
        if q.lower() == "watch":
            start_file_watcher_background(KNOWLEDGE_DIR, INDEX_PATH)
            continue
        if q.lower() == "save":
            save_index(INDEX_PATH)
            continue
        if q.lower() == "reindex":
            force_reindex(INDEX_PATH)
            initial_scan_and_index(KNOWLEDGE_DIR, INDEX_PATH)
            continue
            continue

        if q.lower().startswith("add"):
            # usage: add <optional_filename>
            parts = q.split(maxsplit=1)
            fname = parts[1].strip() if len(parts) > 1 else None
            print("Enter content (end with a single line containing only 'EOF'):")
            lines = []
            while True:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            text = "\n".join(lines).strip()
            if not text:
                print("No text provided.")
                continue
            fp = add_user_knowledge(text, KNOWLEDGE_DIR, INDEX_PATH, filename=fname)
            print(f"Saved and indexed: {fp}")
            continue

        # treat as a question
        answer, sources = answer_query(q, k=4)
        print("\n--- Answer ---")
        print(answer)
        print("--------------")
        if sources:
            print("\nSources (snippet or file):")
            for i, s in enumerate(sources, 1):
                print(f"{i}. {s[:300].replace(chr(10), ' ')}")
        else:
            print("No sources found in index.")

        # save interaction asynchronously
        try:
            threading.Thread(target=save_interaction, args=(q, answer, sources), daemon=True).start()
        except Exception:
            logging.exception("Failed to spawn thread to save interaction.")

        # Ask whether the answer is correct / should be learned
        try:
            resp = input("\nWas this answer correct/helpful? (y/n) ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = "n"
        if resp == "y":
            learn = input("Save this Q&A as knowledge for future (y/n)? ").strip().lower()
            if learn == "y":
                # save a small file with Q + A
                content = f"Q: {q}\nA: {answer}"
                fp = add_user_knowledge(content, KNOWLEDGE_DIR, INDEX_PATH)
                print(f"Saved Q&A as knowledge file: {fp}")
        else:
            # user says answer was not good -> ask for correction
            print("Please provide the correct answer or additional context. End with a single line 'EOF'.")
            lines = []
            while True:
                try:
                    line = input()
                except (EOFError, KeyboardInterrupt):
                    line = "EOF"
                if line.strip() == "EOF":
                    break
                lines.append(line)
            corrected = "\n".join(lines).strip()
            if corrected:
                # store corrected content as knowledge and index
                fp = add_user_knowledge(f"UserCorrection Q: {q}\nCorrectedAnswer: {corrected}", KNOWLEDGE_DIR, INDEX_PATH)
                print(f"Saved correction as knowledge file: {fp}")
                # Optionally re-run query now that knowledge is indexed
                print("Re-running query with updated knowledge...")
                ans2, src2 = answer_query(q, k=4)
                print("\n--- New Answer ---")
                print(ans2)
                print("--------------")
                threading.Thread(target=save_interaction, args=(q + " (corrected)", ans2, src2), daemon=True).start()


def main():
    # read mysql password from env if present
    MYSQL_CONFIG["password"] = MYSQL_CONFIG.get("password") or os.environ.get("MYSQL_PASSWORD", "")
    try:
        init_mysql_database(MYSQL_CONFIG)
    except Exception as e:
        logging.warning("MySQL initialization failed; continuing without persistence. Error: %s", e)

    initialize_models(LLM_MODEL_NAME, EMBEDDING_MODEL_NAME, INDEX_PATH)
    initial_scan_and_index(KNOWLEDGE_DIR, INDEX_PATH)
    # start watcher by default
    start_file_watcher_background(KNOWLEDGE_DIR, INDEX_PATH)
    interactive_loop()


if __name__ == "__main__":
    main()
