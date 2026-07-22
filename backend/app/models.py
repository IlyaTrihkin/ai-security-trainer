from flask_login import UserMixin
from datetime import datetime
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress = db.relationship('UserProgress', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='beginner')
    icon = db.Column(db.String(50), default='🔐')
    order = db.Column(db.Integer, default=0)
    parent_skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=True)
    lessons = db.relationship('Lesson', backref='skill', lazy=True)
    children = db.relationship('Skill', backref=db.backref('parent', remote_side=[id]))

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='Начальный')
    xp_reward = db.Column(db.Integer, default=10)
    duration_minutes = db.Column(db.Integer, default=30)
    order = db.Column(db.Integer, default=0)
    homework_text = db.Column(db.Text)
    practice_config = db.Column(db.JSON)
    topics = db.relationship('Topic', backref='lesson', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('Question', backref='lesson', lazy=True, cascade='all, delete-orphan')

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)   # теория по теме
    image_url = db.Column(db.String(200))
    question = db.Column(db.JSON, nullable=False)  # {text, options, correct}
    order = db.Column(db.Integer, default=0)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)  # JSON-строка с вариантами ответов
    correct_answer = db.Column(db.Integer, default=0)
    explanation = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0)
    xp_earned = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime)

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='🏆')
    condition_type = db.Column(db.String(50))
    condition_value = db.Column(db.Integer)

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
