# src/indexing.py
import os
import logging
import shutil
from pathlib import Path
from typing import List
import threading

from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader
)

from src import models

# A re-entrant lock to prevent deadlocks when a locked function calls another locked function.
db_lock = threading.RLock()

# Supported file types and their loaders
LOADER_MAPPING = {
    # Text-based
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".csv": CSVLoader,
    
    # Office Documents
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".xls": UnstructuredExcelLoader,

    # Programming Languages (all treated as plain text)
    ".py": TextLoader, 
    ".js": TextLoader,
    ".java": TextLoader,
    ".c": TextLoader,
    ".cpp": TextLoader,
    ".h": TextLoader,
    ".hpp": TextLoader,
    ".cs": TextLoader,
    ".go": TextLoader,
    ".rs": TextLoader,
    ".ts": TextLoader,
    ".rb": TextLoader,
    ".php": TextLoader,
    ".kt": TextLoader,
    ".swift": TextLoader,
    ".scala": TextLoader,
    ".lua": TextLoader,
    ".pl": TextLoader,
    ".sh": TextLoader,
    ".bat": TextLoader,
    ".sql": TextLoader,
    ".html": TextLoader,
    ".css": TextLoader,
    ".xml": TextLoader,
    ".json": TextLoader,
    ".yaml": TextLoader,
    ".yml": TextLoader,
    ".ini": TextLoader,
    ".cfg": TextLoader,
    ".toml": TextLoader,
}

def _ensure_dirs(path_str: str):
    """Ensure the directory for a given path exists."""
    Path(path_str).parent.mkdir(parents=True, exist_ok=True)

def force_reindex(index_path: str):
    """Deletes the existing FAISS index directory."""
    with db_lock:
        if os.path.exists(index_path):
            logging.info(f"Removing existing index at {index_path}")
            shutil.rmtree(index_path)
        models.db = None # Clear the in-memory index

def save_index(index_path: str):
    """Saves the current in-memory FAISS index to disk."""
    with db_lock:
        if models.db:
            logging.info(f"Saving FAISS index to {index_path}")
            models.db.save_local(index_path)
        else:
            logging.warning("No index in memory to save.")

def _load_documents_from_files(file_paths: List[str]) -> List[Document]:
    """Loads and splits documents from a list of file paths."""
    docs = []
    for file_path in file_paths:
        ext = Path(file_path).suffix.lower()
        if ext in LOADER_MAPPING:
            try:
                loader = LOADER_MAPPING[ext](file_path)
                loaded_docs = loader.load()
                # Add source metadata to each document
                for doc in loaded_docs:
                    doc.metadata["source"] = os.path.basename(file_path)
                docs.extend(loaded_docs)
            except Exception as e:
                logging.error(f"Failed to load {file_path}: {e}")
        else:
            logging.warning(f"Skipping unsupported file type: {file_path}")
    
    if not docs:
        return []

    return models.text_splitter.split_documents(docs)

def update_vector_store(file_paths: List[str], index_path: str):
    """
    Updates the FAISS index with new documents from file_paths.
    Creates a new index if one doesn't exist.
    """
    if not models.embedder:
        logging.error("Embedder not initialized. Cannot update vector store.")
        return

    split_docs = _load_documents_from_files(file_paths)
    if not split_docs:
        logging.info("No new documents to add to the index.")
        return

    logging.info(f"Embedding and indexing {len(split_docs)} new document chunks...")
    with db_lock:
        if models.db is None:
            # Create a new index from scratch
            models.db = models.FAISS.from_documents(split_docs, models.embedder)
            logging.info("Created a new FAISS index.")
        else:
            # Add new documents to the existing index
            models.db.add_documents(split_docs)
            logging.info("Updated existing FAISS index.")
        
        # Save the potentially updated index to disk
        save_index(index_path)

        # Crucial step: Reload the index from disk to ensure consistency
        try:
            logging.info("Reloading FAISS index from disk to ensure consistency.")
            models.db = models.FAISS.load_local(
                index_path, 
                models.embedder, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            logging.error(f"FATAL: Failed to reload index from disk after update: {e}")
            # If reloading fails, the in-memory index might be out of sync.
            # Clearing it to prevent incorrect answers.
            models.db = None

def initial_scan_and_index(knowledge_dir: str, index_path: str):
    """Scans the knowledge directory and indexes all supported files."""
    if not os.path.exists(knowledge_dir):
        logging.info(f"Knowledge directory '{knowledge_dir}' not found. Creating it.")
        os.makedirs(knowledge_dir)
        return
        
    all_files = [str(p) for p in Path(knowledge_dir).rglob("*") if p.is_file()]
    if not all_files:
        logging.info("Knowledge directory is empty. Nothing to index.")
        return

    logging.info(f"Starting initial scan of {len(all_files)} files in '{knowledge_dir}'...")
    update_vector_store(all_files, index_path)
    logging.info("Initial scan and indexing complete.")
