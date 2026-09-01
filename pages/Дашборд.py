import streamlit as st
import pandas as pd
from datetime import datetime

from config import Config
from queries import AUTO_REFRESH_OUT


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Дашборд",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# КОНСТАНТЫ
# ============================================================

# Интервал обновления данных из БД
REFRESH_INTERVAL = 120

# Интервал переключения отчета
CAROUSEL_INTERVAL = 15


# ============================================================
# SESSION STATE
# ============================================================

# ------------------------------------------------------------
# Автообновление данных
# ------------------------------------------------------------

if "auto_refresh_enabled" not in st.session_state:

    st.session_state.auto_refresh_enabled = False


# ------------------------------------------------------------
# Время следующего обновления данных
# ------------------------------------------------------------

if "next_refresh_time" not in st.session_state:

    st.session_state.next_refresh_time = (
        datetime.now().timestamp()
        + REFRESH_INTERVAL
    )


# ------------------------------------------------------------
# Текущий отчет
# ------------------------------------------------------------

if "current_report" not in st.session_state:

    st.session_state.current_report = 0


# ------------------------------------------------------------
# Время следующего переключения отчета
# ------------------------------------------------------------

if "next_carousel_time" not in st.session_state:

    st.session_state.next_carousel_time = (
        datetime.now().timestamp()
        + CAROUSEL_INTERVAL
    )


# ------------------------------------------------------------
# Автопрокрутка карусели
# ------------------------------------------------------------

if "carousel_enabled" not in st.session_state:

    st.session_state.carousel_enabled = True


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

    /* ====================================================== */
    /* Основной контейнер */
    /* ====================================================== */

    .main > div {
        padding-top: 3rem !important;
    }

    .block-container {
        padding-top: 3rem !important;
    }

    /* ====================================================== */
    /* Номер и название отчета */
    /* ====================================================== */

    .carousel-counter {
        text-align: center;
        font-size: 18px;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 15px;
        padding: 18px;
        background: var(--secondary-background-color);
        color: var(--text-color) !important;
        border-radius: 10px;
    }



    /* ====================================================== */
    /* Таймер карусели */
    /* ====================================================== */

    .carousel-timer {
        text-align: center;
        font-size: 14px;
        margin-bottom: 15px;
        padding: 18px;
        background: #f8f9fa;
        border-radius: 10px;
    }


    /* ====================================================== */
    /* Таймер обновления */
    /* ====================================================== */

    .refresh-timer {
        font-size: 14px;
        font-weight: 400;
        margin-top: 5px;
        margin-bottom: 10px;
    }

    .refresh-countdown {
        font-size: 14px;
        font-weight: 400;
    }


    /* ====================================================== */
    /* Кнопки */
    /* ====================================================== */

    div.stButton > button {
        width: 100%;
    }

</style>
""",
    unsafe_allow_html=True
)


# ============================================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ
# ============================================================

engine = Config.get_engine()


# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================

@st.cache_data
def load_data(query_name, params=None):

    try:

        query = AUTO_REFRESH_OUT.get(query_name)

        if query is None:

            return pd.DataFrame()


        # ----------------------------------------------------
        # Запрос с параметрами
        # ----------------------------------------------------

        if params:

            df = pd.read_sql(
                query,
                engine,
                params=params
            )

        # ----------------------------------------------------
        # Обычный запрос
        # ----------------------------------------------------

        else:

            df = pd.read_sql(
                query,
                engine
            )


        return df


    except Exception as e:

        st.error(
            f"Ошибка загрузки отчета "
            f"'{query_name}': {str(e)}"
        )

        return pd.DataFrame()


# ============================================================
# ОТОБРАЖЕНИЕ ОТЧЕТА
# ============================================================

def show_report(report_name):

    # --------------------------------------------------------
    # Загружаем данные
    # --------------------------------------------------------

    df = load_data(report_name)


    # --------------------------------------------------------
    # Нет данных
    # --------------------------------------------------------

    if df.empty:

        st.warning(
            f"Нет данных для отчета «{report_name}»"
        )

        return


    # --------------------------------------------------------
    # Таблица
    # --------------------------------------------------------

    st.dataframe(
        df,
        use_container_width=True,
        height=500
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # ========================================================
    # РУЧНОЕ ОБНОВЛЕНИЕ
    # ========================================================

    if st.button(
        "🔄 Обновить данные",
        use_container_width=True
    ):

        now = datetime.now()


        # ----------------------------------------------------
        # Очищаем кэш
        # ----------------------------------------------------

        load_data.clear()


        # ----------------------------------------------------
        # Перезапускаем таймер
        # ----------------------------------------------------

        st.session_state.next_refresh_time = (
            now.timestamp()
            + REFRESH_INTERVAL
        )


        st.rerun()


    st.header("⚙️ Настройки")


    # ========================================================
    # АВТООБНОВЛЕНИЕ
    # ========================================================

    st.subheader("🔄 Обновление данных")


    auto_refresh = st.checkbox(
        "Включить автообновление (2 мин.)",
        value=st.session_state.auto_refresh_enabled
    )


    # --------------------------------------------------------
    # Изменилось состояние
    # --------------------------------------------------------

    if auto_refresh != st.session_state.auto_refresh_enabled:

        st.session_state.auto_refresh_enabled = auto_refresh

        now = datetime.now()


        # ----------------------------------------------------
        # Включили автообновление
        # ----------------------------------------------------

        if auto_refresh:

            st.session_state.next_refresh_time = (
                now.timestamp()
                + REFRESH_INTERVAL
            )


        # ----------------------------------------------------
        # Выключили автообновление
        # ----------------------------------------------------

        else:

            # Никакого обновления данных здесь нет.
            # Просто отключаем автоматический цикл.

            st.session_state.next_refresh_time = (
                now.timestamp()
            )


        st.rerun()


    # ========================================================
    # КАРУСЕЛЬ
    # ========================================================

    st.subheader("🎞️ Карусель отчетов")


    carousel_enabled = st.checkbox(
        f"Автопереключение ({CAROUSEL_INTERVAL} сек.)",
        value=st.session_state.carousel_enabled
    )


    # --------------------------------------------------------
    # Изменилось состояние карусели
    # --------------------------------------------------------

    if carousel_enabled != st.session_state.carousel_enabled:

        st.session_state.carousel_enabled = carousel_enabled

        st.session_state.next_carousel_time = (
            datetime.now().timestamp()
            + CAROUSEL_INTERVAL
        )

        st.rerun()


# ============================================================
# ПРОВЕРКА ОТЧЕТОВ
# ============================================================

if not AUTO_REFRESH_OUT:

    st.info(
        "Нет настроенных отчетов"
    )

    st.stop()


# ============================================================
# СПИСОК ОТЧЕТОВ
# ============================================================

report_names = list(
    AUTO_REFRESH_OUT.keys()
)

report_count = len(report_names)


# ============================================================
# ЗАЩИТА ИНДЕКСА
# ============================================================

if st.session_state.current_report >= report_count:

    st.session_state.current_report = 0


# ============================================================
# FRAGMENT
#
# ВАЖНО:
#
# Если автообновление выключено:
# fragment НЕ перезапускается каждую секунду.
#
# Если включено:
# fragment работает каждую секунду.
# ============================================================

@st.fragment(
    run_every=(
        1
        if st.session_state.auto_refresh_enabled
        or st.session_state.carousel_enabled
        else None
    )
)
def reports_page():

    now = datetime.now()


    # ========================================================
    # АВТООБНОВЛЕНИЕ ДАННЫХ
    # ========================================================

    seconds_left_refresh = 0


    if st.session_state.auto_refresh_enabled:

        seconds_left_refresh = int(
            st.session_state.next_refresh_time
            - now.timestamp()
        )


        # ----------------------------------------------------
        # Пора обновлять данные
        # ----------------------------------------------------

        if seconds_left_refresh <= 0:

            # -----------------------------------------------
            # Очищаем кэш
            # -----------------------------------------------

            load_data.clear()


            # -----------------------------------------------
            # Фиксируем следующее обновление
            # -----------------------------------------------

            refresh_time = datetime.now()


            st.session_state.next_refresh_time = (
                refresh_time.timestamp()
                + REFRESH_INTERVAL
            )


            seconds_left_refresh = REFRESH_INTERVAL


        seconds_left_refresh = max(
            0,
            seconds_left_refresh
        )


    # ========================================================
    # АВТОПЕРЕКЛЮЧЕНИЕ КАРУСЕЛИ
    # ========================================================

    seconds_left_carousel = 0


    if (
        st.session_state.carousel_enabled
        and report_count > 1
    ):

        seconds_left_carousel = int(
            st.session_state.next_carousel_time
            - now.timestamp()
        )


        # ----------------------------------------------------
        # Пора переключать отчет
        # ----------------------------------------------------

        if seconds_left_carousel <= 0:

            st.session_state.current_report = (
                st.session_state.current_report + 1
            ) % report_count


            # -----------------------------------------------
            # Перезапускаем таймер карусели
            # -----------------------------------------------

            st.session_state.next_carousel_time = (
                datetime.now().timestamp()
                + CAROUSEL_INTERVAL
            )


            seconds_left_carousel = CAROUSEL_INTERVAL


        seconds_left_carousel = max(
            0,
            seconds_left_carousel
        )


    # ========================================================
    # ТАЙМЕР ОБНОВЛЕНИЯ ДАННЫХ
    # ========================================================

    if st.session_state.auto_refresh_enabled:

        with st.sidebar:
            
            st.divider()
            st.markdown(
                f"""
    <div class="refresh-timer">
        🔄 Следующее обновление через:
        <span class="refresh-countdown">
            {seconds_left_refresh} сек.
        </span>
    </div>
    """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "⏸️ Автообновление выключено"
        )


    # ========================================================
    # ТЕКУЩИЙ ОТЧЕТ
    # ========================================================

    current_index = (
        st.session_state.current_report
    )


    current_report_name = (
        report_names[current_index]
    )


    # ========================================================
    # НОМЕР + НАЗВАНИЕ ОТЧЕТА
    # ========================================================

    st.markdown(
        f"""
<div class="carousel-counter">
    Отчет {current_index + 1} / {report_count}
    — {current_report_name}
</div>
""",
        unsafe_allow_html=True
    )


#     # ========================================================
#     # ТАЙМЕР КАРУСЕЛИ
#     # ========================================================

#     if (
#         st.session_state.carousel_enabled
#         and report_count > 1
#     ):

#         st.markdown(
#             f"""
# <div class="carousel-timer">
#     Следующий отчет через:
#     <b>{seconds_left_carousel} сек.</b>
# </div>
# """,
#             unsafe_allow_html=True
#         )


    # ========================================================
    # НАВИГАЦИЯ
    # ========================================================

    nav_col1, nav_col2, nav_col3 = st.columns(
        [1, 4, 1]
    )


    # --------------------------------------------------------
    # НАЗАД
    # --------------------------------------------------------

    with nav_col1:

        if st.button(
            "← Предыдущий",
            use_container_width=True
        ):

            st.session_state.current_report = (
                st.session_state.current_report - 1
            ) % report_count


            st.session_state.next_carousel_time = (
                datetime.now().timestamp()
                + CAROUSEL_INTERVAL
            )


    # --------------------------------------------------------
    # ЦЕНТР
    # --------------------------------------------------------

    with nav_col2:

        st.empty()


    # --------------------------------------------------------
    # ВПЕРЕД
    # --------------------------------------------------------

    with nav_col3:

        if st.button(
            "Следующий →",
            use_container_width=True
        ):

            st.session_state.current_report = (
                st.session_state.current_report + 1
            ) % report_count


            st.session_state.next_carousel_time = (
                datetime.now().timestamp()
                + CAROUSEL_INTERVAL
            )


    # ========================================================
    # ОТЧЕТ
    # ========================================================

    show_report(
        current_report_name
    )


# ============================================================
# ЗАПУСК
# ============================================================

reports_page()