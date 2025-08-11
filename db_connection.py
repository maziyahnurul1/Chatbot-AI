import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
import psycopg2

# Load .env
load_dotenv()

# Ambil variabel dari environment
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Validasi
if not all([user, password, host, port, db_name]):
    raise ValueError("Pastikan semua variabel lingkungan (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME) telah diatur.")

# Bangun URL koneksi
connection_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
print("Connection URL:", repr(connection_url))  # opsional debug

# Buat engine SQLAlchemy
engine = create_engine(connection_url)

# Buat SQLDatabase LangChain
db = SQLDatabase(engine)

# Fungsi koneksi psycopg2
def get_db_connection():
    return psycopg2.connect(
        dbname=db_name,
        user=user,
        password=password,
        host=host,
        port=port
    )

# Fungsi menyimpan & mengambil pesan (boleh tetap seperti yang kamu buat)

def save_message(username, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, message) VALUES (%s, %s)", (username, message))
    conn.commit()
    cursor.close()
    conn.close()

def fetch_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, message FROM users")
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return messages

def chatbot_response(username, user_message):
    save_message(username, user_message)
    messages = fetch_messages()
    last_message = messages[-1] if messages else "No messages yet."
    return f"Hello {username}! Your message '{user_message}' has been saved. Last message: {last_message}"

# Tes koneksi
with engine.connect() as conn:
    print("✅ Berhasil koneksi ke database!")
