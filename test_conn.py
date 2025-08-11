import psycopg

try:
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="db_payroll",
        user="postgres",
        password="maziyahcantik"
    )
    print("🎉 Terhubung! client_encoding =", conn.info.encoding)
except Exception as e:
    print("ERROR:", e)
    
