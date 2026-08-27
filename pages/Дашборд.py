import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime


from config import Config
from queries import AUTO_REFRESH_OUT


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Дашборд",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# КОНСТАНТЫ
# ============================================================

# Обновление данных из БД
REFRESH_INTERVAL = 120

# Переключение отчета в карусели
CAROUSEL_INTERVAL = 15


# ============================================================
# ИНИЦИАЛИЗАЦИЯ SESSION STATE
# ============================================================

# ------------------------------------------------------------
# Автообновление данных
# ------------------------------------------------------------

if "auto_refresh_enabled" not in st.session_state:
    st.session_state.auto_refresh_enabled = False


# ------------------------------------------------------------
# Время последнего обновления данных
# ------------------------------------------------------------

if "last_refresh_time" not in st.session_state:
    st.session_state.last_refresh_time = datetime.now()


# ------------------------------------------------------------
# Время следующего обновления данных
# ------------------------------------------------------------

if "next_refresh_time" not in st.session_state:
    st.session_state.next_refresh_time = (
        datetime.now().timestamp()
        + REFRESH_INTERVAL
    )


# ------------------------------------------------------------
# Текущий отчет карусели
# ------------------------------------------------------------

if "current_report" not in st.session_state:
    st.session_state.current_report = 0


# ------------------------------------------------------------
# Время следующего переключения карусели
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

        /* -------------------------------------------------- */
        /* Убираем стандартный header Streamlit */
        /* -------------------------------------------------- */

        header {
            display: none !important;
        }

        .stAppHeader {
            display: none !important;
        }

        [data-testid="stHeader"] {
            display: none !important;
        }


        /* -------------------------------------------------- */
        /* Убираем верхний отступ */
        /* -------------------------------------------------- */

        .main > div {
            padding-top: 0px !important;
        }

        .block-container {
            padding-top: 0px !important;
        }


        /* -------------------------------------------------- */
        /* Заголовок карусели */
        /* -------------------------------------------------- */

        .carousel-title {
            text-align: center;
            font-size: 24px;
            font-weight: 700;
            margin-top: 5px;
            margin-bottom: 10px;
        }


        /* -------------------------------------------------- */
        /* Номер и название отчета */
        /* -------------------------------------------------- */

        .carousel-counter {
            text-align: center;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
        }


        /* -------------------------------------------------- */
        /* Таймер карусели */
        /* -------------------------------------------------- */

        .carousel-timer {
            text-align: center;
            font-size: 14px;
            margin-bottom: 15px;
        }


        /* -------------------------------------------------- */
        /* Таймер обновления данных */
        /* -------------------------------------------------- */

        .refresh-timer {
            font-size: 16px;
            font-weight: 600;
            margin-top: 5px;
            margin-bottom: 10px;
        }

        .refresh-countdown {
            font-size: 18px;
            font-weight: 700;
        }


        /* -------------------------------------------------- */
        /* Кнопки навигации */
        /* -------------------------------------------------- */

        div.stButton > button {
            width: 100%;
        }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================================

engine = Config.get_engine()


# ============================================================
# ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
# ============================================================

@st.cache_data(ttl=10)
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
            f"Ошибка загрузки отчета '{query_name}': {str(e)}"
        )

        return pd.DataFrame()


# ============================================================
# ОТОБРАЖЕНИЕ ОДНОГО ОТЧЕТА
# ============================================================

def show_report(report_name):

    # --------------------------------------------------------
    # Загружаем данные
    # --------------------------------------------------------

    df = load_data(report_name)


    # --------------------------------------------------------
    # Если данных нет
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


    # --------------------------------------------------------
    # Определяем числовые колонки
    # --------------------------------------------------------

    numeric_cols = df.select_dtypes(
        include=["number"]
    ).columns


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Настройки")


    # ========================================================
    # АВТООБНОВЛЕНИЕ ДАННЫХ
    # ========================================================

    st.subheader("🔄 Обновление данных")

    auto_refresh = st.checkbox(
        "Включить автообновление (2 мин.)",
        value=st.session_state.auto_refresh_enabled
    )


    # --------------------------------------------------------
    # Изменилось состояние автообновления
    # --------------------------------------------------------

    if auto_refresh != st.session_state.auto_refresh_enabled:

        st.session_state.auto_refresh_enabled = auto_refresh

        now = datetime.now()


        # ----------------------------------------------------
        # Включили автообновление
        # ----------------------------------------------------

        if auto_refresh:

            st.session_state.last_refresh_time = now

            st.session_state.next_refresh_time = (
                now.timestamp()
                + REFRESH_INTERVAL
            )


        # ----------------------------------------------------
        # Выключили автообновление
        # ----------------------------------------------------

        else:

            st.session_state.next_refresh_time = (
                now.timestamp()
            )


        # ----------------------------------------------------
        # Очищаем кэш
        # ----------------------------------------------------

        load_data.clear()

        st.rerun()


    # ========================================================
    # РУЧНОЕ ОБНОВЛЕНИЕ
    # ========================================================

    if st.button(
        "🔄 Обновить сейчас",
        use_container_width=True
    ):

        now = datetime.now()


        # ----------------------------------------------------
        # Фиксируем время обновления
        # ----------------------------------------------------

        st.session_state.last_refresh_time = now


        # ----------------------------------------------------
        # Запускаем таймер заново
        # ----------------------------------------------------

        st.session_state.next_refresh_time = (
            now.timestamp()
            + REFRESH_INTERVAL
        )


        # ----------------------------------------------------
        # Очищаем кэш
        # ----------------------------------------------------

        load_data.clear()

        st.rerun()


    # ========================================================
    # НАСТРОЙКИ КАРУСЕЛИ
    # ========================================================

    st.subheader("🎞️ Карусель отчетов")


    # --------------------------------------------------------
    # Включение / выключение автопрокрутки
    # --------------------------------------------------------

    carousel_enabled = st.checkbox(
        f"Автопереключение ({CAROUSEL_INTERVAL} сек.)",
        value=st.session_state.carousel_enabled
    )


    # --------------------------------------------------------
    # Если изменили состояние
    # --------------------------------------------------------

    if carousel_enabled != st.session_state.carousel_enabled:

        st.session_state.carousel_enabled = carousel_enabled

        st.session_state.next_carousel_time = (
            datetime.now().timestamp()
            + CAROUSEL_INTERVAL
        )

        st.rerun()

# ============================================================
# ПРОВЕРКА НАЛИЧИЯ ОТЧЕТОВ
# ============================================================

if not AUTO_REFRESH_OUT:

    st.info(
        "Нет настроенных отчетов"
    )

    st.stop()


# ============================================================
# ПОЛУЧАЕМ СПИСОК ОТЧЕТОВ
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
# ============================================================

@st.fragment(run_every=1)
def reports_page():

    now = datetime.now()


    # ========================================================
    # АВТООБНОВЛЕНИЕ ДАННЫХ
    # ========================================================

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
            # Фиксируем время обновления
            # -----------------------------------------------

            refresh_time = datetime.now()

            st.session_state.last_refresh_time = (
                refresh_time
            )


            # -----------------------------------------------
            # Запускаем новый цикл
            # -----------------------------------------------

            st.session_state.next_refresh_time = (
                refresh_time.timestamp()
                + REFRESH_INTERVAL
            )


            seconds_left_refresh = REFRESH_INTERVAL


        seconds_left_refresh = max(
            0,
            seconds_left_refresh
        )


    else:

        seconds_left_refresh = 0


    # ========================================================
    # АВТОПЕРЕКЛЮЧЕНИЕ КАРУСЕЛИ
    # ========================================================

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
            # Запускаем таймер заново
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

    else:

        seconds_left_carousel = 0

    # ========================================================
    # ВРЕМЯ ОБНОВЛЕНИЯ ДАННЫХ
    # ========================================================


    st.caption(
        "Последнее обновление: "
        f"{st.session_state.last_refresh_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


    # ========================================================
    # ТАЙМЕР ОБНОВЛЕНИЯ ДАННЫХ
    # ========================================================

    if st.session_state.auto_refresh_enabled:

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
            "⏸️ Автообновление выключено",
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


    # ========================================================
    # ТАЙМЕР КАРУСЕЛИ
    # ========================================================

    if (
        st.session_state.carousel_enabled
        and report_count > 1
    ):

        st.markdown(
            f"""
            <div class="carousel-timer">
                Следующий отчет через:
                <b>{seconds_left_carousel} сек.</b>
            </div>
            """,
            unsafe_allow_html=True
        )


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

            st.rerun(scope="fragment")


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

            st.rerun(scope="fragment")


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