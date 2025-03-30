import sqlite3
import os

# Настройки
BASE_DIR = r'C:\Users\gamer\OneDrive\Рабочий стол\Bot Pashka2'  # Основная директория проекта
DB_FOLDER = os.path.join(BASE_DIR, 'data_base')
QR_FOLDER = os.path.join(BASE_DIR, 'QRcodes')
DB_NAME = 'clinic_users.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

# Создание папок для базы данных и QR-кодов, если они не существуют
os.makedirs(DB_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)


# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                user_id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qr_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при инициализации базы данных: {e}")
    finally:
        if conn:
            conn.close()


# Добавление пользователя
def add_user(username, user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, user_id) VALUES (?, ?)', (username, user_id))
            return cursor.lastrowid  # Возвращаем ID нового пользователя
    except sqlite3.IntegrityError:
        print("Пользователь с таким ID уже существует.")
        return None
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return None


# Получение ID пользователя из базы данных
def get_user_id(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Ошибка при получении ID пользователя: {e}")
    finally:
        if conn:
            conn.close()
