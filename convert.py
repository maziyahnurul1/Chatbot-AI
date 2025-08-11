import os
import tempfile
from jinja2 import Environment, FileSystemLoader
import pdfkit
import logging
import base64 # Pastikan ini diimpor jika belum ada

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Konfigurasi Jalur wkhtmltopdf ---
# PERHATIKAN: ganti path ini jika lokasi instalasi wkhtmltopdf Anda berbeda
WKHTML_BIN_PATH = r'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'

# Konfigurasi PDF options (digunakan oleh pdfkit.from_file)
PDF_OPTIONS = {
    'enable-local-file-access': '',
    'page-size': 'A4',
    'encoding': 'UTF-8',
    'no-stop-slow-scripts': None,
    'enable-javascript': None,
    'zoom': 1.0,
    'margin-top': '0mm',
    'margin-right': '0mm',
    'margin-bottom': '0mm',
    'margin-left': '0mm',
    'disable-smart-shrinking': None
}

# Konfigurasi PDFKit (ImgKit sudah tidak digunakan karena tidak relevan dengan image_to_base64)
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=WKHTML_BIN_PATH)

def image_to_base64(filepath: str) -> str:
    """
    Mengkonversi file gambar menjadi string base64.
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

def render_slip_gaji(slip_data: dict, output_path: str):
    """
    Mengisi template HTML dengan data slip gaji dan menyimpannya sebagai PDF.
    """
    try:
        # Tentukan jalur ke folder 'templates'
        templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        template_file = 'slip_gaji_template.html'
        
        # Tentukan jalur lengkap ke file logo
        # logo_path = os.path.join(templates_dir, 'images', 'LogoYakes.png')
        logo_path = os.path.abspath(os.path.join(templates_dir, 'images', 'LogoYakes.png'))

        # Konversi ke URL format: file:///... (penting untuk wkhtmltopdf)
        logo_url = f"file:///{logo_path.replace(os.sep, '/')}"

        # logger.info(f"Mencoba memuat logo dari: {logo_path}")
        # logo_base64 = image_to_base64(logo_path)
        # if not logo_base64:
        #     logger.warning("Logo Base64 tidak dapat dibuat. PDF mungkin tidak memiliki logo.")
        # else:
        #     logger.info("Logo Base64 berhasil dibuat.")   

        template_data = {
            **slip_data,
            'logo_path': logo_url,
        }

        # Siapkan Jinja2 Environment
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template(template_file)

        # Render template dengan data
        html_output = template.render(template_data)

        # Buat file HTML sementara
        temp_html_file_path = os.path.join(tempfile.gettempdir(), os.path.basename(output_path).replace(".pdf", ".html"))
        
        with open(temp_html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        logger.info(f"HTML sementara dibuat di: {temp_html_file_path}")

        # Konversi HTML sementara ke PDF
        # Pastikan PDFKIT_CONFIG sudah diinisialisasi dengan WKHTML_BIN_PATH yang benars
        pdfkit.from_file(temp_html_file_path, output_path, options=PDF_OPTIONS, configuration=PDFKIT_CONFIG)
        logger.info(f"PDF slip gaji berhasil dibuat di: {output_path}")

        # Hapus file HTML sementara
        if os.path.exists(temp_html_file_path):
            os.remove(temp_html_file_path)
            logger.info(f"File HTML sementara {temp_html_file_path} berhasil dihapus.")

    except Exception as e:
        logger.error(f"Gagal merender slip gaji: {e}", exc_info=True)
        raise
    return html_output