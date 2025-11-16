from flask import Flask
from app.config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = 'default'

    app = Flask(__name__)

    # Загружаем конфигурацию из объекта
    cfg = config[config_name]
    app.config.from_object(cfg)

    # Также устанавливаем отдельные параметры для удобства
    app.config['DB_TYPE'] = cfg.DB_TYPE
    app.config['DB_SCHEMA'] = cfg.DB_SCHEMA

    # Initialize database
    from app.utils.database import init_db
    init_db(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.user import user_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    return app