import os
import json
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')


def extract_json(text: str):
    """
    Пытается извлечь и распарсить JSON из текста, пробуя несколько стратегий.
    Возвращает распарсенные данные или None.
    """
    # 1. Попытка распарсить весь текст как JSON
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Поиск JSON в markdown-блоках
    patterns = [
        r'```json\s*(.*?)\s*```',        # ```json ... ```
        r'```\s*(.*?)\s*```',            # ``` ... ```
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                continue

    # 3. Поиск JSON-массива: от первой '[' до последней ']'
    start_arr = text.find('[')
    end_arr = text.rfind(']')
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        candidate = text[start_arr:end_arr + 1]
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

    # 4. Поиск JSON-объекта: от первой '{' до последней '}'
    start_obj = text.find('{')
    end_obj = text.rfind('}')
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        candidate = text[start_obj:end_obj + 1]
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def generate_questions(topic: str, lesson_title: str, count: int = 3) -> list:
    """
    Генерирует дополнительные вопросы по теме урока с помощью YandexGPT.
    Возвращает список вопросов с вариантами ответов и правильным ответом.
    При любой ошибке возвращает пустой список.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        logger.warning("YandexGPT API не настроен — YANDEX_API_KEY или YANDEX_FOLDER_ID отсутствуют")
        return []

    prompt = f"""Ты — эксперт по информационной безопасности. Сгенерируй ровно {count} дополнительных вопросов для урока «{lesson_title}» по теме «{topic}».
Каждый вопрос должен быть в формате JSON с полями: text (строка), options (массив из 4 строк), correct_answer (число 0-3 — индекс правильного варианта), explanation (строка с пояснением).
Верни ТОЛЬКО JSON-массив, без markdown-разметки, без пояснительного текста. Пример:
[{{"text": "Что такое SQL-инъекция?", "options": ["Атака на БД", "Атака на сеть", "Атака на ОС", "Атака на браузер"], "correct_answer": 0, "explanation": "SQL-инъекция — это внедрение вредоносного SQL-кода в запросы к базе данных."}}]"""

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — эксперт по информационной безопасности, генерируешь вопросы для обучения. Твой ответ — строго JSON без лишнего текста."
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    logger.info("Отправка запроса к YandexGPT для генерации вопросов по теме «%s»", topic)

    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logger.error("Ошибка YandexGPT: %s - %s", response.status_code, response.text)
        return []

    result = response.json()
    answer_text = result['result']['alternatives'][0]['message']['text']
    answer_text = answer_text.strip()

    logger.info("YandexGPT ответил успешно, длина ответа: %d символов", len(answer_text))
    logger.debug("Сырой ответ YandexGPT: %s", answer_text[:1000])

    questions = extract_json(answer_text)
    if questions is not None:
        logger.info("Успешно сгенерировано %d вопросов", len(questions) if isinstance(questions, list) else 1)
        return questions
    else:
        logger.error("Не удалось распарсить JSON от YandexGPT. Ответ (первые 1000 символов): %s", answer_text[:1000])
        return []


def generate_answer(question: str, context: str = "") -> str:
    """
    Генерирует ответ на вопрос пользователя по информационной безопасности с помощью YandexGPT.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        logger.warning("YandexGPT API не настроен — YANDEX_API_KEY или YANDEX_FOLDER_ID отсутствуют")
        return "Извините, API YandexGPT не настроен. Пожалуйста, обратитесь к администратору."

    prompt = f"""Ты — эксперт по информационной безопасности. Отвечай на вопросы пользователя чётко, по делу, с примерами, если нужно.
Контекст (если есть): {context}
Вопрос: {question}
Ответ:"""

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 1500
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты — полезный ассистент, эксперт по информационной безопасности. Отвечай кратко, но содержательно."
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    logger.info("Отправка запроса к YandexGPT для ответа на вопрос: «%s»", question[:100])

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
    except requests.exceptions.Timeout:
        logger.error("Таймаут при обращении к YandexGPT API")
        return "Извините, YandexGPT не ответил вовремя. Попробуйте позже."
    except requests.exceptions.RequestException as e:
        logger.error("Сетевая ошибка при обращении к YandexGPT: %s", e)
        return "Извините, произошла ошибка при обращении к YandexGPT. Попробуйте позже."

    if response.status_code != 200:
        logger.error("YandexGPT API error: %s - %s", response.status_code, response.text[:200])
        return "Извините, произошла ошибка при обращении к YandexGPT. Попробуйте позже."

    result = response.json()
    answer = result['result']['alternatives'][0]['message']['text']
    answer = answer.strip()

    logger.info("YandexGPT ответил успешно, длина ответа: %d символов", len(answer))
    return answer