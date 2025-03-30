import asyncio
import logging
import sqlite3
from fastapi import FastAPI, HTTPException, logger
from fastapi.responses import JSONResponse

from scraper.scraper_contacts import get_contacts_from_db, run_contacts_scraper
from scraper.scraper_price import get_prices_from_db, init_db, run_price_scraper
from scraper.scraper_recomendation import get_recommendations_from_db, run_recommendation_scraper
from scraper.scraper_working_hours import get_schedule_from_db, run_working_hours_scraper

app = FastAPI()
logger = logging.getLogger(__name__)


@app.get("/review")
async def review():
    return JSONResponse(
        content={
            "message": "Пожалуйста, оставьте ваш отзыв по ссылке ниже",
            "review_url": "https://example.com/review"
        }
    )

def get_db_connection():
    conn = sqlite3.connect('data_base/FAQ.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/faq")
async def get_all_questions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question FROM faqs")
    questions = cursor.fetchall()
    conn.close()
    return [dict(question) for question in questions]

@app.get("/faq/{faq_id}")
async def get_answer(faq_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM faqs WHERE id = ?", (faq_id,))
    faq = cursor.fetchone()
    conn.close()
    if faq is None:
        return JSONResponse(status_code=404, content={"message": "FAQ not found"})
    return dict(faq)

@app.get("/schedule")
async def schedule():
    """
    Получает расписание работы клиники либо из базы данных, либо запускает скрапер для получения данных.
    """
    try:
        logger.info("Запрос расписания через API")
        
        # Инициализируем БД
        if not init_db():
            logger.error("Ошибка инициализации БД")
            raise HTTPException(status_code=500, detail="Ошибка инициализации базы данных")
        
        # Пытаемся получить данные из БД
        schedule_data = await asyncio.to_thread(get_schedule_from_db)
        logger.info(f"Данные из БД: {schedule_data}")
        
        # Если в БД нет данных, запускаем скрапер
        if not schedule_data or not schedule_data[0][0]:
            logger.info("В базе данных нет данных, запускаем скрапер...")
            if await asyncio.to_thread(run_working_hours_scraper):
                schedule_data = await asyncio.to_thread(get_schedule_from_db)
                logger.info(f"Данные после скрапера: {schedule_data}")
            else:
                logger.error("Не удалось получить данные через скрапер")
                raise HTTPException(status_code=500, detail="Не удалось получить данные через скрапер")
        
        # Преобразуем данные
        result = schedule_data[0][0] if schedule_data and schedule_data[0][0] else ""
        logger.info(f"Возвращаемые данные: {result}")
        
        return {
            "status": "success",
            "data": result,
            "count": 1 if result else 0,
            "source": "database" if schedule_data and schedule_data[0][0] else "scraper"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    
@app.get("/contacts")
async def contacts():
    """
    Получает список контактов (адресов) либо из базы данных, либо запускает скрапер для получения данных.
    """
    try:
        # Инициализируем БД (если еще не создана)
        if not init_db():
            raise HTTPException(status_code=500, detail="Ошибка инициализации базы данных")
        
        # Пытаемся получить данные из БД
        contacts = get_contacts_from_db()
        
        # Если в БД нет данных, запускаем скрапер
        if not contacts:
            logger.info("В базе данных нет данных, запускаем скрапер...")
            if run_contacts_scraper():
                contacts = get_contacts_from_db()
            else:
                raise HTTPException(status_code=500, detail="Не удалось получить данные через скрапер")
        
        # Преобразуем данные в удобный для API формат
        result = [address[0] for address in contacts] if contacts else []
        
        return {
            "status": "success",
            "data": result,
            "count": len(result),
            "source": "database" if contacts else "scraper"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении контактов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@app.get("/price")
async def price():
    """
    Получает список услуг либо из базы данных, либо запускает скрапер для получения данных.
    """
    try:
        # Инициализируем БД (если еще не создана)
        if not init_db():
            raise HTTPException(status_code=500, detail="Ошибка инициализации базы данных")
        
        # Пытаемся получить данные из БД
        prices = get_prices_from_db()
        
        # Если в БД нет данных, запускаем скрапер
        if not prices:
            logger.info("В базе данных нет данных, запускаем скрапер...")
            if run_price_scraper():
                prices = get_prices_from_db()
            else:
                raise HTTPException(status_code=500, detail="Не удалось получить данные через скрапер")
        
        # Преобразуем данные в удобный для API формат
        result = [
            {
                "service_name": item[0],
                "doctor_specialty": item[1],
                "appointment_type": item[2],
                "price": item[3]
            }
            for item in prices
        ]
        
        return {
            "status": "success",
            "data": result,
            "count": len(result),
            "source": "database" if prices else "scraper"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")


@app.get("/recomendation")
async def recomendation():
    """
    Получает список рекомендаций либо из базы данных, либо запускает скрапер для получения данных.
    """
    try:
        # Инициализируем БД (если еще не создана)
        if not init_db():
            raise HTTPException(status_code=500, detail="Ошибка инициализации базы данных")
        
        # Пытаемся получить данные из БД
        recommendations = get_recommendations_from_db()
        
        # Если в БД нет данных, запускаем скрапер
        if not recommendations:
            logger.info("В базе данных нет данных, запускаем скрапер...")
            if run_recommendation_scraper():
                recommendations = get_recommendations_from_db()
            else:
                raise HTTPException(status_code=500, detail="Не удалось получить данные через скрапер")
        
        # Преобразуем данные в удобный для API формат
        result = [
            {
                "analysis_type": item[0],
                "recommendations": item[1].split('\n')  # Разбиваем на список
            }
            for item in recommendations
        ]
        
        return {
            "status": "success",
            "data": result,
            "count": len(result),
            "source": "database" if recommendations else "scraper"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")