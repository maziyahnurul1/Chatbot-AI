from sqlalchemy import create_engine, text
from db_connection import engine
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text

import os

url = os.getenv("DATABASE_URL")
print(repr(url))

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

