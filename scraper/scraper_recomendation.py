import os
import requests
import logging
from bs4 import BeautifulSoup
import re
from .db_operations import DatabaseManager

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
DATABASE = "data_base/recommendations.db"
URL_RECOMMENDATIONS = "https://clinica.chitgma.ru/informatsiya-po-otdeleniyu-12"
URL_ADDITIONAL_RECOMMENDATIONS = "https://clinica.chitgma.ru/informatsiya-po-otdeleniyu-13"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Инициализация менеджера базы данных
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data_base", "recommendations.db")
db_manager = DatabaseManager(DB_PATH)

def create_recommendations_table():
    """Создает таблицу рекомендаций в базе данных."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS analysis_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_type TEXT NOT NULL,
        recommendations TEXT NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    return db_manager.create_table(create_table_sql)

def extract_recommendations(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Парсит рекомендации из HTML-кода страницы."""
    analysis_patterns = {
        'кровь': r'Подготовка пациента к (процедуре сдачи|сдаче)?\s*крови',
        'общий анализ мочи': r'Сбор мочи для общего анализа',
        'суточный анализ мочи': r'Сбор суточной мочи для биохимического анализа',
        'спермограмма': r'Правила сдачи спермограммы',
        'моча (микробиологическое исследование)': r'Требования к забору мочи для микробиологического исследования',
        'мокрота (микробиологическое исследование)': r'Требования к забору мокроты для микробиологического исследования',
        'кал (дисбактериоз)': r'Требования к забору материала для исследования кала на дисбактериоз'
    }
    recommendations_data = []
    
    # Ищем во всех текстовых элементах страницы
    for element in soup.find_all(string=True):
        parent = element.parent
        text = element.strip()
        
        # Проверяем все возможные родительские теги, включая заголовки и параграфы
        if parent.name in ['p', 'strong', 'h2', 'h3', 'h4', 'em', 'span']:
            for analysis_type, pattern in analysis_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    # Ищем следующий элемент списка (может быть не сразу после)
                    next_node = parent.find_next(['ol', 'ul'])
                    if next_node:
                        recommendations = [li.get_text(strip=True) for li in next_node.find_all('li', recursive=False)]
                        if recommendations:
                            recommendations_data.append((analysis_type, "\n".join(recommendations)))
    
    return recommendations_data

def extract_recommendations_list(parent_element) -> str:
    """Извлекает список рекомендаций из следующего за элементом списка (ol/ul)."""
    next_node = parent_element.find_next(['ol', 'ul'])
    if not next_node:
        return ""
    recommendations = [li.get_text(strip=True) for li in next_node.find_all('li', recursive=False)]
    return "\n".join(recommendations)

def get_recommendations() -> list[tuple[str, str]]:
    """Скачивает рекомендации с сайта и парсит их."""
    try:
        recommendations = []
        for url in [URL_RECOMMENDATIONS, URL_ADDITIONAL_RECOMMENDATIONS]:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            recommendations.extend(extract_recommendations(soup))
        return list(set(recommendations))
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при парсинге рекомендаций: {e}")
        return []

def save_recommendations_to_db(recommendations):
    """Сохраняет рекомендации в базу данных."""
    if not recommendations:
        logger.warning("Попытка сохранить пустой список рекомендаций")
        return False
    try:
        if not db_manager.clear_table("analysis_recommendations"):
            return False
        insert_sql = """
        INSERT INTO analysis_recommendations (analysis_type, recommendations)
        VALUES (?, ?)
        """
        if not db_manager.execute_many(insert_sql, recommendations):
            return False
        logger.info(f"Успешно сохранено {len(recommendations)} рекомендаций в БД")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении рекомендаций в БД: {e}")
        return False

from datetime import datetime, timedelta

def check_if_fresh(last_updated: str, freshness_days: int = 1) -> bool:
    """Проверяет, являются ли данные актуальными (по умолчанию, 1 день)."""
    try:
        last_date = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")  # Подстрой формат под БД
        return datetime.now() - last_date < timedelta(days=freshness_days)
    except ValueError:
        logger.error("Ошибка при разборе даты из БД")
        return False
    
def run_recommendation_scraper(force_update: bool = False) -> bool:
    """Запускает процесс скрапинга и сохранения рекомендаций."""
    if not force_update:
        result = db_manager.fetch_all("SELECT last_updated FROM analysis_recommendations ORDER BY last_updated DESC LIMIT 1")
        if result:  # Проверяем, есть ли данные
            last_updated = result[0][0]  # Берем первую запись
            if check_if_fresh(last_updated):  # Предполагается, что check_if_fresh определен
                logger.info("Данные в БД актуальны, пропускаем сканирование")
                return True

    recommendations = get_recommendations()
    if recommendations:
        return save_recommendations_to_db(recommendations)
    return False

def get_recommendations_from_db() -> list[tuple]:
    """Получает рекомендации из базы данных."""
    query = """
    SELECT analysis_type, recommendations 
    FROM analysis_recommendations
    ORDER BY analysis_type
    """
    return db_manager.fetch_all(query)

def init_db():
    """Инициализирует базу данных."""
    return create_recommendations_table()

if __name__ == "__main__":
    if init_db() and run_recommendation_scraper():
        print("Данные успешно сохранены в базу данных")
    else:
        print("Не удалось сохранить данные в базу данных")
