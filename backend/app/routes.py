import json
import markdown
import random
import hmac
import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from . import db
from .models import User, Skill, Lesson, UserProgress, Question, Achievement, Topic, UserAchievement
from .gamification import check_achievements
from .yandex_gpt import generate_questions, generate_answer

bp = Blueprint('main', __name__)

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'static', 'avatars'))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def shuffle_options(options, correct_idx):
    """Перемешивает варианты ответов, возвращает (shuffled_list, new_correct_idx)."""
    if not options or correct_idx >= len(options):
        return options, correct_idx
    correct_value = options[correct_idx]
    shuffled = list(options)
    random.shuffle(shuffled)
    new_correct_idx = shuffled.index(correct_value)
    return shuffled, new_correct_idx

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('Все поля обязательны', 'danger')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html')
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Неверное имя или пароль', 'danger')
    return render_template('login.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    # Уровень: каждые 100 XP
    level = (current_user.xp // 100) + 1
    xp_for_next = 100 - (current_user.xp % 100)
    xp_percent = ((current_user.xp % 100) / 100) * 100

    total_lessons = Lesson.query.count()
    completed_lessons = UserProgress.query.filter_by(user_id=current_user.id, completed=True).count()
    progress_percent = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    # Последние пройденные уроки (до 10)
    recent_progress = (
        UserProgress.query
        .filter_by(user_id=current_user.id, completed=True)
        .order_by(UserProgress.completed_at.desc())
        .limit(10)
        .all()
    )
    recent_lessons = []
    for rp in recent_progress:
        les = Lesson.query.get(rp.lesson_id)
        if les:
            topics = Topic.query.filter_by(lesson_id=les.id).all()
            questions = Question.query.filter_by(lesson_id=les.id).all()
            tq = len(topics) + len(questions)
            pct = int((rp.score / tq) * 100) if tq > 0 else 0
            pct = min(pct, 100)
            recent_lessons.append({
                'title': les.title,
                'score': rp.score,
                'total': tq,
                'percentage': pct,
                'xp_earned': rp.xp_earned,
                'completed_at': rp.completed_at
            })

    # Прогресс по навыкам
    all_skills = Skill.query.order_by(Skill.order).all()
    skill_progress = []
    for skill in all_skills:
        total = Lesson.query.filter_by(skill_id=skill.id).count()
        completed = UserProgress.query.filter_by(
            user_id=current_user.id, skill_id=skill.id, completed=True
        ).count()
        pct = int((completed / total) * 100) if total > 0 else 0
        skill_progress.append({
            'id': skill.id,
            'title': skill.title,
            'icon': skill.icon,
            'difficulty': skill.difficulty,
            'total': total,
            'completed': completed,
            'percent': pct
        })

    # Достижения
    achievements = (
        UserAchievement.query
        .filter_by(user_id=current_user.id)
        .order_by(UserAchievement.unlocked_at.desc())
        .all()
    )
    achievement_details = []
    for ua in achievements:
        ach = Achievement.query.get(ua.achievement_id)
        if ach:
            achievement_details.append({
                'name': ach.name,
                'description': ach.description,
                'icon': ach.icon,
                'unlocked_at': ua.unlocked_at
            })

    # Общая активность за сегодня
    today = datetime.utcnow().date()
    today_count = UserProgress.query.filter(
        UserProgress.user_id == current_user.id,
        UserProgress.completed == True,
        db.func.date(UserProgress.completed_at) == today
    ).count()

    return render_template(
        'dashboard.html',
        user=current_user,
        level=level,
        xp_for_next=xp_for_next,
        xp_percent=xp_percent,
        progress_percent=progress_percent,
        recent_lessons=recent_lessons,
        skill_progress=skill_progress,
        achievements=achievement_details,
        today_count=today_count,
        has_progress=completed_lessons > 0
    )

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            flash('Все поля обязательны', 'danger')
        elif not check_password_hash(current_user.password_hash, current_password):
            flash('Текущий пароль неверен', 'danger')
        elif not hmac.compare_digest(new_password.encode('utf-8'), confirm_password.encode('utf-8')):
            flash('Новые пароли не совпадают', 'danger')
        elif len(new_password) < 6:
            flash('Новый пароль должен содержать не менее 6 символов', 'danger')
        else:
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Пароль успешно изменён!', 'success')

    return render_template('profile.html', user=current_user)

@bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'}), 400
    # Проверка размера файла (макс. 2 МБ)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    max_size = 2 * 1024 * 1024  # 2 МБ
    if file_size > max_size:
        return jsonify({'success': False, 'message': 'Файл не должен превышать 2 МБ'}), 400

    if file and allowed_file(file.filename):
        try:
            ext = os.path.splitext(file.filename)[1].lower()
            filename = f"{uuid.uuid4().hex}{ext}"
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            print(f"[AVATAR] Saved to: {file_path}")
            if current_user.avatar:
                old_path = os.path.join(UPLOAD_FOLDER, current_user.avatar)
                try:
                    os.remove(old_path)
                    print(f"[AVATAR] Deleted old avatar: {old_path}")
                except FileNotFoundError:
                    print(f"[AVATAR] Old avatar already gone: {old_path}")
                except OSError as e:
                    print(f"[AVATAR] Failed to delete old avatar {old_path}: {e}")
            current_user.avatar = filename
            db.session.commit()
            print(f"[AVATAR] User {current_user.id} avatar updated to: {filename}")
            return jsonify({'success': True, 'message': 'Аватар обновлён'})
        except Exception as e:
            logger.error(f"Avatar upload error: {e}")
            return jsonify({'success': False, 'message': 'Ошибка при сохранении файла'}), 500
    else:
        return jsonify({'success': False, 'message': 'Недопустимый формат'}), 400

@bp.route('/delete_avatar', methods=['POST'])
@login_required
def delete_avatar():
    if current_user.avatar:
        old_path = os.path.join(UPLOAD_FOLDER, current_user.avatar)
        print(f"[AVATAR] Deleting: {old_path}")
        try:
            os.remove(old_path)
            print(f"[AVATAR] Deleted: {old_path}")
        except FileNotFoundError:
            print(f"[AVATAR] File not found: {old_path}")
        except OSError as e:
            print(f"[AVATAR] Failed to delete {old_path}: {e}")
        current_user.avatar = None
        db.session.commit()
        print(f"[AVATAR] User {current_user.id} avatar set to None")
        return jsonify({'success': True, 'message': 'Аватар удалён'})
    return jsonify({'success': False, 'message': 'Аватар не найден'}), 400

@bp.route('/skills')
@login_required
def skills():
    all_skills = Skill.query.order_by(Skill.order).all()
    progress_records = UserProgress.query.filter_by(user_id=current_user.id).all()
    completed_lessons = {p.lesson_id for p in progress_records if p.completed}

    # Словарь прогресса для шаблона
    progress = {}
    for p in progress_records:
        lesson = Lesson.query.get(p.lesson_id)
        total_q = (len(lesson.topics) + len(lesson.questions)) if lesson else 0
        progress[p.lesson_id] = {
            'score': p.score,
            'completed': p.completed,
            'attempts': p.attempts,
            'xp_earned': p.xp_earned,
            'total_questions': total_q,
        }

    # Группировка по difficulty (beginner, intermediate, advanced)
    grouped = {}
    for skill in all_skills:
        diff = skill.difficulty or 'other'
        if diff not in grouped:
            grouped[diff] = []
        grouped[diff].append(skill)

    # Порядок уровней для табов
    level_order = ['beginner', 'intermediate', 'advanced']
    levels = [l for l in level_order if l in grouped]
    # Добавляем остальные категории, если есть
    for key in grouped:
        if key not in levels:
            levels.append(key)

    return render_template(
        'skills.html',
        grouped_skills=grouped,
        levels=levels,
        completed_lessons=completed_lessons,
        progress=progress,
        user=current_user
    )

@bp.route('/lesson/<int:lesson_id>')
@login_required
def lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    topics = Topic.query.filter_by(lesson_id=lesson_id).order_by(Topic.order).all()
    questions = Question.query.filter_by(lesson_id=lesson_id).order_by(Question.order).all()

    progress = UserProgress.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id, completed=True
    ).first()

    reset = request.args.get('reset', 'false').lower() == 'true'
    if progress and not reset:
        flash('Вы уже прошли этот урок! Нажмите «Пройти заново», чтобы попробовать ещё раз.', 'info')

    # Сериализация данных для JSON-передачи в JavaScript
    # Преобразуем Markdown-контент в HTML
    topics_data = []
    for t in topics:
        html_content = markdown.markdown(t.content, extensions=['extra', 'codehilite', 'toc']) if t.content else ''
        topics_data.append({
            'id': t.id,
            'title': t.title,
            'content': html_content,
            'question': t.question,
            'order': t.order,
        })
    # Перемешиваем варианты ответов с сохранением правильного индекса
    questions_data = []
    for q in questions:
        opts = q.options
        try:
            if isinstance(opts, str):
                opts = json.loads(opts)
        except json.JSONDecodeError:
            opts = []
        if isinstance(opts, list) and len(opts) > 0:
            correct_idx = q.correct_answer if q.correct_answer is not None else 0
            shuffled, new_correct = shuffle_options(opts, correct_idx)
            questions_data.append({
                'id': q.id,
                'text': q.text,
                'options': shuffled,
                'correct_answer': new_correct,
                'explanation': q.explanation or ''
            })
        else:
            questions_data.append({
                'id': q.id,
                'text': q.text,
                'options': opts,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation or ''
            })

    # Перемешиваем варианты в вопросах внутри тем
    for t in topics_data:
        if t.get('question') and t['question'].get('options'):
            opts = t['question']['options']
            if isinstance(opts, list) and len(opts) > 0:
                correct_idx = t['question'].get('correct', 0) if t['question'].get('correct') is not None else 0
                shuffled, new_correct = shuffle_options(list(opts), correct_idx)
                t['question']['options'] = shuffled
                t['question']['correct'] = new_correct
    lesson_data = {'id': lesson.id, 'title': lesson.title, 'description': lesson.description, 'difficulty': lesson.difficulty, 'xp_reward': lesson.xp_reward}

    # XP за прохождение: 10 XP за каждый вопрос
    total_xp = (len(topics) + len(questions)) * 10

    # Ищем следующий урок
    next_lesson = Lesson.query.filter(
        Lesson.skill_id == lesson.skill_id,
        Lesson.order > lesson.order
    ).order_by(Lesson.order).first()

    if not next_lesson:
        current_skill = Skill.query.get(lesson.skill_id)
        if current_skill:
            next_skill = Skill.query.filter(
                Skill.order > current_skill.order
            ).order_by(Skill.order).first()
            if next_skill:
                next_lesson = Lesson.query.filter_by(
                    skill_id=next_skill.id
                ).order_by(Lesson.order).first()

    return render_template('lesson.html', lesson=lesson, topics=topics, questions=questions, topics_data=topics_data, questions_data=questions_data, lesson_data=lesson_data, total_xp=total_xp, next_lesson=next_lesson, user=current_user)

@bp.route('/submit/<int:lesson_id>', methods=['POST'])
@login_required
def submit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    topics = Topic.query.filter_by(lesson_id=lesson_id).order_by(Topic.order).all()
    questions = Question.query.filter_by(lesson_id=lesson_id).order_by(Question.order).all()

    # Ищем существующую запись прогресса
    existing = UserProgress.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id
    ).first()

    # Определяем источник данных: JSON или form-data
    if request.is_json:
        data = request.get_json()
        answers_list = data.get('answers', [])
        # Сохраняем весь объект ответа ({question_id, selected, correct}), а не только selected
        answers = {a['question_id']: a for a in answers_list}
        is_json = True
    else:
        answers = request.form
        is_json = False

    # Сбор ответов: темы (ключи: question_<id>)
    correct_count = 0
    total_questions = 0
    for topic in topics:
        if not topic.question or not topic.question.get('text'):
            continue
        total_questions += 1
        key = f'question_{topic.id}'
        ans_data = answers.get(key) if is_json else answers.get(key)
        user_ans = ans_data if not is_json else (ans_data.get('selected') if isinstance(ans_data, dict) else ans_data)
        correct_ans = topic.question.get('correct')

        # Определяем, открытый ли это вопрос (нет вариантов ответа)
        question_opts = topic.question.get('options', [])
        is_open = not question_opts or len(question_opts) == 0

        if is_open:
            # Открытый вопрос — используем флаг correct из фронтенда (проверка по ключевым словам)
            frontend_correct = ans_data.get('correct', 0) if isinstance(ans_data, dict) else 0
            if frontend_correct == 1:
                correct_count += 1
        else:
            # Закрытый вопрос — сравниваем индекс ответа с правильным индексом (из данных клиента)
            if is_json and isinstance(ans_data, dict):
                # Используем correct из клиентских данных (перемешанный индекс)
                client_correct = ans_data.get('correct')
                try:
                    user_ans = int(ans_data.get('selected'))
                except (TypeError, ValueError):
                    user_ans = None
                if user_ans is not None and user_ans == client_correct:
                    correct_count += 1
            elif not is_json:
                try:
                    user_ans = int(user_ans) if user_ans is not None else None
                except (ValueError, TypeError):
                    user_ans = None
                if user_ans == correct_ans:
                    correct_count += 1

    # Сбор ответов: вопросы (ключи: q_<id>)
    for q in questions:
        total_questions += 1
        key = f'q_{q.id}'
        ans_data = answers.get(key) if is_json else answers.get(key)
        user_ans = ans_data if not is_json else (ans_data.get('selected') if isinstance(ans_data, dict) else ans_data)
        correct_ans = q.correct_answer

        # Определяем, открытый ли это вопрос
        try:
            q_opts = json.loads(q.options) if isinstance(q.options, str) else (q.options or [])
        except json.JSONDecodeError:
            q_opts = []
        is_open = not q_opts or len(q_opts) == 0

        if is_open:
            # Открытый вопрос — используем флаг correct из фронтенда
            frontend_correct = ans_data.get('correct', 0) if isinstance(ans_data, dict) else 0
            if frontend_correct == 1:
                correct_count += 1
        else:
            # Закрытый вопрос — используем correct из клиентских данных (перемешанный индекс)
            if is_json and isinstance(ans_data, dict):
                client_correct = ans_data.get('correct')
                try:
                    user_ans = int(ans_data.get('selected'))
                except (TypeError, ValueError):
                    user_ans = None
                if user_ans is not None and user_ans == client_correct:
                    correct_count += 1
            elif not is_json:
                if not is_json and user_ans is not None:
                    try:
                        user_ans = int(user_ans)
                    except (ValueError, TypeError):
                        user_ans = None
                if user_ans == correct_ans:
                    correct_count += 1

    percentage = int((correct_count / total_questions) * 100) if total_questions > 0 else 0

    # Порог 70% для начисления XP
    xp_reward = lesson.xp_reward if percentage >= 70 else 0

    # Сохраняем / обновляем прогресс
    if existing:
        existing.attempts = (existing.attempts or 0) + 1
        if correct_count > existing.score:
            existing.score = correct_count
            existing.xp_earned = xp_reward
        existing.completed = True
        existing.completed_at = datetime.utcnow()
        progress = existing
    else:
        progress = UserProgress(
            user_id=current_user.id,
            skill_id=lesson.skill_id,
            lesson_id=lesson.id,
            completed=True,
            score=correct_count,
            xp_earned=xp_reward,
            attempts=1,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)

    # Начисляем XP пользователю (только если порог пройден)
    level_up = False
    new_level = current_user.level
    if xp_reward > 0:
        current_user.xp += xp_reward
        new_level = (current_user.xp // 50) + 1
        if new_level > current_user.level:
            current_user.level = new_level
            level_up = True

    db.session.commit()

    # Проверка достижений
    new_achievements = check_achievements(current_user)

    if is_json:
        return jsonify({
            'success': True,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'percentage': percentage,
            'xp_earned': xp_reward,
            'level_up': level_up,
            'new_level': new_level,
            'achievements': [{'name': a, 'description': ''} for a in new_achievements] if new_achievements else []
        })

    # Для form-data — старый путь с редиректом
    if new_achievements:
        flash('🏆 Вы получили новое достижение!', 'success')
    if level_up:
        flash(f'🎉 Поздравляем! Вы достигли {new_level} уровня!', 'success')

    return redirect(url_for('main.result', lesson_id=lesson.id))

@bp.route('/result/<int:lesson_id>')
@login_required
def result(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    # Ищем последнюю попытку пользователя по этому уроку
    progress = UserProgress.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id, completed=True
    ).order_by(UserProgress.completed_at.desc()).first()

    if not progress:
        flash('Вы ещё не проходили этот урок.', 'info')
        return redirect(url_for('main.lesson', lesson_id=lesson_id))

    topics = Topic.query.filter_by(lesson_id=lesson_id).all()
    questions = Question.query.filter_by(lesson_id=lesson_id).all()
    total_questions = len(topics) + len(questions)
    percentage = int((progress.score / total_questions) * 100) if total_questions > 0 else 0

    # Ищем достижения, полученные после прохождения этого урока
    new_achievements = UserAchievement.query.filter(
        UserAchievement.user_id == current_user.id,
        UserAchievement.unlocked_at >= progress.completed_at
    ).order_by(UserAchievement.unlocked_at.desc()).all()
    achievement_details = []
    for ua in new_achievements:
        ach = Achievement.query.get(ua.achievement_id)
        if ach:
            achievement_details.append(ach)

    # Ищем следующий урок в рамках того же скилла
    next_lesson = Lesson.query.filter(
        Lesson.skill_id == lesson.skill_id,
        Lesson.order > lesson.order
    ).order_by(Lesson.order).first()

    # Если следующего урока нет в этом скилле — ищем первый урок следующего скилла
    if not next_lesson:
        current_skill = Skill.query.get(lesson.skill_id)
        if current_skill:
            next_skill = Skill.query.filter(
                Skill.order > current_skill.order
            ).order_by(Skill.order).first()
            if next_skill:
                next_lesson = Lesson.query.filter_by(
                    skill_id=next_skill.id
                ).order_by(Lesson.order).first()

    return render_template('result.html',
        lesson=lesson,
        correct_count=progress.score,
        total_questions=total_questions,
        percentage=percentage,
        xp_earned=progress.xp_earned,
        user=current_user,
        achievements=achievement_details,
        next_lesson=next_lesson
    )

@bp.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.xp.desc()).limit(20).all()
    leaderboard = []
    for idx, u in enumerate(users, 1):
        # Подсчёт пройденных уроков
        lessons_count = UserProgress.query.filter_by(
            user_id=u.id, completed=True
        ).count()
        # Уровень: каждые 100 XP
        user_level = (u.xp // 100) + 1
        leaderboard.append({
            'place': idx,
            'username': u.username,
            'xp': u.xp,
            'level': user_level,
            'lessons': lessons_count,
            'avatar': u.avatar
        })
    return render_template('leaderboard.html', leaderboard=leaderboard, user=current_user)

@bp.route('/ai/ask', methods=['POST'])
@login_required
def ai_ask():
    data = request.json
    question = data.get('question', '').strip()
    context = data.get('context', 'Общий вопрос по ИБ')

    if not question:
        return jsonify({'answer': 'Пожалуйста, задайте вопрос.'})

    answer = generate_answer(question, context)
    return jsonify({'answer': answer})


@bp.route('/generate_questions/<int:lesson_id>', methods=['POST'])
@login_required
def generate_questions_route(lesson_id):
    """Генерация дополнительных вопросов через YandexGPT"""
    lesson = Lesson.query.get_or_404(lesson_id)
    topics = Topic.query.filter_by(lesson_id=lesson.id).order_by(Topic.order).all()
    if not topics:
        return jsonify({'error': 'У этого урока нет тем'}), 400

    # Используем текст первой темы как контекст для генерации
    topic_text = topics[0].content[:500]  # ограничиваем длину

    questions = generate_questions(topic_text, lesson.title, count=3)
    if not questions:
        logger.error("Не удалось сгенерировать вопросы для урока %d", lesson_id)
        return jsonify({'error': 'Не удалось сгенерировать вопросы. Попробуйте позже.'}), 500

    return jsonify({'questions': questions, 'success': True})
