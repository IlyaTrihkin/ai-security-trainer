from backend.app import create_app, db
from backend.app.models import Skill

app = create_app()
with app.app_context():
    skills = Skill.query.order_by(Skill.order).all()
    for s in skills:
        print(f'ID={s.id}, title={s.title}, difficulty={s.difficulty}, order={s.order}')