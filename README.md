# 🧠 SynthCerebrum

SynthCerebrum is a fully offline, local RAG (Retrieval-Augmented Generation) application. It allows you to chat with your own documents using a powerful language model, manage your knowledge base, and monitor system performance through a clean, multi-page web interface.

-----

##  Features

  * **🧠 Interactive Chat UI**: A clean, conversational interface to ask questions about your documents.
  * **📚 Knowledge Base Management**: A built-in dashboard to upload, view, and delete documents from your knowledge folder.
  * **⚙️ Live Performance Monitoring**: A real-time view of your system's CPU, Memory (RAM), and Disk usage to see the application's impact.
  * **🔒 Fully Offline & Private**: All models and documents are processed locally on your machine. Nothing is sent to the cloud.
  * **🔄 Automatic Updates**: The system automatically watches your knowledge folder for new or changed files and updates the index in the background.
  * **🤖 Powerful LLM Support**: Built to use state-of-the-art GGUF models like Llama 3 for high-quality responses.

-----

##  Tech Stack

  * **Backend**: Python
  * **Web Framework**: Streamlit
  * **LLM Serving**: `llama-cpp-python`
  * **Vector Database**: FAISS (Facebook AI Similarity Search)
  * **Embeddings**: `sentence-transformers`
  * **Orchestration**: `langchain`
  * **System Monitoring**: `psutil`
  * **Database**: MySQL (for logging interactions)

-----

##  🚀 Installation and Setup

Follow these steps to get SynthCerebrum running on your local machine.

###  Prerequisites

Make sure you have the following installed on your system:

  * **Python** 3.10 or newer
  * **Git** for cloning the repository
  * A running **MySQL Server** instance

###  Step 1: Clone the Repository

Open your terminal and clone the project repository:

```bash
git clone https://github.com/your-username/SynthCerebrum.git
cd SynthCerebrum
```

###  Step 2: Set Up Python Environment & Install Dependencies

It is highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv .venv

# Activate the environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

You will need a `requirements.txt` file. Create one with the following content:

```txt
# requirements.txt
streamlit
psutil
langchain-community
langchain-huggingface
faiss-cpu
sentence-transformers
pypdf
mysql-connector-python
torch
pandas
numpy
altair
llama-cpp-python
```

###  Step 3: Download the LLM Model

The application requires a model in GGUF format.

1.  Create a folder named `models` in the main project directory.
2.  Download the recommended model: **Meta-Llama-3-8B-Instruct.Q2\_K.gguf**. You can find it on [Hugging Face by unsloth](https://www.google.com/search?q=https://huggingface.co/unsloth/Meta-Llama-3-8B-Instruct-GGUF).
3.  Place the downloaded `.gguf` file inside the `models` folder. The final path should be: `models/Meta-Llama-3-8B-Instruct.Q2_K.gguf`.

###  Step 4: Configure the MySQL Database

1.  Connect to your local MySQL server.

2.  Create a database for the application to store conversation history.

    ```sql
    CREATE DATABASE synthcerebrum;
    ```

3.  Open the `PlayGround.py` file and update the `MYSQL_CONFIG` dictionary with your MySQL username and password.

    ```python
    # in PlayGround.py
    MYSQL_CONFIG = {
        "host": "localhost",
        "user": "your_mysql_username", # e.g., "root"
        "password": "your_mysql_password", 
        "database": "synthcerebrum",
        "port": 3306
    }
    ```

    **Note**: For security, avoid hardcoding credentials in production. Use environment variables instead.

-----

##  💻 Usage

###  Running the Application

1.  Make sure your virtual environment is activated.
2.  Run the following command in your terminal:
    ```bash
    python -m streamlit run PlayGround.py
    ```
3.  Your web browser should open with the application running, typically at `http://localhost:8501`.

### How to Use the App

  * **Chat Page**: The main page where you can ask questions. Your conversation history will be displayed here.
  * **Knowledge Base Page**: Navigate to this page using the sidebar. Here you can upload new `.txt`, `.md`, `.pdf`, or `.csv` files. You can also view the content of existing files or delete them. The vector index will be updated automatically.
  * **System Performance Page**: This page shows a live feed of your CPU and RAM usage, helping you understand the resource impact of the application.

-----

##  🔧 Configuration

All major configurations are at the top of the `PlayGround.py` file.

  * `KNOWLEDGE_DIR`: The path to the folder containing your documents.
  * `LLM_MODEL_PATH`: The local path to your downloaded GGUF model file.
  * `EMBEDDING_MODEL_NAME`: The Hugging Face model to use for generating embeddings. If you change this, **you must delete the `faiss_index` folder** to force a re-index with the new model.
  * `MYSQL_CONFIG`: Your database connection details.

-----

##  ❓ Troubleshooting

  * **PermissionError**: If you see a permission error when the app tries to create a folder, ensure the path in your config (e.g., `LLM_MODEL_PATH`) is a **relative path** (like `models/model.gguf`) and not an **absolute path** (like `/models/model.gguf`).
  * **AssertionError: `d == self.d`**: This means you changed the `EMBEDDING_MODEL_NAME` without deleting the old index. **Delete the `faiss_index` folder** and restart the app.
  * **CUDA Initialization Warning**: If you don't have an NVIDIA GPU or your drivers are outdated, you may see a CUDA warning. The app will safely fall back to using your CPU. For better performance, ensure your NVIDIA drivers are up to date.