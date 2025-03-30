# main.py
import os
from typing import List, Optional, Tuple
import requests
import pdfplumber
import io
import re
import logging
from .db_operations import DatabaseManager

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
DATABASE = "data_base/price.db"
URL = "https://clinica.chitgma.ru/images/Preyskurant/2025/1DP.pdf"
# Добавьте в начало файла
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_base", "price.db")
db_manager = DatabaseManager(DB_PATH)

# Обновите функцию run_price_scraper
def run_price_scraper(force_update: bool = False) -> bool:
    """Запускает скрапер только если данные устарели или принудительно"""
    if not force_update and db_manager.is_data_fresh():
        logger.info("Данные в БД актуальны, пропускаем сканирование")
        return True
        
    services = get_prices()
    if services:
        return save_prices_to_db(services)
    return False
# Инициализация менеджера базы данных
db_manager = DatabaseManager(DATABASE)

def extract_appointment_type(service_name: str) -> str:
    """Определяет тип приема (первичный, повторный, профилактический)."""
    patterns = {
        'повторный': r'повторн\w+',
        'первичный': r'первичн\w+',
        'профилактический': r'профилактич\w+',
    }
    for app_type, pattern in patterns.items():
        if re.search(pattern, service_name, re.IGNORECASE):
            return app_type
    return 'не указано'

def extract_doctor_specialty(service_name: str) -> Optional[str]:
    """Определяет специальность врача из названия услуги."""
    patterns = [
        r'врача\s*-\s*детского\s+([а-яё-]+)',
        r'врача\s*-\s*([а-яё-]+\s[а-яё-]+)',
        r'врача\s+([а-яё-]+)(?:\s|$)',
        r'врача\s*-\s*([а-яё-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, service_name, re.IGNORECASE)
        if match:
            specialty = match.group(1).strip()
            if 'детского' in service_name.lower():
                return f"детский {specialty}".capitalize()
            specialty = re.sub(r'(повторн\w+|первичn\w+|планов\w+|консультац\w+|\d+).*$', '', specialty, flags=re.IGNORECASE)
            specialty = re.sub(r'[()]', '', specialty)
            specialty = specialty.replace('-', ' ').strip()
            return specialty.capitalize() if specialty else None
    return None

def create_services_table():
    """Создает таблицу услуг в базе данных."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL,
        doctor_specialty TEXT,
        appointment_type TEXT,
        price REAL NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    return db_manager.create_table(create_table_sql)

def get_prices() -> List[Tuple]:
    """Скачивает PDF и парсит цены, возвращая список услуг."""
    try:
        logger.info(f"Начинаем загрузку PDF с {URL}")
        response = requests.get(URL, timeout=30)
        response.raise_for_status()

        pdf_file = io.BytesIO(response.content)
        services = []
        stop_parsing = False

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                if stop_parsing:
                    break
                text = page.extract_text()
                if text:
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        if "выезды на дом" in line.lower():
                            stop_parsing = True
                            break
                        if "прием" in line.lower():
                            parts = line.split()
                            service_name = " ".join(parts[2:])
                            price_match = re.search(r'(\d[\d\s:]*[\d.,]+)\s?r?u?b?\.?$', service_name, re.IGNORECASE)

                            if price_match:
                                price = price_match.group(1).replace(' ', '').replace(':', '').replace(',', '.')
                                service_name_clean = service_name[:price_match.start()].strip()
                                doctor_specialty = extract_doctor_specialty(service_name_clean)
                                appointment_type = extract_appointment_type(service_name_clean)

                                services.append((
                                    service_name_clean, 
                                    doctor_specialty, 
                                    appointment_type, 
                                    float(price)
                                ))
                                logger.debug(f"Найдена услуга: {service_name_clean}")

        logger.info(f"Найдено {len(services)} услуг")
        return services

    except requests.RequestException as e:
        logger.error(f"Ошибка при загрузке PDF: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при парсинге PDF: {e}")
        return []

def save_prices_to_db(services: List[Tuple]) -> bool:
    """Сохраняет список услуг в базу данных."""
    if not services:
        logger.warning("Попытка сохранить пустой список услуг")
        return False

    try:
        # Очищаем старые данные
        if not db_manager.clear_table("services"):
            return False
            
        # Вставляем новые данные
        insert_sql = """
        INSERT INTO services (service_name, doctor_specialty, appointment_type, price)
        VALUES (?, ?, ?, ?)
        """
        if not db_manager.execute_many(insert_sql, services):
            return False
            
        logger.info(f"Успешно сохранено {len(services)} услуг в БД")
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при сохранении в БД: {e}")
        return False

def run_price_scraper() -> bool:
    """Запускает процесс парсинга и сохранения услуг."""
    services = get_prices()
    if services:
        return save_prices_to_db(services)
    return False

def get_prices_from_db() -> List[Tuple]:
    """Получает список услуг из базы данных."""
    query = """
    SELECT service_name, doctor_specialty, appointment_type, price
    FROM services
    ORDER BY doctor_specialty, service_name
    """
    return db_manager.fetch_all(query)

def init_db():
    """Инициализирует базу данных."""
    return create_services_table()

if __name__ == '__main__':
    if init_db() and run_price_scraper():
        print("Данные успешно сохранены в базу данных")
    else:
        print("Не удалось сохранить данные в базу данных")