import sys
sys.stdout.flush()  
import os
import time
import logging
import threading
import torch
import json
from typing import List, Optional
from pathlib import Path
from getpass import getpass

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from transformers import (
    pipeline,
    AutoTokenizer,
    AutoConfig,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
)
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

import mysql.connector
from mysql.connector import errorcode

# ---------------- CONFIG ----------------
KNOWLEDGE_DIR = "./knowledge"
INDEX_PATH = "faiss_index"
LLM_MODEL_NAME = "philschmid/flan-t5-base-samsum"         # or any other local model
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L3-v2"  # smaller and faster
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "utsav1424", 
    "database": "synthcerebrum",
    "port": 3306
}
# ---------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Globals
db: Optional[FAISS] = None
db_lock = threading.Lock()   # protect FAISS operations
llm = None
embedder: Optional[HuggingFaceEmbeddings] = None
text_splitter: Optional[RecursiveCharacterTextSplitter] = None
llm_is_seq2seq: bool = False
llm_pipeline_task: str = "text2text-generation"

# MySQL connection (will be set in init_db())
mysql_conn: Optional[mysql.connector.connection_cext.CMySQLConnection] = None


# ----------------- MySQL helpers -----------------
def init_mysql_database(cfg: dict):
    """
    Connects to MySQL, creates database + tables if not exist.
    Tables:
      - interactions(id, user_query, answer, context_snippet, sources_json, created_at)
      - knowledge_files(id, file_path, added_at)
    """
    global mysql_conn
    pwd = cfg.get("password") or ""
    if not pwd:
        # ask interactively if not set (safer)
        try:
            pwd = getpass(prompt="MySQL password (press Enter for none): ")
        except Exception:
            pwd = ""
    cfg_copy = cfg.copy()
    cfg_copy["password"] = pwd

    # First connect without database to create it if needed
    tmp_cfg = cfg_copy.copy()
    dbname = tmp_cfg.pop("database", None)
    try:
        conn = mysql.connector.connect(**tmp_cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET 'utf8mb4'")
        conn.close()
    except mysql.connector.Error as err:
        logging.error(f"MySQL error while creating database: {err}")
        raise

    # Now connect to the database
    try:
        conn = mysql.connector.connect(**cfg_copy)
        mysql_conn = conn
        cursor = conn.cursor()
        # interactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_query TEXT NOT NULL,
                answer LONGTEXT,
                context_snippet LONGTEXT,
                sources_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
        )
        # knowledge_files table (record of files added/learned)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                file_path VARCHAR(1024) NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
        )
        conn.commit()
        logging.info("MySQL initialized and tables are ready.")
    except mysql.connector.Error as err:
        logging.error(f"MySQL connection error: {err}")
        raise


def save_interaction(user_query: str, answer: str, sources: List[str]):
    """Save a Q/A interaction to MySQL (non-blocking best-effort)."""
    global mysql_conn
    try:
        if mysql_conn is None:
            logging.debug("MySQL connection not set; skipping save_interaction.")
            return
        cursor = mysql_conn.cursor()
        sources_json = json.dumps(sources, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO interactions (user_query, answer, context_snippet, sources_json) VALUES (%s,%s,%s,%s)",
            (user_query, answer, "" if not sources else "\n".join(sources[:5]), sources_json),
        )
        mysql_conn.commit()
    except Exception as e:
        logging.exception(f"Failed to save interaction to MySQL: {e}")


def save_knowledge_file_record(file_path: str):
    global mysql_conn
    try:
        if mysql_conn is None:
            return
        cursor = mysql_conn.cursor()
        cursor.execute("INSERT INTO knowledge_files (file_path) VALUES (%s)", (file_path,))
        mysql_conn.commit()
    except Exception:
        logging.exception("Failed to save knowledge file record.")

# ----------------- Model & Index init -----------------
def _ensure_dirs():
    Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)


def initialize_models():
    """Load embedder, load or create FAISS, load LLM pipeline, and setup text splitter."""
    global db, llm, embedder, text_splitter, llm_is_seq2seq, llm_pipeline_task

    logging.info("Initializing embedder and text splitter...")
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    logging.info("Loading FAISS index if exists...")
    if os.path.exists(INDEX_PATH):
        try:
            db = FAISS.load_local(INDEX_PATH, embedder, allow_dangerous_deserialization=True)
            logging.info("Loaded FAISS index from disk.")
        except Exception:
            logging.exception("Failed to load FAISS index. A new index will be created when indexing content.")
            db = None
    else:
        db = None
        logging.info("No FAISS index on disk yet.")

    # ---------------- LOCAL MODEL LOADING ----------------
    # Always look for models inside ./models/<model-name>
    local_model_path = Path("./models") / LLM_MODEL_NAME.replace("/", "--")
    if local_model_path.exists():
        logging.info(f"Loading model from local path: {local_model_path}")
        config = AutoConfig.from_pretrained(local_model_path)
        tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        if getattr(config, "is_encoder_decoder", False):
            llm_is_seq2seq = True
            model = AutoModelForSeq2SeqLM.from_pretrained(local_model_path, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text2text-generation"
        else:
            llm_is_seq2seq = False
            model = AutoModelForCausalLM.from_pretrained(local_model_path, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text-generation"
    else:
        logging.info(f"Local model path not found, downloading from HuggingFace: {LLM_MODEL_NAME}")
        config = AutoConfig.from_pretrained(LLM_MODEL_NAME)
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        if getattr(config, "is_encoder_decoder", False):
            llm_is_seq2seq = True
            model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL_NAME, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text2text-generation"
        else:
            llm_is_seq2seq = False
            model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_NAME, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text-generation"
        # Save locally for future use
        Path(local_model_path).mkdir(parents=True, exist_ok=True)
        model.save_pretrained(local_model_path)
        tokenizer.save_pretrained(local_model_path)
        config.save_pretrained(local_model_path)

    llm = pipeline(llm_pipeline_task, model=model, tokenizer=tokenizer, max_new_tokens=256)
    logging.info(f"LLM pipeline ready ({llm_pipeline_task}).")


def _create_or_get_db() -> FAISS:
    """Create FAISS if missing. Thread-safe via db_lock."""
    global db, embedder
    with db_lock:
        if db is None:
            # Create an in-memory FAISS index
            db = FAISS.from_texts(["__init__"], embedder)
            logging.info("Created initial in-memory FAISS index.")
    return db


def _index_chunks(chunks: List[str], file_path: str):
    """Create a temporary FAISS from chunks and merge it into the main index."""
    global db, embedder
    if not chunks:
        return
    
    # Create metadata for each chunk
    metadatas = [{"source": file_path} for _ in chunks]
    
    # Create a new FAISS index from the chunks
    new_db = FAISS.from_texts(chunks, embedder, metadatas=metadatas)
    
    with db_lock:
        base = _create_or_get_db()
        base.merge_from(new_db)


def save_index():
    """Save the FAISS index to disk. Thread-safe."""
    global db
    with db_lock:
        if db:
            db.save_local(INDEX_PATH)
            logging.info(f"FAISS index saved to {INDEX_PATH}")

# ----------------- File reading & indexing -----------------
def update_vector_store(file_path):
    """Reads a file, splits it into chunks, embeds them, and adds to FAISS."""
    global db
    try:
        logging.info(f"Processing and indexing file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            logging.warning(f"File {file_path} is empty. Skipping.")
            return

        # Split into chunks (your file will probably stay as 1 chunk)
        chunks = text_splitter.split_text(content)

        # Instead of creating a new FAISS each time, just add directly
        db.add_texts(chunks, embedder)

        # Save updated index
        db.save_local(INDEX_PATH)
        logging.info(f"Successfully indexed {len(chunks)} chunks from {file_path}")

    except Exception as e:
        logging.error(f"Failed to process file {file_path}: {e}")



def initial_scan_and_index():
    _ensure_dirs()
    logging.info(f"Scanning {KNOWLEDGE_DIR} for .txt files...")
    found = False
    for f in Path(KNOWLEDGE_DIR).iterdir():
        if f.is_file() and f.suffix.lower() == ".txt":
            update_vector_store(str(f))
            found = True
    if not found:
        # add a sample file and index it
        sample = Path(KNOWLEDGE_DIR) / "sample.txt"
        if not sample.exists():
            sample.write_text(
                "Python is a high-level, general-purpose programming language created by Guido van Rossum. "
                "Its design emphasizes code readability and significant indentation.", encoding="utf-8"
            )
        update_vector_store(str(sample))
    save_index()


class KnowledgeFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".txt"):
            logging.info(f"Detected new file: {event.src_path}")
            update_vector_store(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".txt"):
            logging.info(f"Detected modified file: {event.src_path}")
            update_vector_store(event.src_path)


def start_file_watcher_background():
    handler = KnowledgeFolderHandler()
    observer = Observer()
    observer.schedule(handler, KNOWLEDGE_DIR, recursive=False)
    observer.start()
    logging.info("Started file watcher in background thread.")
    # run in its own daemon thread so it exits with program
    def _observe_loop():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    t = threading.Thread(target=_observe_loop, daemon=True)
    t.start()
    return observer


# ----------------- RAG Querying & Learning -----------------
def _build_prompt(query: str, context: str) -> str:
    base = (
        "Use ONLY the following context to answer the question. "
        "If the answer is not in the context, reply exactly: "
        "\"I cannot answer this question based on the provided information.\""
    )
    prompt = f"""{base}

Context:
---
{context if context.strip() else "(no relevant context found)"}
---

Question: {query}

Answer:"""
    return prompt


def answer_query(query: str, k: int = 4) -> (str, List[str]):
    """Retrieve top-k docs, generate answer and return (answer, sources)."""
    global db
    if db is None:
        logging.warning("Index empty. Cannot perform similarity search.")
        return "I cannot answer this question based on the provided information.", []

    with db_lock:
        docs = db.similarity_search(query, k=k)
    context = "\n\n".join(d.page_content for d in docs) if docs else ""
    sources = [getattr(d, "metadata", {}).get("source", "") or d.page_content[:200] for d in docs]
    prompt = _build_prompt(query, context)

    logging.info("Calling LLM...")
    resp = llm(prompt)
    # pipeline returns list of dicts with 'generated_text'
    gen = resp[0].get("generated_text", "").strip() if resp else ""
    if not gen:
        gen = "I cannot answer this question based on the provided information."
    return gen, sources


def add_user_knowledge(text: str, filename: Optional[str] = None) -> str:
    """
    Save the user-provided correction or new knowledge as a .txt in knowledge folder and index it.
    Returns file path.
    """
    _ensure_dirs()
    if not filename:
        filename = f"user_added_{int(time.time())}.txt"
    path = Path(KNOWLEDGE_DIR) / filename
    path.write_text(text, encoding="utf-8")
    update_vector_store(str(path))
    return str(path.resolve())


# ---------------- Interactive CLI ----------------
def interactive_loop():
    print("\n--- Offline RAG System ---")
    print("Commands: 'exit', 'watch' (start watcher), 'add' (add new knowledge), 'save' (save index), or type a question.")
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
            start_file_watcher_background()
            continue
        if q.lower() == "save":
            save_index()
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
            fp = add_user_knowledge(text, filename=fname)
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
                fp = add_user_knowledge(content)
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
                fp = add_user_knowledge(f"UserCorrection Q: {q}\nCorrectedAnswer: {corrected}")
                print(f"Saved correction as knowledge file: {fp}")
                # Optionally re-run query now that knowledge is indexed
                print("Re-running query with updated knowledge...")
                ans2, src2 = answer_query(q, k=4)
                print("\n--- New Answer ---")
                print(ans2)
                print("--------------")
                threading.Thread(target=save_interaction, args=(q + " (corrected)", ans2, src2), daemon=True).start()


# ---------------- Main ----------------
def main():
    # read mysql password from env if present
    MYSQL_CONFIG["password"] = MYSQL_CONFIG.get("password") or os.environ.get("MYSQL_PASSWORD", "")
    try:
        init_mysql_database(MYSQL_CONFIG)
    except Exception as e:
        logging.warning("MySQL initialization failed; continuing without persistence. Error: %s", e)

    initialize_models()
    initial_scan_and_index()
    # start watcher by default
    start_file_watcher_background()
    interactive_loop()


if __name__ == "__main__":
    main()