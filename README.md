Создание бд в консоли postgres:
```
CREATE USER lombard_user WITH PASSWORD '123456';
```
```
-- 2. Создание базы данных
CREATE DATABASE flask_pawn_shop_db
WITH 
    OWNER = lombard_user
    ENCODING = 'UTF8'
    LC_COLLATE = 'ru_RU.UTF-8'
    LC_CTYPE = 'ru_RU.UTF-8'
    TEMPLATE = template0;
```
```
-- 3. Предоставление прав пользователю
GRANT ALL PRIVILEGES ON DATABASE flask_pawn_shop_db TO lombard_user;
```

Создай виртаульное окружение venv в корне репозитория (не в папке app)
```
python -m venv venv
```

Зайди в него 
```
myenv\Scripts\activate
```

В .env поменяй порт на 5432 (у меня просто он для postgres 5433)

Потом
```
pip install -r requirements.txt
```

```
python init_db.py
```
```
python populate_test_data.py
```

ну и flask
```
flask run
```
