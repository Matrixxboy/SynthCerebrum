import os
import logging
import torch
from pathlib import Path
from typing import Optional
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

# Globals
db: Optional[FAISS] = None
llm = None
embedder: Optional[HuggingFaceEmbeddings] = None
text_splitter: Optional[RecursiveCharacterTextSplitter] = None
llm_is_seq2seq: bool = False
llm_pipeline_task: str = "text2text-generation"

def initialize_models(llm_model_name, embedding_model_name, index_path):
    """Load embedder, load or create FAISS, load LLM pipeline, and setup text splitter."""
    global db, llm, embedder, text_splitter, llm_is_seq2seq, llm_pipeline_task

    logging.info("Initializing embedder and text splitter...")
    embedder = HuggingFaceEmbeddings(model_name=embedding_model_name)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    logging.info("Loading FAISS index if exists...")
    if os.path.exists(index_path):
        try:
            db = FAISS.load_local(index_path, embedder, allow_dangerous_deserialization=True)
            logging.info("Loaded FAISS index from disk.")
        except Exception:
            logging.exception("Failed to load FAISS index. A new index will be created when indexing content.")
            db = None
    else:
        db = None
        logging.info("No FAISS index on disk yet.")

    # ---------------- LOCAL MODEL LOADING ----------------
    # Always look for models inside ./models/<model-name>
    local_model_path = Path("./models") / llm_model_name.replace("/", "--")
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
        logging.info(f"Local model path not found, downloading from HuggingFace: {llm_model_name}")
        config = AutoConfig.from_pretrained(llm_model_name)
        tokenizer = AutoTokenizer.from_pretrained(llm_model_name)
        if getattr(config, "is_encoder_decoder", False):
            llm_is_seq2seq = True
            model = AutoModelForSeq2SeqLM.from_pretrained(llm_model_name, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text2text-generation"
        else:
            llm_is_seq2seq = False
            model = AutoModelForCausalLM.from_pretrained(llm_model_name, device_map="auto", dtype=torch.float16)
            llm_pipeline_task = "text-generation"
        # Save locally for future use
        Path(local_model_path).mkdir(parents=True, exist_ok=True)
        model.save_pretrained(local_model_path)
        tokenizer.save_pretrained(local_model_path)
        config.save_pretrained(local_model_path)

    llm = pipeline(llm_pipeline_task, model=model, tokenizer=tokenizer, max_new_tokens=256)
    logging.info(f"LLM pipeline ready ({llm_pipeline_task}).")
