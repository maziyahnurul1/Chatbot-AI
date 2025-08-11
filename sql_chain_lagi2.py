# sql_chain.py
import os
import psycopg2

# # Koneksi ke PostgreSQL
def get_conf():
	conn = psycopg2.connect(
        database="northwind", 
		user="postgres", 
		password="maziyahcantik", 
		host="localhost", 
		port="5432"
	)
	return conn

# Membuat cursor dan menjalankan query
def get_data():
    cur = get_conf().cursor()
    cur.execute("SELECT * FROM employees LIMIT 1;")
    rows = cur.fetchall()

    for row in rows:
        print(row)

# os.environ["PGCLIENTENCODING"] = "UTF8"

if __name__ == "__main__":
    get_data()
