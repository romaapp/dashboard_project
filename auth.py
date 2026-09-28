import re
import streamlit as st

from logger import logger


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

    # Фамилия + И. + О.
    pattern = r"^[А-ЯЁа-яёA-Za-z-]+ [А-ЯЁа-яёA-Za-z]\. [А-ЯЁа-яёA-Za-z]\.$"

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
# ВХОД ПОЛЬЗОВАТЕЛЯ
# ============================================================

def login_user(user_id, login):
    """Авторизует пользователя."""

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = login

    # Обновляем время последнего входа
    logger.update_last_login(user_id)

    # Логируем вход
    logger.log_action(
        "login"
    )


# ============================================================
# ВЫХОД ПОЛЬЗОВАТЕЛЯ
# ============================================================

def logout_user():
    """Выход пользователя из системы."""

    # Логируем выход до очистки session_state
    if is_authenticated():

        logger.log_action(
            "logout"
        )

    # Удаляем данные авторизации
    st.session_state["authenticated"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("username", None)

    # Чтобы после выхода снова показать окно авторизации
    st.rerun()


# ============================================================
# РЕГИСТРАЦИЯ
# ============================================================

def registration_form():
    """Форма регистрации нового пользователя."""

    st.subheader("📝 Регистрация",
            help=(
                "Регистрация нужна для будущих персональных "
                "возможностей дашборда: избранные отчеты, "
                "сохраненные настройки, история выбранных "
                "отчетов и другие индивидуальные функции."
            ))

    # --------------------------------------------------------
    # Поле и кнопка регистрации
    # --------------------------------------------------------

    login = st.text_input(
        "Логин в формате Фамилия И. О.",
        placeholder="Введите здесь",
        key="registration_login"
    )

    if st.button(
        "Зарегистрироваться",
        key="register_user_button",
        use_container_width=True
    ):

        is_valid, result = validate_login(
            login
        )

        if not is_valid:

            st.error(result)

            return

        success, user_id = logger.register_user(
            result
        )

        if success:

            st.success(
                "Регистрация выполнена успешно. "
                "Теперь можно войти."
            )

            # Очищаем поле регистрации
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

    st.title("🔐 Авторизация")

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

        st.subheader("👤 Вход")

        # ----------------------------------------------------
        # Получаем только активных пользователей
        # ----------------------------------------------------

        users = logger.get_active_users()

        if users:

            user_options = {
                login: user_id
                for user_id, login in users
            }

            # ------------------------------------------------
            # Пустое значение при загрузке
            # ------------------------------------------------

            login_options = [
                "— Выберите пользователя —"
            ] + list(user_options.keys())

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

                    st.rerun()

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

    Если пользователь авторизован:
        возвращает True

    Если нет:
        показывает окно авторизации
        возвращает False
    """

    if is_authenticated():

        return True

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
        "Выйти",
        use_container_width=True
    ):
        logout_user()