#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Skill, Lesson, Topic, Achievement

app = create_app()

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

with app.app_context():
    db.drop_all()
    db.create_all()

    # 1. Скиллы
    skills_data = load_json('data/skills.json')
    for skill_data in skills_data:
        skill = Skill(**skill_data)
        db.session.add(skill)
    db.session.commit()
    print(f"✅ Загружено {len(skills_data)} скиллов")

    # 2. Уроки и темы
    lessons_dir = Path('data/lessons')
    topics_dir = Path('data/topics')
    for lesson_file in sorted(lessons_dir.glob('*.json')):
        lesson_data = load_json(lesson_file)
        lesson = Lesson(**lesson_data)
        db.session.add(lesson)
        db.session.flush()  # чтобы получить id урока
        
        # Загружаем темы для этого урока
        topic_file = topics_dir / f"{lesson_data['title'].replace(' ', '_')}.json"
        if topic_file.exists():
            topics_data = load_json(topic_file)
            for topic_data in topics_data:
                topic = Topic(
                    lesson_id=lesson.id,
                    title=topic_data['title'],
                    content=topic_data['content'],
                    image_url=topic_data.get('image_url'),
                    question=topic_data['question'],
                    order=topic_data.get('order', 0)
                )
                db.session.add(topic)
        print(f"   📘 Загружен урок: {lesson_data['title']} с {len(lesson.topics)} темами")
    db.session.commit()
    print(f"✅ Загружено {Lesson.query.count()} уроков, {Topic.query.count()} тем")

    # 3. Достижения
    try:
        achievements_data = load_json('data/achievements.json')
        for ach_data in achievements_data:
            ach = Achievement(**ach_data)
            db.session.add(ach)
        db.session.commit()
        print(f"✅ Загружено {Achievement.query.count()} достижений")
    except FileNotFoundError:
        print("⚠️ Файл achievements.json не найден, пропускаем")

    print("\n🎉 База данных успешно инициализирована!")
