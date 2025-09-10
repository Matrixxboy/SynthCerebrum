# pages/3_⚙️_Settings.py
import streamlit as st

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Application Settings")

st.warning("⚠️ Changing settings will cause the application to relaunch and re-initialize all models and resources.")

if st.button("Save and Relaunch Application"):
    # Update session state from the input widgets
    # The keys for widgets are used to retrieve their values
    st.session_state.KNOWLEDGE_DIR = st.session_state.knowledge_dir_input
    st.session_state.INDEX_PATH = st.session_state.index_path_input
    st.session_state.LLM_MODEL_PATH = st.session_state.llm_model_path_input
    st.session_state.EMBEDDING_MODEL_NAME = st.session_state.embedding_model_name_input
    st.session_state.SYSTEM_PROMPT = st.session_state.system_prompt_input
    st.session_state.CHUNK_SIZE = st.session_state.chunk_size_input
    st.session_state.CHUNK_OVERLAP = st.session_state.chunk_overlap_input
    st.session_state.MYSQL_HOST = st.session_state.mysql_host_input
    st.session_state.MYSQL_USER = st.session_state.mysql_user_input
    st.session_state.MYSQL_PASSWORD = st.session_state.mysql_password_input
    st.session_state.MYSQL_DATABASE = st.session_state.mysql_database_input
    st.session_state.MYSQL_PORT = st.session_state.mysql_port_input
    
    # Clear cached resources to force re-initialization
    st.cache_resource.clear()
    st.rerun()

st.divider()

# --- Path Configuration ---
st.header("Path Configuration")
st.text_input(
    "Knowledge Base Path", 
    value=st.session_state.get('KNOWLEDGE_DIR', ''), 
    key="knowledge_dir_input",
    help="The directory containing your source documents."
)
st.text_input(
    "FAISS Index Path", 
    value=st.session_state.get('INDEX_PATH', ''), 
    key="index_path_input",
    help="The directory where the FAISS index will be stored."
)

# --- Model Configuration ---
st.header("Model Configuration")
st.text_input(
    "LLM Model Path", 
    value=st.session_state.get('LLM_MODEL_PATH', ''), 
    key="llm_model_path_input",
    help="Path to the GGUF model file."
)
st.text_input(
    "Embedding Model Name", 
    value=st.session_state.get('EMBEDDING_MODEL_NAME', ''), 
    key="embedding_model_name_input",
    help="Name of the sentence-transformers model for embeddings."
)

# --- Prompt Configuration ---
st.header("Prompt Configuration")
st.text_area(
    "System Prompt", 
    value=st.session_state.get('SYSTEM_PROMPT', ''), 
    key="system_prompt_input",
    height=250,
    help="The system prompt that guides the LLM's behavior."
)

# --- Indexing Configuration ---
st.header("Indexing Configuration")
col1, col2 = st.columns(2)
with col1:
    st.number_input(
        "Chunk Size", 
        min_value=100, 
        max_value=8000, 
        value=st.session_state.get('CHUNK_SIZE', 1000), 
        step=100, 
        key="chunk_size_input",
        help="The size of text chunks for indexing. Larger chunks provide more context but use more resources."
    )
with col2:
    st.number_input(
        "Chunk Overlap", 
        min_value=0, 
        max_value=1000, 
        value=st.session_state.get('CHUNK_OVERLAP', 150), 
        step=10,
        key="chunk_overlap_input",
        help="The number of characters to overlap between chunks to maintain context."
    )

# --- Database Configuration ---
st.header("Database Configuration")
col1, col2, col3 = st.columns(3)
with col1:
    st.text_input("MySQL Host", value=st.session_state.get('MYSQL_HOST', 'localhost'), key="mysql_host_input")
    st.text_input("MySQL User", value=st.session_state.get('MYSQL_USER', 'root'), key="mysql_user_input")
with col2:
    st.text_input("MySQL Password", value=st.session_state.get('MYSQL_PASSWORD', ''), type="password", key="mysql_password_input")
    st.text_input("MySQL Database", value=st.session_state.get('MYSQL_DATABASE', 'synthcerebrum'), key="mysql_database_input")
with col3:
    st.number_input("MySQL Port", min_value=1, max_value=65535, value=st.session_state.get('MYSQL_PORT', 3306), key="mysql_port_input")
