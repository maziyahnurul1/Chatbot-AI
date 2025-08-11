import re 
import os 
import logging 
import tempfile
import pandas as pd 
from datetime import datetime, time 
from num2words import num2words 
import pdfkit 

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot 

# Import dari file lokal 
from zizi import ask_sql, ambil_data_slip, PDFKIT_CONFIG
from convert import render_slip_gaji

# --- Logging Configuration --- 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') 
logger = logging.getLogger(__name__) 

# Integrasi ke telegram menggunakan token
API_TOKEN = "8105883042:AAG6l2Mo29v33UUWLo4bC38DltWlOir8-uw" 

PDF_OPTIONS = {
    'enable-local-file-access': None,
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

# Replace with your admin's Telegram chat_id 
ADMIN_CHAT_ID = 1096497195 

# --- Dictionary to store the chat_id an admin is replying to --- 
ADMIN_REPLY_TARGET = {} 
 
# --- Bot's Basic Functions --- 
def start(update: Update, context: CallbackContext) -> None: 
    """Handles the /start command."""
    user = update.effective_user 
    logger.info(f"[USER] ID: {user.id}, Chat ID: {update.effective_chat.id}, Username: @{user.username}, Name: {user.full_name}") 
    
    # Check if the user is an admin
    if str(update.effective_chat.id) == str(ADMIN_CHAT_ID):
        message = (
            f"Halo, Admin {user.mention_markdown_v2()} \\! Saya adalah asisten bot Anda\\. "
            "Ketik /admin untuk melihat opsi admin\\."
        )
        reply_markup = None
    else:
        message = (
            f"Halo {user.mention_markdown_v2()} \\! Saya adalah asisten bot Anda\\. Ada yang bisa saya bantu\\?\n\n" 
            f"Ketik /slipgaji untuk mendapatkan slip gaji Anda\\. Atau ajukan pertanyaan seputar data karyawan\\."
        )
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Dapatkan Slip Gaji", callback_data='get_slip_gaji')]])
    
    update.message.reply_markdown_v2( 
        message, 
        reply_markup=reply_markup 
    ) 

def admin_button(update: Update, context: CallbackContext) -> None: 
    """Handles the /admin command, displaying admin options."""
    chat_id = update.effective_chat.id 
    if str(chat_id) == str(ADMIN_CHAT_ID): 
        keyboard = [[ 
            InlineKeyboardButton("List Semua User", callback_data='list_users'), 
            InlineKeyboardButton("Tanya Database", callback_data='tanya_database') 
        ]] 
        reply_markup = InlineKeyboardMarkup(keyboard) 
        update.message.reply_text('Selamat datang, Admin! Pilih aksi:', reply_markup=reply_markup) 
    else: 
        update.message.reply_text('Maaf, Anda tidak memiliki akses admin.') 
        logger.warning(f"Akses admin ditolak untuk user ID: {chat_id}") 

def reply_command(update: Update, context: CallbackContext) -> None: 
    """Handles the /reply command for admin to start a conversation with a user."""
    admin_chat_id = update.effective_chat.id 
    if str(admin_chat_id) != str(ADMIN_CHAT_ID): 
        update.message.reply_text("Maaf, Anda tidak memiliki akses untuk perintah ini.") 
        return 

    args = context.args 
    if not args or not args[0].isdigit(): 
        update.message.reply_text("Penggunaan: /reply <chat_id_user_target>") 
        return 

    target_user_chat_id = int(args[0]) 
    ADMIN_REPLY_TARGET[admin_chat_id] = target_user_chat_id 
    update.message.reply_markdown_v2( 
        f"Anda sekarang dalam mode balasan untuk user dengan ID: `{target_user_chat_id}`.\\n" 
        "Silakan ketik pesan balasan Anda sekarang.", 
        parse_mode='Markdown' 
    ) 
    logger.info(f"Admin (ID: {admin_chat_id}) memulai mode balasan ke user (ID: {target_user_chat_id}).") 

def handle_slip_gaji(update: Update, context: CallbackContext) -> None:
    """Handles the /slipgaji command and 'get_slip_gaji' callback."""
    chat_id = update.effective_chat.id
    
    # Inisialisasi variabel path file agar bisa diakses di finally block
    temp_html_file_path = None
    pdf_file_path = None
    output_path = 'C:/Users/maziyah nurul/Documents/MAGANG/rag-ds-main/rag-ds-main/templates/file.pdf'
    try:
        data_karyawan = ambil_data_slip(chat_id)
        if data_karyawan:
            # Pastikan render_slip_gaji di convert.py hanya mengembalikan string HTML
            html_content = render_slip_gaji(data_karyawan, output_path=output_path)

            if not html_content: # Jika render_slip_gaji mengembalikan kosong
                context.bot.send_message(chat_id=chat_id, text="Maaf, gagal merender slip gaji. Silakan coba lagi.")
                logger.error(f"HTML konten kosong untuk chat ID: {chat_id}")
                return

            # Gunakan tempfile.mkstemp untuk membuat file HTML sementara yang unik dan aman
            fd, temp_html_file_path = tempfile.mkstemp(suffix=".html", prefix=f"slip_gaji_{chat_id}_")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"File HTML sementara dibuat di: {temp_html_file_path}")

            # Tentukan jalur untuk file PDF akhir
            pdf_file_path = f"slip_gaji_{chat_id}.pdf"
            
            try:
                # Konversi HTML ke PDF dengan konfigurasi yang benar
                pdfkit.from_file(temp_html_file_path, pdf_file_path, configuration=PDFKIT_CONFIG, options=PDF_OPTIONS)
                logger.info(f"PDF berhasil dibuat di: {pdf_file_path}")

                # Kirim file PDF ke user
                with open(pdf_file_path, "rb") as pdf_file:
                    # Anda bisa membuat nama file lebih deskriptif jika data_karyawan tersedia
                    filename = f"slip_gaji_{data_karyawan.get('nama_karyawan', 'Anda')}_{data_karyawan.get('periode', 'Tidak_Diketahui')}.pdf"
                    context.bot.send_document(chat_id=chat_id, document=pdf_file, filename=filename)
                logger.info(f"Slip gaji berhasil dikirim ke user: {chat_id}")

            except Exception as pdf_e:
                logger.error(f"Gagal mengkonversi HTML ke PDF atau mengirim PDF: {pdf_e}", exc_info=True)
                context.bot.send_message(chat_id=chat_id, text="Maaf, gagal membuat atau mengirim slip gaji dalam format PDF.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Maaf, data slip gaji Anda tidak ditemukan. Pastikan chat ID Anda terdaftar.")
            logger.info(f"Data slip gaji tidak ditemukan untuk chat ID: {chat_id}")
    except Exception as e:
        logger.error(f"Terjadi error saat memproses slip gaji: {e}", exc_info=True)
        context.bot.send_message(chat_id=chat_id, text="Maaf, terjadi kesalahan saat memproses permintaan slip gaji Anda.")
    finally:
        # Hapus file sementara HTML
        if temp_html_file_path and os.path.exists(temp_html_file_path):
            os.remove(temp_html_file_path)
            logger.info(f"File HTML sementara dihapus: {temp_html_file_path}")
        # Hapus file PDF yang sudah dikirim
        if pdf_file_path and os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)
            logger.info(f"File PDF sementara dihapus: {pdf_file_path}")

def handle_message(update: Update, context: CallbackContext) -> None: 
    """Handles all non-command text messages."""
    if not update.message or not update.message.text: 
        logger.warning(f"handle_message menerima update tanpa teks pesan: {update}") 
        return 

    user_message = update.message.text 
    chat_id = update.effective_chat.id 
    user = update.effective_user 
    user_id = user.id 

    logger.info(f"[USER_MESSAGE] ID: {user_id}, Chat ID: {chat_id}, Text: {user_message}") 

    # --- Logic for Admin Reply Mode --- 
    if str(chat_id) == str(ADMIN_CHAT_ID) and ADMIN_REPLY_TARGET.get(chat_id): 
        target_user_chat_id = ADMIN_REPLY_TARGET.pop(chat_id) 
        try: 
            context.bot.send_message(chat_id=target_user_chat_id, text=f"Balasan dari Admin: {user_message}") 
            update.message.reply_text(f"Balasan Anda berhasil dikirim ke user (ID: {target_user_chat_id}).") 
            logger.info(f"Admin (ID: {chat_id}) membalas user (ID: {target_user_chat_id}): '{user_message}'") 
        except Exception as e: 
            logger.error(f"Gagal membalas user {target_user_chat_id}: {e}", exc_info=True) 
            update.message.reply_text(f"Gagal mengirim balasan ke user. Error: {e}") 
        return 
    
    # --- Logic for Working Hours and Admin Handover --- 
    current_time = datetime.now() 
    current_weekday = current_time.weekday() 
    is_weekday = 0 <= current_weekday <= 4 
    is_within_hours = time(8, 0) <= current_time.time() < time(17, 0) 

    if str(chat_id) != str(ADMIN_CHAT_ID) and not (is_weekday and is_within_hours): 
        update.message.reply_text( 
            "Mohon maaf, layanan bantuan ke admin hanya tersedia pada hari kerja (Senin-Jumat) " 
            "pukul 08.00 - 17.00 WIB. Silakan hubungi kami kembali pada jam operasional." 
        ) 
        logger.info(f"Pesan dari {chat_id} ditolak karena di luar jam kerja.") 
        return 

    msg_lower = user_message.lower() 

    # ====== HANDLE SLIP GAJI FROM TEXT MESSAGE ====== 
    if any(x in msg_lower for x in ["slip gaji", "slipgaji", "slip"]): 
        return handle_slip_gaji(update, context) 
     
    # ====== HANDLE CONTACT ADMIN (If message is from a regular user) ====== 
    if str(chat_id) != str(ADMIN_CHAT_ID) and \
       re.search(r"\b(admin|cs|manusia|customer service|hubungi)\b", msg_lower): 
        context.bot.send_message(chat_id=chat_id, text="Baik, kami akan meneruskan pesan Anda ke admin. Mohon tunggu balasan.") 
        keyboard = [[InlineKeyboardButton("Balas Langsung", callback_data=f'reply_to_user:{chat_id}')]] 
        reply_markup = InlineKeyboardMarkup(keyboard) 
        admin_message = ( 
            f"🚨 Pesan dari User\n" 
            f"User: @{user.username if user.username else user.full_name} ({user.first_name})\n" 
            f"ID: {chat_id}\n" 
            f"Pesan: {user_message}" 
        ) 
        try: 
            context.bot.send_message( 
                chat_id=ADMIN_CHAT_ID, 
                text=admin_message, 
                reply_markup=reply_markup 
            ) 
            logger.info(f"Pesan user {chat_id} diteruskan ke admin dengan tombol balas.") 
        except Exception as e: 
            logger.error(f"Gagal mengirim pesan ke admin: {e}", exc_info=True) 
            context.bot.send_message(chat_id=chat_id, text="Maaf, gagal menghubungi admin.") 
        return 
     
    # ====== HANDLE ask_sql (default) - Will execute if no other conditions are met ====== 
    show_pdf = any(x in msg_lower for x in ["pdf", "download", "unduh"]) 
    show_image = any(x in msg_lower for x in ["gambar", "visualisasi", "image", "imagenya"]) 
     
    try: 
        # Clean up old files if they exist
        if os.path.exists("hasil_query.pdf"): os.remove("hasil_query.pdf") 
        if os.path.exists("hasil_query.png"): os.remove("hasil_query.png") 

        response = "" 
        # Access control logic for non-admins 
        if str(user_id) == str(ADMIN_CHAT_ID): 
            # Admin can ask anything to the database 
            logger.info(f"Admin (ID: {user_id}) is asking a direct SQL question.")
            response = ask_sql(user_message, show_pdf=show_pdf, show_image=show_image, user_chat_id=user_id) 
        else: 
            # Non-admins: Restrict questions containing salary-related keywords 
            if re.search(r"\b(gaji|terbesar|total|penghasilan|honor)\b", msg_lower): 
                response = "Maaf, Anda tidak memiliki izin untuk menanyakan informasi gaji secara umum atau data orang lain." 
                logger.warning(f"Akses ditolak: Pengguna non-admin (ID: {user_id}) mencoba menanyakan gaji umum.") 
            else: 
                # Allow other questions, but ask_sql must filter further if there are joins to sensitive tables 
                logger.info(f"Pengguna non-admin (ID: {user_id}) mengajukan pertanyaan non-gaji.")
                response = ask_sql(user_message, show_pdf=show_pdf, show_image=show_image, user_chat_id=user_id) 
         
        file_sent = False 
        if show_pdf and os.path.exists("hasil_query.pdf"): 
            with open("hasil_query.pdf", "rb") as f: 
                context.bot.send_document(chat_id=chat_id, document=f, filename="Hasil_Query.pdf") 
            os.remove("hasil_query.pdf") 
            file_sent = True 

        if show_image and os.path.exists("hasil_query.png"): 
            with open("hasil_query.png", "rb") as img_file: 
                context.bot.send_photo(chat_id=chat_id, photo=img_file, caption="Visualisasi hasil query") 
            os.remove("hasil_query.png") 
            file_sent = True 

        if not file_sent: 
            if not response or not response.strip(): 
                response = "Maaf, saya tidak menemukan data yang relevan atau tidak dapat memproses permintaan Anda." 
            for chunk in split_message(response): 
                context.bot.send_message(chat_id=chat_id, text=chunk) 
    
    except Exception as e: 
        logger.error(f"[ERROR] Gagal memproses pertanyaan atau mengirim file: {e}", exc_info=True) 
        context.bot.send_message(chat_id=chat_id, text="Maaf, terjadi error saat memproses pertanyaan Anda.") 

def handle_callback(update: Update, context: CallbackContext) -> None:
    """Handles inline keyboard button presses."""
    query = update.callback_query
    query.answer()  # Acknowledge the callback query
    data = query.data
    chat_id = query.message.chat_id

    logger.info(f"CallbackQuery received from user: {chat_id}, data: {data}")

    if data == 'get_slip_gaji':
        handle_slip_gaji(update, context)
    elif data == 'list_users':
        # This functionality is not yet implemented in the provided code,
        # but this is where you would call the function to list all users.
        query.edit_message_text(text="Fungsi untuk menampilkan daftar user belum diimplementasi.")
    elif data == 'tanya_database':
        query.edit_message_text(text="Silakan ajukan pertanyaan SQL Anda sekarang.")
    elif data.startswith('reply_to_user:'):
        target_user_chat_id = data.split(':')[1]
        ADMIN_REPLY_TARGET[chat_id] = int(target_user_chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=f"Anda sekarang dalam mode balasan untuk user dengan ID: `{target_user_chat_id}`. Silakan ketik pesan balasan Anda."
        )

def split_message(text, max_length=4000): 
    """Splits a long message into chunks to avoid Telegram's message length limit."""
    lines = text.splitlines() 
    chunks = [] 
    current = "" 
    for line in lines: 
        if len(current) + len(line) + 1 > max_length and current: 
            chunks.append(current) 
            current = "" 
        current += line + "\n" 
    if current: 
        chunks.append(current) 
    return chunks 

# --- Main Function --- 
def main(): 
    """Starts the bot."""
    print("--- DEBUG: Bot started with the latest code version. ---") 
    updater = Updater(API_TOKEN, use_context=True) 
    dp = updater.dispatcher 

    # Handlers 
    dp.add_handler(CommandHandler("start", start)) 
    dp.add_handler(CommandHandler("admin", admin_button)) 
    dp.add_handler(CommandHandler("reply", reply_command))     
    dp.add_handler(CommandHandler("slipgaji", handle_slip_gaji))
    
    # MessageHandler for all text messages that are not commands 
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message)) 
    dp.add_handler(CallbackQueryHandler(handle_callback)) 

    logger.info("Bot is running...") 
    updater.start_polling() 
    updater.idle() 

if __name__ == '__main__': 
    main()