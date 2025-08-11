from sqlalchemy import text
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.llms import Ollama
from langchain_community.utilities.sql_database import SQLDatabase
import pandas as pd
import re

# Bersihkan output model agar hanya SQL
def clean_sql(query):
    query = query.strip()
    code_block_match = re.search(r"sql(.*?)", query, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        print('masuk sini if=============')
        query = code_block_match.group(1).strip()
    else:
        query_lines = query.splitlines()
        query_lines = [line.strip() for line in query_lines if line.strip()]
        select_lines = [line for line in query_lines if line.lower().startswith("select")]
        if select_lines:
            query = select_lines[0]
            if ";" not in query:
                query += ";"
        else:
            query = query_lines[0] if query_lines else ""

    query = re.sub(r"<.*?>", "", query)
    query = query.replace("```", "").strip()
    return query

# Fungsi utama chatbot SQL
def ask_sql(question: str) -> str:
    # Koneksi ke database
    connection_string = "postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/northwind"
    db = SQLDatabase.from_uri(
        connection_string,
        include_tables=["customers", "orders", "order_details", "suppliers", "employees"]
    )

    # LLM untuk SQL
    llm = Ollama(model="deepseek-r1:8b", temperature=0, base_url="http://10.15.224.10:11434")
    # llm_sql = Ollama(model="deepseek-coder", temperature=0)

    # Prompt untuk membuat SQL
    prompt_sql = ChatPromptTemplate.from_template("""
You are an SQL expert. Translate the following question into a valid PostgreSQL query.

    Provide only the SQL query without any explanation, formatting, or additional text. 
    Do not include phrases like "Here's your query:" or any surrounding text:
                                                  
    Tables:
    {table_info}
    
    Question: {input}
    
    SQL:
""")

    # Ambil info tabel
    def get_table_info(_: str) -> str:
        return db.get_table_info()

    # Buat SQL dari pertanyaan
    sql_chain = (
        {"input": RunnablePassthrough(), "table_info": RunnableLambda(get_table_info)}
        | prompt_sql
        | llm
    )

    # Hasil SQL dari LLM
    sql_query = sql_chain.invoke(question)
    print("🧪 Jawaban dari LLM:", sql_query)

    # Bersihkan SQL
    sql_query = clean_sql(sql_query)
    print("🧪 Clean dari LLM:", sql_query)

    # Validasi dasar SQL
    # if not sql_query.lower().startswith("select") or "from" not in sql_query.lower():
    #     return "[SQL ERROR] Model tidak menghasilkan SQL yang valid."
    # if "table_name" in sql_query.lower():
    #     return "[SQL ERROR] Model memakai nama tabel placeholder."
    # if "support_rep_id" in sql_query.lower():
    #     return "[SQL ERROR] Model menggunakan kolom tidak tersedia: support_rep_id."

    try:
        # Jalankan query
        result = db.run(sql_query)

        # Format hasil
        if isinstance(result, list) and len(result) > 0:
            try:
                columns = db.run(f"SELECT * FROM ({sql_query[:-1]}) AS sub LIMIT 0").keys()
                if len(columns) == 1:
                    result_str = f"{columns[0]}: {result[0][0]}"
                else:
                    df = pd.DataFrame(result, columns=columns)
                    result_str = df.to_markdown(index=False)
            except Exception:
                result_str = str(result)
        elif isinstance(result, list):
            result_str = "Tidak ada hasil ditemukan."
        else:
            result_str = str(result)

        # Gunakan LLM untuk menjawab dengan bahasa natural
        # llm_chat = Ollama(model="mistral:latest", temperature=0.7, base_url="http://10.15.224.10:11434")
        answer_prompt = ChatPromptTemplate.from_template("""
Berikut adalah hasil data dari database:

{query_result}

Jawablah pertanyaan berikut ini dengan bahasa Indonesia yang alami dan mudah dimengerti.
Jangan tampilkan query SQL. Fokus hanya pada jawaban akhir yang dibutuhkan oleh user.

Pertanyaan: {user_question}

Jawaban:
""")

        answer_chain = answer_prompt | llm
        final_answer = answer_chain.invoke({
            "query_result": result_str,
            "user_question": question
        })
        return final_answer.strip()

    except Exception as e:
        return f"[SQL ERROR] {str(e)}"
