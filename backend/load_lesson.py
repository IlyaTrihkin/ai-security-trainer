#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Lesson, Topic, Question

app = create_app()

def load_lessons(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        for lesson_data in data.get('lessons', []):
            title = lesson_data['title']
            skill_id = lesson_data['skill_id']

            # Check if lesson already exists
            existing = Lesson.query.filter_by(title=title, skill_id=skill_id).first()
            if existing:
                print(f"⚠️  Урок '{title}' уже существует (id={existing.id}). Удаляю и пересоздаю...")
                # Delete associated topics first
                Topic.query.filter_by(lesson_id=existing.id).delete()
                db.session.delete(existing)
                db.session.flush()

            # Create lesson
            lesson = Lesson(
                skill_id=skill_id,
                title=title,
                description=lesson_data.get('description'),
                difficulty=lesson_data.get('difficulty', 'Начальный'),
                xp_reward=lesson_data.get('xp_reward', 10),
                duration_minutes=lesson_data.get('duration_minutes', 30),
                order=lesson_data.get('order', 0),
                homework_text=lesson_data.get('homework_text'),
                practice_config=lesson_data.get('practice_config'),
            )
            db.session.add(lesson)
            db.session.flush()  # get lesson.id

            # Create topics
            topics_count = 0
            for topic_data in lesson_data.get('topics', []):
                topic = Topic(
                    lesson_id=lesson.id,
                    title=topic_data['title'],
                    content=topic_data['content'],
                    question=topic_data.get('question', {}),
                    order=topic_data.get('order', 0),
                )
                db.session.add(topic)
                topics_count += 1

            # Create questions
            questions_count = 0
            for i, q_data in enumerate(lesson_data.get('questions', [])):
                question = Question(
                    lesson_id=lesson.id,
                    text=q_data['text'],
                    options=q_data.get('options', '[]'),
                    correct_answer=q_data.get('correct_answer', 0),
                    explanation=q_data.get('explanation', ''),
                    order=i,
                )
                db.session.add(question)
                questions_count += 1

            db.session.commit()
            print(f"✅ Урок '{title}' загружен: {topics_count} тем, {questions_count} вопросов")

        print("\n🎉 Все уроки успешно загружены!")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Загрузка уроков из JSON')
    parser.add_argument(
        '--file', '-f',
        default=os.path.join(os.path.dirname(__file__), 'data', 'lessons_full.json'),
        help='Путь к JSON-файлу с уроками'
    )
    args = parser.parse_args()
    load_lessons(args.file)