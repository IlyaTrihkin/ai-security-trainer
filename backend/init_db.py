#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Skill, Lesson, Question

app = create_app()

with app.app_context():
    # Удаляем старые данные (если нужно)
    db.drop_all()
    db.create_all()

    # --- Создаём скиллы ---
    skill1 = Skill(
        title="Основы безопасности",
        description="Базовые навыки безопасного поведения в интернете и на рабочем месте.",
        difficulty="beginner",
        icon="🛡️",
        order=1
    )
    skill2 = Skill(
        title="Социальная инженерия",
        description="Распознавание и предотвращение атак социальной инженерии.",
        difficulty="intermediate",
        icon="🎣",
        order=2,
        parent_skill_id=None
    )
    skill3 = Skill(
        title="Управление паролями",
        description="Правила создания, хранения и использования паролей.",
        difficulty="beginner",
        icon="🔐",
        order=3
    )
    skill4 = Skill(
        title="Фишинг",
        description="Как распознать фишинговые письма и сайты.",
        difficulty="intermediate",
        icon="📧",
        order=4
    )
    skill5 = Skill(
        title="Защита от вредоносного ПО",
        description="Основы защиты от вирусов, троянов и других угроз.",
        difficulty="intermediate",
        icon="🦠",
        order=5
    )
    skill6 = Skill(
        title="Безопасность в соцсетях",
        description="Как защитить свои данные в социальных сетях.",
        difficulty="beginner",
        icon="🌐",
        order=6
    )
    db.session.add_all([skill1, skill2, skill3, skill4, skill5, skill6])
    db.session.commit()

    # --- Создаём уроки для скилла "Фишинг" (skill4) ---
    lesson1 = Lesson(
        skill_id=skill4.id,
        title="Что такое фишинг?",
        content="Фишинг — это вид мошенничества, при котором злоумышленники пытаются получить ваши данные (пароли, номера карт, коды) под видом легальных организаций. Чаще всего фишинг распространяется через электронные письма, SMS или поддельные сайты.",
        order=1
    )
    lesson2 = Lesson(
        skill_id=skill4.id,
        title="Как распознать фишинговое письмо?",
        content="Признаки фишинга:\n1. Необычный адрес отправителя (например, support@arnazon.com вместо amazon.com)\n2. Срочный запрос ('Ваш аккаунт будет заблокирован!')\n3. Подозрительные ссылки (наведите курсор, чтобы увидеть реальный URL)\n4. Орфографические ошибки и странная грамматика.\n5. Запрос личной информации (пароль, СНИЛС, код подтверждения).",
        order=2
    )
    lesson3 = Lesson(
        skill_id=skill4.id,
        title="Правило «Стоп-проверка»",
        content="Перед тем как перейти по ссылке или ввести данные, всегда:\n1. Остановись.\n2. Проверь адрес отправителя и URL.\n3. Если сомневаешься — позвони в компанию по официальному номеру.",
        order=3
    )
    db.session.add_all([lesson1, lesson2, lesson3])
    db.session.commit()

    # --- Создаём вопросы для уроков ---

    # Вопрос для урока "Что такое фишинг?" (выбор правильного ответа)
    q1 = Question(
        lesson_id=lesson1.id,
        type="choice",
        data={
            "question": "Что такое фишинг?",
            "options": [
                "Вид рыбной ловли",
                "Мошенничество с целью получения личных данных",
                "Программа для взлома паролей",
                "Антивирусное ПО"
            ],
            "correct": 1
        },
        points=10,
        order=1
    )

    # Вопрос для урока "Что такое фишинг?" (выбор правильного ответа)
    q2 = Question(
        lesson_id=lesson1.id,
        type="choice",
        data={
            "question": "Каким способом чаще всего распространяется фишинг?",
            "options": [
                "Через электронные письма",
                "Через телефонные звонки",
                "Через почтовые отправления",
                "Через личные встречи"
            ],
            "correct": 0
        },
        points=10,
        order=2
    )

    # Вопрос для урока "Как распознать фишинговое письмо?" (выбор всех правильных ответов — тип sort)
    q3 = Question(
        lesson_id=lesson2.id,
        type="choice",
        data={
            "question": "Выберите все признаки фишингового письма:",
            "options": [
                "Необычный адрес отправителя",
                "Приветствие по имени",
                "Срочный запрос на действия",
                "Орфографические ошибки",
                "Наличие вложений"
            ],
            "correct": [0, 2, 3]
        },
        points=15,
        order=1
    )

    # Вопрос для урока "Правило «Стоп-проверка»" (диалог — выбор ответа)
    q4 = Question(
        lesson_id=lesson3.id,
        type="choice",
        data={
            "question": "Вам пришло письмо от «банка» с просьбой срочно обновить данные по ссылке. Ваши действия:",
            "options": [
                "Перейду по ссылке и обновлю данные",
                "Позвоню в банк по официальному номеру и проверю информацию",
                "Отправлю письмо другу для проверки",
                "Проигнорирую письмо, но ничего не предприму"
            ],
            "correct": 1
        },
        points=15,
        order=1
    )

    db.session.add_all([q1, q2, q3, q4])
    db.session.commit()

    print("✅ База данных успешно инициализирована!")
    print(f"Создано скиллов: {Skill.query.count()}")
    print(f"Создано уроков: {Lesson.query.count()}")
    print(f"Создано вопросов: {Question.query.count()}")
