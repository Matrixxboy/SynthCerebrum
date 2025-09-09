import os
import logging
from pathlib import Path
import threading
from typing import List
import csv
from PyPDF2 import PdfReader
import pandas as pd
import docx

from langchain_community.vectorstores import FAISS

from src import models

db_lock = threading.Lock()

def _ensure_dirs(knowledge_dir):
    Path(knowledge_dir).mkdir(parents=True, exist_ok=True)


def _create_or_get_db() -> FAISS:
    """Create FAISS if missing. Thread-safe via db_lock."""
    with db_lock:
        if models.db is None:
            # Create an in-memory FAISS index
            models.db = FAISS.from_texts(["__init__"], models.embedder)
            logging.info("Created initial in-memory FAISS index.")
    return models.db


def _index_chunks(chunks: List[str], file_path: str):
    """Create a temporary FAISS from chunks and merge it into the main index."""
    if not chunks:
        return
    
    # Create metadata for each chunk
    metadatas = [{"source": file_path} for _ in chunks]
    
    # Create a new FAISS index from the chunks
    new_db = FAISS.from_texts(chunks, models.embedder, metadatas=metadatas)
    
    with db_lock:
        base = _create_or_get_db()
        base.merge_from(new_db)


def save_index(index_path):
    """Save the FAISS index to disk. Thread-safe."""
    with db_lock:
        if models.db:
            models.db.save_local(index_path)
            logging.info(f"FAISS index saved to {index_path}")

def _read_file_content(file_path):
    """Reads content from a file, supporting different file types."""
    content = ""
    try:
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() or ""
        elif file_path.endswith(".csv"):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    content += ", ".join(row) + "\n"
        elif file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
            content = df.to_string()
        elif file_path.endswith(('.doc', '.docx')):
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                content += para.text + '\n'
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
    return content

def update_vector_store(file_path, index_path):
    """Reads a file, splits it into chunks, embeds them, and adds to FAISS."""
    _create_or_get_db() # Ensure db is initialized
    try:
        logging.info(f"Processing and indexing file: {file_path}")
        content = _read_file_content(file_path)

        if not content.strip():
            logging.warning(f"File {file_path} is empty or could not be read. Skipping.")
            return

        # Split into chunks (your file will probably stay as 1 chunk)
        chunks = models.text_splitter.split_text(content)

        # Create metadata for each chunk
        metadatas = [{"source": file_path} for _ in chunks]

        # Instead of creating a new FAISS each time, just add directly
        models.db.add_texts(chunks, metadatas=metadatas)

        # Save updated index
        save_index(index_path)
        logging.info(f"Successfully indexed {len(chunks)} chunks from {file_path}")

    except Exception as e:
        logging.error(f"Failed to process file {file_path}: {e}")


def initial_scan_and_index(knowledge_dir, index_path):
    _ensure_dirs(knowledge_dir)
    logging.info(f"Scanning {knowledge_dir} for files...")
    found = False
    for f in Path(knowledge_dir).iterdir():
        if f.is_file():
            update_vector_store(str(f), index_path)
            found = True
    if not found:
        # add a sample file and index it
        sample = Path(knowledge_dir) / "sample.txt"
        if not sample.exists():
            sample.write_text(
                "Python is a high-level, general-purpose programming language created by Guido van Rossum. "
                "Its design emphasizes code readability and significant indentation.", encoding="utf-8"
            )
        update_vector_store(str(sample), index_path)
    save_index(index_path)
