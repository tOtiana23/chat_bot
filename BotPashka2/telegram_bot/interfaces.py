# interfaces.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Union
from aiogram import Bot, Dispatcher
import io

class ChatService(ABC):
    """Абстрактный базовый класс для сервисов чата.

    Определяет интерфейс для получения ответа от чат-сервиса.
    """

    @abstractmethod
    async def get_response(self, prompt: str) -> str:
        """Получает ответ от чат-сервиса на основе переданного запроса.

        Args:
            prompt (str): Текст запроса пользователя.

        Returns:
            str: Ответ от чат-сервиса.
        """
        pass

class IntentDetector(ABC):
    """Абстрактный базовый класс для детекторов намерений.

    Определяет интерфейс для определения намерения пользователя.
    """

    @abstractmethod
    async def detect(self, user_input: str) -> Optional[str]:
        """Определяет намерение пользователя на основе ввода.

        Args:
            user_input (str): Текст ввода пользователя.

        Returns:
            Optional[str]: Код намерения (например, "1", "2", "3") или None, если намерение не определено.
        """
        pass

class StateManager(ABC):
    """Абстрактный базовый класс для управления состояниями пользователей.

    Определяет интерфейс для работы с состояниями пользователей.
    """

    @abstractmethod
    def get_state(self, user_id: int) -> int:
        """Получает текущее состояние пользователя.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            int: Текущее состояние пользователя.
        """
        pass

    @abstractmethod
    def set_state(self, user_id: int, state: int) -> None:
        """Устанавливает состояние для пользователя.

        Args:
            user_id (int): Идентификатор пользователя.
            state (int): Новое состояние.
        """
        pass

class SpeechRecognitionService(ABC):
    """Абстрактный базовый класс для сервисов распознавания речи.

    Определяет интерфейс для обработки голосовых сообщений.
    """

    @abstractmethod
    async def process_voice_message(self, bot: Bot, file_id: str) -> Optional[str]:
        """Обрабатывает голосовое сообщение и возвращает распознанный текст.

        Args:
            bot (Bot): Экземпляр бота Telegram.
            file_id (str): Идентификатор файла голосового сообщения.

        Returns:
            Optional[str]: Распознанный текст или None в случае ошибки.
        """
        pass

class AnalysisProcessorService(ABC):
    """Абстрактный базовый класс для сервисов обработки анализов.

    Определяет интерфейс для анализа данных из PDF-файлов.
    """

    @abstractmethod
    async def process_analysis(self, pdf_file: Union[str, io.BytesIO]) -> Optional[Dict[str, str]]:
        """Обрабатывает PDF-файл с анализами и возвращает структурированный результат.

        Args:
            pdf_file (Union[str, io.BytesIO]): Путь к PDF-файлу или поток BytesIO.

        Returns:
            Optional[Dict[str, str]]: Результат анализа (понижено/повышено/в норме, рекомендации и т.д.) или None в случае ошибки.
        """
        pass

class BotRunner(ABC):
    """Абстрактный базовый класс для запуска бота.

    Определяет интерфейс для запуска Telegram-бота.
    """

    @abstractmethod
    async def run(self) -> None:
        """Запускает Telegram-бота."""
        pass

class MessageHandler(ABC):
    """Абстрактный базовый класс для обработчиков сообщений.

    Определяет интерфейс для регистрации обработчиков сообщений.
    """

    @abstractmethod
    def register_handlers(self, dp: Dispatcher) -> None:
        """Регистрирует обработчики сообщений в диспетчере.

        Args:
            dp (Dispatcher): Диспетчер aiogram для регистрации обработчиков.
        """
        pass