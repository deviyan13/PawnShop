import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from datetime import datetime


def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_files(files, subfolder='attachments'):
    """Сохраняет загруженные файлы и возвращает список путей"""
    saved_files = []

    # Создаем папку для загрузок если её нет
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', subfolder)
    os.makedirs(upload_folder, exist_ok=True)

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            # Генерируем уникальное имя файла
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"

            # Сохраняем файл
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            # Сохраняем относительный путь для БД
            relative_path = f"uploads/{subfolder}/{unique_filename}"
            saved_files.append({
                'file_path': relative_path,
                'file_name': secure_filename(file.filename),
                'original_name': file.filename
            })

    return saved_files


def delete_file(file_path):
    """Удаляет файл с диска"""
    try:
        full_path = os.path.join(current_app.root_path, 'static', file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    except Exception:
        pass
    return False