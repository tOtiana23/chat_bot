from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
import logging
import os
import asyncio

from aiogram.types import BotCommand, BotCommandScopeDefault
from handlers import (
    faq_callback_handler,
    faq_command,
    operator,
    price_command,
    recomendation_callback_handler,
    recomendation_command,
    start_command,
    help_command,
    schedule_command,
    contacts_command,
    review,
    qrcode_command,
    unknown_command,
)
from handlers import process_specialty_selection

# Настройки и инициализация бота
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7268521429:AAE7e3LUX2pXawePYBxdV5L86GRmpzZqD0g")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

dp.callback_query.register(process_specialty_selection, lambda c: c.data.startswith("specialty_"))
dp.callback_query.register(recomendation_callback_handler, lambda c: c.data.startswith('rec_'))

# Регистрация обработчиков команд
dp.message.register(start_command, Command("start"))
dp.message.register(help_command, Command("help"))
dp.message.register(schedule_command, Command("schedule"))
dp.message.register(faq_command, Command("faq"))
dp.message.register(faq_command, F.text == "FAQ")
dp.message.register(faq_command, F.text == "Частые вопросы")
dp.callback_query.register(faq_callback_handler, F.data.startswith("faq_"))

dp.message.register(contacts_command, Command("contacts"))
dp.message.register(price_command, Command("price"))
dp.message.register(recomendation_command, Command("recomendation"))
dp.message.register(operator, Command("operator"))
dp.message.register(review, Command("review"))

dp.message.register(qrcode_command, Command("qrcode"))

dp.message.register(unknown_command)

async def set_bot_commands(bot: Bot):
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
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
    
async def main():
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())