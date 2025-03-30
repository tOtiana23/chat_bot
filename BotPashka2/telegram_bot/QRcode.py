import qrcode
import time
import os
import sqlite3

# Настройки
BOT_USERNAME = 'test_HealthCode_bot'
BASE_DIR = r'C:\Users\busyg\Desktop\РАБОТАЙ БЛЯТЬ3'  # Основная директория проекта
DB_FOLDER = os.path.join(BASE_DIR, 'data_base')
QR_FOLDER = os.path.join(BASE_DIR, 'QRcodes')
DB_NAME = 'clinic_users.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

# Генерация QR-кода
def generate_qr(user_id):
    conn = None
    try:
        # Проверяем, существует ли папка для QR-кодов
        os.makedirs(QR_FOLDER, exist_ok=True)

        # Создаём ссылку и QR-код
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        qr = qrcode.make(link)
        qr_file_path = os.path.join(QR_FOLDER, f'qr_{user_id}.png')
        qr.save(qr_file_path)

        # Сохраняем в БД
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO qr_codes (user_id) VALUES (?)', (user_id,))
        conn.commit()

        print(f"✅ QR-код сохранён: {qr_file_path}")
        return qr, qr_file_path

    except Exception as e:
        print(f"❌ Ошибка в generate_qr(): {e}")
        return None
    finally:
        if conn:
            conn.close()

# Проверка действительности QR-кода
def is_qr_valid(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT created_at FROM qr_codes WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        result = cursor.fetchone()

        if result:
            created_at = result[0]
            created_time = time.mktime(time.strptime(created_at, '%Y-%m-%d %H:%M:%S'))
            current_time = time.time()
            # Проверка, прошло ли n-количество секунд
            return (current_time - created_time) < 60 * 2
        else:
            print("QR-код не найден.")
            return False
    except Exception as e:
        print(f"Ошибка при проверке QR-кода: {e}")
    finally:
        if conn:
            conn.close()
