import hashlib
from flask import session
from app.utils.database import query_db


def hash_password(password):
    """Хэширование пароля"""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password, password_hash):
    """Проверка пароля"""
    return hash_password(password) == password_hash


def login_user(email, password):
    """Аутентификация пользователя"""
    try:
        user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)

        if user and verify_password(password, user['password_hash']):
            session['user_id'] = user['user_id']
            session['user_email'] = user['email']
            session['user_role'] = user['role_id']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            return True
        return False
    except Exception as e:
        print(f"Auth error: {e}")
        return False


def get_current_user():
    """Получение текущего пользователя"""
    if 'user_id' in session:
        try:
            return query_db('SELECT * FROM users WHERE user_id = %s', [session['user_id']], one=True)
        except Exception as e:
            print(f"Get current user error: {e}")
            return None
    return None


def is_admin():
    """Проверка, является ли пользователь администратором"""
    return session.get('user_role') == 1