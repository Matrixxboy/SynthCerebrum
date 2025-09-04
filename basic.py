import os
import time
import logging
from typing import List

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
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


# --- Configuration ---
KNOWLEDGE_DIR = "./knowledge"
INDEX_PATH = "faiss_index"
# Small, instruction-tuned model that works well for Q&A style:
LLM_MODEL_NAME = "google/flan-t5-small"  # you can switch to "google/flan-t5-base" later
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- Global Variables ---
db: FAISS | None = None
llm = None
embedder: HuggingFaceEmbeddings | None = None
text_splitter: RecursiveCharacterTextSplitter | None = None
llm_is_seq2seq: bool = False  # set during init


def _ensure_dirs():
    if not os.path.exists(KNOWLEDGE_DIR):
        os.makedirs(KNOWLEDGE_DIR)
        logging.info(f"Created knowledge directory: {KNOWLEDGE_DIR}")


def initialize_models():
    """Loads all models and initializes the vector store."""
    global db, llm, embedder, text_splitter, llm_is_seq2seq

    logging.info("Initializing models and vector store...")

    # 1) Embeddings
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # 2) Vector store (FAISS)
    if os.path.exists(INDEX_PATH):
        logging.info(f"Loading existing FAISS index from {INDEX_PATH}")
        db = FAISS.load_local(INDEX_PATH, embedder, allow_dangerous_deserialization=True)
    else:
        logging.info("No FAISS index found; a new one will be created on first document add.")
        # We'll lazily create on first add. For now, keep db as None.

    # 3) LLM (auto-detect seq2seq vs causal)
    logging.info(f"Loading LLM: {LLM_MODEL_NAME}")
    config = AutoConfig.from_pretrained(LLM_MODEL_NAME)
    tokenizer = None
    model = None

    if getattr(config, "is_encoder_decoder", False):
        # T5/Flan and friends
        llm_is_seq2seq = True
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL_NAME)
        llm_task = "text2text-generation"
    else:
        # GPT-style causal models
        llm_is_seq2seq = False
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_NAME)
        llm_task = "text-generation"

    llm_kwargs = dict(
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=256,
    )
    # Build pipeline
    global llm_pipeline_task
    llm_pipeline_task = llm_task
    llm = pipeline(llm_task, **llm_kwargs)

    # 4) Text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    logging.info("Initialization complete.")


def _create_or_get_db() -> FAISS:
    """Ensures a FAISS db object exists; creates an empty one if needed."""
    global db, embedder
    if db is None:
        # Create an empty FAISS by adding a tiny dummy, then we’ll replace on first real add.
        db = FAISS.from_texts(["__init__"], embedder)
        db.save_local(INDEX_PATH)
    return db


def _index_chunks(chunks: List[str]):
    """Indexes a list of text chunks by merging into existing FAISS and saving."""
    global db, embedder
    if not chunks:
        return
    # Build a small FAISS for these chunks and merge (ensures embeddings are computed)
    new_db = FAISS.from_texts(chunks, embedder)
    db = _create_or_get_db()
    db.merge_from(new_db)
    db.save_local(INDEX_PATH)


def update_vector_store(file_path: str):
    """Reads a file, splits it into chunks, embeds them, and adds to FAISS."""
    try:
        if not os.path.isfile(file_path):
            return
        if not file_path.lower().endswith(".txt"):
            return

        logging.info(f"Processing and indexing file: {file_path}")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if not content.strip():
            logging.warning(f"File {file_path} is empty. Skipping.")
            return

        chunks = text_splitter.split_text(content)
        _index_chunks(chunks)
        logging.info(f"Successfully indexed {len(chunks)} chunks from {file_path}")

    except Exception as e:
        logging.exception(f"Failed to process file {file_path}: {e}")


def initial_scan_and_index():
    """Scans the knowledge directory and indexes all existing .txt files."""
    _ensure_dirs()
    logging.info(f"Performing initial scan of '{KNOWLEDGE_DIR}'...")
    any_indexed = False

    for filename in os.listdir(KNOWLEDGE_DIR):
        if filename.lower().endswith(".txt"):
            file_path = os.path.join(KNOWLEDGE_DIR, filename)
            update_vector_store(file_path)
            any_indexed = True

    if not any_indexed:
        # Create a small sample so the system can answer something immediately
        sample_path = os.path.join(KNOWLEDGE_DIR, "sample.txt")
        if not os.path.exists(sample_path):
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write(
                    "Python is a high-level, general-purpose programming language. "
                    "Its design philosophy emphasizes code readability with significant indentation. "
                    "It was created by Guido van Rossum."
                )
            update_vector_store(sample_path)


class KnowledgeFolderHandler(FileSystemEventHandler):
    """Handles file system events in the knowledge directory."""

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".txt"):
            logging.info(f"New file detected: {event.src_path}")
            update_vector_store(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".txt"):
            logging.info(f"File modified: {event.src_path}")
            update_vector_store(event.src_path)


def start_file_watcher():
    """Starts the watchdog observer to monitor the knowledge folder."""
    event_handler = KnowledgeFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, KNOWLEDGE_DIR, recursive=False)
    observer.start()
    logging.info(f"Watching directory: {KNOWLEDGE_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _build_prompt(query: str, context: str) -> str:
    """
    Builds a strict prompt.
    For seq2seq models, shorter instructions work better; causal LMs can take a longer instruction.
    """
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


def answer_query(query: str):
    """Answers a user query using the RAG pipeline."""
    global db, llm

    if db is None:
        logging.warning("Vector store is not initialized yet. Index some files first.")
        print("\n--- Answer ---")
        print("I cannot answer this question based on the provided information.")
        print("--------------\n")
        return

    logging.info(f"Received query: '{query}'")

    # 1) Retrieve relevant documents
    docs = db.similarity_search(query, k=4) if db is not None else []
    context = "\n\n".join(d.page_content for d in docs) if docs else ""

    # 2) Build prompt
    prompt = _build_prompt(query, context)

    # 3) Generate
    logging.info("Generating answer from LLM...")
    # For seq2seq ("text2text-generation"), pass the prompt directly.
    # For causal ("text-generation"), same—because we constructed the full instruction.
    response = llm(prompt)

    # Both pipelines return [{'generated_text': '...'}]
    text = (response[0]['generated_text'].strip()) if response else "Response generation failed."
    print("\n--- Answer ---")
    print(text)
    print("--------------\n")


if __name__ == "__main__":
    initialize_models()
    initial_scan_and_index()

    # --- Interactive Query Loop ---
    print("\n\n--- Offline AI Query System Ready ---")
    print("You can now add or modify .txt files in the './knowledge' folder.")
    print("The system will index them automatically (check logs).")
    print("Enter a query below or type 'exit' to quit.")

    while True:
        try:
            user_query = input("Enter your query: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_query.lower() == "exit":
            break
        if not user_query:
            continue
        answer_query(user_query)

    # To run a live watcher, uncomment:
    # start_file_watcher()
