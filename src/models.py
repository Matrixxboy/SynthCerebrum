# src/models.py
import os
import logging
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import LlamaCpp

# Globals to hold the initialized models and objects
db: Optional[FAISS] = None
llm: Optional[LlamaCpp] = None
embedder: Optional[HuggingFaceEmbeddings] = None
text_splitter: Optional[RecursiveCharacterTextSplitter] = None


def initialize_models_and_index(llm_model_path: str, embedding_model_name: str, index_path: str, chunk_size: int, chunk_overlap: int) -> bool:
    """
    Initialize embeddings, FAISS index, LLM, and text splitter.
    Returns True on success, False on failure.
    """
    global db, llm, embedder, text_splitter

    # 1. Initialize Embedder
    logging.info(f"Initializing embedding model: {embedding_model_name}")
    try:
        embedder = HuggingFaceEmbeddings(model_name=embedding_model_name)
    except Exception as e:
        logging.error(f"Failed to load embedding model: {e}")
        return False

    # 2. Initialize Text Splitter
    logging.info(f"Initializing text splitter with chunk_size={chunk_size} and chunk_overlap={chunk_overlap}")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # 3. Load FAISS Index from disk if it exists
    logging.info(f"Looking for FAISS index at: {index_path}")
    if os.path.exists(index_path):
        try:
            db = FAISS.load_local(
                index_path, 
                embedder, 
                allow_dangerous_deserialization=True
            )
            logging.info("Successfully loaded FAISS index from disk.")
        except Exception as e:
            logging.warning(f"Failed to load FAISS index: {e}. A new index will be created.")
            db = None
    else:
        db = None
        logging.info("No FAISS index found. A new one will be created upon scanning knowledge files.")

    # 4. Load GGUF LLM
    gguf_model_file = Path(llm_model_path)
    if not gguf_model_file.exists():
        logging.error(f"LLM model file not found at {gguf_model_file}")
        llm = None
        return False
    else:
        try:
            logging.info(f"Loading GGUF model from: {gguf_model_file}")
            llm = LlamaCpp(
                model_path=str(gguf_model_file),
                n_gpu_layers=-1,
                n_batch=512,
                n_ctx=2048,
                f16_kv=True,
                verbose=False,
            )
            logging.info("LLM loaded successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to load LLM: {e}", exc_info=True)
            llm = None
            return False