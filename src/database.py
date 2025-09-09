import logging
import json
from getpass import getpass
from typing import List, Optional

from typing import Optional
import mysql.connector

mysql_conn: Optional[mysql.connector.connection.MySQLConnection] = None


def init_mysql_database(cfg: dict):
    """
    Connects to MySQL, creates database + tables if not exist.
    Tables:
      - interactions(id, user_query, answer, context_snippet, sources_json, created_at)
      - knowledge_files(id, file_path, added_at)
    """
    global mysql_conn
    pwd = cfg.get("password") or ""
    if not pwd:
        # ask interactively if not set (safer)
        try:
            pwd = getpass(prompt="MySQL password (press Enter for none): ")
        except Exception:
            pwd = ""
    cfg_copy = cfg.copy()
    cfg_copy["password"] = pwd

    # First connect without database to create it if needed
    tmp_cfg = cfg_copy.copy()
    dbname = tmp_cfg.pop("database", None)
    try:
        conn = mysql.connector.connect(**tmp_cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET 'utf8mb4'")
        conn.close()
    except mysql.connector.Error as err:
        logging.error(f"MySQL error while creating database: {err}")
        raise

    # Now connect to the database
    try:
        conn = mysql.connector.connect(**cfg_copy)
        mysql_conn = conn
        cursor = conn.cursor()
        # interactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_query TEXT NOT NULL,
                answer LONGTEXT,
                context_snippet LONGTEXT,
                sources_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
        )
        # knowledge_files table (record of files added/learned)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_files (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                file_path VARCHAR(1024) NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
        )
        conn.commit()
        logging.info("MySQL initialized and tables are ready.")
    except mysql.connector.Error as err:
        logging.error(f"MySQL connection error: {err}")
        raise


def save_interaction(user_query: str, answer: str, sources: List[str]):
    """Save a Q/A interaction to MySQL (non-blocking best-effort)."""
    global mysql_conn
    try:
        if mysql_conn is None:
            logging.debug("MySQL connection not set; skipping save_interaction.")
            return
        cursor = mysql_conn.cursor()
        sources_json = json.dumps(sources, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO interactions (user_query, answer, context_snippet, sources_json) VALUES (%s,%s,%s,%s)",
            (user_query, answer, "" if not sources else "\n".join(sources[:5]), sources_json),
        )
        mysql_conn.commit()
    except Exception as e:
        logging.exception(f"Failed to save interaction to MySQL: {e}")


def save_knowledge_file_record(file_path: str):
    global mysql_conn
    try:
        if mysql_conn is None:
            return
        cursor = mysql_conn.cursor()
        cursor.execute("INSERT INTO knowledge_files (file_path) VALUES (%s)", (file_path,))
        mysql_conn.commit()
    except Exception:
        logging.exception("Failed to save knowledge file record.")
