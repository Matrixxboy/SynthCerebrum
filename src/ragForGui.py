# src/ragForGui.py
import logging
import time
from pathlib import Path
from typing import List, Tuple, Optional

from src import models
from src.indexing import db_lock, update_vector_store, _ensure_dirs

def _build_prompt(query: str, context: str, system_prompt: str) -> str:
    """Builds a structured prompt for the Llama 3 Instruct model."""
    # Llama 3 Instruct models require a specific format with special tokens.
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

Context:
---
{context if context.strip() else '(No relevant context found)'}
---

Question: {query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    return prompt


def answer_query(query: str, system_prompt: str, k: int = 4) -> Tuple[str, List[str]]:
    """Retrieve top-k docs, generate answer, and return (answer, sources)."""
    if not models.db:
        logging.warning("FAISS index not loaded or empty.")
        return "The knowledge base is not available. I cannot answer questions right now.", []

    with db_lock:
        try:
            docs = models.db.similarity_search(query, k=k)
        except Exception as e:
            logging.error(f"Error during similarity search: {e}")
            return "An error occurred while searching the knowledge base.", []

    context = "\n\n".join(d.page_content for d in docs)
    # Use a set to get unique sources, then convert back to a list
    sources = list(set(d.metadata.get("source", "Unknown") for d in docs))
    prompt = _build_prompt(query, context, system_prompt)

    if not models.llm:
        logging.warning("LLM not loaded. Cannot generate answer.")
        return "The language model is not available, so I cannot generate an answer.", sources


    logging.info("Calling LLM to generate answer...")
    try:
        # Using stop tokens specific to Llama 3 to ensure clean output.
        response_text = models.llm(prompt, max_tokens=1024, stop=["<|eot_id|>", "<|end_of_text|>"])

        return response_text.strip(), sources

    except Exception as e:
        logging.error(f"LLM call failed: {e}")
        return "The language model failed to generate an answer. Please check the logs.", sources


def add_user_knowledge(text: str, knowledge_dir: str, index_path: str, filename: Optional[str] = None) -> str:
    """Save user-provided knowledge as a .txt and update FAISS index."""
    if not text.strip():
        logging.warning("Attempted to add empty content to knowledge base.")
        return ""
        
    _ensure_dirs(knowledge_dir)
    if not filename:
        filename = f"user_added_{int(time.time())}.txt"
    
    path = Path(knowledge_dir) / filename
    path.write_text(text, encoding="utf-8")
    logging.info(f"Saved new knowledge to {path}")

    try:
        update_vector_store([str(path)], index_path)
    except Exception as e:
        logging.error(f"Failed to update vector store after adding user knowledge: {e}")

    return str(path.resolve())