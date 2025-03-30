import io
import librosa
import numpy as np
import wave
from aiogram import Bot
import logging
import aiohttp
import requests

logger = logging.getLogger(__name__)

class DeepgramService:
    def __init__(self, api_key: str, bot_token: str):
        """Инициализация сервиса Deepgram с API-ключом и токеном бота."""
        self.api_key = api_key
        self.bot_token = bot_token
        self.api_url = "https://api.deepgram.com/v1/listen"

    async def download_ogg(self, bot: Bot, file_id: str) -> io.BytesIO:
        """Загрузка голосового сообщения из Telegram и сохранение в OGG."""
        try:
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"

            response = requests.get(file_url)
            if response.status_code == 200:
                logger.debug(f"OGG-файл скачан, размер: {len(response.content)} байт")
                return io.BytesIO(response.content)
            else:
                logger.error(f"Ошибка загрузки OGG: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Ошибка при скачивании OGG: {e}")
            return None

    async def process_voice_message(self, bot: Bot, file_id: str) -> str:
        """Обработка голосового сообщения с конвертацией и распознаванием текста."""
        try:
            # Скачиваем OGG файл
            ogg_data = await self.download_ogg(bot, file_id)
            if not ogg_data:
                return "Ошибка при загрузке файла"

            # Конвертируем OGG в WAV с использованием librosa
            y, sr = librosa.load(ogg_data, sr=16000, mono=True)  # Загружаем аудио и приводим к моно

            # Сохраняем в WAV для отладки
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # моно
                wav_file.setsampwidth(2)  # 16 бит
                wav_file.setframerate(sr)  # 16000 Гц
                wav_file.writeframes((y * 32767).astype(np.int16).tobytes())

            wav_bytes = wav_buffer.getvalue()
            logger.info(f"WAV-файл создан, размер: {len(wav_bytes)} байт")

            # Теперь передаем распознанный WAV в Deepgram API
            return await self.recognize_speech(wav_bytes)
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения: {e}")
            return "Ошибка при обработке голосового сообщения"

    async def recognize_speech(self, audio_data: bytes) -> str:
        """Распознавание речи через Deepgram API."""
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",
        }
        params = {"model": "general", "language": "ru"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, data=audio_data, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript")
                        if transcript:
                            logger.info(f"Распознанный текст: {transcript}")
                            return transcript
                        else:
                            logger.warning("Текст не распознан")
                            return "Не удалось распознать текст"
                    else:
                        logger.error(f"Ошибка распознавания: {response.status}")
                        return f"Ошибка распознавания: {response.status}"
        except Exception as e:
            logger.error(f"Ошибка при отправке в Deepgram: {e}")
            return "Ошибка при отправке в Deepgram"