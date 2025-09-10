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
    """Recursively finds all files in the knowledge directory."""
    knowledge_path = Path(KNOWLEDGE_DIR)
    if not knowledge_path.exists():
        knowledge_path.mkdir(parents=True)
    return sorted([p for p in knowledge_path.rglob("*") if p.is_file()], key=os.path.getmtime, reverse=True)

def handle_file_delete(file_path):
    """Deletes a file and forces a full re-index."""
    try:
        os.remove(file_path)
        st.success(f"Deleted {os.path.basename(file_path)}. Re-indexing...")
        with st.spinner("Updating knowledge base... This may take a moment."):
            force_reindex(INDEX_PATH)
            initial_scan_and_index(KNOWLEDGE_DIR, INDEX_PATH)
        st.success("Re-indexing complete!")
        st.rerun()
    except Exception as e:
        st.error(f"Error deleting file: {e}")

# --- UI Layout ---
st.header("Upload New Documents")
uploaded_files = st.file_uploader(
    "Add new files to your knowledge base. Subdirectories are supported.",
    accept_multiple_files=True
)

if uploaded_files:
    new_file_paths = []
    # To preserve subdirectories, we can't use the uploader easily.
    # For now, all uploaded files will be placed in the root of the knowledge directory.
    for uploaded_file in uploaded_files:
        file_path = os.path.join(KNOWLEDGE_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        new_file_paths.append(file_path)
    
    st.success(f"Successfully uploaded {len(uploaded_files)} file(s).")
    with st.spinner("Indexing new documents..."):
        update_vector_store(new_file_paths, INDEX_PATH)
    st.success("Indexing complete!")
    st.rerun()

st.divider()

st.header("Manage Existing Documents")
st.markdown(f"Displaying all files from: `{KNOWLEDGE_DIR}`")

files = get_knowledge_files()

if not files:
    st.info("Your knowledge base is empty. Upload some documents to get started!")
else:
    col1, col2, col3 = st.columns([3, 1, 1])
    col1.subheader("File Path (relative)")
    col2.subheader("Size (KB)")
    col3.subheader("Actions")
    
    st.divider()

    for file_path in files:
        try:
            # Display path relative to the knowledge directory
            relative_path = file_path.relative_to(KNOWLEDGE_DIR)
            file_size = round(file_path.stat().st_size / 1024, 2)

            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Use an expander to show file content without taking too much space
                with st.expander(str(relative_path)):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            st.text(f.read(1000) + ("..." if len(f.read()) > 1000 else ""))
                    except Exception:
                        st.warning("Cannot display preview for this file type (e.g., PDF, DOCX).")

            with col2:
                st.write(f"{file_size} KB")

            with col3:
                if st.button("🗑️ Delete", key=f"delete_{relative_path}"):
                    handle_file_delete(file_path)
        except Exception as e:
            st.error(f"Error processing file {file_path.name}: {e}")
