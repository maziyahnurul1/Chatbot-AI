import re
import pandas as pd
import matplotlib
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.llms import Ollama
from sqlalchemy import text
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader, Template
import imgkit
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import pdfkit
from sqlalchemy import create_engine
from matplotlib.backends.backend_pdf import PdfPages
import os
import logging
from num2words import num2words
from config import ADMIN_CHAT_ID # Pastikan ini diimpor dengan benar

def image_to_base64(filepath: str) -> str:
    """
    Mengkonversi file gambar menjadi string base64 untuk disematkan dalam HTML.
    """
    try:
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
    except FileNotFoundError:
        logger.error(f"File gambar tidak ditemukan di: {filepath}")
        return ""
    except Exception as e:
        logger.error(f"Gagal mengkonversi gambar ke base64: {e}")
        return ""

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ganti dengan info database kamu
engine = create_engine("postgresql+psycopg2://postgres:maziyahcantik@localhost:5432/db_payroll")

# --- Konfigurasi Jalur wkhtmltopdf dan wkhtmltoimage ---
WKHTML_BIN_PATH = r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe' # Untuk PDF (pdfkit)
WKHTMLTOIMAGE_BIN_PATH = r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe' # Untuk Gambar (imgkit)

PDFKIT_CONFIG = None
if os.path.exists(WKHTML_BIN_PATH):
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTML_BIN_PATH)
else:
    logger.warning(f"wkhtmltopdf tidak ditemukan di {WKHTML_BIN_PATH}. PDF generation mungkin tidak berfungsi.")

IMGKIT_CONFIG = None
if os.path.exists(WKHTMLTOIMAGE_BIN_PATH):
    IMGKIT_CONFIG = imgkit.config(wkhtmltoimage=WKHTMLTOIMAGE_BIN_PATH)
else:
    logger.warning(f"wkhtmltoimage tidak ditemukan di {WKHTMLTOIMAGE_BIN_PATH}. Image generation mungkin tidak berfungsi.")

# --- FUNGSI UNTUK MENGHASILKAN FILE PDF/GAMBAR DARI DATAFRAME ---
def generate_output_file(df: pd.DataFrame, filename: str, format: str) -> str:
    # Selalu simpan sebagai .png untuk gambar untuk konsistensi
    if format == "image":
        output_filepath = f"{filename}.png" 
    else:
        output_filepath = f"{filename}.{format}"

    if df.empty:
        logger.warning(f"DataFrame kosong, tidak dapat membuat file {format}.")
        return None

    if format == "pdf":
        try:
            if PDFKIT_CONFIG is None:
                logger.error("pdfkit configuration is not set up. Cannot generate PDF.")
                return None

            html_content = df.to_html(index=False)
            template_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Hasil Kueri PDF</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    h1 { font-size: 20px; color: #333; }
                </style>
            </head>
            <body>
                <h1>Hasil Kueri</h1>
                {{ table_html }}
            </body>
            </html>
            """
            template = Template(template_html)
            final_html = template.render(table_html=html_content)

            options = {
                'enable-local-file-access': None,
                'page-size': 'A4',
                'encoding': 'UTF-8',
            }

            pdfkit.from_string(final_html, output_filepath, configuration=PDFKIT_CONFIG, options=options)
            logger.info(f"PDF berhasil dibuat di: {output_filepath}")
            return output_filepath
        except Exception as e:
            logger.error(f"Error saat membuat PDF: {e}", exc_info=True)
            return None

    elif format == "image":
        try:
            if IMGKIT_CONFIG is None:
                logger.error("imgkit configuration is not set up. Cannot generate image.")
                return None

            html_content = df.to_html(index=False)
            template_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Hasil Kueri Gambar</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background-color: white; }
                    table { width: auto; border-collapse: collapse; margin-top: 10px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; white-space: nowrap; }
                    th { background-color: #f2f2f2; }
                    h1 { font-size: 18px; color: #333; }
                </style>
            </head>
            <body>
                <h1>Hasil Kueri</h1>
                {{ table_html }}
            </body>
            </html>
            """
            template = Template(template_html)
            final_html = template.render(table_html=html_content)

            options = {
                'format': 'png',
                'encoding': 'UTF-8',
                'zoom': 1.0, 
                'enable-local-file-access': None
            }

            imgkit.from_string(final_html, output_filepath, config=IMGKIT_CONFIG, options=options)
            logger.info(f"Gambar berhasil dibuat di: {output_filepath}")
            return output_filepath
        except Exception as e:
            logger.error(f"Error saat membuat gambar: {e}", exc_info=True)
            return None

    else:
        logger.warning(f"Format output tidak didukung: {format}")
        return None

# --- Fungsi ambil_data_slip Anda ---
def ambil_data_slip(chat_id):
    try:
        with engine.connect() as conn:
            query = text("""
        SELECT
            k.nama AS nama_karyawan,
            k.nik,
            k.unit AS unit_karyawan,
            k.posisi,
            g.periode,
            g.gadas AS gaji_dasar,
            g.tudas AS tunjangan_dasar,
            g.tupos AS tunjangan_posisi,
            g.tunprof AS tunjangan_profesi,
            g.transport AS transportasi,
            g.fastel,
            g.tunjkepklinik AS tunjangan_kepala_klinik,
            g.tunjkoordinator AS tunjangan_koordinator,
            g.tunjpjtpkk AS tunjangan_pjtpkk,
            g.tunjpic AS tunjangan_pic,
            g.faktorpenyesuai AS faktor_penyesuai,
            g.jaminankeselamatankerja AS jaminan_keselamatan_kerja,
            g.jaminankematian AS jaminan_kematian,
            g.jhtpk AS jht_pk,
            g.jhttk AS jht_tk,
            g.jaminanpensiunpk AS jaminan_pensiun_pk,
            g.jaminanpensiuntk AS jaminan_pensiun_tk,
            g.jamkespk AS jamkes_pk,
            g.jamkestk AS jamkes_tk,
            g.tunpes AS tunjangan_pes,
            g.tunjpph21 AS tunjangan_pph21,
            g.rapelan,
            g.potongan, 
            k.no_rek AS nomor_rekening
        FROM karyawan_karyawan k
        JOIN karyawan_gajireguler g ON k.id = g.id_karyawan_id
        WHERE k.chat_id = :chat_id
    """)
            result = conn.execute(query, {"chat_id": chat_id})
            row = result.fetchone()
            if row:
                data = row._asdict()

                # Hitung Total Penghasilan Bruto (semua tunjangan dan gaji sebelum potongan)
                # Gunakan .get() untuk semua kolom numerik agar lebih robust
                data['total_penghasilan_bruto'] = sum([
                    data.get('gaji_dasar', 0),
                    data.get('tunjangan_dasar', 0),
                    data.get('tunjangan_posisi', 0),
                    data.get('tunjangan_profesi', 0),
                    data.get('transportasi', 0),
                    data.get('fastel', 0),
                    data.get('tunjangan_kepala_klinik', 0),
                    data.get('tunjangan_koordinator', 0),
                    data.get('tunjpjtpkk', 0), # Diubah menjadi .get()
                    data.get('tunjpic', 0),
                    data.get('faktor_penyesuai', 0),
                    data.get('jaminan_keselamatan_kerja', 0),
                    data.get('jaminan_kematian', 0),
                    data.get('jht_pk', 0),
                    data.get('jaminan_pensiun_pk', 0),
                    data.get('jamkes_pk', 0),
                    data.get('tunjangan_pes', 0),
                    data.get('tunjpph21', 0),
                    data.get('rapelan', 0)
                ])

                # Hitung Total Potongan Terinci, HANYA BERDASARKAN KOLOM YANG ADA DI DATABASE
                # Gunakan .get() untuk semua kolom numerik agar lebih robust
                data['total_potongan_terinci'] = sum([
                    data.get('jhttk', 0),
                    data.get('jaminan_pensiuntk', 0),
                    data.get('jamkes_tk', 0),
                    data.get('potongan', 0) # Potongan umum dari DB
                ])

                # Hitung Gaji Bersih (total_gaji)
                data['total_gaji'] = data['total_penghasilan_bruto'] - data['total_potongan_terinci']

                # Konversi Gaji Bersih ke terbilang
                data['total_gaji_terbilang'] = num2words(data['total_gaji'], lang='id') + " Rupiah"

                # Debugging: Cetak data yang diambil
                logger.info(f"Data slip gaji untuk chat_id {chat_id}: {data}")

                return data
            else:
                logger.warning(f"Tidak ada data slip gaji ditemukan untuk chat_id: {chat_id}")
                return None
    except Exception as e:
        logger.error(f"Error dalam mengambil data slip gaji untuk chat_id {chat_id}: {e}", exc_info=True)
        return None

# --- Fungsi untuk membersihkan dan memvalidasi SQL Query ---
def sanitize_sql_query(query: str) -> str:
    original_query = query # Keep original for logging if needed
    query = query.strip()

    # Hapus klausa LIMIT dan OFFSET jika ada, karena LLM sering menambahkannya secara tidak perlu
    query = re.sub(r"\s+LIMIT\s+\d+", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\s+OFFSET\s+\d+", "", query, flags=re.IGNORECASE)

    # Pastikan query SELECT atau WITH
    if not re.match(r"^\s*(select|with)\b", query, re.IGNORECASE):
        logger.warning(f"[SAN_SQL] Query tidak diawali SELECT/WITH: {query}")
        return "" # Atau raise error, tergantung kebijakan

    # Hapus semicolon di akhir jika ada, karena dapat mengganggu beberapa eksekusi
    # Ini juga ditangani oleh clean_sql, tapi tidak ada salahnya double check
    if query.endswith(';'):
        query = query[:-1]

    # --- DIHAPUS: PATCH untuk menangani kolom komputasi langsung ---
    # Logika ini terbukti menyebabkan korupsi pada subkueri yang valid.
    # LLM sekarang diharapkan untuk menghasilkan kueri yang benar
    # berdasarkan instruksi di TABLE_INFO.

    # Hapus spasi berlebih
    query = re.sub(r'\s+', ' ', query).strip()

    logger.info(f"[SAN_SQL] Query setelah sanitasi: {query}")
    return query


# --- Integrasi dengan Langchain (untuk mengubah pertanyaan ke SQL) ---
db = SQLDatabase(engine)

# Skema database yang diekspos ke LLM
# PENTING: Hanya ekspos tabel dan kolom yang benar-benar relevan dan aman.
# Gunakan alias 'kk' untuk karyawan_karyawan dan 'kg' untuk karyawan_gajireguler
# Definisikan kolom dan hubungan dengan jelas.
TABLE_INFO = """
Tabel: karyawan_karyawan (alias: kk)
Kolom:
- id (INT, Primary Key)
- nik (VARCHAR)
- nama (VARCHAR)
- posisi (VARCHAR)
- kelas_posisi (VARCHAR)
- no_hp (VARCHAR)
- email (VARCHAR)
- unit (VARCHAR)
- bidang (VARCHAR)
- loker (VARCHAR)
- kategori (VARCHAR)
- status (VARCHAR)
- tgl_masuk (DATE)
- kontribusi_1_tahun (INT)
- tgl_bp_terakhir (DATE)
- tgl_posisi (DATE)
- no_npwp (VARCHAR)
- no_ktp (VARCHAR)
- jenis_kelamin (VARCHAR)
- no_rek (VARCHAR)
- status_bpjs_kesehatan (VARCHAR)
- no_bpjs_kesehatan (VARCHAR)
- no_bpjs_ketenagakerjaan (VARCHAR)
- dasar_perhitungan_bpjs (VARCHAR)
- dasar_perhitungan_bpjs_ket (VARCHAR)
- chat_id (BIGINT, untuk identifikasi pengguna Telegram)

Tabel: karyawan_gajireguler (alias: kg)
Kolom:
- id (INT, Primary Key)
- periode (DATE)
- gadas (NUMERIC) - Gaji Dasar
- tudas (NUMERIC) - Tunjangan Dasar
- tupos (NUMERIC) - Tunjangan Posisi
- tunprof (NUMERIC) - Tunjangan Profesi
- transport (NUMERIC) - Tunjangan Transportasi
- fastel (NUMERIC) - Tunjangan Fasilitas Telekomunikasi
- tunjkepklinik (NUMERIC) - Tunjangan Kepala Klinik
- tunjkoordinator (NUMERIC) - Tunjangan Koordinator
- tunjpjtpkk (NUMERIC) - Tunjangan PJTPKK
- tunjpic (NUMERIC) - Tunjangan PIC
- faktorpenyesuai (NUMERIC) - Faktor Penyesuai
- jaminankeselamatankerja (NUMERIC) - Jaminan Keselamatan Kerja (Perusahaan)
- jaminankematian (NUMERIC) - Jaminan Kematian (Perusahaan)
- jhtpk (NUMERIC) - Jaminan Hari Tua (Perusahaan)
- jhttk (NUMERIC) - Jaminan Hari Tua (Karyawan)
- jaminanpensiunpk (NUMERIC) - Jaminan Pensiun (Perusahaan)
- jaminanpensiuntk (NUMERIC) - Jaminan Pensiun (Karyawan)
- jamkespk (NUMERIC) - Jaminan Kesehatan (Perusahaan)
- jamkestk (NUMERIC) - Jaminan Kesehatan (Karyawan)
- tunpes (NUMERIC) - Tunjangan Prestasi/Pesangon
- tunjpph21 (NUMERIC) - Tunjangan PPh 21
- rapelan (NUMERIC)
- potongan (NUMERIC) - Potongan umum
- id_karyawan_id (INT, Foreign Key ke karyawan_karyawan.id)
- chat_id (BIGINT, Foreign Key ke karyawan_karyawan.chat_id, penting untuk filter)

Hubungan:
karyawan_karyawan.id = karyawan_gajireguler.id_karyawan_id
karyawan_karyawan.chat_id = karyawan_gajireguler.chat_id

Contoh penggunaan:
- Untuk pertanyaan tentang gaji atau tunjangan, JOIN kedua tabel dengan `ON kk.id = kg.id_karyawan_id` atau `ON kk.chat_id = kg.chat_id`.
- Selalu gunakan alias 'kk' untuk `karyawan_karyawan` dan 'kg' untuk `karyawan_gajireguler`.
- **PENTING: Untuk kolom 'unit' di tabel 'karyawan_karyawan', nilai yang valid adalah seperti 'Div IT', 'Div HR', 'Div Keuangan', dll. Pastikan menggunakan format yang tepat.**

--- ATURAN PENGURUTAN ---
- Untuk nilai numerik 'tertinggi'/'terbesar', gunakan ORDER BY [kolom] DESC.
- Untuk nilai numerik 'terendah'/'terkecil', gunakan ORDER BY [kolom] ASC.
- UNTUK KOLOM TEKS/ALFABETIS (seperti 'kelas_posisi', 'nama', 'posisi'):
  - 'tertinggi' atau 'secara alfabet tertinggi' berarti urutan Z-A, gunakan ORDER BY [kolom] DESC.
  - 'terendah' atau 'secara alfabet terendah' berarti urutan A-Z, gunakan ORDER BY [kolom] ASC.
- Jika pertanyaan adalah tentang siapa yang memiliki 'kelas_posisi' tertentu (tertinggi/terendah), sertakan juga kolom 'kelas_posisi' di SELECT.

Kolom Komputasi (HARUS DIHITUNG, BUKAN dipilih langsung sebagai kolom):
- 'total_penghasilan_bruto': `SUM(kg.gadas + kg.tudas + tupos + tunprof + transport + fastel + tunjkepklinik + tunjkoordinator + tunjpjtpkk + tunjpic + faktorpenyesuai + tunpes + rapelan + jaminankeselamatankerja + jaminankematian + jhtpk + jaminanpensiunpk + jamkespk + tunjpph21)`
- 'total_potongan': `SUM(kg.jhttk + kg.jaminanpensiuntk + kg.jamkestk + kg.potongan)`
- 'gaji_bersih': `(total_penghasilan_bruto - total_potongan)`
Jika pengguna menanyakan "total penghasilan bruto", "total potongan", atau "gaji bersih", Anda HARUS menghitungnya menggunakan rumus SUM ini di query SQL (misal: di SELECT clause), BUKAN memilih nama kolom tersebut secara langsung.

Role LLM:
Anda adalah asisten yang membantu user mendapatkan informasi dari database penggajian karyawan.
Gunakan informasi di atas untuk membuat query SQL yang akurat.
Berikan query SQL yang bersih, tanpa ```sql atau sintaks Markdown lainnya.
Fokus pada informasi yang diminta user.
Jika user menanyakan informasi gaji dirinya sendiri, pastikan untuk menambahkan filter `WHERE kk.chat_id = [chat_id_pengguna]` di query.
Jika user BUKAN admin (chat_id nya tidak sama dengan ADMIN_CHAT_ID), dan user menanyakan informasi gaji orang lain (misal: "gaji Andi", "siapa gaji terbesar"), atau informasi yang bersifat agregat yang bisa disalahgunakan, Anda HARUS menolak pertanyaan tersebut dengan mengatakan: "Maaf, Anda tidak memiliki izin untuk menanyakan informasi gaji orang lain."
Jika user admin (chat_id nya sama dengan ADMIN_CHAT_ID), user dapat menanyakan informasi gaji siapa pun.
Jika pertanyaan adalah tentang siapa yang memiliki 'kelas_posisi' tertentu (tertinggi/terendah), sertakan juga kolom 'kelas_posisi' di SELECT.

TOLAK query yang TIDAK menghasilkan query SQL SELECT yang valid.
TOLAK query yang mencoba melakukan INSERT, UPDATE, DELETE, atau DDL (CREATE, ALTER, DROP).
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", TABLE_INFO),
        ("human", "{question}\nSQL Query:"),
    ]
)

# --- Chain untuk Mengubah Pertanyaan ke SQL Query ---
sql_chain = (
    RunnablePassthrough.assign(
        schema=RunnableLambda(lambda x: db.get_table_info()) # Perubahan di sini!
    )
    | _PROMPT
    | Ollama(model="llama3") # Ganti dengan model LLM Anda
    | RunnableLambda(lambda sql: sql.strip()) # Pastikan tidak ada spasi atau newline berlebih
)

# --- Fungsi untuk mengubah hasil DataFrame menjadi jawaban natural ---
def result_to_natural_answer(question: str, df: pd.DataFrame) -> str:
    """
    Mengkonversi DataFrame hasil query menjadi jawaban dalam bahasa alami.
    """
    if df.empty:
        logger.info(f"DataFrame kosong untuk pertanyaan: {question}")
        return "Tidak ditemukan data yang relevan untuk pertanyaan Anda."

    # General handling for common queries
    if "karyawan mana saja" in question.lower() and "tunprof" in question.lower():
        names = df['nama'].tolist()
        if names:
            return f"Karyawan yang menerima tunjangan profesi lebih dari 400.000 adalah: {', '.join(names)}."
        else:
            return "Tidak ada karyawan yang menerima tunjangan profesi lebih dari 400.000."

    # If the dataframe has only one row and one column, return the value directly
    if len(df) == 1 and len(df.columns) == 1:
        # Check if the column is 'nama' and question is about 'kelas_posisi' or 'posisi'
        if 'nama' in df.columns and ('kelas_posisi' in question.lower() or 'posisi' in question.lower()):
            # If the query includes 'kelas_posisi' in SELECT, it should be reflected here.
            # Example: SELECT nama, kelas_posisi FROM ...
            # To handle this, result_to_natural_answer needs to be smarter or the LLM should format it better.
            # For now, let's assume the LLM will give 'nama' and 'kelas_posisi' if asked.
            # If the DataFrame contains 'kelas_posisi' as well, handle it.
            if 'kelas_posisi' in df.columns:
                return f"Hasilnya adalah: {df.iloc[0]['nama']} dengan kelas posisi {df.iloc[0]['kelas_posisi']}"
            else:
                return f"Hasilnya adalah: {df.iloc[0, 0]}"
        else:
            return f"Hasilnya adalah: {df.iloc[0, 0]}"

    # Generic response for other queries, displaying the first few rows
    header = "Berikut adalah hasil query Anda:\n\n"
    table_str = df.to_string(index=False)
    
    return header + "```\n" + table_str + "\n```"

# --- Fungsi utama untuk bertanya ke database ---
def ask_sql(question: str, user_chat_id: int, show_pdf: bool = False, show_image: bool = False) -> str:
    try:
        # ─────[1] Logging Pertanyaan Awal─────
        logger.info(f"[TRACE] Pertanyaan diterima: {question} dari user {user_chat_id}")

        # ─────[2] Mengganti engine database (jika diperlukan untuk pengujian)─────
        # db._engine = new_engine # Hanya jika Anda perlu mengganti engine secara dinamis

        # ─────[3] Generate SQL Query dari LLM─────
        sql_raw = sql_chain.invoke({"question": question})
        logger.info(f"[TRACE] SQL hasil LLM (raw):\n{sql_raw}")

        # ─────[4] Sanitasi dan Validasi SQL (PENTING UNTUK KEAMANAN!)─────
        sql_cleaned = clean_sql(sql_raw)
        logger.info(f"[TRACE] SQL setelah dibersihkan:\n{sql_cleaned}")

        if not re.match(r"^\s*(select|with)\b", sql_cleaned.strip(), re.IGNORECASE):
            return "Pertanyaan tidak bisa dijawab karena LLM tidak menghasilkan query SQL yang valid."

        sql_final = sanitize_sql_query(sql_cleaned)
        logger.info(f"[TRACE] Final SQL Query setelah sanitasi:\n{sql_final}")

        # ─────[5] Penanganan Izin (Permission Handling)─────
        # Cek apakah user adalah admin
        is_admin = (user_chat_id == ADMIN_CHAT_ID)
        
        sensitive_salary_patterns = [
            r"\bgaji\b",
            r"\btunjangan\b",
            r"\bpenghasilan\b",
            r"\btunprof\b",
            r"\btransport\b", # <--- PASTIKAN INI DITAMBAHKAN
            r"\bfastel\b",
            r"\btunjkepklinik\b",
            r"\btunjkoordinator\b",
            r"\btunjpjtpkk\b",
            r"\btunjpic\b",
            r"\bfaktorpenyesuai\b",
            r"\bjaminankeselamatankerja\b",
            r"\bjaminankematian\b",
            r"\bjhtpk\b",
            r"\bjhttk\b",
            r"\bjaminanpensiunpk\b",
            r"\bjaminanpensiuntk\b",
            r"\bjamkespk\b",
            r"\bjamkestk\b",
            r"\btunpes\b",
            r"\btunjpph21\b",
            r"\brapelan\b",
            r"\bpotongan\b",
            r"\btotal\b",
            r"\bsiapa\s+gaji\b",
            r"\bgaji\s+terbesar\b",
            r"\bgaji\s+terkecil\b",
            r"\bmax\(.+\)\b",
            r"\bmin\(.+\)\b",
            r"\bavg\(.+\)\b",
            r"\bsum\(.+\)\b",
            r"\bselect\s+sum\(",
            r"\bselect\s+avg\(",
            r"\bselect\s+max\(",
            r"\bselect\s+min\(",
            r"\bORDER\s+BY\s+\w+\.(?:gadas|tunprof|tudas|transport|fastel|tunjkepklinik|tunjkoordinator|tunjpjtpkk|tunjpic|faktorpenyesuai|jaminankeselamatankerja|jaminankematian|jhtpk|jhttk|jaminanpensiunpk|jaminanpensiuntk|jamkespk|jamkestk|tunpes|tunjpph21|rapelan|potongan)\s+DESC\s+LIMIT\s+1\b",
            r"\bORDER\s+BY\s+\w+\.(?:gadas|tunprof|tudas|transport|fastel|tunjkepklinik|tunjkoordinator|tunjpjtpkk|tunjpic|faktorpenyesuai|jaminankeselamatankerja|jaminankematian|jhtpk|jhttk|jaminanpensiunpk|jaminanpensiuntk|jamkespk|jamkestk|tunpes|tunjpph21|rapelan|potongan)\s+ASC\s+LIMIT\s+1\b"
        ]
        
        # Cek apakah pertanyaan mengandung pola sensitif
        is_sensitive_salary_question = any(re.search(pattern, question, re.IGNORECASE) for pattern in sensitive_salary_patterns)
        logger.info(f"[DEBUG_PERMISSION] is_sensitive_salary_question: {is_sensitive_salary_question} untuk pertanyaan: '{question}'")
        logger.info(f"[DEBUG_PERMISSION] is_admin: {is_admin}") 
        
        has_chat_id_filter = re.search(r"\bkk\.chat_id\s*=\s*\d+", sql_final, re.IGNORECASE)
        
        # Cek apakah user mencari datanya sendiri
        is_asking_for_own_data = False
        if has_chat_id_filter:
            # Ekstrak chat_id dari query untuk verifikasi
            match_chat_id = re.search(r"\bkk\.chat_id\s*=\s*(\d+)", sql_final, re.IGNORECASE)
            if match_chat_id and int(match_chat_id.group(1)) == user_chat_id:
                is_asking_for_own_data = True

        # Kebijakan Izin
        if not is_admin: # Jika user BUKAN admin
            if is_sensitive_salary_question and not is_asking_for_own_data:
                logger.warning(f"Pengguna non-admin (ID: {user_chat_id}) mengajukan pertanyaan gaji sensitif tentang orang lain.")
                return "Maaf, Anda tidak memiliki izin untuk menanyakan informasi gaji orang lain."
            
            # Ini adalah bagian yang mencoba menambahkan filter chat_id jika user non-admin menanyakan data yang bersifat umum
            # namun tidak spesifik gaji, atau jika LLM lupa menambahkan filter chat_id
            if ("FROM karyawan_karyawan" in sql_final.upper() or "JOIN karyawan_karyawan" in sql_final.upper()) \
               and not has_chat_id_filter and not is_asking_for_own_data:
                
                # Cek apakah ada klausa WHERE lain yang sudah ada
                if "WHERE" in sql_final.upper():
                    sql_final_modified = re.sub(r"WHERE", f"WHERE kk.chat_id = {user_chat_id} AND ", sql_final, 1, flags=re.IGNORECASE)
                else:
                    # Cari FROM atau JOIN terakhir untuk menyisipkan WHERE clause
                    insert_point_match = re.search(r"(FROM\s+\w+\s+(?:AS\s+\w+)?)(.*?)(ORDER\s+BY|LIMIT|;|$)", sql_final, re.IGNORECASE | re.DOTALL)
                    if insert_point_match:
                        sql_final_modified = f"{insert_point_match.group(1)} WHERE kk.chat_id = {user_chat_id}{insert_point_match.group(2)}{insert_point_match.group(3)}"
                    else:
                        logger.error(f"Tidak dapat menemukan tempat untuk menyisipkan filter chat_id: {sql_final}")
                        return "Maaf, terjadi masalah dalam memproses permintaan Anda terkait izin."
                
                logger.warning(f"Kueri non-admin ke data sensitif tanpa filter ID eksplisit. sql_final sebelum mod: {sql_final}")
                sql_final = sql_final_modified
                logger.info(f"Query non-admin dimodifikasi dengan filter ID: {sql_final}")
                
                # Ini adalah langkah tambahan untuk user non-admin yang datanya tidak ada
                with db._engine.connect() as conn:
                    # Buat query untuk memeriksa keberadaan data user
                    check_user_data_query = text(f"SELECT COUNT(kk.id) FROM karyawan_karyawan kk WHERE kk.chat_id = {user_chat_id}")
                    user_data_exists = conn.execute(check_user_data_query).scalar() > 0
                
                if not user_data_exists:
                    return "Maaf, data Anda tidak ditemukan di sistem. Silakan hubungi administrator."
        
        else: # Jika user adalah admin
            logger.info(f"Pengguna admin (ID: {user_chat_id}) mengajukan pertanyaan.")
            
        # ─────[6] Eksekusi Query─────
        with db._engine.connect() as conn:
            result = conn.execute(text(sql_final))
            rows = result.fetchall()
            columns = result.keys()

        if not rows:
            return "Tidak ditemukan data yang relevan untuk menjawab pertanyaan tersebut."

        df = pd.DataFrame(rows, columns=columns)
        logger.info(f"[TRACE] DataFrame hasil:\n{df}")

        # ─────[7] Opsi Output Tambahan─────
        # Jika diminta gambar/pdf, maka generate file di sini
        if show_pdf:
            generate_output_file(df, filename="hasil_query", format="pdf")

        if show_image:
            generate_output_file(df, filename="hasil_query", format="image")

        return result_to_natural_answer(question, df)

    except Exception as e:
        logger.error(f"[ERROR] Terjadi exception:\n{e}", exc_info=True)
        return "Maaf, terjadi kesalahan saat memproses permintaan Anda. Silakan coba lagi atau hubungi administrator."

# Fungsi untuk membersihkan raw SQL dari LLM
def clean_sql(sql_raw: str) -> str:
    # Hapus blok markdown jika ada
    sql_cleaned = re.sub(r"```sql\s*", "", sql_raw, flags=re.IGNORECASE)
    sql_cleaned = re.sub(r"\s*```", "", sql_cleaned, flags=re.IGNORECASE)

    # Pisahkan baris dan filter baris yang jelas merupakan catatan/komentar LLM
    lines = sql_cleaned.splitlines()
    filtered_lines = []
    for line in lines:
        stripped_line = line.strip()
        # Periksa pola catatan LLM atau komentar SQL standar
        if stripped_line.lower().startswith("note:") or \
           stripped_line.lower().startswith("comment:") or \
           stripped_line.startswith("--") or \
           stripped_line.startswith("/*"): 
            continue
        filtered_lines.append(line)
    sql_cleaned = "\n".join(filtered_lines)

    # Ambil hanya bagian sebelum semicolon pertama, karena kadang LLM menambahkan teks setelahnya
    if ';' in sql_cleaned:
        sql_cleaned = sql_cleaned.split(';')[0]

    # Hapus spasi atau newline berlebih
    sql_cleaned = sql_cleaned.strip()
    return sql_cleaned