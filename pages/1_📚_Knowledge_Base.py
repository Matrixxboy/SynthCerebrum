# pages/1_📚_Knowledge_Base.py
import streamlit as st
import os
from pathlib import Path
from src.indexing import force_reindex, initial_scan_and_index, update_vector_store

st.set_page_config(page_title="Knowledge Base Management", page_icon="📚", layout="wide")
st.title("📚 Knowledge Base Management")

# Check if the main app has been run and session state is initialized
if 'KNOWLEDGE_DIR' not in st.session_state or 'INDEX_PATH' not in st.session_state:
    st.error("Configuration not loaded. Please start from the main Chat page.")
    st.stop()

KNOWLEDGE_DIR = st.session_state.KNOWLEDGE_DIR
INDEX_PATH = st.session_state.INDEX_PATH

# --- Utility Functions ---
def get_knowledge_files():
    """Returns a list of files in the knowledge directory."""
    return [f for f in os.listdir(KNOWLEDGE_DIR) if os.path.isfile(os.path.join(KNOWLEDGE_DIR, f))]

def handle_file_delete(file_path):
    """Deletes a file and forces a full re-index."""
    try:
        os.remove(file_path)
        st.success(f"Deleted {os.path.basename(file_path)}. Re-indexing...")
        with st.spinner("Updating knowledge base... This may take a moment."):
            force_reindex(INDEX_PATH)
            initial_scan_and_index(KNOWLEDGE_DIR, INDEX_PATH)
        st.success("Re-indexing complete!")
    except Exception as e:
        st.error(f"Error deleting file: {e}")

# --- UI Layout ---
st.header("Upload New Documents")
uploaded_files = st.file_uploader(
    "Add new files to your knowledge base (.txt, .md, .pdf, .csv)",
    accept_multiple_files=True,
    type=['txt', 'md', 'pdf', 'csv']
)

if uploaded_files:
    new_file_paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(KNOWLEDGE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        new_file_paths.append(file_path)
    
    st.success(f"Successfully uploaded {len(uploaded_files)} file(s).")
    with st.spinner("Indexing new documents..."):
        update_vector_store(new_file_paths, INDEX_PATH)
    st.success("Indexing complete!")


st.header("Manage Existing Documents")
st.markdown(f"Displaying files from: `{KNOWLEDGE_DIR}`")

files = get_knowledge_files()

if not files:
    st.info("Your knowledge base is empty. Upload some documents to get started!")
else:
    col1, col2, col3 = st.columns([3, 1, 1])
    col1.subheader("File Name")
    col2.subheader("Size (KB)")
    col3.subheader("Actions")
    
    st.divider()

    for file in files:
        file_path = os.path.join(KNOWLEDGE_DIR, file)
        file_size = round(os.path.getsize(file_path) / 1024, 2)

        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            with st.expander(file):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        st.text(f.read())
                except Exception:
                    st.warning("Cannot display content for this file type (e.g., PDF).")

        with col2:
            st.write(f"{file_size} KB")

        with col3:
            if st.button("🗑️ Delete", key=f"delete_{file}"):
                handle_file_delete(file_path)
                st.rerun()