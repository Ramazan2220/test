
def update_account_session_data(account_id, session_data, last_login=None):
    """Обновляет данные сессии аккаунта Instagram"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        account.session_data = session_data
        if last_login:
            account.last_login = last_login
        else:
            account.last_login = datetime.now()

        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных сессии аккаунта: {e}")
        return False, str(e)
