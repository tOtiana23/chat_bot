import asyncio
import logging
import os
from aiogram import Bot, F
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import BotCommand, BotCommandScopeDefault

# Конфигурация и ключи API
from config import TELEGRAM_TOKEN, DEEPGRAM_API_KEY, GIGACHAT_API_KEY
from integration.gigachat import GigaChatService, GigaChatIntentDetector, InMemoryStateManager
from integration.deepgram import DeepgramService
from integration.analysis import AnalysisProcessor
from integration.reminder import ReminderService
# Импорт обработчиков
from handlers import (
    TextMessageHandler, 
    VoiceMessageHandler, DocumentMessageHandler, faq_callback_handler, 
    faq_command, operator, price_command, recomendation_callback_handler, 
    recomendation_command, start_command, help_command, schedule_command, 
    contacts_command, review, qrcode_command, unknown_command, 
    process_specialty_selection
)


# Настройки логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Инициализация сервисов
chat_service = GigaChatService()
intent_detector = GigaChatIntentDetector(chat_service)
state_manager = InMemoryStateManager()
speech_service = DeepgramService(api_key=DEEPGRAM_API_KEY, bot_token=TELEGRAM_TOKEN)
analysis_processor = AnalysisProcessor(gigachat_api_key=GIGACHAT_API_KEY)
reminder_service = ReminderService(bot)

handlers = [
    TextMessageHandler(chat_service, intent_detector, state_manager, reminder_service),
    VoiceMessageHandler(chat_service, intent_detector, state_manager, speech_service),
    DocumentMessageHandler(analysis_processor),
]

for handler in handlers:
     handler.register_handlers(dp)


# Регистрация обработчиков сообщений и команд
dp.callback_query.register(process_specialty_selection, lambda c: c.data.startswith("specialty_"))
dp.callback_query.register(recomendation_callback_handler, lambda c: c.data.startswith('rec_'))
dp.callback_query.register(faq_callback_handler, F.data.startswith("faq_"))

dp.message.register(start_command, Command("start"))
dp.message.register(help_command, Command("help"))
dp.message.register(schedule_command, Command("schedule"))
dp.message.register(faq_command, Command("faq"))
dp.message.register(faq_command, F.text.in_(["FAQ", "Частые вопросы"]))
dp.message.register(contacts_command, Command("contacts"))
dp.message.register(price_command, Command("price"))
dp.message.register(recomendation_command, Command("recomendation"))
dp.message.register(operator, Command("operator"))
dp.message.register(review, Command("review"))
dp.message.register(qrcode_command, Command("qrcode"))
dp.message.register(unknown_command)

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="review", description="Оставить отзыв"),
        BotCommand(command="price", description="Узнать цены"),
        BotCommand(command="faq", description="Частые вопросы"),
        BotCommand(command="schedule", description="Время работы"),
        BotCommand(command="contacts", description="Контакты клиник"),
        BotCommand(command="recomendation", description="Рекомендации"),
        BotCommand(command="operator", description="Связаться с оператором"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
