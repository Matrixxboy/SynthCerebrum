# pages/2_⚙️_System_Performance.py
import os
import streamlit as st
import psutil
import time
import platform
import torch

st.set_page_config(page_title="System Performance", page_icon="⚙️", layout="wide")
st.title("⚙️ System Performance Monitor")

# Retrieve config from session state
try:
    config = st.session_state.config
except AttributeError:
    st.error("Configuration not loaded. Please start from the main Chat page.")
    st.stop()


# --- System Information ---
st.header("System Information")
col1, col2, col3 = st.columns(3)
col1.metric("Operating System", f"{platform.system()} {platform.release()}")
col2.metric("CPU Architecture", platform.machine())
col3.metric("Total CPU Cores", f"{psutil.cpu_count(logical=False)} Physical, {psutil.cpu_count(logical=True)} Logical")

# --- Model Information ---
st.header("Model Configuration")
col1, col2 = st.columns(2)
col1.info(f"**LLM Model:** `{os.path.basename(config['LLM_MODEL_PATH'])}`")
col2.info(f"**Embedding Model:** `{config['EMBEDDING_MODEL_NAME']}`")


# --- Live Performance Metrics ---
st.header("Live Metrics")
placeholder = st.empty()

# Function to check for CUDA availability and get device name
def get_torch_device():
    if torch.cuda.is_available():
        return f"GPU ({torch.cuda.get_device_name(0)})"
    return "CPU"

# Loop to update metrics
while True:
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    
    with placeholder.container():
        st.subheader("CPU Usage")
        st.progress(int(cpu_percent), text=f"{cpu_percent}%")

        st.subheader("Memory (RAM) Usage")
        st.progress(int(ram_percent), text=f"{ram_percent}% ({ram.used/1e9:.2f} GB / {ram.total/1e9:.2f} GB)")

        st.subheader("Disk Usage (Root)")
        st.progress(int(disk_percent), text=f"{disk_percent}% ({disk.used/1e9:.2f} GB / {disk.total/1e9:.2f} GB)")
        
        st.subheader("PyTorch Device")
        st.success(f"Embeddings and model inference are running on: **{get_torch_device()}**")
        
        time.sleep(1)