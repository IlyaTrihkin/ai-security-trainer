#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
from pathlib import Path
from app.models import Skill, Lesson, Question, Achievement

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Skill, Lesson, Question

app = create_app()

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

with app.app_context():
    # Удаляем старые данные
    db.drop_all()
    db.create_all()

    # 1. Загружаем скиллы
    skills_data = load_json('data/skills.json')
    skills_map = {}
    for skill_data in skills_data:
        skill = Skill(**skill_data)
        db.session.add(skill)
        skills_map[skill_data['id']] = skill
    db.session.commit()
    print(f"✅ Загружено {len(skills_data)} скиллов")

    # 2. Загружаем уроки из папки data/lessons/
    lessons_dir = Path('data/lessons')
    for lesson_file in sorted(lessons_dir.glob('*.json')):
        lesson_data = load_json(lesson_file)
        lesson = Lesson(**lesson_data)
        db.session.add(lesson)
        # Запоминаем урок для связи с вопросами
        lesson_title = lesson_data['title']
        print(f"   📘 Загружен урок: {lesson_title}")
    db.session.commit()
    print(f"✅ Загружено {Lesson.query.count()} уроков")

    # 3. Загружаем вопросы из папки data/questions/
    questions_dir = Path('data/questions')
    for q_file in sorted(questions_dir.glob('*.json')):
        questions_data = load_json(q_file)
        for q_data in questions_data:
            # Находим урок по названию
            lesson = Lesson.query.filter_by(title=q_data['lesson_title']).first()
            if lesson:
                question = Question(
                    lesson_id=lesson.id,
                    type=q_data['type'],
                    data=q_data['data'],
                    points=q_data['points'],
                    order=q_data['order']
                )
                db.session.add(question)
            else:
                print(f"   ⚠️ Урок '{q_data['lesson_title']}' не найден для вопроса")
    db.session.commit()
    print(f"✅ Загружено {Question.query.count()} вопросов")

    print("\n🎉 База данных успешно инициализирована!")

    # 4. Загружаем достижения
    achievements_data = load_json('data/achievements.json')
    for ach_data in achievements_data:
        ach = Achievement(**ach_data)
        db.session.add(ach)
    db.session.commit()
    print(f"✅ Загружено {Achievement.query.count()} достижений")
