from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.auth import login_user, hash_password, get_current_user
from app.utils.database import get_db, query_db
from app.forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        if login_user(email, password):
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Неверный email или пароль', 'error')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        phone = form.phone.data

        # Проверяем, нет ли уже пользователя с таким email
        existing_user = query_db('SELECT * FROM users WHERE email = %s', [email], one=True)
        if existing_user:
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('auth/register.html', form=form)

        # Создаем нового пользователя (роль user = 2)
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO users (email, password_hash, first_name, last_name, phone, role_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (email, hash_password(password), first_name, last_name, phone, 2)
        )
        conn.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))