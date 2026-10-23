import streamlit as st
import pandas as pd
import uuid

from logger import logger
from auth import require_auth, logout_button


# Сброс флага при каждом запуске страницы
st.session_state["_stats_rendered_this_run"] = False

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Главная страница",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# ГЛОБАЛЬНАЯ СТАТИСТИКА ПО ВЫДЕЛЕННЫМ ЯЧЕЙКАМ
# ============================================================

_original_dataframe = st.dataframe


def dataframe_with_selection(*args, **kwargs):
    kwargs.setdefault("on_select", "rerun")
    kwargs.setdefault("selection_mode", "multi-cell")

    event = _original_dataframe(*args, **kwargs)

    df = args[0] if args else kwargs.get("data")

    if not isinstance(df, pd.DataFrame):
        return event

    selection = getattr(event, "selection", None)
    selected_cells = getattr(selection, "cells", [])

    if not selected_cells:
        return event

    selected_values = []

    for row_index, column_name in selected_cells:
        if column_name not in df.columns:
            continue

        value = df.iloc[row_index][column_name]

        # Разрешаем числовые значения, сохранённые как текст
        if isinstance(value, str):
            value = (
                value.strip()
                .replace("\u00a0", "")
                .replace(" ", "")
            )

            # Поддержка десятичной запятой
            if "," in value and "." not in value:
                value = value.replace(",", ".")

        numeric_value = pd.to_numeric(
            value,
            errors="coerce"
        )

        if pd.notna(numeric_value):
            selected_values.append(numeric_value)

    numbers = pd.to_numeric(
        pd.Series(selected_values),
        errors="coerce"
    ).dropna()

    if numbers.empty:
        return event

    # Показываем статистику только один раз за запуск
    if not st.session_state.get("_stats_rendered_this_run", False):

        stats_text = (
            f"📊 Ячеек: {len(numbers)}"
            f" | Сумма: {numbers.sum():,.2f}"
            f" | Среднее: {numbers.mean():,.2f}"
            f" | Мин.: {numbers.min():,.2f}"
            f" | Макс.: {numbers.max():,.2f}"
        )

        st.markdown(
            f"""
            <div style="
                position: fixed;
                right: 25px;
                bottom: 25px;
                z-index: 999999;
                background: #20242b;
                color: white;
                padding: 14px 18px;
                border-radius: 10px;
                border: 1px solid #596273;
                box-shadow: 0 4px 18px rgba(0,0,0,0.35);
                font-size: 14px;
                font-weight: 500;
                max-width: 90vw;
            ">
                {stats_text}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.session_state["_stats_rendered_this_run"] = True

    return event


st.dataframe = dataframe_with_selection


# ============================================================
# НАСТРОЙКА НАВИГАЦИИ
# ============================================================

pages = [
    st.Page(
        "pages/Главная страница.py",
        title="🏠 Главная страница",
    ),

    st.Page(
        "pages/Дашборд отгрузки.py",
        title="📊 Дашборд отгрузки"
    ),

    st.Page(
        "pages/Выдача клиенту.py",
        title="📦 Выдача клиенту"
    ),

    st.Page(
        "pages/Разработка.py",
        title="🛠️ Разработка"
    ),

    st.Page(
        "pages/Честный знак.py",
        title="🏷️ Честный знак"
    ),

    st.Page(
        "pages/Timeline заявки.py",
        title="🕐 Timeline заявки"
    ),

    st.Page(
        "pages/Администрирование.py",
        title="🔐 Администрирование"
    ),
]


# ============================================================
# ОТКРЫТЫЕ БЕЗ АВТОРИЗАЦИИ СТРАНИЦЫ
# ============================================================

PUBLIC_PAGES = [
    "📊 Дашборд отгрузки",
    "📦 Выдача клиенту",
]


# ============================================================
# ЗАПУСК НАВИГАЦИИ
# ============================================================

pg = st.navigation(pages)


# ============================================================
# ИНИЦИАЛИЗАЦИЯ СЕССИИ
# ============================================================

if "session_id" not in st.session_state:

    st.session_state.session_id = str(
        uuid.uuid4()
    )


# ============================================================
# ОПРЕДЕЛЯЕМ ТЕКУЩУЮ СТРАНИЦУ
# ============================================================

current_page = pg.title


# ============================================================
# ПРОВЕРКА ДОСТУПА
# ============================================================

# ------------------------------------------------------------
# ОТКРЫТЫЕ СТРАНИЦЫ
# ------------------------------------------------------------

if current_page in PUBLIC_PAGES:

    # --------------------------------------------------------
    # Запуск страницы без авторизации
    # --------------------------------------------------------

    pg.run()


# ------------------------------------------------------------
# ЗАЩИЩЕННЫЕ СТРАНИЦЫ
# ------------------------------------------------------------

else:

    if require_auth():

        # ====================================================
        # КНОПКА ВЫХОДА
        # ====================================================

        logout_button()

        # ====================================================
        # ЛОГИРОВАНИЕ ПОСЕЩЕНИЯ СТРАНИЦЫ
        # ====================================================

        if (
            st.session_state.get("last_logged_page")
            != current_page
        ):

            logger.log_action(
                "page_visit",
                current_page
            )

            st.session_state.last_logged_page = (
                current_page
            )

        # ====================================================
        # ЗАПУСК СТРАНИЦЫ
        # ====================================================

        pg.run()