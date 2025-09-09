import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Configuration ---
KNOWLEDGE_DIR = "./knowledge"
INDEX_PATH = "faiss_index"
# Use a smaller model for the PoC to ensure it runs on most systems.
# For better results, use "mistralai/Mistral-7B-Instruct-v0.1" or another powerful model.
LLM_MODEL_NAME = "distilgpt2"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Global Variables ---
db = None
llm = None
embedder = None
text_splitter = None

def initialize_models():
    """Loads all models and initializes the vector store."""
    global db, llm, embedder, text_splitter
    
    logging.info("Initializing models and vector store...")
    
    # 1. Load Embedding Model
    # Using HuggingFaceEmbeddings with LangChain for compatibility.
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    # 2. Load or Create Vector Store (FAISS)
    if os.path.exists(INDEX_PATH):
        logging.info(f"Loading existing FAISS index from {INDEX_PATH}")
        db = FAISS.load_local(INDEX_PATH, embedder, allow_dangerous_deserialization=True)
    else:
        logging.info("Creating new FAISS index.")
        # Create an empty index to start with. It requires some text.
        db = FAISS.from_texts(["initialization"], embedder)
        db.save_local(INDEX_PATH)

    # 3. Load Local LLM
    logging.info(f"Loading LLM: {LLM_MODEL_NAME}")
    # For a more powerful model, you might need device_map="auto" and quantization
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_NAME)
    llm = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=100,
        return_full_text=False # We only want the generated answer
    )
    
    # 4. Initialize Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    logging.info("Initialization complete.")

def update_vector_store(file_path):
    """Reads a file, splits it into chunks, and adds it to the FAISS index."""
    global db
    try:
        logging.info(f"Processing and indexing file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not content.strip():
            logging.warning(f"File {file_path} is empty. Skipping.")
            return

        chunks = text_splitter.split_text(content)
        db.add_texts(chunks)
        db.save_local(INDEX_PATH)
        logging.info(f"Successfully indexed {len(chunks)} chunks from {file_path}")

    except Exception as e:
        logging.error(f"Failed to process file {file_path}: {e}")

def initial_scan_and_index():
    """Scans the knowledge directory and indexes all existing .txt files."""
    logging.info(f"Performing initial scan of '{KNOWLEDGE_DIR}'...")
    if not os.path.exists(KNOWLEDGE_DIR):
        os.makedirs(KNOWLEDGE_DIR)
        logging.info(f"Created knowledge directory: {KNOWLEDGE_DIR}")
        # Create a sample file for demonstration
        with open(os.path.join(KNOWLEDGE_DIR, "sample.txt"), "w") as f:
            f.write("Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation. It was created by Guido van Rossum.")

    for filename in os.listdir(KNOWLEDGE_DIR):
        if filename.endswith(".txt"):
            file_path = os.path.join(KNOWLEDGE_DIR, filename)
            update_vector_store(file_path)

class KnowledgeFolderHandler(FileSystemEventHandler):
    """Handles file system events in the knowledge directory."""
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            logging.info(f"New file detected: {event.src_path}")
            update_vector_store(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            logging.info(f"File modified: {event.src_path}")
            # For simplicity, we re-index the whole file.
            # A more advanced approach would update specific chunks.
            update_vector_store(event.src_path)

def start_file_watcher():
    """Starts the watchdog observer to monitor the knowledge folder."""
    event_handler = KnowledgeFolderHandler()
    observer = Observer()
    observer.schedule(event_handler, KNOWLEDGE_DIR, recursive=False)
    observer.start()
    logging.info(f"Watching directory: {KNOWLEDGE_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def answer_query(query):
    """Answers a user query using the RAG pipeline."""
    global db, llm
    
    logging.info(f"Received query: '{query}'")
    
    # 1. Retrieve relevant documents
    docs = db.similarity_search(query, k=3)
    context = "\n".join([d.page_content for d in docs])
    
    # 2. Construct the strict prompt
    prompt = f"""Use ONLY the following context to answer the question. Do not use any external knowledge. If the information is not in the context, respond with "I cannot answer this question based on the provided information."

Context:
---
{context}
---

Question: {query}

Answer:"""

    # 3. Generate the answer
    logging.info("Generating answer from LLM...")
    response = llm(prompt)
    
    print("\n--- Answer ---")
    print(response[0]['generated_text'].strip())
    print("--------------\n")


if __name__ == "__main__":
    initialize_models()
    initial_scan_and_index()
    
    # --- Interactive Query Loop ---
    # The file watcher would run in a separate thread in a real application.
    # For this PoC, we run an interactive loop first.
    
    print("\n\n--- Offline AI Query System Ready ---")
    print("You can now add or modify .txt files in the './knowledge' folder.")
    print("The system will index them automatically (check logs).")
    print("Enter a query below or type 'exit' to quit.")
    
    # Example queries to try:
    # Who created Python?
    # What is the design philosophy of Python?
    
    while True:
        user_query = input("Enter your query: ")
        if user_query.lower() == 'exit':
            break
        answer_query(user_query)
        
    # You can uncomment the line below to run the file watcher indefinitely
    # start_file_watcher()
