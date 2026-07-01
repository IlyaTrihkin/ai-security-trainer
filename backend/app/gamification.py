from flask_login import current_user
from . import db
from .models import User, UserProgress, Achievement, UserAchievement
from datetime import datetime, timedelta

def check_achievements(user):
    """Проверяет все условия достижений для пользователя и выдаёт новые"""
    # Получаем список уже полученных достижений
    earned_achievement_ids = [ua.achievement_id for ua in user.achievements]
    all_achievements = Achievement.query.all()

    # 1. Подсчёт пройденных уроков
    lessons_completed = UserProgress.query.filter_by(
        user_id=user.id, completed=True
    ).count()

    # 2. Общее количество XP
    total_xp = user.xp

    # 3. Streak (серия)
    # Для простоты пока не реализуем, позже добавим

    # 4. Пройдены ли все уроки по фишингу (skill_id = 4)
    phishing_lessons = UserProgress.query.join(UserProgress.lesson).filter(
        UserProgress.user_id == user.id,
        UserProgress.completed == True,
        Lesson.skill_id == 4
    ).count()
    total_phishing_lessons = 3  # у нас 3 урока по фишингу

    new_achievements = []
    for ach in all_achievements:
        if ach.id in earned_achievement_ids:
            continue

        achieved = False
        if ach.condition_type == 'lessons_completed':
            if lessons_completed >= ach.condition_value:
                achieved = True
        elif ach.condition_type == 'xp_earned':
            if total_xp >= ach.condition_value:
                achieved = True
        elif ach.condition_type == 'skill_completed':
            if ach.condition_value == 4 and phishing_lessons >= total_phishing_lessons:
                achieved = True

        if achieved:
            user_ach = UserAchievement(
                user_id=user.id,
                achievement_id=ach.id,
                unlocked_at=datetime.utcnow()
            )
            db.session.add(user_ach)
            new_achievements.append(ach)

    if new_achievements:
        db.session.commit()
        # Возвращаем список новых достижений для уведомления
        return new_achievements
    return []
