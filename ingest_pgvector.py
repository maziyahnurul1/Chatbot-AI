from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter  # tetap pakai langchain

# 1. Generate embedding
embedding = OllamaEmbeddings(model="nomic-embed-text")

# 2. Koneksi ke PostgreSQL
CONNECTION_STRING = "postgresql://postgres:maziyahcantik@localhost:5432/db_payroll"

# 3. Load dokumen
loader = TextLoader("docs/sample.txt")
documents = loader.load()

# 4. Split dokumen
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)
docs = text_splitter.split_documents(documents)

# 5. Simpan ke vectorstore
vectorstore = PGVector.from_documents(
    documents=docs,
    embedding=embedding,
    collection_name="my_vectors",
    connection_string=CONNECTION_STRING,
)

print("✅ Sukses menyimpan embedding ke PostgreSQL dengan PGVector.")
