# About SynthCerebrum

SynthCerebrum is a powerful, offline-first AI assistant designed to chat with your local documents. It leverages a Retrieval-Augmented Generation (RAG) architecture to provide answers based on a knowledge base you provide. The entire system runs locally, ensuring your data remains private.

## Core Features

### 1. Chat Interface
- A user-friendly, Streamlit-based interface for asking questions and receiving answers.
- Displays sources for each answer, allowing you to verify the information.

### 2. Comprehensive File Support
- The system can index and learn from a wide variety of file types:
  - **Documents:** `.pdf`, `.docx`, `.md`, `.txt`
  - **Data Files:** `.csv`, `.xlsx`, `.xls`
  - **Code & Config:** `.py`, `.js`, `.java`, `.c`, `.cpp`, `.html`, `.css`, `.json`, `.yaml`, and many more.

### 3. Dynamic Knowledge Base
- **Automatic Updates:** A background file watcher automatically detects any changes (additions, modifications, or deletions) in your knowledge directory and updates the search index in real-time.
- **Manual Control:** A "Forcefully Re-index" button allows you to manually rebuild the entire knowledge base index at any time.
- **Direct Management:** The "Knowledge Base Management" page provides a UI to upload new files or delete existing ones.

### 4. Advanced Session Management
- **Persistent Chats:** All conversations are automatically saved and are available even after restarting the application.
- **Multi-Session Support:** Create unlimited new chat sessions, each with its own independent context and history.
- **Full Control:** Easily switch between, rename, or delete chat sessions directly from the sidebar.

### 5. System Configuration & Monitoring
- **Configurable Paths:** Set the paths for your `knowledge` directory and `faiss_index` directly from the UI. The application will relaunch and load the new configuration.
- **Performance Dashboard:** The "System Performance" page provides a live look at your system's CPU, RAM, and Disk usage, and confirms which device (CPU or GPU) is being used for model inference.

## Methodology & Architecture

SynthCerebrum is built on the principle of Retrieval-Augmented Generation (RAG).

**Workflow:**
1.  **Indexing:** When documents are added to the knowledge base, they are loaded and processed. They are split into smaller chunks of text. Each chunk is then converted into a numerical representation (an embedding) using the `paraphrase-MiniLM-L3-v2` model. These embeddings are stored in a highly efficient FAISS vector index.
2.  **Retrieval:** When you ask a question, your query is also converted into an embedding. The system then performs a similarity search against the FAISS index to find the document chunks with embeddings most similar to your question's embedding.
3.  **Generation:** The top relevant chunks retrieved from the index are combined with your original question and passed as a detailed prompt to the Large Language Model (`Meta-Llama-3-8B-Instruct`). The LLM uses this context to generate a relevant and accurate answer.

**Key Components:**
- **Frontend:** Streamlit
- **Vector Store:** FAISS (Facebook AI Similarity Search)
- **LLM:** `Meta-Llama-3-8B-Instruct.Q2_K.gguf` (via `llama-cpp-python`)
- **Embedding Model:** `sentence-transformers/paraphrase-MiniLM-L3-v2`
- **Document Processing:** LangChain document loaders
- **File Monitoring:** `watchdog` library

## How to Use

1.  **Installation:** Ensure all dependencies are installed by running:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the Application:** Run the following command in your terminal:
    ```bash
    streamlit run PlayGround.py
    ```
3.  **Add Documents:**
    - Place your files into the `knowledge` directory (or any other directory you configure in the UI).
    - Alternatively, use the "Upload New Documents" feature on the "Knowledge Base Management" page.
4.  **Chat:** Start asking questions on the main chat page!

## Project Structure

```
/SynthCerebrum/
├── PlayGround.py             # Main application file (Streamlit UI)
├── pages/
│   ├── 1_📚_Knowledge_Base.py # UI for managing files
│   └── 2_⚙️_System_Performance.py # UI for system metrics
├── src/
│   ├── indexing.py           # Logic for file loading and FAISS indexing
│   ├── file_watcher.py       # Background service to monitor file changes
│   ├── rag.py / ragForGui.py # Core RAG logic (retrieval and generation)
│   └── ...
├── knowledge/                # Default directory for your documents
├── faiss_index/              # Default directory for the FAISS vector index
├── chat_sessions/            # Directory where chat histories are saved
├── requirements.txt          # Project dependencies
└── ABOUT.md                  # This file
```
