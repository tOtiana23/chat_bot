# services.py
import logging
from typing import Optional
import gigachat
from gigachat.models import Chat, Messages, MessagesRole
from interfaces import ChatService, IntentDetector, StateManager
from config import GIGACHAT_API_KEY, STATE_NORMAL

logger = logging.getLogger(__name__)

class GigaChatService(ChatService):
    async def get_response(self, prompt: str) -> str:
        """Отправляет запрос к GigaChat и возвращает ответ."""
        try:
            with gigachat.GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False) as giga:
                messages = [
                    Messages(role=MessagesRole.SYSTEM, content="Ты полезный помощник в Telegram боте для больницы."),
                    Messages(role=MessagesRole.USER, content=prompt)
                ]
                response = giga.chat(Chat(messages=messages))
                logger.debug(f"Ответ от GigaChat: {response.choices[0].message.content}")
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка при запросе к GigaChat: {e}")
            return "Извините, произошла ошибка при обработке запроса."

class GigaChatIntentDetector(IntentDetector):
    def __init__(self, chat_service: ChatService):
        """Инициализация детектора намерений с сервисом чата."""
        self.chat_service = chat_service

    async def detect(self, user_input: str) -> Optional[str]:
        """Определяет намерение пользователя на основе ввода для всех команд."""
        prompt = f"""
        Ты — классификатор намерений. Тебе дан запрос пользователя. Определи его намерение и верни ТОЛЬКО цифру от 1 до 9.
        Варианты:
        1. Оставить отзыв (триггеры: "отзыв", "feedback", "жалоба", "хочу пожаловаться", "хочу оставить отзыв", "/review")
        2. Узнать цены (триггеры: "цена", "стоимость", "прайс", "сколько стоит", "/price")
        3. Часто задаваемые вопросы (триггеры: "вопросы", "faq", "часто задаваемые", "/faq")
        4. Время работы клиники (триггеры: "расписание", "график", "время работы", "/schedule")
        5. Контакты (триггеры: "контакты", "адрес", "телефон", "где находится", "/contacts")
        6. Рекомендации для анализов (триггеры: "рекомендации", "правила", "подготовка", "/recomendation")
        7. Установить напоминание (триггеры: "напомни", "напомнить", "установи напоминание", "запись к", "выпить таблетки", "/remind")
        8. Связь с оператором (триггеры: "оператор", "регистратура", "связаться", "передать сообщение", "/operator")
        9. Другое (если не подходит под 1-8)

        Запрос: "{user_input}"

        Верни ТОЛЬКО одну цифру: 1, 2, 3, 4, 5, 6, 7, 8 или 9. Никакого другого текста!
        """
        response = await self.chat_service.get_response(prompt)
        return response.strip() if response else "9"  # Возвращаем "9" по умолчанию при ошибке

class InMemoryStateManager(StateManager):
    def __init__(self):
        """Инициализация менеджера состояний в памяти."""
        self.user_states = {}

    def get_state(self, user_id: int) -> int:
        """Возвращает текущее состояние пользователя или нормальное по умолчанию."""
        return self.user_states.get(user_id, STATE_NORMAL)

    def set_state(self, user_id: int, state: int) -> None:
        """Устанавливает состояние для пользователя."""
        self.user_states[user_id] = state
        logger.debug(f"Установлено состояние {state} для пользователя {user_id}")