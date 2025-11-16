import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g, current_app
import os


def get_db():
    if 'db' not in g:
        db_type = current_app.config.get('DB_TYPE', 'postgresql')

        if db_type == 'postgresql':
            # Используем DATABASE_URL из конфигурации
            g.db = psycopg2.connect(
                current_app.config['DATABASE_URL'],
                cursor_factory=RealDictCursor
            )
            # Устанавливаем схему поиска
            cur = g.db.cursor()
            schema = current_app.config.get('DB_SCHEMA', 'lombard')
            cur.execute(f"SET search_path TO {schema}, public;")
            cur.close()
        elif db_type == 'sqlite':
            db_path = current_app.config['DATABASE_URL'].replace('sqlite:///', '')
            g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(close_db)


def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.cursor()

    # Преобразуем аргументы для корректной работы с JSON
    processed_args = []
    for arg in args:
        if isinstance(arg, dict):
            processed_args.append(json.dumps(arg))
        else:
            processed_args.append(arg)

    cur.execute(query, processed_args)

    if query.strip().upper().startswith('SELECT'):
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv
    else:
        conn.commit()
        cur.close()
        return cur.rowcount