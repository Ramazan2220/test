import os
import sqlite3
import sys

# Получаем текущий путь
current_dir = os.getcwd()
print(f"Текущая директория: {current_dir}")

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(current_dir)

try:
    # Импортируем конфигурацию
    from config import DATABASE_URL
    print(f"Используем базу данных: {DATABASE_URL}")

    # Извлекаем путь к файлу базы данных из DATABASE_URL
    db_path = DATABASE_URL.replace('sqlite:///', '')

    print(f"Путь к файлу базы данных: {db_path}")

    # Проверяем существование файла
    if not os.path.exists(db_path):
        print(f"Ошибка: файл базы данных не существует по пути {db_path}")
        sys.exit(1)

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(publish_tasks)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]

    print(f"Текущие колонки в таблице publish_tasks: {column_names}")

    # Проверяем наличие колонки media_id
    if 'media_id' not in column_names:
        # Добавляем колонку media_id
        try:
            cursor.execute("ALTER TABLE publish_tasks ADD COLUMN media_id TEXT")
            conn.commit()
            print("Колонка media_id успешно добавлена в таблицу publish_tasks")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при добавлении колонки media_id: {e}")
    else:
        print("Колонка media_id уже существует в таблице publish_tasks")

    # Проверяем наличие колонки completed_at
    if 'completed_at' not in column_names:
        # Добавляем колонку completed_at
        try:
            cursor.execute("ALTER TABLE publish_tasks ADD COLUMN completed_at TIMESTAMP")
            conn.commit()
            print("Колонка completed_at успешно добавлена в таблицу publish_tasks")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при добавлении колонки completed_at: {e}")
    else:
        print("Колонка completed_at уже существует в таблице publish_tasks")

    # Закрываем соединение
    conn.close()
    print("Операция завершена")
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Проверьте, что вы находитесь в корневой директории проекта и активировали правильное виртуальное окружение")
except Exception as e:
    print(f"Ошибка: {e}")