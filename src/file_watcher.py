import logging
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.indexing import update_vector_store, force_reindex, initial_scan_and_index

class KnowledgeFolderHandler(FileSystemEventHandler):
    def __init__(self, knowledge_dir, index_path):
        self.index_path = index_path
        self.knowledge_dir = knowledge_dir

    def on_created(self, event):
        if not event.is_directory:
            logging.info(f"Detected new file: {event.src_path}")
            update_vector_store([event.src_path], self.index_path)

    def on_modified(self, event):
        if not event.is_directory:
            logging.info(f"Detected modified file: {event.src_path}")
            # For simplicity, re-indexing on modification.
            # A more advanced approach would be to remove old vectors and add new ones.
            force_reindex(self.index_path)
            initial_scan_and_index(self.knowledge_dir, self.index_path)
            
    def on_deleted(self, event):
        if not event.is_directory:
            logging.info(f"Detected deleted file: {event.src_path}")
            # Rebuild the entire index from scratch
            force_reindex(self.index_path)
            initial_scan_and_index(self.knowledge_dir, self.index_path)


def start_file_watcher_background(knowledge_dir, index_path):
    handler = KnowledgeFolderHandler(knowledge_dir, index_path)
    observer = Observer()
    observer.schedule(handler, knowledge_dir, recursive=True) # Recursive to watch subdirectories
    observer.start()
    logging.info("Started file watcher in background thread.")
    # run in its own daemon thread so it exits with program
    def _observe_loop():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    t = threading.Thread(target=_observe_loop, daemon=True)
    t.start()
    return observer
