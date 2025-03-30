import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from .db_operations import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
URL = "https://clinica.chitgma.ru/informatsiya-po-otdeleniyu-9"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_base", "working_hours.db")
db_manager = DatabaseManager(DB_PATH)

def clean_schedule_text(text: str) -> str:
    """Очищает текст расписания от лишних пробелов и форматирует время."""
    text = ' '.join(text.split())
    return text.replace(':0 0 -', ':00 -')

def create_schedule_table() -> bool:
    """Создает таблицу расписания в базе данных."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hours_text TEXT NOT NULL,
        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    return db_manager.create_table(create_table_sql)

def get_schedule_from_db() -> list[tuple]:
    """Получает расписание из базы данных."""
    try:
        logger.debug("Попытка подключения к БД")
        result = db_manager.fetch_all("SELECT hours_text FROM schedule LIMIT 1")
        logger.debug(f"Результат запроса из БД: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении расписания из БД: {e}", exc_info=True)
        return []

def is_schedule_fresh(max_age_hours: int = 24) -> bool:
    """Проверяет, актуальны ли данные о расписании."""
    query = """
    SELECT MAX(last_update) FROM schedule
    """
    result = db_manager.fetch_all(query)
    if not result or not result[0][0]:
        return False
    
    last_update = datetime.strptime(result[0][0], "%Y-%m-%d %H:%M:%S")
    return datetime.now() - last_update < timedelta(hours=max_age_hours)

def get_working_hours() -> str:
    """Скрапит расписание работы с сайта и возвращает строку с расписанием."""
    try:
        logger.info(f"Загружаем страницу {URL}")
        response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        work_hours = []
        found = False

        for p in soup.find_all('p'):
            text = clean_schedule_text(p.get_text())
            if 'Режим работы отделения' in text:
                found = True
                continue
            if found and text:
                work_hours.append(text)
                if len(work_hours) == 3:  # Берем только 3 строки расписания
                    break

        schedule_text = "\n".join(work_hours) if work_hours else ""
        logger.info(f"Получено расписание: {schedule_text}")
        return schedule_text
    
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе расписания: {e}")
        return ""
    except Exception as e:
        logger.error(f"Ошибка при парсинге расписания: {e}")
        return ""

def save_schedule_to_db(schedule_text: str) -> bool:
    """Сохраняет расписание в базу данных."""
    if not schedule_text:
        logger.warning("Попытка сохранить пустое расписание")
        return False
    
    try:
        if not db_manager.clear_table("schedule"):
            return False
        
        insert_sql = """
        INSERT INTO schedule (hours_text)
        VALUES (?)
        """
        if not db_manager.execute_query(insert_sql, (schedule_text,), commit=True):
            return False
        
        logger.info("Расписание успешно сохранено в БД")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении расписания: {e}")
        return False

def run_working_hours_scraper(force_update: bool = False) -> bool:
    """Запускает процесс парсинга и сохранения расписания."""
    if not force_update and is_schedule_fresh():
        logger.info("Расписание в БД актуально, пропускаем сканирование")
        return True
    
    schedule_text = get_working_hours()
    return save_schedule_to_db(schedule_text)

def init_db() -> bool:
    """Инициализирует базу данных для расписания."""
    return create_schedule_table()

if __name__ == '__main__':
    if init_db() and run_working_hours_scraper():
        print("Расписание успешно сохранено в базу данных")
    else:
        print("Не удалось сохранить расписание в базу данных")