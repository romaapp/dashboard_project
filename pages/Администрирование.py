import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from logger import logger
from styles import load_css
from config import Config
from suggestions import (
    get_suggestions,
    get_suggestion_files,
    set_suggestion_completed,
    delete_suggestion
)

import os
import sqlite3


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Администрирование",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()


# ============================================================
# ПОЛЬЗОВАТЕЛИ ПО ДНЯМ
# ============================================================

def get_daily_visitors():
    """Получает количество уникальных пользователей по дням."""

    conn = None

    try:

        conn = sqlite3.connect(
            logger.db_path
        )

        df = pd.read_sql_query(
            """
            SELECT
                DATE(timestamp) AS Дата,
                COUNT(DISTINCT user_id) AS Пользователей
            FROM user_actions
            WHERE user_id IS NOT NULL
            GROUP BY DATE(timestamp)
            ORDER BY Дата DESC
            LIMIT 30
            """,
            conn
        )

        return df

    except Exception as e:

        print(
            f"Ошибка получения пользователей по дням: {e}"
        )

        return pd.DataFrame(
            columns=[
                "Дата",
                "Пользователей"
            ]
        )

    finally:

        if conn is not None:

            conn.close()


# ============================================================
# ПРОВЕРКА ПАРОЛЯ
# ============================================================

def check_password():
    """Проверка пароля для доступа к админ-панели"""

    if "admin_authenticated" not in st.session_state:

        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:

        st.title(
            "🔐 Административный доступ"
        )

        st.markdown(
            "Введите пароль для доступа"
        )

        password = st.text_input(
            "Пароль:",
            type="password"
        )

        if st.button("Войти"):

            if password == Config.ADMIN_PASSWORD:

                st.session_state.admin_authenticated = True

                st.success(
                    "✅ Доступ разрешен!"
                )

                st.rerun()

            else:

                st.error(
                    "❌ Неверный пароль!"
                )

        return False

    return True


# ============================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ============================================================

def users_management():

    st.subheader(
        "👤 Управление пользователями"
    )

    st.caption(
        "Здесь можно просматривать зарегистрированных "
        "пользователей, изменять их статус и удалять учетные записи."
    )

    # ========================================================
    # ПОЛУЧАЕМ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ
    # ========================================================

    users = logger.get_all_users()

    if not users:

        st.info(
            "Зарегистрированных пользователей пока нет."
        )

        return

    # ========================================================
    # ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
    # ========================================================

    users_data = []

    for user in users:

        (
            user_id,
            login,
            is_active,
            created_at,
            last_login
        ) = user

        status = (
            "✔ Активен"
            if bool(is_active)
            else "⭕ Отключён"
        )

        users_data.append(
            {
                "ID": user_id,
                "Пользователь": login,
                "Статус": status,
                "Дата регистрации": created_at,
                "Последний вход": (
                    last_login
                    if last_login
                    else "—"
                )
            }
        )

    df_users = pd.DataFrame(
        users_data
    )

    st.dataframe(
        df_users[
            [
                "Пользователь",
                "Статус",
                "Дата регистрации",
                "Последний вход"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # ========================================================
    # ВЫБОР ПОЛЬЗОВАТЕЛЯ
    # ========================================================

    st.subheader(
        "⚙️ Управление учетной записью"
    )

    user_options = {
        user[1]: user
        for user in users
    }

    selected_login = st.selectbox(
        "Выберите пользователя:",
        options=list(user_options.keys()),
        key="admin_selected_user"
    )

    selected_user = user_options[
        selected_login
    ]

    (
        selected_user_id,
        selected_user_login,
        selected_is_active,
        selected_created_at,
        selected_last_login
    ) = selected_user

    # ========================================================
    # ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ
    # ========================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "👤 Пользователь",
            selected_user_login
        )

    with col2:

        st.metric(
            "Статус",
            "✔ Активен"
            if bool(selected_is_active)
            else "⭕ Отключён"
        )

    with col3:

        st.metric(
            "🆔 ID",
            selected_user_id
        )

    st.caption(
        f"📅 Регистрация: "
        f"{selected_created_at or '—'}"
        f"   •   "
        f"🕐 Последний вход: "
        f"{selected_last_login or '—'}"
    )

    st.divider()

    # ========================================================
    # КНОПКИ УПРАВЛЕНИЯ
    # ========================================================

    col_activate, col_delete = st.columns(
        2
    )

    # ========================================================
    # АКТИВАЦИЯ / ОТКЛЮЧЕНИЕ
    # ========================================================

    with col_activate:

        if bool(selected_is_active):

            if st.button(
                "⭕ Отключить пользователя",
                use_container_width=True,
                key="deactivate_selected_user"
            ):

                logger.set_user_active(
                    selected_user_id,
                    False
                )

                st.success(
                    f"Пользователь "
                    f"«{selected_user_login}» отключён."
                )

                st.rerun()

        else:

            if st.button(
                "✔ Активировать пользователя",
                use_container_width=True,
                key="activate_selected_user"
            ):

                logger.set_user_active(
                    selected_user_id,
                    True
                )

                st.success(
                    f"Пользователь "
                    f"«{selected_user_login}» активирован."
                )

                st.rerun()

    # ========================================================
    # УДАЛЕНИЕ
    # ========================================================

    with col_delete:

        if st.button(
            "🗑 Удалить пользователя",
            use_container_width=True,
            key="delete_selected_user"
        ):

            st.session_state[
                "confirm_delete_user"
            ] = True

    # ========================================================
    # ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
    # ========================================================

    if st.session_state.get(
        "confirm_delete_user",
        False
    ):

        st.warning(
            f"⚠️ Вы действительно хотите удалить "
            f"пользователя «{selected_user_login}»?"
        )

        st.caption(
            "История действий пользователя "
            "в статистике дашборда при этом сохранится."
        )

        col_confirm, col_cancel = st.columns(
            2
        )

        with col_confirm:

            if st.button(
                "🗑 Да, удалить",
                type="primary",
                use_container_width=True,
                key="confirm_delete_user_button"
            ):

                logger.delete_user(
                    selected_user_id
                )

                st.session_state[
                    "confirm_delete_user"
                ] = False

                st.success(
                    f"Пользователь "
                    f"«{selected_user_login}» удалён."
                )

                st.rerun()

        with col_cancel:

            if st.button(
                "✖ Отмена",
                use_container_width=True,
                key="cancel_delete_user_button"
            ):

                st.session_state[
                    "confirm_delete_user"
                ] = False

                st.rerun()


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():

    st.title(
        "🔐 Администрирование"
    )

    st.caption(
        f"Обновлено: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # ========================================================
    # ПОЛУЧАЕМ ПРЕДЛОЖЕНИЯ
    # ========================================================

    all_suggestions = get_suggestions(
        "all"
    )

    # ========================================================
    # СЧИТАЕМ НОВЫЕ ПРЕДЛОЖЕНИЯ
    # ========================================================

    new_suggestions_count = sum(
        1
        for suggestion in all_suggestions
        if not bool(suggestion[5])
    )

    # ========================================================
    # КНОПКА ВОЗВРАТА + ИНДИКАТОР НОВЫХ ПРЕДЛОЖЕНИЙ
    # ========================================================

    col_home, col_spacer, col_suggestions = st.columns(
        [1, 3, 2]
    )

    # --------------------------------------------------------
    # НА ГЛАВНУЮ
    # --------------------------------------------------------

    with col_home:

        if st.button(
            "⬅️ На главную"
        ):

            st.switch_page(
                "pages/Главная страница.py"
            )

    # --------------------------------------------------------
    # НОВЫЕ ПРЕДЛОЖЕНИЯ
    # --------------------------------------------------------

    with col_suggestions:

        if new_suggestions_count > 0:

            st.markdown(
                f"""
                <div style="
                    padding-top: 8px;
                    font-size: 0.95rem;
                ">
                    💡 Новые предложения по развитию —
                    <strong>{new_suggestions_count}</strong>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                """
                <div style="
                    padding-top: 8px;
                    font-size: 0.95rem;
                    opacity: 0.65;
                ">
                    💡 Новые предложения по развитию —
                    нет
                </div>
                """,
                unsafe_allow_html=True
            )

    # ========================================================
    # ВКЛАДКИ
    # ========================================================

    (
        tab_statistics,
        tab_online,
        tab_suggestions,
        tab_users
    ) = st.tabs(
        [
            "📊 Статистика использования дашборда",
            "🌐 Пользователи онлайн",
            "💡 Предложения по развитию",
            "👤 Пользователи"
        ]
    )

    # ========================================================
    # ВКЛАДКА 1 — СТАТИСТИКА
    # ========================================================

    with tab_statistics:

        stats = logger.get_statistics()

        # ----------------------------------------------------
        # ВЕРХНИЕ МЕТРИКИ
        # ----------------------------------------------------

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            st.metric(
                "👥 Уникальных посетителей",
                stats["unique_visitors"]
            )

        with col2:

            st.metric(
                "📊 Всего действий",
                stats["total_actions"]
            )

        with col3:

            st.metric(
                "🔄 Сессий",
                stats["unique_sessions"]
            )

        with col4:

            st.metric(
                "📅 Действий сегодня",
                stats["today_actions"]
            )

        with col5:

            st.metric(
                "👤 Посетителей сегодня",
                stats["today_visitors"]
            )

        st.divider()

        # ----------------------------------------------------
        # ПОПУЛЯРНЫЕ ОТЧЕТЫ
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            st.subheader(
                "🔥 Популярные отчеты"
            )

            if stats["popular_reports"]:

                df_popular = pd.DataFrame(
                    stats["popular_reports"],
                    columns=[
                        "Отчет",
                        "Просмотров"
                    ]
                )

                st.dataframe(
                    df_popular,
                    use_container_width=True
                )

                if len(df_popular) > 0:

                    fig = px.bar(
                        df_popular,
                        x="Отчет",
                        y="Просмотров",
                        title="Популярность отчетов",
                        template="plotly_white"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

            else:

                st.info(
                    "Нет данных о просмотренных отчетах"
                )

        # ----------------------------------------------------
        # ЕЖЕДНЕВНАЯ АКТИВНОСТЬ
        # ----------------------------------------------------

        with col2:

            st.subheader(
                "📅 Ежедневная активность"
            )

            if stats["daily_activity"]:

                df_daily = pd.DataFrame(
                    stats["daily_activity"],
                    columns=[
                        "Дата",
                        "Действий"
                    ]
                )

                df_daily["Дата"] = pd.to_datetime(
                    df_daily["Дата"]
                )

                df_daily = df_daily.sort_values(
                    "Дата"
                )

                # --------------------------------------------
                # АКТИВНОСТЬ ПО ДНЯМ
                # --------------------------------------------

                fig = px.line(
                    df_daily,
                    x="Дата",
                    y="Действий",
                    title="Активность по дням (последние 30 дней)",
                    template="plotly_white"
                )

                fig.update_layout(
                    height=400
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                st.dataframe(
                    df_daily,
                    use_container_width=True
                )

            else:

                st.info(
                    "Нет данных об активности"
                )

            # ------------------------------------------------
            # ПОЛЬЗОВАТЕЛИ ПО ДНЯМ
            # ------------------------------------------------

            df_visitors = get_daily_visitors()

            if not df_visitors.empty:

                df_visitors["Дата"] = pd.to_datetime(
                    df_visitors["Дата"]
                )

                df_visitors = df_visitors.sort_values(
                    "Дата"
                )

                fig_visitors = px.line(
                    df_visitors,
                    x="Дата",
                    y="Пользователей",
                    title="Пользователи по дням (последние 30 дней)",
                    template="plotly_white"
                )

                fig_visitors.update_layout(
                    height=400
                )

                st.plotly_chart(
                    fig_visitors,
                    use_container_width=True
                )

                st.dataframe(
                    df_visitors,
                    use_container_width=True
                )

            else:

                st.info(
                    "Нет данных о пользователях"
                )

    # ========================================================
    # ВКЛАДКА 2 — ПОЛЬЗОВАТЕЛИ ОНЛАЙН
    # ========================================================

    with tab_online:

        st.caption(
            "Пользователь считается онлайн, "
            "если его последняя активность была "
            "в течение последних 5 минут."
        )

        # ----------------------------------------------------
        # ПОЛУЧАЕМ ОНЛАЙН ПОЛЬЗОВАТЕЛЕЙ
        # ----------------------------------------------------

        online_users = logger.get_online_users(
            minutes=5
        )

        # ----------------------------------------------------
        # ПОЛУЧАЕМ СТАТИСТИКУ
        # ----------------------------------------------------

        stats = logger.get_statistics()

        # ----------------------------------------------------
        # МЕТРИКИ
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "👁️‍🗨️ Сейчас онлайн",
                len(online_users)
            )

        with col2:

            st.metric(
                "👥 Уникальных посетителей",
                stats["unique_visitors"]
            )

        with col3:

            st.metric(
                "👤 Посетителей сегодня",
                stats["today_visitors"]
            )

        st.divider()

        # ----------------------------------------------------
        # СПИСОК ОНЛАЙН ПОЛЬЗОВАТЕЛЕЙ
        # ----------------------------------------------------

        st.subheader(
            "👁️‍🗨️ Активные пользователи"
        )

        if online_users:

            df_online = pd.DataFrame(
                online_users,
                columns=[
                    "ID",
                    "Пользователь",
                    "IP адрес",
                    "Последняя активность"
                ]
            )

            # -----------------------------------------------
            # ФОРМАТИРУЕМ ВРЕМЯ
            # -----------------------------------------------

            df_online["Последняя активность"] = pd.to_datetime(
                df_online["Последняя активность"],
                errors="coerce"
            )

            df_online["Статус"] = "👁️‍🗨️ Онлайн"

            # -----------------------------------------------
            # ПОРЯДОК КОЛОНОК
            # -----------------------------------------------

            df_online = df_online[
                [
                    "Статус",
                    "Пользователь",
                    "IP адрес",
                    "Последняя активность"
                ]
            ]

            st.dataframe(
                df_online,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Сейчас активных пользователей нет."
            )

        st.divider()

        # ====================================================
        # ПОСЛЕДНИЕ ДЕЙСТВИЯ
        # ====================================================

        st.subheader(
            "🕐 Последние действия"
        )

        # ----------------------------------------------------
        # Получаем свежую статистику
        # ----------------------------------------------------

        stats = logger.get_statistics()

        if stats["recent_actions"]:

            df_actions = pd.DataFrame(
                stats["recent_actions"],
                columns=[
                    "Время",
                    "IP адрес",
                    "Действие",
                    "Отчет",
                    "Пользователь"
                ]
            )

            df_actions["Действие"] = df_actions[
                "Действие"
            ].replace({
                "login": "Вход",
                "logout": "Выход",
                "page_visit": "Посещение страницы",
                "view_report": "Запуск отчета",
                "visit": "Посещение страницы"
            })

            # ------------------------------------------------
            # ФИЛЬТР ПО ЛОГИНУ
            # ------------------------------------------------

            st.subheader(
                "🔍 Фильтр по пользователю"
            )

            # Получаем зарегистрированных пользователей
            all_users = logger.get_all_users()

            login_list = [
                user[1]
                for user in all_users
                if user[1]
            ]

            login_list = sorted(
                set(login_list)
            )

            # Добавляем возможность увидеть действия
            # без привязанного логина
            has_empty_login = df_actions[
                "Пользователь"
            ].isna().any()

            filter_options = [
                "Все пользователи"
            ] + login_list

            if has_empty_login:

                filter_options.append(
                    "Без логина"
                )

            selected_login = st.selectbox(
                "Выберите пользователя:",
                filter_options,
                key="admin_recent_actions_login_filter"
            )

            # ------------------------------------------------
            # ПРИМЕНЯЕМ ФИЛЬТР
            # ------------------------------------------------

            if selected_login == "Все пользователи":

                filtered_df = df_actions

            elif selected_login == "Без логина":

                filtered_df = df_actions[
                    df_actions["Пользователь"].isna()
                ]

            else:

                filtered_df = df_actions[
                    df_actions["Пользователь"] == selected_login
                ]

            # ------------------------------------------------
            # ТАБЛИЦА
            # ------------------------------------------------

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Нет записей о действиях"
            )

    # ========================================================
    # ВКЛАДКА 3 — ПРЕДЛОЖЕНИЯ
    # ========================================================

    with tab_suggestions:

        suggestions = all_suggestions

        if not suggestions:

            st.info(
                "Пока нет предложений."
            )

        else:

            for (
                suggestion_id,
                title,
                author,
                suggestion,
                created_at,
                completed,
                completed_at,
                completed_by
            ) in suggestions:

                # ------------------------------------------------
                # СТАРЫЕ ПРЕДЛОЖЕНИЯ БЕЗ ТЕМЫ
                # ------------------------------------------------

                if not title:

                    title = suggestion.split(
                        "\n"
                    )[0][:80]

                # ------------------------------------------------
                # СТАТУС
                # ------------------------------------------------

                status = (
                    "✅ Выполнено"
                    if completed
                    else "⌛ В работе"
                )

                # ------------------------------------------------
                # СВЕРНУТАЯ ЗАЯВКА
                # ------------------------------------------------

                with st.expander(
                    f"💡 {title}  •  👤 {author}  •  {status}",
                    expanded=False
                ):

                    # --------------------------------------------
                    # ШАПКА
                    # --------------------------------------------

                    col1, col2 = st.columns(
                        [8, 2]
                    )

                    with col1:

                        st.markdown(
                            f"### 💡 Предложение #{suggestion_id}"
                        )

                        st.caption(
                            f"👤 {author} • "
                            f"📅 {created_at} • "
                            f"{status}"
                        )

                    # --------------------------------------------
                    # ВЫПОЛНЕНО
                    # --------------------------------------------

                    with col2:

                        new_completed = st.checkbox(
                            "Выполнено",
                            value=bool(completed),
                            key=(
                                f"admin_completed_"
                                f"{suggestion_id}"
                            )
                        )

                        if new_completed != bool(
                            completed
                        ):

                            set_suggestion_completed(
                                suggestion_id,
                                new_completed,
                                "admin"
                            )

                            st.rerun()

                    st.divider()

                    # --------------------------------------------
                    # ТЕМА
                    # --------------------------------------------

                    st.markdown(
                        f"**💡 Тема:** {title}"
                    )

                    # --------------------------------------------
                    # ТЕКСТ ПРЕДЛОЖЕНИЯ
                    # --------------------------------------------

                    st.markdown(
                        "### Описание"
                    )

                    st.text(
                        suggestion
                    )

                    # --------------------------------------------
                    # ИНФОРМАЦИЯ О ВЫПОЛНЕНИИ
                    # --------------------------------------------

                    if completed:

                        completion_text = (
                            f"✅ Выполнено: "
                            f"{completed_at or ''}"
                        )

                        if completed_by:

                            completion_text += (
                                f" • {completed_by}"
                            )

                        st.caption(
                            completion_text
                        )

                    # --------------------------------------------
                    # ВЛОЖЕНИЯ
                    # --------------------------------------------

                    files = get_suggestion_files(
                        suggestion_id
                    )

                    if files:

                        st.markdown(
                            "### 📎 Вложения"
                        )

                        for file_data in files:

                            (
                                file_id,
                                original_name,
                                stored_name,
                                file_path,
                                uploaded_at
                            ) = file_data

                            if not os.path.exists(
                                file_path
                            ):

                                continue

                            extension = (
                                os.path.splitext(
                                    original_name
                                )[1]
                                .lower()
                            )

                            # ------------------------------------
                            # ИЗОБРАЖЕНИЕ
                            # ------------------------------------

                            if extension in [
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".webp",
                                ".gif"
                            ]:

                                with st.expander(
                                    f"🖼 {original_name}",
                                    expanded=False
                                ):

                                    st.image(
                                        file_path,
                                        use_container_width=True
                                    )

                            # ------------------------------------
                            # ФАЙЛ
                            # ------------------------------------

                            else:

                                with open(
                                    file_path,
                                    "rb"
                                ) as file:

                                    file_bytes = (
                                        file.read()
                                    )

                                st.download_button(
                                    f"📎 {original_name}",
                                    data=file_bytes,
                                    file_name=original_name,
                                    key=(
                                        f"admin_download_"
                                        f"{file_id}"
                                    )
                                )

                    # --------------------------------------------
                    # УДАЛЕНИЕ
                    # --------------------------------------------

                    with st.expander(
                        "⚠️ Дополнительные действия"
                    ):

                        if st.button(
                            "🗑 Удалить предложение",
                            key=(
                                f"delete_suggestion_"
                                f"{suggestion_id}"
                            )
                        ):

                            delete_suggestion(
                                suggestion_id
                            )

                            st.success(
                                "Предложение удалено."
                            )

                            st.rerun()

    # ========================================================
    # ВКЛАДКА 4 — ПОЛЬЗОВАТЕЛИ
    # ========================================================

    with tab_users:

        users_management()


# ============================================================
# ЗАПУСК
# ============================================================

if check_password():

    main()

else:

    st.stop()