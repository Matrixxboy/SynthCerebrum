# gui.py
import os
import threading
import logging
import streamlit as st
from pathlib import Path

# Make sure all source files are in a directory named 'src'
from src.database import init_mysql_database, save_interaction
from src.models import initialize_models_and_index
from src.indexing import initial_scan_and_index
from src.ragForGui import answer_query, add_user_knowledge
from src.file_watcher import start_file_watcher_background

# ---------------- CONFIG ----------------
KNOWLEDGE_DIR = "./knowledge"
INDEX_PATH = "faiss_index"
LLM_MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct.Q2_K.gguf"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L3-v2"
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "utsav1424", 
    "database": "synthcerebrum",
    "port": 3306
}
# ---------------------------------------

# Function to inject custom CSS for styling
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Store config in session state to access it from other pages
st.session_state.config = {
    "KNOWLEDGE_DIR": KNOWLEDGE_DIR,
    "INDEX_PATH": INDEX_PATH,
    "LLM_MODEL_PATH": LLM_MODEL_PATH,
    "EMBEDDING_MODEL_NAME": EMBEDDING_MODEL_NAME
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@st.cache_resource
def load_resources():
    """Loads all expensive resources once and caches them."""
    logging.info("--- Initializing all resources ---")
    # Create knowledge directory if it doesn't exist
    Path(KNOWLEDGE_DIR).mkdir(parents=True, exist_ok=True)
    
    try:
        init_mysql_database(MYSQL_CONFIG)
    except Exception as e:
        logging.warning(f"MySQL init failed: {e}. Continuing without database logging.")

    initialize_models_and_index(LLM_MODEL_PATH, EMBEDDING_MODEL_NAME, INDEX_PATH)
    initial_scan_and_index(KNOWLEDGE_DIR, INDEX_PATH)
    start_file_watcher_background(KNOWLEDGE_DIR, INDEX_PATH)
    logging.info("--- All resources initialized ---")
    return True

# Load resources at the start
load_resources()

# ---------------- STREAMLIT UI ----------------
st.set_page_config(
    page_title="SynthCerebrum RAG", 
    page_icon="🧠",
    layout="wide"
)

# Create a style.css file for more advanced styling if you wish
# local_css("style.css") 

st.title("🧠 SynthCerebrum")
st.caption("Your offline AI assistant, powered by local documents.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.info(source)

# Main chat input
if user_question := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            answer, sources = answer_query(user_question.strip(), k=4)
            
            message_placeholder.markdown(answer)
            if sources:
                with st.expander("Sources"):
                    for source in sources:
                        st.info(source)

            st.session_state.current_response = {"question": user_question, "answer": answer, "sources": sources}
            threading.Thread(target=save_interaction, args=(user_question.strip(), answer, sources), daemon=True).start()

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})