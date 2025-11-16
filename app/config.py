import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING = os.getenv('TESTING', 'False').lower() == 'true'

    # Database configuration
    DB_TYPE = os.getenv('DB_TYPE', 'postgresql')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5433')
    DB_NAME = os.getenv('DB_NAME', 'flask_pawn_shop_db')
    DB_USER = os.getenv('DB_USER', 'lombard_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
    DB_SCHEMA = os.getenv('DB_SCHEMA', 'lombard')

    # Вычисляем DATABASE_URL при создании экземпляра
    def __init__(self):
        if self.DB_TYPE == 'postgresql':
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        elif self.DB_TYPE == 'sqlite':
            self.DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'lombard.db')}"
        else:
            raise ValueError(f"Unsupported database type: {self.DB_TYPE}")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DB_NAME = 'test_flask_pawn_shop_db'


# Создаем экземпляры конфигураций
config = {
    'development': DevelopmentConfig(),
    'production': ProductionConfig(),
    'testing': TestingConfig(),
    'default': DevelopmentConfig()
}