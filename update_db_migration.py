import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Добавляем родительскую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATABASE_URL
except ImportError:
    # Если не удается импортировать из config, используем значение по умолчанию
    DATABASE_URL = "sqlite:///database.db"

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Создаем сессию
Session = sessionmaker(bind=engine)
session = Session()

# Проверяем, существуют ли уже нужные столбцы
def column_exists(table_name, column_name):
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result]
        return column_name in columns

# Добавляем столбцы, если они не существуют
if not column_exists('instagram_accounts', 'email'):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE instagram_accounts ADD COLUMN email TEXT"))
        conn.commit()
    print("Добавлен столбец 'email' в таблицу 'instagram_accounts'")

if not column_exists('instagram_accounts', 'email_password'):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE instagram_accounts ADD COLUMN email_password TEXT"))
        conn.commit()
    print("Добавлен столбец 'email_password' в таблицу 'instagram_accounts'")

if not column_exists('instagram_accounts', 'session_data'):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE instagram_accounts ADD COLUMN session_data TEXT"))
        conn.commit()
    print("Добавлен столбец 'session_data' в таблицу 'instagram_accounts'")

if not column_exists('instagram_accounts', 'last_login'):
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE instagram_accounts ADD COLUMN last_login DATETIME"))
        conn.commit()
    print("Добавлен столбец 'last_login' в таблицу 'instagram_accounts'")

print("Миграция базы данных завершена успешно")