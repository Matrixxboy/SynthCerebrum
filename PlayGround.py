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
from src.ragForGui import answer_query, add_user_knowledge
from src.file_watcher import start_file_watcher_background

# ---------------- CONFIG ----------------
SESSIONS_DIR = "chat_sessions"

# --- Default values ---
# Use session state to store all configuration. This makes it accessible across pages.
if 'KNOWLEDGE_DIR' not in st.session_state:
    st.session_state.KNOWLEDGE_DIR = "./knowledge"
if 'INDEX_PATH' not in st.session_state:
    st.session_state.INDEX_PATH = "faiss_index"
if 'LLM_MODEL_PATH' not in st.session_state:
    st.session_state.LLM_MODEL_PATH = "./models/Meta-Llama-3-8B-Instruct.Q2_K.gguf"
if 'EMBEDDING_MODEL_NAME' not in st.session_state:
    st.session_state.EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L3-v2"

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "utsav1424", 
    "database": "synthcerebrum",
    "port": 3306
}
# ---------------------------------------

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
def load_resources(knowledge_dir: str, index_path: str, llm_path: str, embed_model: str):
    """Loads all expensive resources once and caches them."""
    logging.info(f"--- Initializing all resources for KNOWLEDGE_DIR: {knowledge_dir} ---")
    Path(knowledge_dir).mkdir(parents=True, exist_ok=True)
    try:
        init_mysql_database(MYSQL_CONFIG)
    except Exception as e:
        logging.warning(f"MySQL init failed: {e}. Continuing without database logging.")
    initialize_models_and_index(llm_path, embed_model, index_path)
    initial_scan_and_index(knowledge_dir, index_path)
    start_file_watcher_background(knowledge_dir, index_path)
    logging.info("--- All resources initialized ---")
    return True

load_resources(
    st.session_state.KNOWLEDGE_DIR, 
    st.session_state.INDEX_PATH, 
    st.session_state.LLM_MODEL_PATH, 
    st.session_state.EMBEDDING_MODEL_NAME
)

# Initialize session state
if 'sessions' not in st.session_state:
    st.session_state.sessions = get_sorted_sessions()

if 'current_session' not in st.session_state or not st.session_state.current_session.exists():
    sessions = get_sorted_sessions()
    if sessions:
        st.session_state.current_session = sessions[0]
    else:
        # This will create a new session and rerun
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

    st.header("Path Configuration")
    new_knowledge_dir = st.text_input("Knowledge Base Path", value=st.session_state.KNOWLEDGE_DIR)
    new_index_path = st.text_input("Index Path", value=st.session_state.INDEX_PATH)

    if st.button("Apply and Relaunch"):
        st.session_state.KNOWLEDGE_DIR = new_knowledge_dir
        st.session_state.INDEX_PATH = new_index_path
        st.cache_resource.clear()
        st.rerun()

# --- MAIN CHAT INTERFACE --- 
st.title("🧠 SynthCerebrum")
st.caption("Your offline AI assistant, powered by local documents.")

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
    save_chat_history(st.session_state.current_session, st.session_state.messages)
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
            
            assistant_message = {"role": "assistant", "content": answer, "sources": sources}
            st.session_state.messages.append(assistant_message)
            save_chat_history(st.session_state.current_session, st.session_state.messages)
