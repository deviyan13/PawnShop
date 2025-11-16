import os
import random
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def populate_test_data():
    # Подключаемся к БД используя настройки из .env
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'flask_pawn_shop_db'),
        user=os.getenv('DB_USER', 'lombard_user'),
        password=os.getenv('DB_PASSWORD', '123456')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Устанавливаем схему
    schema = os.getenv('DB_SCHEMA', 'lombard')
    cur.execute(f"SET search_path TO {schema}, public;")

    try:
        # 1. Сначала заполняем базовые таблицы, если они пустые

        # Проверяем и заполняем роли
        cur.execute("SELECT COUNT(*) as count FROM roles")
        if cur.fetchone()['count'] == 0:
            print("Заполняем таблицу ролей...")
            cur.execute("INSERT INTO roles (role_name, description) VALUES (%s, %s)",
                        ('admin', 'Администратор системы'))
            cur.execute("INSERT INTO roles (role_name, description) VALUES (%s, %s)",
                        ('user', 'Обычный пользователь'))

        # Проверяем и заполняем филиалы
        cur.execute("SELECT COUNT(*) as count FROM branches")
        if cur.fetchone()['count'] == 0:
            print("Заполняем таблицу филиалов...")
            branches = [
                ('Центральный филиал', 'г. Минск, ул. Немига, 5', '+375 (17) 111-11-11'),
                ('Фрунзенский филиал', 'г. Минск, ул. Кальварийская, 24', '+375 (17) 222-22-22'),
                ('Советский филиал', 'г. Минск, ул. Веры Хоружей, 15', '+375 (17) 333-33-33'),
                ('Первомайский филиал', 'г. Минск, ул. Чкалова, 35', '+375 (17) 444-44-44')
            ]
            for branch in branches:
                cur.execute("INSERT INTO branches (name, address, phone) VALUES (%s, %s, %s)", branch)

        # Проверяем и заполняем категории
        cur.execute("SELECT COUNT(*) as count FROM item_categories")
        if cur.fetchone()['count'] == 0:
            print("Заполняем таблицу категорий...")
            categories = [
                ('Электроника', 'Смартфоны, ноутбуки, планшеты, фотоаппараты'),
                ('Ювелирные изделия', 'Золото, серебро, драгоценности, часы'),
                ('Бытовая техника', 'Холодильники, телевизоры, стиральные машины'),
                ('Антиквариат', 'Старинные предметы, искусство, коллекционные вещи'),
                ('Музыкальные инструменты', 'Гитары, синтезаторы, скрипки')
            ]
            for category in categories:
                cur.execute("INSERT INTO item_categories (name, description) VALUES (%s, %s)", category)

        # Проверяем и заполняем тарифы
        cur.execute("SELECT COUNT(*) as count FROM tariffs")
        if cur.fetchone()['count'] == 0:
            print("Заполняем таблицу тарифов...")
            tariffs = [
                ('Электроника - Центральный', 1, 1, 50.0, 8.0, 50, 2000, '2024-01-01',
                 'Тариф для электроники в центральном филиале'),
                ('Ювелирные - Центральный', 2, 1, 70.0, 6.0, 100, 5000, '2024-01-01',
                 'Тариф для ювелирных изделий в центральном филиале'),
                (
                'Электроника - Все филиалы', 1, None, 45.0, 9.0, 50, 1500, '2024-01-01', 'Общий тариф для электроники'),
                ('Ювелирные - Все филиалы', 2, None, 65.0, 7.0, 100, 4000, '2024-01-01',
                 'Общий тариф для ювелирных изделий'),
                ('Общий тариф', None, None, 35.0, 12.0, 50, 1000, '2024-01-01', 'Общий тариф по умолчанию')
            ]
            for tariff in tariffs:
                cur.execute('''
                    INSERT INTO tariffs (name, category_id, branch_id, loan_percent, interest_rate, min_loan, max_loan, effective_from, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', tariff)

        # 2. Проверяем существующих администраторов
        cur.execute("SELECT COUNT(*) as count FROM users WHERE role_id = 1")
        admin_count = cur.fetchone()['count']

        if admin_count == 0:
            print("Создаем администраторов...")
            # Создаем администраторов
            admins = [
                ('admin@lombard.by', hash_password('123456'), 'Александр', 'Петров', '+375 (29) 111-11-11', 1),
                ('manager@lombard.by', hash_password('123456'), 'Екатерина', 'Иванова', '+375 (29) 222-22-22', 1)
            ]

            for admin in admins:
                cur.execute(
                    'INSERT INTO users (email, password_hash, first_name, last_name, phone, role_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    admin
                )

            # Привязываем администраторов к филиалам
            cur.execute("SELECT user_id FROM users WHERE email = 'admin@lombard.by'")
            admin1_id = cur.fetchone()['user_id']

            cur.execute("SELECT user_id FROM users WHERE email = 'manager@lombard.by'")
            admin2_id = cur.fetchone()['user_id']

            user_branches = [
                (admin1_id, 1, True),  # Александр - Центральный филиал (основной)
                (admin1_id, 2, False),  # Александр - Фрунзенский филиал (дополнительный)
                (admin2_id, 3, True),  # Екатерина - Советский филиал (основной)
                (admin2_id, 4, False)  # Екатерина - Первомайский филиал (дополнительный)
            ]

            for ub in user_branches:
                cur.execute("INSERT INTO user_branches (user_id, branch_id, is_primary) VALUES (%s, %s, %s)", ub)

        # 3. Создаем тестовых пользователей (role_id = 2)
        print("Создаем тестовых пользователей...")
        test_users = [
            ('user1@example.com', hash_password('123456'), 'Дмитрий', 'Сидоров', '+375 (29) 333-33-33', 2),
            ('user2@example.com', hash_password('123456'), 'Ольга', 'Ковалева', '+375 (29) 444-44-44', 2),
            ('client1@test.by', hash_password('123456'), 'Иван', 'Козлов', '+375 (29) 555-55-55', 2),
            ('client2@test.by', hash_password('123456'), 'Мария', 'Петрова', '+375 (29) 666-66-66', 2),
            ('client3@test.by', hash_password('123456'), 'Сергей', 'Смирнов', '+375 (29) 777-77-77', 2),
        ]

        for user in test_users:
            # Проверяем, нет ли уже пользователя с таким email
            cur.execute("SELECT COUNT(*) as count FROM users WHERE email = %s", (user[0],))
            if cur.fetchone()['count'] == 0:
                cur.execute(
                    'INSERT INTO users (email, password_hash, first_name, last_name, phone, role_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    user
                )

        # 4. Создаем тестовые заявки
        print("Создаем тестовые заявки...")

        # Получаем ID обычных пользователей
        cur.execute("SELECT user_id FROM users WHERE role_id = 2")
        user_ids = [row['user_id'] for row in cur.fetchall()]

        categories = [1, 2, 3, 4, 5]  # ID категорий
        branches = [1, 2, 3, 4]  # ID филиалов

        items = [
            ('iPhone 13 Pro', 'Смартфон в отличном состоянии', 1500),
            ('Золотое кольцо', '585 проба, с камнем', 800),
            ('Ноутбук Dell', 'Core i5, 8GB RAM', 1200),
            ('Телевизор Samsung', '55 дюймов, 4K', 1800),
            ('Гитара Fender', 'Акустическая, классика', 600)
        ]

        for i in range(20):
            request_number = f"TEST-REQ-{i + 1:03d}"
            user_id = random.choice(user_ids)
            branch_id = random.choice(branches)
            category_id = random.choice(categories)

            item_name, item_desc, base_price = random.choice(items)
            estimated_cost = base_price * random.uniform(0.8, 1.2)

            cur.execute('''
                INSERT INTO requests 
                (request_number, user_id, branch_id, category_id, item_name, item_description, estimated_cost, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_number, user_id, branch_id, category_id,
                item_name, item_desc, round(estimated_cost, 2), 'submitted'
            ))

        conn.commit()

        # Выводим статистику
        print("\n=== Статистика базы данных ===")
        cur.execute("SELECT COUNT(*) as count FROM roles")
        print(f"Ролей: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM branches")
        print(f"Филиалов: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM item_categories")
        print(f"Категорий: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM tariffs")
        print(f"Тарифов: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM users WHERE role_id = 1")
        print(f"Администраторов: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM users WHERE role_id = 2")
        print(f"Пользователей: {cur.fetchone()['count']}")

        cur.execute("SELECT COUNT(*) as count FROM requests")
        print(f"Заявок: {cur.fetchone()['count']}")

        print("\n=== Тестовые аккаунты ===")
        print("Администраторы:")
        print("  admin@lombard.by / 123456")
        print("  manager@lombard.by / 123456")
        print("\nПользователи:")
        print("  user1@example.com / 123456")
        print("  client1@test.by / 123456")

        print("\nТестовые данные успешно добавлены!")

    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    #populate_test_data()
    # Гарантированный общий тариф на случай, если другие не подходят
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'flask_pawn_shop_db'),
        user=os.getenv('DB_USER', 'lombard_user'),
        password=os.getenv('DB_PASSWORD', '123456')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Устанавливаем схему
    schema = os.getenv('DB_SCHEMA', 'lombard')
    cur.execute(f"SET search_path TO {schema}, public;")

    cur.execute('''
        INSERT INTO tariffs (name, category_id, branch_id, loan_percent, interest_rate, min_loan, max_loan, effective_from, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    ''', (
        'Гарантированный общий тариф',
        None, None, 30.0, 15.0, 10, 10000, '2024-01-01',
        'Гарантированный тариф для всех случаев'
    ))