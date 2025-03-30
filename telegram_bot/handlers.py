from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import requests
import asyncio
import logging
import re
import os
from slugify import slugify
from unidecode import unidecode
from authorization import add_user, init_db, get_user_id
from QRcode import generate_qr


API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")
logger = logging.getLogger(__name__)

async def start_command(message: types.Message):
    await message.reply('Всегда рад помочь! Обращайся'
    '\n\nНажми /help, если хочешь узнать, что я умею')

async def help_command(message: types.Message):
    await message.reply('''Давай расскажу тебе, чему я уже научился. Если что-то заинтересует, просто нажимай на это слово! 🐢

/review - если хочешь оставить отзыв на нашу клинику

/price - если хочешь узнать цены на услуги

/faq - если хочешь почитать часто задаваемые вопросы

/schedule - если хочешь узнать время работы клиники

/contacts - если хочешь узнать где находятся наши подразделения и их номера телефонов

/recomendation - если хочешь узнать правила и рекомендации для сдачи некоторых анализов
                        
/remind - если хочешь, чтоб я тебе напомнил выпить таблетку или о записи к врачу (напомню за день и за два часа)
                        
/operator - если хочешь, чтоб с тобой связались из регистратуры или передать какое-то сообщение
                        
А если ты отправишь мне документ с результатами анализов, то я могу рассказать, какие показатели выше, ниже или в норме, дать некоторые рекомендации, а также определить срочность обращения к врачу. Но не забывай, что я всего лишь черепашка, а не настоящий врач

Также я умею выполнять эти действия не только по конкретной команде, но и если ты попросишь меня сделать это простыми словами. А еще я могу распознать команды в голосовых сообщениях. Что ты хочешь узнать? ☺️''')

async def schedule_command(message: types.Message):
    try:
        # Получаем данные о расписании из API
        response = await asyncio.to_thread(requests.get, f"{API_URL}/schedule")
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем структуру ответа
        if not isinstance(data, dict) or 'data' not in data:
            await message.reply("Информация о расписании временно недоступна")
            return
            
        schedule_text = data['data']
        
        if not schedule_text:
            await message.reply("Расписание работы не найдено")
            return
            
        # Форматируем вывод
        schedule_lines = schedule_text.split('\n')
        formatted_schedule = "🕒 Режим работы клиники:\n\n" + "\n".join(
            f"• {line}" for line in schedule_lines
        )
        
        await message.reply(formatted_schedule)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе расписания: {e}")
        await message.reply("⚠️ Не удалось загрузить расписание. Проблема с соединением.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка при обработке расписания")

async def contacts_command(message: types.Message):
    try:
        # Получаем данные о контактах из API
        response = await asyncio.to_thread(requests.get, f"{API_URL}/contacts")
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем структуру ответа
        if not isinstance(data, dict) or 'data' not in data:
            await message.reply("Информация о контактах временно недоступна")
            return
            
        contacts = data['data']
        
        if not contacts:
            await message.reply("Контактные данные не найдены")
            return
            
        # Форматируем вывод
        formatted_contacts = []
        for i, contact in enumerate(contacts, 1):
            # Разделяем адрес и телефон
            parts = contact.split(" Телефон")
            address = parts[0].replace("Адрес: ", "").strip()
            phone = "Телефон" + parts[1] if len(parts) > 1 else ""
            
            # Форматируем каждый контакт
            contact_entry = f"{i}. {address}"
            if phone:
                contact_entry += f"\n   {phone}"
            
            formatted_contacts.append(contact_entry)
        
        # Отправляем сообщение с контактами
        contacts_message = "📌 Контакты клиники:\n\n" + "\n\n".join(formatted_contacts)
        await message.reply(contacts_message)
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе контактов: {e}")
        await message.reply("⚠️ Не удалось загрузить контакты. Проблема с соединением.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка при обработке контактов")

async def unknown_command(message: types.Message):
    if message.text.startswith('/'):
        await message.reply('''Извини, с этим я помочь не могу(

Но ты всегда можешь позвонить в клинику и там тебе обязательно подскажут!
Вот номер для связи 8 (3022) 73-70-73🐢''')

def clean_specialty(specialty):
    """Удаляет стоп-слова, исправляет падеж и обрабатывает слова через дефис."""
    if not specialty:
        return ""
    
    stop_words = {"врача", "первичный", "для", "на", "по", "в", "и", "из", "с", 
                 "медицинский", "доктор", "специалист", "прием", "осмотр", "консультация"}
    
    # Удаляем "врача-" в начале
    specialty = re.sub(r'^врача[- ]?', '', specialty, flags=re.IGNORECASE)
    
    # Разбиваем на слова (включая слова через '-')
    words = re.split(r'[\s\-]+', specialty.strip().lower())

    # Фильтруем стоп-слова и убираем "а" на конце каждого слова
    cleaned_words = []
    for word in words:
        if word not in stop_words:
            # Удаляем окончание "а" только у существительных женского рода
            if word.endswith('а') and len(word) > 1:
                word = word[:-1]
            cleaned_words.append(word.capitalize())

    # Восстанавливаем дефисы между составными словами
    result = " ".join(cleaned_words)
    return result.replace(" - ", "-").title()

async def price_command(message: types.Message):
    try:
        # Получаем данные о ценах из API
        response = await asyncio.to_thread(requests.get, f"{API_URL}/price")
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or 'data' not in data:
            await message.reply("Информация о ценах временно недоступна")
            return

        services = data['data']
        if not services:
            await message.reply("Данные о ценах не найдены")
            return

        # Группируем услуги по врачам
        categories = {}
        for service in services:
            specialty = service['doctor_specialty']
            cleaned_specialty = clean_specialty(specialty)
            
            if cleaned_specialty not in categories:
                categories[cleaned_specialty] = []
            categories[cleaned_specialty].append(service)

        # Создаем inline-клавиатуру
        keyboard = InlineKeyboardBuilder()
        for specialty in sorted(categories.keys()):
            # Используем очищенное название для отображения
            display_name = specialty
            callback_data = f"specialty_{slugify(specialty, separator='_')}"
            
            keyboard.button(text=display_name, callback_data=callback_data)

        keyboard.adjust(2)
        await message.reply("Выбери врача:", reply_markup=keyboard.as_markup())

    except Exception as e:
        logger.error(f"Ошибка в price_command: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка при обработке данных о ценах")


async def process_specialty_selection(callback_query: types.CallbackQuery):
    try:
        await callback_query.answer("Обрабатываем...")

        # Получаем slug из callback_data
        specialty_slug = callback_query.data.replace("specialty_", "")
        
        # Получаем все услуги
        response = await asyncio.to_thread(requests.get, f"{API_URL}/price")
        response.raise_for_status()
        services = response.json()['data']

        # Находим все услуги, где slug совпадает
        found_services = []
        for service in services:
            if specialty_slug == slugify(clean_specialty(service['doctor_specialty']), separator='_'):
                found_services.append(service)

        if not found_services:
            await callback_query.answer("Нет доступных услуг для этого врача.")
            return

        # Получаем очищенное название специальности для заголовка
        specialty_name = clean_specialty(found_services[0]['doctor_specialty'])

        # Форматируем вывод
        message_text = f"<b>🏥 {specialty_name}</b>\n\n"
        for service in found_services:
            price = f"{service['price']:,.2f} ₽".replace(',', ' ')
            message_text += (
                f"• <b>{service['service_name']}</b>\n"
                f"  <i>{service.get('appointment_type', 'не указано')}</i>\n"
                f"  <b>{price}</b>\n\n"
            )

        await callback_query.message.answer(message_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка в process_specialty_selection: {e}", exc_info=True)
        await callback_query.message.answer("❌ Ошибка при получении данных о враче.")


# Санитизация callback_data с кодированием

async def recomendation_command(message: types.Message):
    try:
        # Получаем данные о рекомендациях из API
        response = await asyncio.to_thread(requests.get, f"{API_URL}/recomendation")
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем структуру ответа
        if not isinstance(data, dict) or 'data' not in data:
            await message.reply("Информация о рекомендациях временно недоступна")
            return
            
        recommendations = data['data']
        
        if not recommendations:
            await message.reply("Рекомендации не найдены")
            return
            
        # Создаем клавиатуру с кнопками для каждого анализа
        keyboard = InlineKeyboardBuilder()
        
        for item in recommendations:
            analysis_type = item['analysis_type']
            # Используем slugify для создания callback_data
            callback_data = f"rec_{slugify(analysis_type, separator='_')}"
            keyboard.button(text=analysis_type, callback_data=callback_data)
        
        # Располагаем кнопки по 2 в ряду
        keyboard.adjust(2)
        
        await message.answer(
            "📋 Выбери анализ, чтобы увидеть рекомендации по подготовке:",
            reply_markup=keyboard.as_markup()
        )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        await message.reply("⚠️ Не удалось загрузить рекомендации. Проблема с соединением.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка при обработке рекомендаций")

async def recomendation_callback_handler(callback_query: types.CallbackQuery):
    try:
        await callback_query.answer()
        
        # Получаем slug анализа из callback_data
        analysis_slug = callback_query.data.replace("rec_", "")
        
        # Получаем все рекомендации
        response = await asyncio.to_thread(requests.get, f"{API_URL}/recomendation")
        response.raise_for_status()
        recommendations = response.json()['data']
        
        # Находим нужный анализ
        selected_analysis = None
        for item in recommendations:
            if analysis_slug == slugify(item['analysis_type'], separator='_'):
                selected_analysis = item
                break
        
        if not selected_analysis:
            await callback_query.message.answer("Рекомендации для этого анализа не найдены")
            return
            
        # Форматируем вывод
        analysis_type = selected_analysis['analysis_type']
        rec_list = selected_analysis['recommendations']
        
        analysis_block = f"<b>🔬 {analysis_type.upper()}</b>\n\n"
        for point in rec_list:
            analysis_block += f"▪️ {point.strip()}\n"
        
        # Отправляем сообщение с рекомендациями
        await callback_query.message.answer(analysis_block, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка в recomendation_callback_handler: {e}", exc_info=True)
        await callback_query.message.answer("❌ Произошла ошибка при загрузке рекомендаций")


async def faq_command(message: types.Message):
    try:
        # Получаем вопросы с API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/faq") as response:
                if response.status != 200:
                    error_text = await response.text()
                    await message.answer("⚠️ Ошибка при загрузке вопросов. Попробуйте позже.")
                    return

                questions = await response.json()

                # Валидация и подготовка кнопок
                buttons = []
                for item in questions:
                    try:
                        if isinstance(item, dict) and 'id' in item and 'question' in item:
                            buttons.append(
                                types.InlineKeyboardButton(
                                    text=item['question'][:64],  # Ограничение длины
                                    callback_data=f"faq_{item['id']}"
                                )
                            )
                    except Exception:
                        continue  # Пропускаем некорректные вопросы

                # Гарантированно правильное создание клавиатуры
                if not buttons:
                    await message.answer("ℹ️ Нет доступных вопросов.")
                    return

                # Создаем клавиатуру с явным указанием inline_keyboard
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[[btn] for btn in buttons]  # Каждая кнопка в отдельном ряду
                )

                await message.answer(
                    "📋 Выберите вопрос:",
                    reply_markup=keyboard
                )

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")

    except aiohttp.ClientError as e:
        await message.answer(f"Ошибка подключения: {str(e)}")
    except Exception as e:
        await message.answer(f"Неожиданная ошибка: {str(e)}")


async def faq_callback_handler(callback_query: types.CallbackQuery):
    try:
        # Извлекаем ID вопроса
        try:
            faq_id = int(callback_query.data.split('_')[1])
        except (IndexError, ValueError):
            await callback_query.answer("Неверный формат вопроса", show_alert=True)
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/faq/{faq_id}") as response:
                # Проверяем статус ответа
                if response.status != 200:
                    error_text = await response.text()
                    await callback_query.answer(
                        f"Не удалось загрузить ответ (код {response.status})",
                        show_alert=True
                    )
                    return

                # Парсим JSON
                try:
                    faq = await response.json()
                except Exception as e:
                    await callback_query.answer("Ошибка при разборе ответа", show_alert=True)
                    return

                # Проверяем структуру ответа
                if not isinstance(faq, dict) or 'question' not in faq or 'answer' not in faq:
                    await callback_query.answer("Неверный формат ответа", show_alert=True)
                    return

                # Форматируем и отправляем ответ
                answer = (
                    f"<b>❓ Вопрос:</b>\n{faq['question']}\n\n"
                    f"<b>💡 Ответ:</b>\n{faq['answer']}"
                )
                
                try:
                    await callback_query.message.answer(answer, parse_mode='HTML')
                    await callback_query.answer()
                except Exception as e:
                    await callback_query.answer(f"Ошибка при отправке: {str(e)}", show_alert=True)

    except aiohttp.ClientError as e:
        await callback_query.answer(f"Ошибка подключения: {str(e)}", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Неожиданная ошибка: {str(e)}", show_alert=True)

async def review(message: types.Message):
    # Создаем инлайн-кнопку с ссылкой
    review_button = InlineKeyboardButton(
        text="Оставить отзыв", 
        url="https://2gis.ru/chita/firm/9007727535719962/tab/reviews/addreview"
    )
    
    # Передаем кнопку сразу при создании клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[review_button]])
    
    await message.answer(
        "Ты можешь оставить свой отзыв о нас на 2ГИС, нажав на кнопочку ниже 🐢👇:",
        reply_markup=keyboard
    )

# Команда для генерации QR-кода. Запускается отдельно от старта бота
async def qrcode_command(message: types.Message):
    init_db()
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown User"

    # Проверка пользователя в базе
    user_record_id = get_user_id(user_id)
    
    if user_record_id is None:
        user_record_id = add_user(username, user_id)
        if user_record_id is None:
            await message.reply("❌ Ошибка регистрации!")
            return
        await message.reply("✅ Вы успешно зарегистрированы!")
    else:
        await message.reply("ℹ️ Вы уже зарегистрированы.")

    # Генерация QR-кода
    qr_result = generate_qr(user_record_id)
    if qr_result is None:
        await message.reply("❌ Ошибка генерации QR-кода!")
        return
    
    _, qr_file_path = qr_result  # Используем только путь к файлу

    try:
        # Правильный способ отправки файла в Aiogram 3.x
        from aiogram.types import FSInputFile
        
        # Отправляем файл с диска
        photo = FSInputFile(qr_file_path)
        await message.reply_photo(
            photo=photo,
            caption=f"🎉 Ваш QR-код, {username}!\n\nПривязка ID: {user_record_id}"
        )
        
    except Exception as e:
        print(f"Ошибка отправки: {str(e)}")
        await message.reply("❌ Не удалось отправить QR-код. Попробуйте позже.")


async def operator(message: types.Message):
    try:
        # Получаем текст сообщения после команды /operator
        user_message = message.text.replace('/operator', '').strip()
        
        if not user_message:
            await message.reply("Напиши, что ты хочешь передать после команды /operator")
            return
        
        # Ваш chat_id (замените на ваш реальный ID)
        YOUR_CHAT_ID = 963221752  # Здесь должен быть ваш реальный chat_id
        username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
        # Отправляем сообщение админу (мне пока)
        await message.bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=f"⚠️ Новое сообщение от пользователя:\n"
                 f"ID: {username}\n"
                 f"Имя: {message.from_user.full_name}\n"
                 f"Сообщение: {user_message}"
        )
        
        # Подтверждаем пользователю
        await message.reply("✅ Я отправил твоё сообщение администратору. Спасибо!")
        
    except Exception as e:
        logger.error(f"Ошибка в функции problem: {e}")
        await message.reply("❌ Произошла ошибка при отправке сообщения")
