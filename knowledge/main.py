# main.py
from src.Processes.file_processor import process_folder
from src.query_ai import answer_question
from src.Database.database import setup_database
from src.Database.connection import get_connection

if __name__ == "__main__":
    setup_database()
    folder_path = "./TestDataFolder" 
    process_folder(folder_path)

    # Example query
    user_input = "what's inside dummy.pdf"
    conn = get_connection()
    answer = answer_question(user_input, conn)
    conn.close()
    print("AI Answer:", answer)
