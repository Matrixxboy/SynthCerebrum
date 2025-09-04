import logging
import time
from pathlib import Path
from typing import List, Optional

from src import models
from src.indexing import db_lock, update_vector_store, _ensure_dirs

def _build_prompt(query: str, context: str) -> str:
    base = (
        "Use ONLY the following context to answer the question. "
        "If the answer is not in the context, reply exactly: "
        "\"I cannot answer this question based on the provided information.\""
    )
    prompt = f"""{base}\n\nContext:\n---\n{context if context.strip() else '(no relevant context found)'}\n---\n\nQuestion: {query}\n\nAnswer: """
    return prompt


def answer_query(query: str, k: int = 4) -> (str, List[str]):
    """Retrieve top-k docs, generate answer and return (answer, sources)."""
    if models.db is None:
        logging.warning("Index empty. Cannot perform similarity search.")
        return "I cannot answer this question based on the provided information.", []

    with db_lock:
        docs = models.db.similarity_search(query, k=k)
    context = "\n\n".join(d.page_content for d in docs) if docs else ""
    sources = [getattr(d, "metadata", {}).get("source", "") or d.page_content[:200] for d in docs]
    prompt = _build_prompt(query, context)

    logging.info("Calling LLM...")
    resp = models.llm(prompt)
    # pipeline returns list of dicts with 'generated_text'
    gen = resp[0].get("generated_text", "").strip() if resp else ""
    if not gen:
        gen = "I cannot answer this question based on the provided information."
    return gen, sources


def add_user_knowledge(text: str, knowledge_dir: str, index_path: str, filename: Optional[str] = None) -> str:
    """
    Save the user-provided correction or new knowledge as a .txt in knowledge folder and index it.
    Returns file path.
    """
    _ensure_dirs(knowledge_dir)
    if not filename:
        filename = f"user_added_{int(time.time())}.txt"
    path = Path(knowledge_dir) / filename
    path.write_text(text, encoding="utf-8")
    update_vector_store(str(path), index_path)
    return str(path.resolve())