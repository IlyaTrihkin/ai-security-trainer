from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required
from .decorators import admin_required
from .models import User, Skill, Lesson, Topic, Question, Achievement
from . import db
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def admin_index():
    stats = {
        'users': User.query.count(),
        'skills': Skill.query.count(),
        'lessons': Lesson.query.count(),
        'achievements': Achievement.query.count(),
    }
    return render_template('admin/index.html', stats=stats)


# ========================
# Пользователи
# ========================

@admin_bp.route('/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    users_pagination = query.order_by(User.id).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', users=users_pagination.items, pagination=users_pagination, search=search)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'Пользователь "{user.username}" {"разблокирован" if user.is_active else "заблокирован"}.', 'success')
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Права администратора для "{user.username}" {"выданы" if user.is_admin else "отозваны"}.', 'success')
    return redirect(url_for('admin.admin_users'))


# ========================
# Навыки
# ========================

@admin_bp.route('/skills')
@login_required
@admin_required
def admin_skills():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Skill.query
    if search:
        query = query.filter(
            (Skill.title.ilike(f'%{search}%')) |
            (Skill.description.ilike(f'%{search}%'))
        )
    skills_pagination = query.order_by(Skill.id).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/skills.html', skills=skills_pagination.items, pagination=skills_pagination, search=search)


@admin_bp.route('/skills/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_skill():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        difficulty = request.form.get('difficulty', 'beginner').strip()
        icon = request.form.get('icon', '🔐').strip()
        order = request.form.get('order', 0, type=int)
        parent_id = request.form.get('parent_skill_id', type=int)

        if not title:
            flash('Название навыка обязательно.', 'danger')
            return render_template('admin/skill_form.html', skill=None)

        skill = Skill(
            title=title,
            description=description,
            difficulty=difficulty,
            icon=icon,
            order=order,
            parent_skill_id=parent_id if parent_id else None,
        )
        db.session.add(skill)
        db.session.commit()
        flash(f'Навык "{title}" создан.', 'success')
        return redirect(url_for('admin.admin_skills'))
    return render_template('admin/skill_form.html', skill=None)


@admin_bp.route('/skills/<int:skill_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Название навыка обязательно.', 'danger')
            return render_template('admin/skill_form.html', skill=skill)

        skill.title = title
        skill.description = request.form.get('description', '').strip()
        skill.difficulty = request.form.get('difficulty', 'beginner').strip()
        skill.icon = request.form.get('icon', '🔐').strip()
        skill.order = request.form.get('order', 0, type=int)
        parent_id = request.form.get('parent_skill_id', type=int)
        skill.parent_skill_id = parent_id if parent_id else None

        db.session.commit()
        flash(f'Навык "{title}" обновлён.', 'success')
        return redirect(url_for('admin.admin_skills'))
    return render_template('admin/skill_form.html', skill=skill)


@admin_bp.route('/skills/<int:skill_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    title = skill.title
    db.session.delete(skill)
    db.session.commit()
    flash(f'Навык "{title}" удалён.', 'success')
    return redirect(url_for('admin.admin_skills'))


# ========================
# Уроки
# ========================

@admin_bp.route('/lessons')
@login_required
@admin_required
def admin_lessons():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Lesson.query
    if search:
        query = query.filter(
            (Lesson.title.ilike(f'%{search}%'))
        )
    lessons_pagination = query.order_by(Lesson.id).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/lessons.html', lessons=lessons_pagination.items, pagination=lessons_pagination, search=search)


@admin_bp.route('/lessons/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_lesson():
    skills = Skill.query.order_by(Skill.title).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Название урока обязательно.', 'danger')
            return render_template('admin/lesson_form.html', lesson=None, skills=skills)

        lesson = Lesson(
            title=title,
            description=request.form.get('description', '').strip(),
            difficulty=request.form.get('difficulty', 'Начальный').strip(),
            xp_reward=request.form.get('xp_reward', 10, type=int),
            duration_minutes=request.form.get('duration_minutes', 30, type=int),
            order=request.form.get('order', 0, type=int),
            skill_id=request.form.get('skill_id', type=int),
            homework_text=request.form.get('homework_text', '').strip(),
            practice_config=request.form.get('practice_config', '').strip() or None,
        )
        db.session.add(lesson)
        db.session.flush()  # получаем lesson.id до коммита

        _save_topics(lesson)
        _save_questions(lesson)

        db.session.commit()
        flash(f'Урок "{title}" создан.', 'success')
        return redirect(url_for('admin.admin_lessons'))
    return render_template('admin/lesson_form.html', lesson=None, skills=skills)


@admin_bp.route('/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    skills = Skill.query.order_by(Skill.title).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Название урока обязательно.', 'danger')
            return render_template('admin/lesson_form.html', lesson=lesson, skills=skills)

        lesson.title = title
        lesson.description = request.form.get('description', '').strip()
        lesson.difficulty = request.form.get('difficulty', 'Начальный').strip()
        lesson.xp_reward = request.form.get('xp_reward', 10, type=int)
        lesson.duration_minutes = request.form.get('duration_minutes', 30, type=int)
        lesson.order = request.form.get('order', 0, type=int)
        lesson.skill_id = request.form.get('skill_id', type=int)
        lesson.homework_text = request.form.get('homework_text', '').strip()
        lesson.practice_config = request.form.get('practice_config', '').strip() or None

        # Удаляем старые темы и вопросы, создаём новые
        Topic.query.filter_by(lesson_id=lesson.id).delete()
        Question.query.filter_by(lesson_id=lesson.id).delete()

        _save_topics(lesson)
        _save_questions(lesson)

        db.session.commit()
        flash(f'Урок "{title}" обновлён.', 'success')
        return redirect(url_for('admin.admin_lessons'))
    return render_template('admin/lesson_form.html', lesson=lesson, skills=skills)



def _save_topics(lesson):
    """Сохраняет темы из form data для урока."""
    topic_titles = request.form.getlist('topic_title')
    topic_contents = request.form.getlist('topic_content')
    topic_orders = request.form.getlist('topic_order')

    for i in range(len(topic_titles)):
        ttl = topic_titles[i].strip()
        if not ttl:
            continue
        topic = Topic(
            lesson_id=lesson.id,
            title=ttl,
            content=topic_contents[i].strip() if i < len(topic_contents) else '',
            question={'text': '', 'options': [], 'correct': 0},  # заглушка, т.к. поле NOT NULL
            order=int(topic_orders[i]) if i < len(topic_orders) and topic_orders[i] else 0,
        )
        db.session.add(topic)


def _save_questions(lesson):
    """Сохраняет вопросы из form data для урока."""
    question_texts = request.form.getlist('question_text')
    question_options = request.form.getlist('question_options')
    question_answers = request.form.getlist('question_correct_answer')
    question_explanations = request.form.getlist('question_explanation')
    question_orders = request.form.getlist('question_order')

    for i in range(len(question_texts)):
        txt = question_texts[i].strip()
        if not txt:
            continue
        q = Question(
            lesson_id=lesson.id,
            text=txt,
            options=question_options[i].strip() if i < len(question_options) else '',
            correct_answer=int(question_answers[i]) if i < len(question_answers) and question_answers[i] else 0,
            explanation=question_explanations[i].strip() if i < len(question_explanations) else '',
            order=int(question_orders[i]) if i < len(question_orders) and question_orders[i] else 0,
        )
        db.session.add(q)


@admin_bp.route('/lessons/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_lessons():
    if request.method == 'POST':
        raw = request.form.get('json_data', '').strip()
        if not raw:
            flash('Поле JSON не может быть пустым.', 'danger')
            return render_template('admin/lessons_import.html')

        # Парсим JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            flash(f'Ошибка парсинга JSON: {e}', 'danger')
            return render_template('admin/lessons_import.html')

        # Нормализуем: поддерживаем {"lessons": [...]} и одиночный объект
        if isinstance(data, dict) and 'lessons' in data:
            items = data['lessons']
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'title' in data:
            items = [data]
        else:
            flash('Неверный формат JSON. Ожидается объект с ключом "lessons", массив уроков или одиночный объект урока.', 'danger')
            return render_template('admin/lessons_import.html')

        created = 0
        updated = 0
        errors = []

        for lesson_data in items:
            title = lesson_data.get('title', '').strip()
            skill_id = lesson_data.get('skill_id')
            if not title:
                errors.append(f'Пропущен урок без названия')
                continue
            if not skill_id:
                errors.append(f'Пропущен урок «{title}»: не указан skill_id')
                continue

            # Проверяем существование skill_id
            skill = Skill.query.get(skill_id)
            if not skill:
                errors.append(f'Пропущен урок «{title}»: навык с id={skill_id} не найден')
                continue

            # Ищем существующий урок по названию + skill_id
            existing = Lesson.query.filter_by(title=title, skill_id=skill_id).first()
            if existing:
                # Обновляем существующий
                existing.description = lesson_data.get('description', '')
                existing.difficulty = lesson_data.get('difficulty', 'Начальный')
                existing.xp_reward = lesson_data.get('xp_reward', 10)
                existing.duration_minutes = lesson_data.get('duration_minutes', 30)
                existing.order = lesson_data.get('order', 0)
                existing.homework_text = lesson_data.get('homework_text')
                existing.practice_config = lesson_data.get('practice_config')
                # Удаляем старые темы и вопросы
                Topic.query.filter_by(lesson_id=existing.id).delete()
                Question.query.filter_by(lesson_id=existing.id).delete()
                db.session.flush()
                _create_topics(existing, lesson_data.get('topics', []))
                _create_questions(existing, lesson_data.get('questions', []))
                updated += 1
            else:
                lesson = Lesson(
                    skill_id=skill_id,
                    title=title,
                    description=lesson_data.get('description', ''),
                    difficulty=lesson_data.get('difficulty', 'Начальный'),
                    xp_reward=lesson_data.get('xp_reward', 10),
                    duration_minutes=lesson_data.get('duration_minutes', 30),
                    order=lesson_data.get('order', 0),
                    homework_text=lesson_data.get('homework_text'),
                    practice_config=lesson_data.get('practice_config'),
                )
                db.session.add(lesson)
                db.session.flush()
                _create_topics(lesson, lesson_data.get('topics', []))
                _create_questions(lesson, lesson_data.get('questions', []))
                created += 1

        db.session.commit()

        msg_parts = []
        if created > 0:
            msg_parts.append(f'Создано уроков: {created}')
        if updated > 0:
            msg_parts.append(f'Обновлено уроков: {updated}')
        if errors:
            msg_parts.append(f'Ошибок: {len(errors)}')
            for err in errors:
                flash(err, 'warning')
        if msg_parts:
            flash(', '.join(msg_parts), 'success')
        elif not errors:
            flash('Не найдено уроков для импорта.', 'info')

        return redirect(url_for('admin.admin_lessons'))

    return render_template('admin/lessons_import.html')


def _create_topics(lesson, topics_data):
    for topic_data in topics_data:
        topic = Topic(
            lesson_id=lesson.id,
            title=topic_data.get('title', ''),
            content=topic_data.get('content', ''),
            question=topic_data.get('question', {}),
            order=topic_data.get('order', 0),
        )
        db.session.add(topic)


def _create_questions(lesson, questions_data):
    for i, q_data in enumerate(questions_data):
        options = q_data.get('options', '[]')
        if isinstance(options, list):
            options = json.dumps(options, ensure_ascii=False)
        question = Question(
            lesson_id=lesson.id,
            text=q_data.get('text', ''),
            options=options,
            correct_answer=q_data.get('correct_answer', 0),
            explanation=q_data.get('explanation', ''),
            order=q_data.get('order', i),
        )
        db.session.add(question)


@admin_bp.route('/lessons/<int:lesson_id>/export')
@login_required
@admin_required
def export_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    topics = Topic.query.filter_by(lesson_id=lesson_id).order_by(Topic.order).all()
    questions = Question.query.filter_by(lesson_id=lesson_id).order_by(Question.order).all()

    data = {
        'title': lesson.title,
        'skill_id': lesson.skill_id,
        'description': lesson.description,
        'difficulty': lesson.difficulty,
        'xp_reward': lesson.xp_reward,
        'duration_minutes': lesson.duration_minutes,
        'order': lesson.order,
        'homework_text': lesson.homework_text,
        'practice_config': lesson.practice_config,
        'topics': [
            {
                'title': t.title,
                'content': t.content,
                'question': t.question if isinstance(t.question, dict) else json.loads(t.question),
                'order': t.order,
            }
            for t in topics
        ],
        'questions': [
            {
                'text': q.text,
                'options': q.options,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation,
                'order': q.order,
            }
            for q in questions
        ],
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        json_str,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=lesson_{lesson_id}.json'
        }
    )


@admin_bp.route('/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    title = lesson.title
    db.session.delete(lesson)
    db.session.commit()
    flash(f'Урок "{title}" удалён.', 'success')
    return redirect(url_for('admin.admin_lessons'))


# ========================
# Достижения
# ========================

@admin_bp.route('/achievements')
@login_required
@admin_required
def admin_achievements():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    query = Achievement.query
    if search:
        query = query.filter(
            (Achievement.name.ilike(f'%{search}%')) |
            (Achievement.description.ilike(f'%{search}%'))
        )
    achievements_pagination = query.order_by(Achievement.id).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/achievements.html', achievements=achievements_pagination.items, pagination=achievements_pagination, search=search)


@admin_bp.route('/achievements/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_achievement():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', '🏆').strip()
        condition_type = request.form.get('condition_type', '').strip()
        condition_value = request.form.get('condition_value', 0, type=int)
        xp_reward = request.form.get('xp_reward', 0, type=int)

        if not name:
            flash('Название достижения обязательно.', 'danger')
            return render_template('admin/achievement_form.html', achievement=None)

        achievement = Achievement(
            name=name,
            description=description,
            icon=icon,
            condition_type=condition_type,
            condition_value=condition_value,
            xp_reward=xp_reward,
        )
        db.session.add(achievement)
        db.session.commit()
        flash(f'Достижение "{name}" создано.', 'success')
        return redirect(url_for('admin.admin_achievements'))
    return render_template('admin/achievement_form.html', achievement=None)


@admin_bp.route('/achievements/<int:achievement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Название достижения обязательно.', 'danger')
            return render_template('admin/achievement_form.html', achievement=achievement)

        achievement.name = name
        achievement.description = request.form.get('description', '').strip()
        achievement.icon = request.form.get('icon', '🏆').strip()
        achievement.condition_type = request.form.get('condition_type', '').strip()
        achievement.condition_value = request.form.get('condition_value', 0, type=int)
        achievement.xp_reward = request.form.get('xp_reward', 0, type=int)

        db.session.commit()
        flash(f'Достижение "{name}" обновлено.', 'success')
        return redirect(url_for('admin.admin_achievements'))
    return render_template('admin/achievement_form.html', achievement=achievement)


@admin_bp.route('/achievements/<int:achievement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)
    name = achievement.name
    db.session.delete(achievement)
    db.session.commit()
    flash(f'Достижение "{name}" удалено.', 'success')
    return redirect(url_for('admin.admin_achievements'))


@admin_bp.route('/achievements/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_achievements():
    if request.method == 'POST':
        raw = request.form.get('json_data', '').strip()
        if not raw:
            flash('Поле JSON не может быть пустым.', 'danger')
            return render_template('admin/achievements_import.html')

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            flash(f'Ошибка парсинга JSON: {e}', 'danger')
            return render_template('admin/achievements_import.html')

        if isinstance(data, dict) and 'achievements' in data:
            items = data['achievements']
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'name' in data:
            items = [data]
        else:
            flash('Неверный формат JSON. Ожидается объект с ключом "achievements", массив достижений или одиночный объект достижения.', 'danger')
            return render_template('admin/achievements_import.html')

        created = 0
        updated = 0
        errors = []

        for ach_data in items:
            name = ach_data.get('name', '').strip()
            if not name:
                errors.append(f'Пропущено достижение без названия')
                continue

            existing = Achievement.query.filter_by(name=name).first()
            if existing:
                existing.description = ach_data.get('description', '')
                existing.icon = ach_data.get('icon', '🏆')
                existing.condition_type = ach_data.get('condition_type')
                existing.condition_value = ach_data.get('condition_value', 0)
                existing.xp_reward = ach_data.get('xp_reward', 0)
                updated += 1
            else:
                achievement = Achievement(
                    name=name,
                    description=ach_data.get('description', ''),
                    icon=ach_data.get('icon', '🏆'),
                    condition_type=ach_data.get('condition_type'),
                    condition_value=ach_data.get('condition_value', 0),
                    xp_reward=ach_data.get('xp_reward', 0),
                )
                db.session.add(achievement)
                created += 1

        db.session.commit()

        msg_parts = []
        if created > 0:
            msg_parts.append(f'Создано достижений: {created}')
        if updated > 0:
            msg_parts.append(f'Обновлено достижений: {updated}')
        if errors:
            msg_parts.append(f'Ошибок: {len(errors)}')
            for err in errors:
                flash(err, 'warning')
        if msg_parts:
            flash(', '.join(msg_parts), 'success')
        elif not errors:
            flash('Не найдено достижений для импорта.', 'info')

        return redirect(url_for('admin.admin_achievements'))

    return render_template('admin/achievements_import.html')


@admin_bp.route('/achievements/<int:achievement_id>/export')
@login_required
@admin_required
def export_achievement(achievement_id):
    achievement = Achievement.query.get_or_404(achievement_id)

    data = {
        'name': achievement.name,
        'description': achievement.description,
        'icon': achievement.icon,
        'condition_type': achievement.condition_type,
        'condition_value': achievement.condition_value,
        'xp_reward': achievement.xp_reward,
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        json_str,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=achievement_{achievement_id}.json'
        }
    )


@admin_bp.route('/achievements/export-all')
@login_required
@admin_required
def export_all_achievements():
    achievements = Achievement.query.order_by(Achievement.id).all()
    data = {
        'achievements': [
            {
                'name': a.name,
                'description': a.description,
                'icon': a.icon,
                'condition_type': a.condition_type,
                'condition_value': a.condition_value,
                'xp_reward': a.xp_reward,
            }
            for a in achievements
        ]
    }

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        json_str,
        mimetype='application/json',
        headers={
            'Content-Disposition': 'attachment; filename=achievements.json'
        }
    )
