import json
import os
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters

from config import ACCOUNTS_DIR, ADMIN_USER_IDS, MEDIA_DIR
from database.db_manager import get_session, get_instagram_accounts, bulk_add_instagram_accounts, delete_instagram_account, get_instagram_account
from database.models import InstagramAccount
from instagram_api.client import test_instagram_login

# Состояния для добавления аккаунта
ENTER_USERNAME, ENTER_PASSWORD, CONFIRM_ACCOUNT = range(1, 4)

# Состояние для ожидания файла с аккаунтами
WAITING_ACCOUNTS_FILE = 10

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def accounts_handler(update, context):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data='list_accounts')],
        [InlineKeyboardButton("📤 Загрузить аккаунты", callback_data='upload_accounts')],
        [InlineKeyboardButton("⚙️ Настройка профиля", callback_data='profile_setup')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "🔧 *Меню управления аккаунтами*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def add_account_handler(update, context):
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            "Пожалуйста, введите имя пользователя (логин) аккаунта Instagram:"
        )
        return ENTER_USERNAME
    else:
        update.message.reply_text(
            "Пожалуйста, введите имя пользователя (логин) аккаунта Instagram:"
        )
        return ENTER_USERNAME

def enter_username(update, context):
    username = update.message.text.strip()

    session = get_session()
    existing_account = session.query(InstagramAccount).filter_by(username=username).first()
    session.close()

    if existing_account:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"Аккаунт с именем пользователя '{username}' уже существует. "
            f"Пожалуйста, используйте другое имя пользователя или вернитесь в меню аккаунтов.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    context.user_data['instagram_username'] = username

    update.message.reply_text(
        "Теперь введите пароль для этого аккаунта Instagram.\n\n"
        "⚠️ *Важно*: Ваш пароль будет храниться в зашифрованном виде и использоваться только для авторизации в Instagram.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ENTER_PASSWORD

def enter_password(update, context):
    password = update.message.text.strip()

    context.user_data['instagram_password'] = password

    username = context.user_data.get('instagram_username')

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, добавить", callback_data='confirm_add_account'),
            InlineKeyboardButton("❌ Нет, отменить", callback_data='cancel_add_account')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        f"Вы собираетесь добавить аккаунт Instagram:\n\n"
        f"👤 *Имя пользователя*: `{username}`\n\n"
        f"Подтверждаете добавление этого аккаунта?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    update.message.delete()

    return CONFIRM_ACCOUNT

def confirm_add_account(update, context):
    query = update.callback_query
    query.answer()

    username = context.user_data.get('instagram_username')
    password = context.user_data.get('instagram_password')

    if not username or not password:
        query.edit_message_text(
            "Произошла ошибка: данные аккаунта не найдены. Пожалуйста, попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]])
        )
        return ConversationHandler.END

    query.edit_message_text("Проверка данных аккаунта Instagram... Это может занять некоторое время.")

    try:
        login_successful = test_instagram_login(username, password)

        if login_successful:
            session = get_session()
            new_account = InstagramAccount(
                username=username,
                password=password,
                is_active=True
            )
            session.add(new_account)
            session.commit()
            account_id = new_account.id
            session.close()

            account_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
            os.makedirs(account_dir, exist_ok=True)

            session_data = {
                'username': username,
                'account_id': account_id,
                'created_at': str(new_account.created_at)
            }
            with open(os.path.join(account_dir, 'session.json'), 'w') as f:
                json.dump(session_data, f)

            keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                f"✅ Аккаунт Instagram успешно добавлен!\n\n"
                f"👤 *Имя пользователя*: `{username}`\n"
                f"🆔 *ID аккаунта*: `{account_id}`\n\n"
                f"Теперь вы можете использовать этот аккаунт для публикации контента.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "❌ Не удалось войти в аккаунт Instagram. Пожалуйста, проверьте правильность имени пользователя и пароля.",
                reply_markup=reply_markup
            )
    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"❌ Произошла ошибка при добавлении аккаунта: {str(e)}",
            reply_markup=reply_markup
        )

    if 'instagram_username' in context.user_data:
        del context.user_data['instagram_username']
    if 'instagram_password' in context.user_data:
        del context.user_data['instagram_password']

    return ConversationHandler.END

def cancel_add_account(update, context):
    query = update.callback_query
    query.answer()

    if 'instagram_username' in context.user_data:
        del context.user_data['instagram_username']
    if 'instagram_password' in context.user_data:
        del context.user_data['instagram_password']

    keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "Добавление аккаунта отменено.",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

def list_accounts_handler(update, context):
    session = get_session()
    accounts = session.query(InstagramAccount).all()
    session.close()

    if update.callback_query:
        query = update.callback_query
        query.answer()

        if not accounts:
            keyboard = [[InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "У вас пока нет добавленных аккаунтов Instagram.",
                reply_markup=reply_markup
            )
            return

        accounts_text = "📋 *Список ваших аккаунтов Instagram:*\n\n"

        for account in accounts:
            status = "✅ Активен" if account.is_active else "❌ Неактивен"
            accounts_text += f"👤 *{account.username}*\n"
            accounts_text += f"🆔 ID: `{account.id}`\n"
            accounts_text += f"📅 Добавлен: {account.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            accounts_text += f"📊 Статус: {status}\n"
            # Добавляем кнопку удаления для каждого аккаунта
            accounts_text += f"[Удалить аккаунт](callback:delete_account_{account.id})\n\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Проверить валидность", callback_data='check_accounts_validity')],
            [InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            accounts_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        if not accounts:
            keyboard = [[InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                "У вас пока нет добавленных аккаунтов Instagram.",
                reply_markup=reply_markup
            )
            return

        accounts_text = "📋 *Список ваших аккаунтов Instagram:*\n\n"

        for account in accounts:
            status = "✅ Активен" if account.is_active else "❌ Неактивен"
            accounts_text += f"👤 *{account.username}*\n"
            accounts_text += f"🆔 ID: `{account.id}`\n"
            accounts_text += f"📅 Добавлен: {account.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            accounts_text += f"📊 Статус: {status}\n"
            # Добавляем кнопку удаления для каждого аккаунта
            accounts_text += f"[Удалить аккаунт](callback:delete_account_{account.id})\n\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Проверить валидность", callback_data='check_accounts_validity')],
            [InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            accounts_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

def delete_account_handler(update, context):
    """Обработчик для удаления аккаунта"""
    query = update.callback_query
    query.answer()

    # Получаем ID аккаунта из callback_data
    account_id = int(query.data.split('_')[2])

    # Получаем информацию об аккаунте
    account = get_instagram_account(account_id)

    if not account:
        query.edit_message_text(
            "Аккаунт не найден.",
            reply_markup=get_accounts_menu_keyboard()
        )
        return

    # Удаляем аккаунт
    success, result = delete_instagram_account(account_id)

    if success:
        # Удаляем файл сессии, если он существует
        session_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
        session_file = os.path.join(session_dir, "session.json")

        if os.path.exists(session_file):
            os.remove(session_file)

        query.edit_message_text(
            f"Аккаунт {account.username} успешно удален.",
            reply_markup=get_accounts_menu_keyboard()
        )
    else:
        query.edit_message_text(
            f"Ошибка при удалении аккаунта: {result}",
            reply_markup=get_accounts_menu_keyboard()
        )

def check_accounts_validity_handler(update, context):
    """Обработчик для проверки валидности аккаунтов"""
    query = update.callback_query
    query.answer()

    query.edit_message_text("Проверка валидности аккаунтов... Это может занять некоторое время.")

    # Получаем все аккаунты
    accounts = get_instagram_accounts()

    if not accounts:
        query.edit_message_text(
            "У вас нет добавленных аккаунтов Instagram.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]])
        )
        return

    # Проверяем каждый аккаунт
    results = []
    for account in accounts:
        try:
            # Проверяем валидность аккаунта
            valid = test_instagram_login(account.username, account.password)
            
            if valid:
                results.append(f"✅ {account.username}: Аккаунт валиден")
                # Обновляем статус аккаунта
                session = get_session()
                db_account = session.query(InstagramAccount).filter_by(id=account.id).first()
                if db_account:
                    db_account.is_active = True
                    session.commit()
                session.close()
            else:
                results.append(f"❌ {account.username}: Аккаунт невалиден")
                # Обновляем статус аккаунта
                session = get_session()
                db_account = session.query(InstagramAccount).filter_by(id=account.id).first()
                if db_account:
                    db_account.is_active = False
                    session.commit()
                session.close()
        except Exception as e:
            results.append(f"❌ {account.username}: Ошибка при проверке - {str(e)}")

    # Формируем отчет
    report = "📊 *Результаты проверки валидности аккаунтов:*\n\n"
    report += "\n".join(results)

    keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        report,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def profile_setup_handler(update, context):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Функция настройки профиля в разработке",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def bulk_upload_accounts_command(update, context):
    """Обработчик команды для массовой загрузки аккаунтов"""
    update.message.reply_text(
        "Отправьте TXT файл с аккаунтами Instagram.\n\n"
        "Формат файла:\n"
        "username:password\n"
        "username:password\n"
        "...\n\n"
        "Каждый аккаунт должен быть на новой строке в формате username:password"
    )
    return WAITING_ACCOUNTS_FILE

def bulk_upload_accounts_file(update, context):
    """Обработчик загрузки файла с аккаунтами"""
    # Получаем файл
    file = update.message.document
    file_id = file.file_id

    # Проверяем расширение файла
    file_name = file.file_name
    if not file_name.endswith('.txt'):
        update.message.reply_text("Пожалуйста, отправьте файл с расширением .txt")
        return WAITING_ACCOUNTS_FILE

    # Скачиваем файл
    new_file = context.bot.get_file(file_id)
    file_path = os.path.join(MEDIA_DIR, f"accounts_{int(time.time())}.txt")
    new_file.download(file_path)

    try:
        # Парсим TXT файл
        accounts_data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):  # Пропускаем пустые строки и комментарии
                    continue

                parts = line.split(':', 1)  # Разделяем строку на username и password
                if len(parts) != 2:
                    continue  # Пропускаем некорректные строки

                username, password = parts
                accounts_data.append({
                    "username": username.strip(),
                    "password": password.strip()
                })

        if not accounts_data:
            update.message.reply_text("Не удалось найти аккаунты в файле. Проверьте формат файла.")
            return ConversationHandler.END

        # Добавляем аккаунты
        success, errors = bulk_add_instagram_accounts(accounts_data)

        # Формируем отчет
        report = f"📊 Результат загрузки аккаунтов:\n\n"
        report += f"✅ Успешно добавлено: {len(success)}\n"
        if success:
            report += "Добавленные аккаунты:\n"
            for username in success[:10]:  # Показываем только первые 10
                report += f"- {username}\n"
            if len(success) > 10:
                report += f"... и еще {len(success) - 10}\n"

        if errors:
            report += f"\n❌ Ошибки ({len(errors)}):\n"
            for username, error in errors[:10]:  # Показываем только первые 10 ошибок
                report += f"- {username}: {error}\n"
            if len(errors) > 10:
                report += f"... и еще {len(errors) - 10} ошибок\n"

        keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(report, reply_markup=reply_markup)

    except Exception as e:
        update.message.reply_text(f"Ошибка при обработке файла: {e}")

    # Удаляем временный файл
    try:
        os.remove(file_path)
    except:
        pass

    return ConversationHandler.END

def get_account_handlers():
    """Возвращает обработчики для управления аккаунтами"""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters

    account_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("add_account", add_account_handler),
            CallbackQueryHandler(add_account_handler, pattern='^add_account$')
        ],
        states={
            ENTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, enter_username)],
            ENTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, enter_password)],
            CONFIRM_ACCOUNT: [
                CallbackQueryHandler(confirm_add_account, pattern='^confirm_add_account$'),
                CallbackQueryHandler(cancel_add_account, pattern='^cancel_add_account$')
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )

    # Новый ConversationHandler для массовой загрузки аккаунтов
    bulk_upload_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("upload_accounts", bulk_upload_accounts_command),
            CallbackQueryHandler(bulk_upload_accounts_command, pattern='^upload_accounts$')
        ],
        states={
            WAITING_ACCOUNTS_FILE: [MessageHandler(Filters.document.file_extension("txt"), bulk_upload_accounts_file)]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )

    return [
        CommandHandler("accounts", accounts_handler),
        account_conversation,
        bulk_upload_conversation,  # Добавляем новый обработчик
        CommandHandler("list_accounts", list_accounts_handler),
        CommandHandler("profile_setup", profile_setup_handler),
        CallbackQueryHandler(delete_account_handler, pattern='^delete_account_\d+$'),
        CallbackQueryHandler(check_accounts_validity_handler, pattern='^check_accounts_validity$')
    ]
