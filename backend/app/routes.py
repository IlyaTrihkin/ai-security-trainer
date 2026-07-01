from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from . import db
from .models import User, Skill, Lesson, UserProgress, Question, Achievement
from .gamification import check_achievements

bp = Blueprint('main', __name__)

UPLOAD_FOLDER = 'frontend/static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    total_lessons = Lesson.query.count()
    completed_lessons = UserProgress.query.filter_by(user_id=current_user.id, completed=True).count()
    progress_percent = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
    return render_template('dashboard.html', user=current_user, progress_percent=progress_percent)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.id}_{file.filename}")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        if current_user.avatar:
            old_path = os.path.join(UPLOAD_FOLDER, current_user.avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        current_user.avatar = filename
        db.session.commit()
        return jsonify({'success': True, 'message': 'Аватар обновлён'})
    else:
        return jsonify({'success': False, 'message': 'Недопустимый формат'}), 400

@bp.route('/delete_avatar', methods=['POST'])
@login_required
def delete_avatar():
    if current_user.avatar:
        old_path = os.path.join(UPLOAD_FOLDER, current_user.avatar)
        if os.path.exists(old_path):
            os.remove(old_path)
        current_user.avatar = None
        db.session.commit()
        return jsonify({'success': True, 'message': 'Аватар удалён'})
    return jsonify({'success': False, 'message': 'Аватар не найден'}), 400

@bp.route('/skills')
@login_required
def skills():
    skills = Skill.query.order_by(Skill.order).all()
    progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    completed_lessons = {p.lesson_id for p in progress if p.completed}
    return render_template('skills.html', skills=skills, completed_lessons=completed_lessons, user=current_user)

@bp.route('/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    questions = Question.query.filter_by(lesson_id=lesson_id).order_by(Question.order).all()
    existing_progress = UserProgress.query.filter_by(
        user_id=current_user.id, lesson_id=lesson_id, completed=True
    ).first()
    if existing_progress:
        flash('Вы уже прошли этот урок!', 'info')
        return redirect(url_for('main.skills'))

    if request.method == 'POST':
        user_answers = {}
        for q in questions:
            user_answers[q.id] = request.form.get(f'question_{q.id}')
        correct_count = 0
        total_points = 0
        for q in questions:
            user_ans = user_answers.get(q.id)
            correct_ans = q.data.get('correct')
            if user_ans is not None:
                try:
                    user_ans = int(user_ans)
                except:
                    user_ans = None
            if user_ans == correct_ans:
                correct_count += 1
                total_points += q.points

        progress = UserProgress(
            user_id=current_user.id,
            skill_id=lesson.skill_id,
            lesson_id=lesson.id,
            completed=True,
            score=total_points,
            xp_earned=total_points,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
        current_user.xp += total_points
        new_level = (current_user.xp // 50) + 1
        if new_level > current_user.level:
            current_user.level = new_level
            flash(f'🎉 Поздравляем! Вы достигли {new_level} уровня!', 'success')
        db.session.commit()

        new_achievements = check_achievements(current_user)
        if new_achievements:
            flash('🏆 Вы получили новое достижение!', 'success')

        return render_template(
            'result.html',
            lesson=lesson,
            correct_count=correct_count,
            total_questions=len(questions),
            total_points=total_points,
            user=current_user
        )
    return render_template('lesson.html', lesson=lesson, questions=questions, user=current_user)

@bp.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.xp.desc()).limit(20).all()
    leaderboard = []
    for idx, u in enumerate(users, 1):
        leaderboard.append({
            'place': idx,
            'username': u.username,
            'xp': u.xp,
            'level': u.level,
            'avatar': u.avatar
        })
    return render_template('leaderboard.html', leaderboard=leaderboard, user=current_user)
