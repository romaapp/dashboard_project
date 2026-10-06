import re
import streamlit as st

from logger import logger
from cookie_bridge import (
    COOKIE_NAME,
    set_auth_cookie,
    delete_auth_cookie,
)


# ============================================================
# ПРОВЕРКА ФОРМАТА ЛОГИНА
# ============================================================

def validate_login(login):
    """
    Проверяет логин пользователя.

    Требуемый формат:
    Фамилия И. О.

    Например:
    Иванов И. И.
    """

    login = login.strip()

    if not login:
        return False, "Введите логин"

    pattern = (
        r"^[А-ЯЁа-яёA-Za-z-]+ "
        r"[А-ЯЁа-яёA-Za-z]\. "
        r"[А-ЯЁа-яёA-Za-z]\.$"
    )

    if not re.fullmatch(pattern, login):
        return False, "Используйте формат: Фамилия И. О."

    return True, login


# ============================================================
# ПРОВЕРКА АВТОРИЗАЦИИ
# ============================================================

def is_authenticated():
    """Возвращает True, если пользователь авторизован."""

    return st.session_state.get(
        "authenticated",
        False
    )


# ============================================================
# ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ
# ============================================================

def get_current_user():
    """
    Возвращает данные текущего пользователя.

    Формат:
    {
        "user_id": ...,
        "login": ...
    }

    Если пользователь не авторизован:
    None
    """

    if not is_authenticated():
        return None

    return {
        "user_id": st.session_state.get("user_id"),
        "login": st.session_state.get("username")
    }


# ============================================================
# ПОИСК ПОЛЬЗОВАТЕЛЯ ПО ID
# ============================================================

def get_user_by_id(user_id):

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        return None

    users = logger.get_active_users()

    for current_user_id, login in users:

        if current_user_id == user_id:
            return current_user_id, login

    return None


# ============================================================
# ВОССТАНОВЛЕНИЕ АВТОРИЗАЦИИ ИЗ COOKIE
# ============================================================

def restore_auth_from_cookie():
    """
    Восстанавливает авторизацию из обычной browser cookie.
    """

    if is_authenticated():
        return True

    try:

        saved_user_id = st.context.cookies.get(
            COOKIE_NAME
        )

    except Exception:
        return False

    if not saved_user_id:
        return False

    user = get_user_by_id(
        saved_user_id
    )

    if not user:

        return False

    user_id, login = user

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = login

    return True


# ============================================================
# ВХОД ПОЛЬЗОВАТЕЛЯ
# ============================================================

def login_user(user_id, login):
    """Авторизует пользователя."""

    # --------------------------------------------------------
    # Сохраняем авторизацию в session_state
    # --------------------------------------------------------

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = login

    # --------------------------------------------------------
    # Обновляем время последнего входа
    # --------------------------------------------------------

    logger.update_last_login(
        user_id
    )

    # --------------------------------------------------------
    # Логируем вход
    # --------------------------------------------------------

    logger.log_action(
        "login"
    )

    # --------------------------------------------------------
    # Устанавливаем обычную browser cookie
    # --------------------------------------------------------

    set_auth_cookie(
        user_id
    )


# ============================================================
# ВЫХОД ПОЛЬЗОВАТЕЛЯ
# ============================================================

def logout_user():
    """Выход пользователя из системы."""

    # --------------------------------------------------------
    # Логируем выход до очистки session_state
    # --------------------------------------------------------

    if is_authenticated():

        logger.log_action(
            "logout"
        )

    # --------------------------------------------------------
    # Очищаем session_state
    # --------------------------------------------------------

    st.session_state["authenticated"] = False

    st.session_state.pop(
        "user_id",
        None
    )

    st.session_state.pop(
        "username",
        None
    )

    # --------------------------------------------------------
    # Удаляем cookie через браузер
    # --------------------------------------------------------

    delete_auth_cookie()


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

def registration_form():
    """Форма регистрации нового пользователя."""

    st.subheader(
        "📝 Регистрация",
        help=(
            "Регистрация нужна для будущих персональных "
            "возможностей дашборда: избранные отчеты, "
            "сохраненные настройки, история выбранных "
            "отчетов и другие индивидуальные функции."
        )
    )

    # --------------------------------------------------------
    # Поле регистрации
    # --------------------------------------------------------

    login = st.text_input(
        "Логин в формате Фамилия И. О.",
        placeholder="Введите здесь",
        key="registration_login"
    )

    # --------------------------------------------------------
    # Кнопка регистрации
    # --------------------------------------------------------

    if st.button(
        "Зарегистрироваться",
        key="register_user_button",
        use_container_width=True
    ):

        is_valid, result = validate_login(
            login
        )

        if not is_valid:

            st.error(
                result
            )

            return

        success, user_id = logger.register_user(
            result
        )

        if success:

            st.success(
                "Регистрация выполнена успешно. "
                "Теперь можно войти."
            )

            st.session_state.pop(
                "registration_login",
                None
            )

            st.rerun()

        else:

            st.error(
                user_id
            )


# ============================================================
# ОКНО АВТОРИЗАЦИИ
# ============================================================

def login_form():
    """Отображает окно авторизации."""

    st.title(
        "🔐 Авторизация"
    )

    # --------------------------------------------------------
    # Два блока рядом
    # --------------------------------------------------------

    col_login, col_registration = st.columns(
        2
    )

    # ========================================================
    # АВТОРИЗАЦИЯ
    # ========================================================

    with col_login:

        st.subheader(
            "👤 Вход"
        )

        # ----------------------------------------------------
        # Получаем только активных пользователей
        # ----------------------------------------------------

        users = logger.get_active_users()

        if users:

            user_options = {
                login: user_id
                for user_id, login in users
            }

            login_options = [
                "— Выберите пользователя —"
            ] + list(
                user_options.keys()
            )

            selected_login = st.selectbox(
                "Пользователь",
                options=login_options,
                index=0,
                key="login_user_select"
            )

            if st.button(
                "Войти",
                key="login_button",
                use_container_width=True
            ):

                if (
                    selected_login
                    == "— Выберите пользователя —"
                ):

                    st.warning(
                        "Сначала выберите пользователя."
                    )

                else:

                    user_id = user_options[
                        selected_login
                    ]

                    login_user(
                        user_id,
                        selected_login
                    )

                    # ------------------------------------------------
                    # НЕ вызываем st.rerun()
                    #
                    # cookie_bridge сам перезагрузит страницу
                    # после того, как браузер установит cookie.
                    # ------------------------------------------------

                    st.stop()

        else:

            st.info(
                "Зарегистрированных пользователей пока нет."
            )

    # ========================================================
    # РЕГИСТРАЦИЯ
    # ========================================================

    with col_registration:

        registration_form()


# ============================================================
# ОСНОВНАЯ ПРОВЕРКА
# ============================================================

def require_auth():
    """
    Проверяет авторизацию пользователя.

    Порядок:

    1. Проверяем session_state.
    2. Проверяем обычную browser cookie.
    3. Если cookie нет — показываем авторизацию.
    """

    # --------------------------------------------------------
    # Уже авторизован
    # --------------------------------------------------------

    if is_authenticated():

        return True

    # --------------------------------------------------------
    # Восстанавливаем из cookie
    # --------------------------------------------------------

    if restore_auth_from_cookie():

        return True

    # --------------------------------------------------------
    # Cookie нет
    # --------------------------------------------------------

    login_form()

    return False


# ============================================================
# КНОПКА ВЫХОДА
# ============================================================

def logout_button():
    """Показывает кнопку выхода в боковой панели."""

    if not is_authenticated():

        return

    st.sidebar.write(
        f"{st.session_state.get('username', '')}"
    )

    if st.sidebar.button(
        ":material/logout: Выйти",
        use_container_width=True
    ):

        logout_user()

        st.stop()