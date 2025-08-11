# sql_chain.py
import os
from dotenv import load_dotenv
import psycopg2

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain

# 4) Connect langsung via keyword args—**TANPA** DSN string
conn = psycopg2.connect(
    dbname="northwind", 
    user="postgres", 
    password="maziyahcantik", 
    host="localhost", 
    port="5432"
)

# 5) Bungkus ke LangChain
db = SQLDatabase(
    conn,
    include_tables=["employees", "customers", "orders"],
    sample_rows_in_table_info=3
)

# 6) Inisialisasi LLM
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    temperature=0,
    model="deepseek",
    openai_api_key=OPENAI_KEY
)

# 7) Buat SQLDatabaseChain
sql_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

def ask_sql(question: str) -> str:
    return sql_chain.run(question)

if __name__ == "__main__":
    print(ask_sql("Siapa karyawan tertua?"))
