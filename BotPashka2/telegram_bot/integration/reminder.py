from aiogram import Bot
from datetime import datetime, timedelta
import asyncio
import logging
from integration.gigachat import GigaChatService 

logger = logging.getLogger(__name__)

class ReminderService:
    """Сервис для обработки и управления напоминаниями."""

    def __init__(self, bot: Bot):
        """Инициализация сервиса напоминаний."""
        self.bot = bot
        self.reminders = {}
        self.chat_service = GigaChatService()  # Инициализация GigaChat

    async def parse_reminder(self, text: str) -> tuple[datetime | None, str | None, str | None]:
        prompt = (
            "Извлеки из текста дату, время и содержание напоминания. "
            "Верни ответ в формате: 'день: <число>, месяц: <название месяца>, время: <часы:минуты>, текст: <содержание>, тип: <pills или doctor>'. "
            "Пример текста: 'напомни мне 31 марта в 14:00, что мне надо выпить таблетки'. "
            f"Текст для обработки: '{text}'"
        )
        
        try:
            response = await self.chat_service.get_response(prompt)
            logger.debug(f"Ответ от GigaChat: {response}")
            
            # Очищаем ответ от лишних пробелов и символов
            response = response.strip()
            
            # Разбиваем строку на части по запятой и удаляем лишние пробелы
            parts = [part.strip() for part in response.split(",")]
            
            # Создаем словарь из частей
            data = {}
            for part in parts:
                if ": " in part:
                    key, value = part.split(": ", 1)
                    data[key.strip()] = value.strip()
                else:
                    logger.warning(f"Некорректная часть: {part}")
            
            # Проверяем наличие всех необходимых ключей
            required_keys = ["день", "месяц", "время", "текст", "тип"]
            if not all(key in data for key in required_keys):
                logger.error(f"Отсутствуют ключи в ответе GigaChat: {data}")
                return None, None, None
            
            day = int(data["день"])
            month_str = data["месяц"].lower()
            time = data["время"]
            reminder_text = data["текст"]
            reminder_type = data["тип"]
            
            months = {
                'января': 1, 'январь': 1,
                'февраля': 2, 'февраль': 2,
                'марта': 3, 'март': 3,
                'апреля': 4, 'апрель': 4,
                'мая': 5, 'май': 5,
                'июня': 6, 'июнь': 6,
                'июля': 7, 'июль': 7,
                'августа': 8, 'август': 8,
                'сентября': 9, 'сентябрь': 9,
                'октября': 10, 'октябрь': 10,
                'ноября': 11, 'ноябрь': 11,
                'декабря': 12, 'декабрь': 12
            }
            
            if month_str not in months:
                logger.error(f"Некорректный месяц: {month_str}")
                return None, None, None
            
            month = months[month_str]
            hours, minutes = map(int, time.split(':'))
            current_year = datetime.now().year
            reminder_time = datetime(current_year, month, day, hours, minutes)
            
            if reminder_time < datetime.now():
                reminder_time = reminder_time.replace(year=current_year + 1)
                
            return reminder_time, reminder_text, reminder_type
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга ответа GigaChat: {e}. Ответ: {response}")
            return None, None, None
        except Exception as e:
            logger.error(f"Неизвестная ошибка при работе с GigaChat: {e}")
            return None, None, None

    async def set_reminder(self, user_id: int, reminder_time: datetime, message: str, reminder_type: str):
        """Устанавливает напоминание для пользователя."""
        if user_id not in self.reminders:
            self.reminders[user_id] = []
                
        self.reminders[user_id].append((reminder_time, message, reminder_type))
        logger.info(f"Установлено напоминание для {user_id}: {message} на {reminder_time}")
        asyncio.create_task(self._schedule_reminder(user_id, reminder_time, message, reminder_type))

    async def _schedule_reminder(self, user_id: int, reminder_time: datetime, message: str, reminder_type: str):
        """Планирует отправку напоминаний в зависимости от типа."""
        now = datetime.now()
        
        if reminder_type == 'doctor':
            one_day_before = reminder_time - timedelta(days=1)
            if one_day_before > now:
                await asyncio.sleep((one_day_before - now).total_seconds())
                await self.bot.send_message(user_id, f"Напоминание: завтра {message}")
                logger.info(f"Отправлено напоминание за день для {user_id}: {message}")

            two_hours_before = reminder_time - timedelta(hours=2)
            if two_hours_before > now:
                await asyncio.sleep((two_hours_before - now).total_seconds())
                await self.bot.send_message(user_id, f"Напоминание: через 2 часа {message}")
                logger.info(f"Отправлено напоминание за 2 часа для {user_id}: {message}")
                
        if reminder_time > now:
            await asyncio.sleep((reminder_time - now).total_seconds())
            await self.bot.send_message(user_id, f"Напоминание: {message}")
            logger.info(f"Отправлено основное напоминание для {user_id}: {message}")