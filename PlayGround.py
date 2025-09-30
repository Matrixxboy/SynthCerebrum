# gui.py
import os
import re
import threading
import logging
import streamlit as st
from pathlib import Path
import json
from datetime import datetime

# Make sure all source files are in a directory named 'src'
from src.database import init_mysql_database, save_interaction
from src.models import initialize_models_and_index
from src.indexing import initial_scan_and_index, force_reindex
from src.ragForGui import answer_query
from src.file_watcher import start_file_watcher_background

# ---------------------------------------
# --- App Configuration & Initialization ---
# ---------------------------------------

SESSIONS_DIR = "chat_sessions"

# Set default values in session_state. This makes them accessible across all pages.
if 'KNOWLEDGE_DIR' not in st.session_state:
    st.session_state.KNOWLEDGE_DIR = "./knowledge"
if 'INDEX_PATH' not in st.session_state:
    st.session_state.INDEX_PATH = "faiss_index"
if 'LLM_MODEL_PATH' not in st.session_state:
    st.session_state.LLM_MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct.Q2_K.gguf"
if 'EMBEDDING_MODEL_NAME' not in st.session_state:
    st.session_state.EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L3-v2"
if 'SYSTEM_PROMPT' not in st.session_state:
    st.session_state.SYSTEM_PROMPT = (
        "You are an expert information extractor. Your sole task is to analyze the user's question and the provided context. "
        "Extract the relevant information from the context and present it clearly and concisely. "
        "If the user asks for a list, provide a bulleted list. "
        "Your answer must be based ONLY on the provided context. Do not use any external knowledge. "
        "If the context does not contain the answer, state that you cannot answer based on the provided information."
    )
if 'CHUNK_SIZE' not in st.session_state:
    st.session_state.CHUNK_SIZE = 1000
if 'CHUNK_OVERLAP' not in st.session_state:
    st.session_state.CHUNK_OVERLAP = 150
if 'MYSQL_HOST' not in st.session_state:
    st.session_state.MYSQL_HOST = "localhost"
if 'MYSQL_USER' not in st.session_state:
    st.session_state.MYSQL_USER = "root"
if 'MYSQL_PASSWORD' not in st.session_state:
    st.session_state.MYSQL_PASSWORD = "utsav1424"
if 'MYSQL_DATABASE' not in st.session_state:
    st.session_state.MYSQL_DATABASE = "synthcerebrum"
if 'MYSQL_PORT' not in st.session_state:
    st.session_state.MYSQL_PORT = 3306


# --- SESSION MANAGEMENT FUNCTIONS ---
def get_sorted_sessions():
    """Gets a list of session files sorted by modification time (newest first)."""
    Path(SESSIONS_DIR).mkdir(exist_ok=True)
    files = Path(SESSIONS_DIR).glob("*.json")
    return sorted(files, key=os.path.getmtime, reverse=True)

def load_chat_history(session_path):
    """Loads chat history from a session file."""
    if session_path.exists():
        with open(session_path, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(session_path, messages):
    """Saves chat history to a session file."""
    Path(SESSIONS_DIR).mkdir(exist_ok=True)
    with open(session_path, 'w') as f:
        json.dump(messages, f, indent=4)

def create_new_session():
    """Creates a new chat session and switches to it."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    new_session_path = Path(SESSIONS_DIR) / f"session_{timestamp}.json"
    st.session_state.messages = []
    save_chat_history(new_session_path, [])
    st.session_state.current_session = new_session_path
    st.session_state.renaming_session = None
    st.rerun()

def switch_session(session_path):
    """Switches to a different chat session."""
    st.session_state.current_session = session_path
    st.session_state.messages = load_chat_history(session_path)
    st.session_state.renaming_session = None

def rename_session(old_path, new_name):
    """Renames a session file."""
    if not new_name.endswith('.json'):
        new_name += '.json'
    new_path = old_path.parent / new_name
    if new_path.exists():
        st.error("A session with this name already exists.")
        return
    os.rename(old_path, new_path)
    st.session_state.current_session = new_path
    st.session_state.renaming_session = None
    st.rerun()

def delete_session(session_path):
    """Deletes a session file."""
    os.remove(session_path)
    st.session_state.renaming_session = None
    sessions = get_sorted_sessions()
    if not sessions:
        create_new_session()
    else:
        switch_session(sessions[0])
    st.rerun()


# --- INITIALIZATION ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

@st.cache_resource
def load_resources(knowledge_dir, index_path, llm_model_path, embedding_model_name, chunk_size, chunk_overlap, mysql_host, mysql_user, mysql_password, mysql_database, mysql_port):
    """Loads all expensive resources once and caches them."""
    logging.info(f"--- Initializing all resources for KNOWLEDGE_DIR: {knowledge_dir} ---")
    Path(knowledge_dir).mkdir(parents=True, exist_ok=True)
    
    mysql_config = {
        "host": mysql_host,
        "user": mysql_user,
        "password": mysql_password,
        "database": mysql_database,
        "port": mysql_port
    }

    try:
        init_mysql_database(mysql_config)
    except Exception as e:
        logging.warning(f"MySQL init failed: {e}. Continuing without database logging.")
    
    models_initialized = initialize_models_and_index(
        llm_model_path=llm_model_path, 
        embedding_model_name=embedding_model_name, 
        index_path=index_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    if not models_initialized:
        st.error("Failed to initialize models. The application cannot continue.")
        st.stop()
    
    initial_scan_and_index(knowledge_dir, index_path)
    start_file_watcher_background(knowledge_dir, index_path)
    logging.info("--- All resources initialized ---")
    return True

# Load all resources once at the start of the app
load_resources(
    st.session_state.KNOWLEDGE_DIR,
    st.session_state.INDEX_PATH,
    st.session_state.LLM_MODEL_PATH,
    st.session_state.EMBEDDING_MODEL_NAME,
    st.session_state.CHUNK_SIZE,
    st.session_state.CHUNK_OVERLAP,
    st.session_state.MYSQL_HOST,
    st.session_state.MYSQL_USER,
    st.session_state.MYSQL_PASSWORD,
    st.session_state.MYSQL_DATABASE,
    st.session_state.MYSQL_PORT
)

# Initialize session state for chat
if 'sessions' not in st.session_state:
    st.session_state.sessions = get_sorted_sessions()

if 'current_session' not in st.session_state or not st.session_state.current_session.exists():
    sessions = get_sorted_sessions()
    if sessions:
        st.session_state.current_session = sessions[0]
    else:
        if 'creating_new' not in st.session_state:
            st.session_state.creating_new = True
            create_new_session()

if 'messages' not in st.session_state:
    st.session_state.messages = load_chat_history(st.session_state.current_session)

if 'renaming_session' not in st.session_state:
    st.session_state.renaming_session = None

# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="SynthCerebrum RAG", page_icon="🧠", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Chat Sessions")
    if st.button("➕ New Chat"):
        create_new_session()

    st.session_state.sessions = get_sorted_sessions() # Refresh session list
    
    for session in st.session_state.sessions:
        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        session_name = session.stem
        with col1:
            if session == st.session_state.current_session:
                st.markdown(f"**> {session_name}**")
            else:
                if st.button(session_name, key=f"switch_{session.name}"):
                    switch_session(session)
                    st.rerun()
        with col2:
            if st.button("✏️", key=f"rename_{session.name}"):
                st.session_state.renaming_session = session
                st.rerun()
        with col3:
            if st.button("🗑️", key=f"delete_{session.name}"):
                delete_session(session)

    if st.session_state.renaming_session:
        st.header("Rename Session")
        new_name = st.text_input("New name", value=st.session_state.renaming_session.stem)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save"):
                rename_session(st.session_state.renaming_session, new_name)
        with col2:
            if st.button("Cancel"):
                st.session_state.renaming_session = None
                st.rerun()

    st.divider()
    st.header("Admin Controls")
    if st.button("Forcefully Re-index Knowledge Base"):
        with st.spinner("Deleting old index and re-indexing all files..."):
            force_reindex(st.session_state.INDEX_PATH)
            initial_scan_and_index(st.session_state.KNOWLEDGE_DIR, st.session_state.INDEX_PATH)
        st.success("Re-indexing complete!")

# --- MAIN CHAT INTERFACE ---
st.title("🧠 SynthCerebrum")
st.caption("Your offline AI assistant, powered by local documents.")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and "sources" in message and message["sources"]:
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.info(source)

# Main chat input
if user_question := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": user_question})
    save_chat_history(st.session_state.current_session, st.session_state.messages)
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            answer, sources = answer_query(user_question.strip(), st.session_state.SYSTEM_PROMPT, k=4)
            
            message_placeholder.markdown(answer)
            if sources:
                with st.expander("Sources"):
                    for source in sources:
                        st.info(source)

            st.session_state.current_response = {"question": user_question, "answer": answer, "sources": sources}
            threading.Thread(target=save_interaction, args=(user_question.strip(), answer, sources), daemon=True).start()
            
            assistant_message = {"role": "assistant", "content": answer, "sources": sources}
            st.session_state.messages.append(assistant_message)
            save_chat_history(st.session_state.current_session, st.session_state.messages)
