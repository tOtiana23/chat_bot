# scraper/db_operations.py
import sqlite3
import os
from typing import Optional, List, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_directory()
        
    def _ensure_db_directory(self):
        """Создает директорию для БД, если её нет"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def get_connection(self) -> Optional[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error as e:
            logger.error(f"DB connection error: {e}")
            return None

    def is_data_fresh(self, max_age_hours: int = 24) -> bool:
        """Проверяет, актуальны ли данные в БД"""
        query = "SELECT MAX(last_updated) FROM services"
        result = self.fetch_one(query)
        
        if not result or not result[0]:
            return False
            
        last_updated = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        return datetime.now() - last_updated < timedelta(hours=max_age_hours)

    def create_table(self, create_table_sql: str):
        """Создает таблицу в базе данных."""
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            conn.execute(create_table_sql)
            conn.commit()
            logger.info("Таблица успешно создана")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблицы: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = (), commit: bool = False) -> bool:
        """Выполняет SQL-запрос с параметрами."""
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def execute_many(self, query: str, data: List[Tuple]) -> bool:
        """Выполняет массовую вставку данных."""
        conn = self.get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.executemany(query, data)
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при массовой вставке данных: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Выполняет запрос на выборку и возвращает все результаты."""
        conn = self.get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении данных: {e}")
            return []
        finally:
            conn.close()

    def clear_table(self, table_name: str) -> bool:
        """Очищает указанную таблицу."""
        return self.execute_query(f"DELETE FROM {table_name}", commit=True)