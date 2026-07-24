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


def generate_questions(topic: str, lesson_title: str, count: int = 3) -> list:
    """
    Генерирует дополнительные вопросы по теме урока с помощью YandexGPT.
    Возвращает список вопросов с вариантами ответов и правильным ответом.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        raise ValueError("YANDEX_API_KEY и YANDEX_FOLDER_ID должны быть установлены в .env")

    prompt = f"""
    Ты — эксперт по информационной безопасности. Сгенерируй {count} дополнительных вопросов для урока «{lesson_title}» по теме «{topic}».
    Каждый вопрос должен быть в формате JSON:
    {{
        "text": "текст вопроса",
        "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
        "correct_answer": 0-3 (индекс правильного ответа),
        "explanation": "пояснение почему это правильно"
    }}
    Верни список из {count} таких объектов в формате JSON. Только JSON, без дополнительного текста.
    """

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
                "text": "Ты — эксперт по информационной безопасности, генерируешь вопросы для обучения."
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
        raise Exception(f"Ошибка YandexGPT: {response.status_code} - {response.text}")

    result = response.json()
    answer_text = result['result']['alternatives'][0]['message']['text']
    answer_text = answer_text.strip()

    logger.info("YandexGPT ответил успешно, длина ответа: %d символов", len(answer_text))

    try:
        questions = json.loads(answer_text)
        logger.info("Успешно сгенерировано %d вопросов", len(questions))
        return questions
    except json.JSONDecodeError:
        logger.warning("JSON не распарсился напрямую, пробую извлечь из markdown-блока")
        match = re.search(r'```json\s*(.*?)\s*```', answer_text, re.DOTALL)
        if match:
            questions = json.loads(match.group(1))
            logger.info("Успешно извлечено %d вопросов из markdown-блока", len(questions))
            return questions
        else:
            logger.error("Не удалось распарсить JSON от YandexGPT. Ответ: %s", answer_text)
            raise Exception("Не удалось распарсить JSON от YandexGPT")