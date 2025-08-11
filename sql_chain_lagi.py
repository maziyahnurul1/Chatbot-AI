# sql_chain.py
import os
import psycopg2

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, inspect

# # Koneksi ke PostgreSQL
conn = psycopg2.connect(
    dbname="northwind", 
    user="postgres", 
    password="maziyahcantik", 
    host="localhost", 
    port="5432"
)

# Membuat cursor dan menjalankan query
cur = conn.cursor()
cur.execute("SELECT * FROM employees LIMIT 1;")
rows = cur.fetchall()

for row in rows:
    print(row)

cur.close()
conn.close()

os.environ["PGCLIENTENCODING"] = "UTF8"  
