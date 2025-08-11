# import re
# # from sqlalchemy import create_engine, text
# # from langchain.chains.sql_database.query import create_sql_query_chain
# # from langchain_community.utilities import SQLDatabase
# # from db_connection import engine
# # from langchain_community.chat_models import ChatOllama
# # from sqlalchemy import create_engine
# # from langchain_ollama import ChatOllama
# # from langchain_community.llms import Ollama  
# # from langchain_ollama import OllamaLLM
# # from langchain_community.utilities import SQLDatabase
# # from langchain.chains import create_sql_query_chain
# # from langchain_community.utilities import SQLDatabase
# # from langchain.agents import create_sql_agent
# # from langchain.agents.agent_toolkits import SQLDatabaseToolkit
# # from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
# # from langchain_community.agent_toolkits.sql.base import create_sql_agent
# # from langchain_community.utilities.sql_database import SQLDatabase
# # from langchain_core.prompts.chat import ChatPromptTemplate
# # from langchain_core.runnables import Runnable
# # from langchain_core.output_parsers import StrOutputParser
# # from langchain_community.chat_models import ChatOllama
# # from sqlalchemy import create_engine
# # from langchain_core.callbacks import StdOutCallbackHandler
# # from langchain_experimental.sql.base import SQLDatabaseChain

# from sqlalchemy import create_engine, text
# from langchain_community.utilities.sql_database import SQLDatabase
# from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
# from langchain_community.agent_toolkits.sql.base import create_sql_agent
# from langchain_community.chat_models import ChatOllama  # atau OllamaLLM


# # Inisialisasi LLM
# llm = Ollama(model="deepseek-coder")

# # Inisialisasi koneksi database
# engine = create_engine("postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/northwind")
# db = SQLDatabase(engine)  # <-- definisi variabel `db` yang diperlukan

# # Bangun SQLDatabaseChain
# db_chain = SQLDatabaseChain.from_llm(llm=llm, db=db, verbose=True)

# # Contoh setup
# db = SQLDatabase.from_uri("postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/northwind")
# llm = ChatOllama(model="deepseek")

# chain = create_sql_query_chain(llm, db)

# # Fungsi untuk dipanggil dari main
# def ask_sql(question):
#     return chain.invoke({"question": question})

# # Inisialisasi koneksi ke database
# db = SQLDatabase(engine)

# # Buat chain SQL dari LLM dan DB
# chain = create_sql_query_chain(llm, db, prompt=PROMPT, k=5)

# # Fungsi utama untuk menerima pertanyaan, ubah ke SQL, dan jalankan
# def ask_sql(pertanyaan: str) -> str:
#     try:
#         sql_query = chain.invoke({"question": pertanyaan})

#         # Bersihkan hasil dari output LLM
#         sql_query = re.sub(r"<.*?>", "", sql_query)
#         sql_query = re.sub(r"```sql\s*([\s\S]*?)```", r"\1", sql_query, flags=re.DOTALL)
#         sql_query = re.sub(r"```.*?```", "", sql_query)

#         # Ambil baris terakhir yang valid
#         lines = sql_query.strip().splitlines()
#         for line in reversed(lines):
#             if line.strip().lower().startswith(("select", "insert", "update", "delete")):
#                 sql_query = line.strip()
#                 break

#         # Jalankan query ke database
#         with engine.connect() as conn:
#             result = conn.execute(text(sql_query))
#             rows = result.fetchall()

#         if not rows:
#             return "⚠️ Tidak ada hasil ditemukan."

#         return "\n".join([", ".join(str(item) for item in row) for row in rows])

#     except Exception as e:
#         return f"⚠️ Terjadi error saat eksekusi query:\n{e}"


import re
from sqlalchemy import create_engine, text

# 1. Import minimal untuk agent
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.chat_models import ChatOllama  # atau: from langchain_ollama import OllamaLLM

# 2. Buat koneksi ke Postgres
engine = create_engine(
    "postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/northwind"
)
db = SQLDatabase(engine)

# 3. Inisialisasi LLM
# Pastikan pakai ChatOllama atau OllamaLLM, bukan Ollama() dari langchain_community.llms
llm = ChatOllama(model="deepseek-coder")

# 4. Siapkan toolkit & agent executor
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
agent_executor = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)

agent_executor = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    handle_parsing_errors=True  # <-- tambahkan ini
)

# 5. Fungsi tanya-jawab via agent
def ask_sql(question: str) -> str:
    print(f"[DEBUG] Menjalankan ask_sql dengan question={question!r}")
    try:
        answer = agent_executor.invoke({"input": question})
        print(f"[DEBUG] Hasil invoke: {answer!r}")
        return answer
    except Exception as e:
        print(f"[DEBUG] Error di agent: {e}")
        return f"⚠️ Terjadi error: {e}"


