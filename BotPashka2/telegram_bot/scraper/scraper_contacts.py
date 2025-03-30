from datetime import datetime, timedelta
import os
import logging
import requests
from bs4 import BeautifulSoup
from .db_operations import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
DATABASE = "data_base/contacts.db"
URL = "https://clinica.chitgma.ru/"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_base", "contacts.db")
db_manager = DatabaseManager(DB_PATH)

def clean_text(text: str) -> str:
    """Удаляет лишние пробелы, сохраняя нормальные интервалы."""
    return ' '.join(text.split())

def create_addresses_table() -> bool:
    """Создает таблицу адресов в базе данных."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL UNIQUE,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    return db_manager.create_table(create_table_sql)

def is_data_fresh() -> bool:
    """Проверяет, актуальны ли данные в таблице."""
    query = """
    SELECT MAX(last_updated) FROM addresses
    """
    result = db_manager.fetch_all(query)
    if result and result[0][0]:
        return True  # Здесь можно добавить проверку на дату
    return False

def get_contacts_from_db() -> list[tuple]:
    """Получает контакты из базы данных."""
    query = """
    SELECT address FROM addresses
    ORDER BY address
    """
    return db_manager.fetch_all(query)

def check_if_fresh(last_updated: str, freshness_days: int = 1) -> bool:
    """Проверяет, являются ли данные актуальными."""
    try:
        last_date = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_date < timedelta(days=freshness_days)
    except ValueError:
        logger.error("Ошибка при разборе даты из БД")
        return False
    
def get_contacts() -> list[str]:
    """Скрапит контакты (адреса) с сайта и возвращает список строк-адресов."""
    try:
        logger.info(f"Загружаем страницу {URL}")
        response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        address_blocks = set()

        for td in soup.find_all('td'):
            if 'Адрес' in td.get_text():
                parts = [clean_text(element.get_text()) for element in td.children if element.name == 'p']
                full_text = ' '.join(parts)
                if full_text:
                    address_blocks.add(full_text)
        
        logger.info(f"Найдено {len(address_blocks)} адресов")
        return list(address_blocks)
    
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при парсинге контактов: {e}")
        return []

def save_contacts_to_db(addresses: list[str]) -> bool:
    """Сохраняет список адресов в базу данных."""
    if not addresses:
        logger.warning("Попытка сохранить пустой список адресов")
        return False
    
    try:
        if not db_manager.clear_table("addresses"):
            return False
        
        insert_sql = """
        INSERT INTO addresses (address)
        VALUES (?)
        """
        if not db_manager.execute_many(insert_sql, [(addr,) for addr in addresses]):
            return False
        
        logger.info(f"Успешно сохранено {len(addresses)} адресов в БД")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}")
        return False

def run_contacts_scraper(force_update: bool = False) -> bool:
    """Запускает процесс парсинга и сохранения контактов."""
    if not force_update and is_data_fresh():
        logger.info("Данные в БД актуальны, пропускаем сканирование")
        return True
    
    addresses = get_contacts()
    return save_contacts_to_db(addresses)

def init_db() -> bool:
    """Инициализирует базу данных."""
    return create_addresses_table()

if __name__ == '__main__':
    if init_db() and run_contacts_scraper():
        print("Данные успешно сохранены в базу данных")
    else:
        print("Не удалось сохранить данные в базу данных")
