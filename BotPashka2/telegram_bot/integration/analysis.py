import logging
import re
from typing import Dict, Optional, Union
import gigachat
from gigachat.models import Chat, Messages, MessagesRole
import pdfplumber
import io
from interfaces import AnalysisProcessorService

logger = logging.getLogger(__name__)

class AnalysisProcessor(AnalysisProcessorService):
    """Сервис для обработки и анализа медицинских анализов из PDF-файлов."""

    def __init__(self, gigachat_api_key: str):
        """Инициализация процессора анализов."""
        self.api_key = gigachat_api_key
        self.reference_ranges = {
            "Базофилы": (0.0, 1.0),  # % относительное количество
            "Гематокрит": (39.0, 40.0),  # %
            "Гемоглобин": (13.2, 13.3),  # Mr/Ωη (г/дл)
            "Лейкоциты": (4.0, 5.0),  # 10^9/л
            "Лимфоциты": (4.0, 4.5),  # 10^9/л (абсолютное)
            "Лимфоциты относительное": (36.0, 37.0),  # %
            "Моноциты": (0.0, 0.6),  # 10^9/л (абсолютное)
            "Моноциты относительное": (1.0, 11.0),  # %
            "Нейтрофилы": (2.04, 5.8),  # 10^9/л (абсолютное)
            "Нейтрофилы относительное": (60.0, 72.0),  # %
            "Ширина распределения эритроцитов": (11.6, 11.8),  # %
            "Скорость оседания эритроцитов": (1.0, 15.0),  # мм/ч
            "Средняя концентрация гемоглобина": (30.0, 38.0),  # Mr/Ωη (г/дл)
            "Среднее содержание гемоглобина": (27.0, 31.0),  # пг
            "Средний объем тромбоцита": (7.4, 10.4),  # фл
            "Средний объем эритроцита": (94.0, 95.0),  # фл
            "Тромбоциты": (150.0, 400.0),  # тыс/мкл
        }

    def _extract_text_from_pdf(self, pdf_file: Union[str, io.BytesIO]) -> str:
        """Извлекает текст из PDF-файла."""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            text = re.sub(r'\s+', ' ', text).strip()
            logger.info(f"Извлечен текст из PDF (первые 100 символов): {text[:100]}...")
            return text
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста из PDF: {e}")
            return ""

    def _parse_value(self, value: str) -> Optional[float]:
        """Извлекает числовое значение из строки."""
        try:
            match = re.search(r'\d+\.?\d*', value)
            if match:
                return float(match.group())
            return None
        except ValueError as e:
            logger.error(f"Ошибка при парсинге значения {value}: {e}")
            return None

    def _extract_parameters(self, text: str) -> Dict[str, float]:
        """Извлекает параметры и их значения из текста."""
        # Улучшенное регулярное выражение
        pattern = re.compile(
            r'([А-Яа-я\s]+(?:относительное|абсолютное)?(?:количество)?(?:в крови)?(?:методом автоматизированного подсчёта|расчётным методом|по Вестергрену)?)\s+'
            r'(\d+\.?\d*)\s+(?:Нормаль(?:ный)?|Повыше(?:нный)?|Пониже(?:нный)?)'
        )
        results = {}
        matches = pattern.findall(text)

        for match in matches:
            param_name = match[0].strip()
            value = self._parse_value(match[1])
            if value is not None and "протокол" not in param_name.lower() and "страница" not in param_name.lower():
                results[param_name] = value

        logger.debug(f"Извлеченные параметры: {results}")
        return results

    def _compare_with_reference(self, param: str, value: float) -> str:
        """Сравнивает значение с референсным диапазоном."""
        normalized_param = re.sub(
            r'(?:в крови|методом автоматизированного подсчёта|расчётным методом|по вестергрену|общий|массовая концентрация|по объему|коэффициент вариации)',
            '', 
            param
        ).strip().lower()

        for ref_param, (low, high) in self.reference_ranges.items():
            normalized_ref = ref_param.lower()
            if normalized_ref in normalized_param:
                if value < low:
                    return "понижено"
                elif value > high:
                    return "повышено"
                return "в норме"
        logger.warning(f"Параметр {param} отсутствует в референтных диапазонах")
        return "Неизвестный параметр"

    def _compare_extracted_data(self, extracted_data: Dict[str, float]) -> Dict[str, Dict[str, str]]:
        """Сравнивает извлеченные данные с референсными диапазонами."""
        comparison_results = {}
        for param, value in extracted_data.items():
            status = self._compare_with_reference(param, value)
            if status != "Неизвестный параметр":
                comparison_results[param] = {"value": value, "status": status}
        logger.debug(f"Сравненные результаты: {comparison_results}")
        return comparison_results

    async def process_analysis(self, pdf_file: Union[str, io.BytesIO]) -> Optional[Dict[str, str]]:
        """Обрабатывает PDF-файл с анализами и возвращает структурированный результат."""
        try:
            pdf_text = self._extract_text_from_pdf(pdf_file)
            if not pdf_text:
                return None

            extracted_data = self._extract_parameters(pdf_text)
            comparison_results = self._compare_extracted_data(extracted_data)

            analysis_text = "\n".join([f"{param}: {data['value']} ({data['status']})" for param, data in comparison_results.items()])
            prompt = f"""
            Ты — медицинский ассистент, который анализирует результаты лабораторных исследований. Я предоставлю тебе данные анализов пациента, в которых есть отклонения. Твоя задача:
            Выводи в строгом формате:
            Повышенные показатели: (перечисление)
            Пониженные показатели: (перечисление)
            Общие рекомендации: (обязательное поле, напиши общие рекомендации, на основе анализов и отклонений от нормы. Пример, что лучше делать в таком случае. Пример, пей больше воды, гуляй на свежем воздухе, кушай больше фруктов и овощей и тому подобные)
            Необходимость обращения к врачу: (обязательное поле, да и почему требуется или нет) 
            Срочность: (обязательное поле, как срочно надо пойти к врачу на консультацию насчёт анализов. Никогда не пиши, что надо срочно)
            Дополнительные исследования: (всегда пиши в этом поле, требуется ли проведение дополнительных исследований, если да то какие)
            Вот данные анализов:
            {analysis_text}
            """

            try:
                with gigachat.GigaChat(credentials=self.api_key, verify_ssl_certs=False) as giga:
                    messages = [
                        Messages(role=MessagesRole.SYSTEM, content="Ты медицинский ассистент, специализирующийся на анализе лабораторных данных."),
                        Messages(role=MessagesRole.USER, content=prompt)
                    ]
                    # logger.debug("Отправка запроса в GigaChat...")
                    response = giga.chat(Chat(messages=messages))
                    result_text = response.choices[0].message.content
                    # logger.debug(f"Ответ от GigaChat: {result_text}")
                    return self._parse_gigachat_response(result_text, comparison_results)
            except Exception as e:
                # logger.error(f"Ошибка при запросе к GigaChat: {e}")
                return comparison_results

        except Exception as e:
            # logger.error(f"Ошибка при обработке анализов: {e}")
            return None

    def _parse_gigachat_response(self, response_text: str, comparison_results: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """Парсит ответ GigaChat в структурированный словарь."""
        result = {
            "Повышенные показатели": "",
            "Пониженные показатели": "",
            "Общие рекомендации": "",
            "Необходимость обращения к врачу": "",
            "Срочность": "",
            "Дополнительные исследования": ""
        }

        lines = response_text.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "Повышенные показатели:" in line:
                current_section = "Повышенные показатели"
                result[current_section] = line.split(":", 1)[1].strip()
            elif "Пониженные показатели:" in line:
                current_section = "Пониженные показатели"
                result[current_section] = line.split(":", 1)[1].strip()
            elif "Общие рекомендации:" in line:
                current_section = "Общие рекомендации"
                result[current_section] = line.split(":", 1)[1].strip()
            elif "Необходимость обращения к врачу:" in line:
                current_section = "Необходимость обращения к врачу"
                result[current_section] = line.split(":", 1)[1].strip()
            elif "Срочность:" in line:
                current_section = "Срочность"
                result[current_section] = line.split(":", 1)[1].strip()
            elif "Дополнительные исследования:" in line:
                current_section = "Дополнительные исследования"
                result[current_section] = line.split(":", 1)[1].strip()
            elif current_section and line:
                result[current_section] += "\n" + line

        for key in result:
            result[key] = result[key].strip()

        return result