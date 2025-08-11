import os
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text
from db_connection import engine
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

url = os.getenv("DATABASE_URL")
print(repr(url))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 1. Membuat koneksi ke database
engine = create_engine('postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/db_payroll')
Session = sessionmaker(bind=engine)
session = Session()

# 2. Mengeksekusi query SELECT untuk memeriksa data menggunakan text()
result = session.execute(text("SELECT embedding_column FROM your_table"))
 

# 3. Mengambil semua hasil query dan mencetaknya
data = result.fetchall()  # Mengambil semua data dari query
print("Hasil query:", data)

# 4. Menutup session setelah operasi selesai
session.close()


from sqlalchemy import create_engine
engine = create_engine("postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/db_payroll")

def insert_vector(id, vec):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO vectors_table (id, embedding)
                VALUES (:id, :vec)
                ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding
            """),
            {"id": id, "vec": vec}
        )
        conn.commit()

# Load model dan buat embedding
model = SentenceTransformer('all-MiniLM-L6-v2')
text_input = "Ini adalah teks untuk diubah jadi vektor"
embedding = model.encode(text_input)

# Simpan ke database
insert_vector(1, embedding.tolist())




