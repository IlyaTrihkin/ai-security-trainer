from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
import json
from dotenv import load_dotenv

basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)  # Теперь Flask сам найдёт templates и static внутри пакета (backend/app)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(basedir, "instance", "security_trainer.db")}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Jinja2-фильтр: парсинг JSON
    @app.template_filter('from_json')
    def from_json_filter(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    migrate.init_app(app, db)

    from . import models
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
