import streamlit as st
import uuid

from logger import logger


# ============================================================ 
# НАСТРОЙКА СТРАНИЦЫ 
# ============================================================ 
st.set_page_config( 
    page_title="Главная страница", 
    page_icon="🏠", 
    layout="wide", 
    initial_sidebar_state="expanded" )

# ============================================================
# НАСТРОЙКА НАВИГАЦИИ
# ============================================================

pages = [
    st.Page(
        "pages/Главная страница.py",
        title="🏠 Главная страница"
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
        "pages/admin.py",
        title="🔐 Администрирование"
    ),

]


# ============================================================
# ЗАПУСК НАВИГАЦИИ
# ============================================================

pg = st.navigation(pages)

# ============================================================
# ИНИЦИАЛИЗАЦИЯ СЕССИИ
# ============================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# ============================================================
# ЛОГИРОВАНИЕ ПОСЕЩЕНИЯ СТРАНИЦЫ
# ============================================================

current_page = pg.title

if st.session_state.get("last_logged_page") != current_page:

    logger.log_action(
        "page_visit",
        current_page
    )

    st.session_state.last_logged_page = current_page


pg.run()