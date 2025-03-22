import logging
import time
import os
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, ChallengeRequired

logger = logging.getLogger(__name__)

def test_instagram_login(username, password):
    """
    Тестирует вход в Instagram с указанными учетными данными.

    Args:
        username (str): Имя пользователя Instagram
        password (str): Пароль пользователя Instagram

    Returns:
        bool: True, если вход успешен, False в противном случае
    """
    try:
        logger.info(f"Тестирование входа для пользователя {username}")

        # Создаем клиент Instagram
        client = Client()

        # Пытаемся войти
        client.login(username, password)

        # Если дошли до этой точки, значит вход успешен
        logger.info(f"Вход успешен для пользователя {username}")

        # Выходим из аккаунта
        client.logout()

        return True

    except BadPassword:
        logger.error(f"Неверный пароль для пользователя {username}")
        return False

    except ChallengeRequired:
        logger.error(f"Требуется подтверждение для пользователя {username}")
        return False

    except LoginRequired:
        logger.error(f"Не удалось войти для пользователя {username}")
        return False

    except Exception as e:
        logger.error(f"Ошибка при входе для пользователя {username}: {str(e)}")
        return False

def login_with_session(username, password, session_file):
    """Вход в аккаунт с использованием сохраненной сессии"""
    client = Client()

    # Проверяем, существует ли файл сессии
    if os.path.exists(session_file):
        try:
            # Загружаем сессию
            with open(session_file, 'r') as f:
                cached_settings = json.load(f)

            client.set_settings(cached_settings)

            # Пробуем использовать сессию
            try:
                client.get_timeline_feed()  # Проверка, что сессия активна
                logger.info(f"Успешный вход по сессии для {username}")
                return client, True
            except Exception as e:
                logger.warning(f"Сессия для {username} устарела, пробуем обычный вход: {e}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке сессии для {username}: {e}")

    # Если сессия не существует или не работает, пробуем обычный вход
    try:
        client.login(username, password)

        # Сохраняем новую сессию
        settings = client.get_settings()
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        with open(session_file, 'w') as f:
            json.dump(settings, f)

        logger.info(f"Успешный вход и сохранение новой сессии для {username}")
        return client, True
    except Exception as e:
        logger.error(f"Ошибка при входе для {username}: {e}")
        return None, False
