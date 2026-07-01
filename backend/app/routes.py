from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User
from .models import Skill, Lesson, UserProgress
from datetime import datetime

bp = Blueprint('main', __name__)

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
            flash('Все поля обязательны для заполнения', 'danger')
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
        
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
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
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/skills')
@login_required
def skills():
    skills = Skill.query.order_by(Skill.order).all()
    progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    # Превращаем прогресс в множество для быстрого поиска
    completed_lessons = {p.lesson_id for p in progress if p.completed}
    return render_template('skills.html', skills=skills, completed_lessons=completed_lessons, user=current_user)

@bp.route('/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    questions = Question.query.filter_by(lesson_id=lesson_id).order_by(Question.order).all()
    
    # Проверяем, не пройден ли уже урок
    existing_progress = UserProgress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id,
        completed=True
    ).first()
    if existing_progress:
        flash('Вы уже прошли этот урок!', 'info')
        return redirect(url_for('main.skills'))
    
    if request.method == 'POST':
        # Собираем ответы пользователя
        user_answers = {}
        for question in questions:
            answer_key = f'question_{question.id}'
            if question.type == 'choice':
                # Для одиночного выбора — берём одно значение
                user_answers[question.id] = request.form.get(answer_key)
            # Здесь можно добавить другие типы вопросов позже
        
        # Проверяем ответы и считаем баллы
        correct_count = 0
        total_points = 0
        for question in questions:
            user_answer = user_answers.get(question.id)
            correct_answer = question.data.get('correct')
            
            if user_answer is not None:
                # Преобразуем в int для сравнения
                try:
                    user_answer = int(user_answer)
                except (ValueError, TypeError):
                    user_answer = None
            
            if user_answer == correct_answer:
                correct_count += 1
                total_points += question.points
        
        # Сохраняем прогресс
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
        
        # Обновляем XP пользователя
        current_user.xp += total_points
        
        # Проверяем, не пора ли повысить уровень
        # Простая формула: уровень = XP // 50 + 1
        new_level = (current_user.xp // 50) + 1
        if new_level > current_user.level:
            current_user.level = new_level
            flash(f'🎉 Поздравляем! Вы достигли {new_level} уровня!', 'success')
        
        db.session.commit()
        
        # Перенаправляем на страницу результата
        return render_template(
            'result.html',
            lesson=lesson,
            correct_count=correct_count,
            total_questions=len(questions),
            total_points=total_points,
            user=current_user
        )
    
    # GET-запрос — показываем страницу урока
    return render_template('lesson.html', lesson=lesson, questions=questions, user=current_user)
