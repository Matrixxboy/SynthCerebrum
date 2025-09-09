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


def initialize_models_and_index(llm_model_path: str, embedding_model_name: str, index_path: str):
    """
    Initialize embeddings, FAISS index, LLM, and text splitter.
    This function should only be called once.
    """
    global db, llm, embedder, text_splitter

    # 1. Initialize Embedder
    logging.info(f"Initializing embedding model: {embedding_model_name}")
    try:
        embedder = HuggingFaceEmbeddings(model_name=embedding_model_name)
    except Exception as e:
        logging.error(f"Failed to load embedding model: {e}")
        raise  # Stop execution if embeddings can't load

    # 2. Initialize Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    # 3. Load FAISS Index from disk if it exists
    logging.info(f"Looking for FAISS index at: {index_path}")
    if os.path.exists(index_path):
        try:
            # Note: allow_dangerous_deserialization is needed for FAISS with pickle.
            # Only load index files from trusted sources.
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
        # Create a placeholder to guide the user
        placeholder = gguf_model_file.parent / "DOWNLOAD_MODEL_HERE.txt"
        gguf_model_file.parent.mkdir(parents=True, exist_ok=True)
        placeholder.write_text(f"Download the GGUF model '{gguf_model_file.name}' and place it in this directory.")
        llm = None
    else:
        try:
            logging.info(f"Loading GGUF model from: {gguf_model_file}")
            llm = LlamaCpp(
                model_path=str(gguf_model_file),
                n_gpu_layers=-1,      # Offload all possible layers to GPU
                n_batch=512,          # Batch size for prompt processing
                n_ctx=2048,           # The context window size
                f16_kv=True,          # Use half-precision for KV cache, saves VRAM
                verbose=False,        # Set to True for detailed LlamaCpp logging
            )
            logging.info("LLM loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load LLM: {e}")
            llm = None