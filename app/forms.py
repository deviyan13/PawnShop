from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DecimalField, SubmitField
from wtforms.fields.simple import MultipleFileField
from wtforms.validators import DataRequired, Length, NumberRange, Email, Regexp
from app.utils.database import query_db


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен для заполнения'),
        Email(message='Введите корректный email адрес')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен для заполнения')
    ])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email обязателен для заполнения'),
        Email(message='Введите корректный email адрес'),
        Regexp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
               message='Некорректный формат email')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message='Пароль обязателен для заполнения'),
        Length(min=6, message='Пароль должен содержать минимум 6 символов')
    ])
    first_name = StringField('Имя', validators=[
        DataRequired(message='Имя обязательно для заполнения'),
        Length(min=2, max=50, message='Имя должно быть от 2 до 50 символов'),
        Regexp(r'^[а-яА-ЯёЁa-zA-Z\- ]+$',
               message='Имя может содержать только буквы, дефисы и пробелы')
    ])
    last_name = StringField('Фамилия', validators=[
        DataRequired(message='Фамилия обязательна для заполнения'),
        Length(min=2, max=50, message='Фамилия должна быть от 2 до 50 символов'),
        Regexp(r'^[а-яА-ЯёЁa-zA-Z\- ]+$',
               message='Фамилия может содержать только буквы, дефисы и пробелы')
    ])
    phone = StringField('Телефон', validators=[
        Regexp(r'^(\+375|80)\(?\s*(29|25|44|33)\)?\s*(\d{3})-?(\d{2})-?(\d{2})$',
               message='Введите номер в формате +375XXXXXXXXX или 80XXXXXXXXX')
    ])
    submit = SubmitField('Зарегистрироваться')


class RequestForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(RequestForm, self).__init__(*args, **kwargs)
        # Динамически заполняем выбор филиалов и категорий
        branches = query_db('SELECT branch_id, name FROM branches ORDER BY name')
        categories = query_db('SELECT category_id, name FROM item_categories ORDER BY name')

        self.branch_id.choices = [(b['branch_id'], b['name']) for b in branches]
        self.category_id.choices = [(c['category_id'], c['name']) for c in categories]

    branch_id = SelectField('Филиал', coerce=int, validators=[
        DataRequired(message='Выберите филиал')
    ])
    category_id = SelectField('Категория', coerce=int, validators=[
        DataRequired(message='Выберите категорию')
    ])
    item_name = StringField('Название вещи', validators=[
        DataRequired(message='Название вещи обязательно'),
        Length(max=200, message='Название не должно превышать 200 символов')
    ])
    item_description = TextAreaField('Описание')
    estimated_cost = DecimalField('Оценочная стоимость', validators=[
        DataRequired(message='Укажите оценочную стоимость'),
        NumberRange(min=0, message='Стоимость не может быть отрицательной')
    ])
    photos = MultipleFileField('Фотографии товара', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Только изображения (JPG, PNG, GIF)')
    ])
    submit = SubmitField('Подать заявку')