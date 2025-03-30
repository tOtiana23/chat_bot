from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    menu = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📅 Расписание"),
                KeyboardButton(text="💰 Цены")
            ],
            [
                KeyboardButton(text="❓ FAQ"),
                KeyboardButton(text="📞 Контакты")
            ],
            [
                KeyboardButton(text="📝 Отзыв"),
                KeyboardButton(text="🧪 Рекомендации")
            ],
            [
                KeyboardButton(text="👨‍⚕️ Оператор"),
                KeyboardButton(text="🔄 QR-код")
            ]
        ],
        resize_keyboard=True
    )
    return menu