import json
from backend.app import create_app, db
from backend.app.models import Lesson, Topic, Question, Skill

app = create_app()
with app.app_context():
    with open('backend/data/lessons_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    for lesson_data in data['lessons']:
        existing = Lesson.query.filter_by(title=lesson_data['title'], skill_id=lesson_data['skill_id']).first()
        if existing:
            print(f'Урок "{lesson_data["title"]}" уже существует, пропускаем')
            continue
        lesson = Lesson(
            skill_id=lesson_data['skill_id'],
            title=lesson_data['title'],
            description=lesson_data['description'],
            difficulty=lesson_data['difficulty'],
            xp_reward=lesson_data['xp_reward'],
            duration_minutes=lesson_data.get('duration_minutes'),
            order=lesson_data.get('order', 1),
            homework_text=lesson_data.get('homework_text'),
            practice_config=json.dumps(lesson_data.get('practice_config')) if lesson_data.get('practice_config') else None
        )
        db.session.add(lesson)
        db.session.flush()
        for topic_data in lesson_data.get('topics', []):
            topic = Topic(
                lesson_id=lesson.id,
                title=topic_data['title'],
                content=topic_data['content'],
                order=topic_data.get('order', 1)
            )
            db.session.add(topic)
        for q_data in lesson_data.get('questions', []):
            question = Question(
                lesson_id=lesson.id,
                text=q_data['text'],
                options=json.dumps(q_data.get('options', [])),
                correct_answer=q_data.get('correct_answer', 0),
                explanation=q_data.get('explanation', '')
            )
            db.session.add(question)
        db.session.commit()
        print(f'✅ Загружен урок: {lesson.title}')