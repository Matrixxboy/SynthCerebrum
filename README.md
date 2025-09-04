# SynthCerebrum
SynthCerebrum is a fully offline, AI-powered assistant that reads and learns from all types of local files. Using advanced neural networks, embeddings, and RAG, it intelligently retrieves, synthesizes, and generates insights from your data, making your folder a brain-like knowledge hub.
Perfect! Let’s **design a smaller, scalable version of SynthCerebrum** using SQL for now. We’ll build a **modular foundation**, so it can later grow into the full advanced offline AI system with RAG, GANs, GNNs, etc.

Here’s a **step-by-step plan**:

---

## **Project Goal (Mini Version)**

* Read all files in a target folder.
* Split files into **text chunks**.
* Store chunks in a **SQL database** (SQLite / MySQL / PostgreSQL).
* Store **file metadata and path** to detect new files.
* Store **chunk IDs separately** for future reference.
* Ensure **incremental processing** (process only new files).

---

## **Step 1: Database Design**

### **Tables**

1. **files** – Track file metadata
   \| Column        | Type        | Description |
   \|---------------|------------|-------------|
   \| id            | INTEGER PK | Unique file ID |
   \| path          | TEXT       | Full file path |
   \| filename      | TEXT       | File name |
   \| last\_modified | DATETIME   | File last modified |
   \| processed     | BOOLEAN    | If file is already chunked |

2. **chunks** – Store text chunks
   \| Column   | Type        | Description |
   \|----------|------------|-------------|
   \| id       | INTEGER PK | Unique chunk ID |
   \| file\_id  | INTEGER FK | File it belongs to |
   \| chunk    | TEXT       | Text content |
   \| chunk\_num| INTEGER    | Chunk order in file |

3. **embeddings (optional)** – For future RAG
   \| Column   | Type        | Description |
   \|----------|------------|-------------|
   \| id       | INTEGER PK | Chunk ID reference |
   \| vector   | BLOB       | Embedding vector (for AI retrieval) |

---

## **Step 2: File Reader & Chunker**

* Read all file types you want (TXT, PDF, DOCX, CSV).
* Convert to text.
* Split text into chunks (e.g., 500–1000 characters).

**Example:**

```python
from pathlib import Path
import sqlite3
import PyPDF2, docx

DB_PATH = "synthcerebrum.db"
CHUNK_SIZE = 500  # characters

# Connect to SQL
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute("""
CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,
    filename TEXT,
    last_modified DATETIME,
    processed BOOLEAN
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS chunks(
    id INTEGER PRIMARY KEY,
    file_id INTEGER,
    chunk TEXT,
    chunk_num INTEGER
)
""")
conn.commit()

# File reading
def read_file(file_path):
    ext = file_path.suffix.lower()
    if ext == ".txt":
        return file_path.read_text()
    elif ext == ".pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() for page in reader.pages)
    elif ext == ".docx":
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# Chunking
def chunk_text(text, size=CHUNK_SIZE):
    return [text[i:i+size] for i in range(0, len(text), size)]

# Process folder
def process_folder(folder_path):
    folder = Path(folder_path)
    for file in folder.rglob("*"):
        text = read_file(file)
        if text:
            # Check if file already processed
            c.execute("SELECT id, last_modified FROM files WHERE path=?", (str(file),))
            row = c.fetchone()
            if row and row[1] == file.stat().st_mtime:
                continue  # already processed

            # Insert file metadata
            c.execute("INSERT OR REPLACE INTO files(path, filename, last_modified, processed) VALUES(?,?,?,?)",
                      (str(file), file.name, file.stat().st_mtime, True))
            file_id = c.lastrowid

            # Insert chunks
            for idx, chunk in enumerate(chunk_text(text)):
                c.execute("INSERT INTO chunks(file_id, chunk, chunk_num) VALUES(?,?,?)",
                          (file_id, chunk, idx))
    conn.commit()
```

---

## **Step 3: Key Features**

* **Incremental Processing:** Only new/modified files are processed.
* **Chunk ID Tracking:** Each chunk has its own ID for future retrieval.
* **File Metadata:** Allows fast checking of processed files.
* **SQL Storage:** Simple, lightweight, scalable.

---

## **Step 4: Future Enhancements**

* **Add Embeddings Table:** Store embeddings for RAG.
* **Integrate Ollama:** Use chunks + embeddings for query answering.
* **Multi-Modal Support:** Process images, audio, code files later.
* **Feedback & Learning:** Mark chunks as “important” or “frequently used.”

---

This **mini project** gives you a **working offline AI-ready pipeline**: folder → chunks → SQL → ready for AI retrieval.

---

If you want, I can **write the next version** where we **add embeddings + RAG + Ollama integration**, keeping all SQL storage intact.

Do you want me to do that next?
