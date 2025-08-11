import streamlit as st
st.set_page_config(page_title="HOHOHO", layout="wide")
import requests
import json
import sys
import os 
from utils.retriever_pipeline import retrieve_documents
from utils.doc_handler import process_documents
from sentence_transformers import CrossEncoder
import torch
from dotenv import load_dotenv, find_dotenv
import re
from zizi import ask_sql
from insert_vector import insert_vector
from db_connection import engine
from sqlalchemy import create_engine
from langchain_community.llms import Ollama
from langchain_community.vectorstores import PGVector
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.document_loaders import TextLoader 
from langchain_text_splitters import CharacterTextSplitter


# Load variabel dari .env
load_dotenv()

if __name__ == "__main__":
    if "streamlit" in sys.argv[0]:
        pass  # Streamlit akan jalan seperti biasa
    # else:
    #     main_cli()

def main():
    st.title("💬 Chatbot")

    question = st.text_input("Masukkan pertanyaan SQL:")

    if question:
        with st.spinner("🔍 Mencari jawaban..."):
            jawaban = ask_sql(question)
            st.markdown("#### 💡 Jawaban:")
            st.markdown(jawaban)  # pakai st.markdown agar tabel markdown tampil rapih

if __name__ == "__main__":
    main()

url = os.getenv("DATABASE_URL")
# print(repr(url))

engine = create_engine("postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/db_payroll")

# Simpan vector
insert_vector(1, [0.1, 0.2, 0.3, 0.4])

# Ambil nilai dari variabel environment
POSTGRES_URI = "postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/db_payroll"


torch.classes.__path__ = [
    os.path.join(torch.__path__[0], torch.classes.__file__)]  # Fix for torch classes not found error
load_dotenv(
    find_dotenv())  # Loads .env file contents into the application based on key-value pairs defined therein, making them accessible via 'os' module functions like os.getenv().

OLLAMA_BASE_URL = "http://10.15.224.10:11434"
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL = "mistral:latest" 
# MODEL = "deepseek r-1:14b"
# MODEL = "llma3:latest"
EMBEDDINGS_MODEL = "nomic-embed-text:latest"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

device = "cuda" if torch.cuda.is_available() else "cpu"

reranker = None  # 🚀 Initialize Cross-Encoder (Reranker) at the global level
try:
    reranker = CrossEncoder(CROSS_ENCODER_MODEL, device=device)
except Exception as e:
    st.error(f"Failed to load CrossEncoder model: {str(e)}")

# Custom CSS
st.markdown("""
    <style>
        .stApp { background-color: #0e1117; }
        h1 { color: #00FF99; text-align: center; }
        .stChatMessage { border-radius: 10px; padding: 10px; margin: 10px 0; }
        .stChatMessage.user { background-color: #e8f0fe; }
        .stChatMessage.assistant { background-color: #d1e7dd; }
        .stButton>button { background-color: #00AAFF; color: white; }
    </style>
""", unsafe_allow_html=True)

# Manage Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "retrieval_pipeline" not in st.session_state:
    st.session_state.retrieval_pipeline = None
if "rag_enabled" not in st.session_state:
    st.session_state.rag_enabled = False
if "documents_loaded" not in st.session_state:
    st.session_state.documents_loaded = False
