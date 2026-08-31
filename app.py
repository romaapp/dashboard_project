import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from config import Config
from queries import SQL_QUERIES
from logger import logger
import uuid
import os
import sqlite3


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Дашборд аналитики",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# ИНИЦИАЛИЗАЦИЯ СЕССИИ
# ============================================================

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'visit_logged' not in st.session_state:
    st.session_state.visit_logged = False

if not st.session_state.visit_logged:
    logger.log_action('visit')
    st.session_state.visit_logged = True


# ============================================================
# ИНИЦИАЛИЗАЦИЯ ДЛЯ ВЫБРАННЫХ ОТЧЕТОВ
# ============================================================

if 'selected_reports' not in st.session_state:
    st.session_state.selected_reports = []


# ============================================================
# ИНИЦИАЛИЗАЦИЯ ДЛЯ ЛОГИРОВАНИЯ ЗАПУЩЕННЫХ ОТЧЕТОВ
# ============================================================

if 'logged_reports' not in st.session_state:
    st.session_state.logged_reports = set()


# ============================================================
# ИНИЦИАЛИЗАЦИЯ ДЛЯ ЗАПУСКА ОТЧЕТА ИЗ ПЛИТКИ
# ============================================================

if 'tile_report' not in st.session_state:
    st.session_state.tile_report = None


# ============================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ТОП-5 ОТЧЕТОВ
# ============================================================

def get_top_reports(limit=5):
    """Получает топ-5 самых запускаемых отчетов из логов"""

    try:

        db_path = os.path.join(
            os.path.dirname(__file__),
            "logs",
            "dashboard_logs.db"
        )

        if not os.path.exists(db_path):
            return []

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='user_actions'
            """
        )

        if not cursor.fetchone():

            conn.close()

            return []

        cursor.execute(
            """
            SELECT
                report_name,
                COUNT(*) as count

            FROM user_actions

            WHERE action = 'view_report'
              AND report_name IS NOT NULL
              AND report_name != ''

            GROUP BY report_name

            ORDER BY count DESC

            LIMIT ?
            """,
            (limit,)
        )

        top_reports = cursor.fetchall()

        conn.close()

        return top_reports

    except Exception as e:

        print(
            f"Ошибка получения топ-отчетов: {e}"
        )

        return []


# ============================================================
# CSS ДЛЯ УПРАВЛЕНИЯ ШИРИНОЙ
# ============================================================

def apply_width_settings():
    """Применяет настройки ширины страницы"""

    css = """
    <style>

        .main > div {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }

        section.main > div {
            max-width: 100% !important;
        }

        .stPlotlyChart {
            width: 100% !important;
        }

        .stDataFrame {
            width: 100% !important;
        }

        .stDataFrame > div {
            width: 100% !important;
        }

    </style>
    """

    st.markdown(
        css,
        unsafe_allow_html=True
    )



# ============================================================
# ФУНКЦИЯ ДЛЯ ПРЕОБРАЗОВАНИЯ В EXCEL
# ============================================================


def dataframe_to_excel(df):
    """Преобразует DataFrame в Excel-файл."""

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Данные"
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ ОТЧЕТА
# ============================================================


# ============================================================
# ФУНКЦИЯ ДЛЯ ПОИСКА
# ============================================================

def filter_dataframe(df, key):
    """Фильтрует строки таблицы и предоставляет кнопки поиска,
    очистки и скачивания."""

    # --------------------------------------------------------
    # Состояние поиска
    # --------------------------------------------------------

    if f"{key}_applied" not in st.session_state:
        st.session_state[f"{key}_applied"] = ""

    def apply_search():
        st.session_state[f"{key}_applied"] = (
            st.session_state.get(key, "")
        )

    def clear_search():
        st.session_state[key] = ""
        st.session_state[f"{key}_applied"] = ""

    # --------------------------------------------------------
    # Одна строка: поиск + кнопка поиска + очистка + скачать
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns([6, 1, 1.2, 1.2])

    # --------------------------------------------------------
    # Поле поиска
    # --------------------------------------------------------

    with col1:

        st.text_input(
            "🔎 Поиск по таблице",
            key=key,
            placeholder="Введите значение для поиска...",
            on_change=apply_search
        )

    # --------------------------------------------------------
    # Кнопка ПОИСК
    # --------------------------------------------------------

    with col2:

        st.markdown(
            """
            <div style="height: 28px;"></div>
            """,
            unsafe_allow_html=True
        )

        st.button(
            "🔎 Найти",
            key=f"{key}_search",
            use_container_width=True,
            on_click=apply_search
        )

    # --------------------------------------------------------
    # Кнопка ОЧИСТИТЬ
    # --------------------------------------------------------

    with col3:

        st.markdown(
            """
            <div style="height: 28px;"></div>
            """,
            unsafe_allow_html=True
        )

        st.button(
            "✖ Очистить",
            key=f"{key}_clear",
            use_container_width=True,
            on_click=clear_search
        )

    # --------------------------------------------------------
    # ФИЛЬТРАЦИЯ
    # --------------------------------------------------------

    df_filtered = df

    search_text = st.session_state[f"{key}_applied"]

    if search_text:

        search_text = search_text.lower()

        mask = df.astype(str).apply(
            lambda column: column.str.lower().str.contains(
                search_text,
                na=False
            )
        ).any(axis=1)

        df_filtered = df[mask]

    # --------------------------------------------------------
    # ПОДГОТОВКА EXCEL
    # --------------------------------------------------------

    excel_data = dataframe_to_excel(
        df_filtered
    )

    # --------------------------------------------------------
    # КНОПКА СКАЧИВАНИЯ
    # --------------------------------------------------------

    with col4:

        st.markdown(
            """
            <div style="height: 28px;"></div>
            """,
            unsafe_allow_html=True
        )

        st.download_button(
            "⇩ Скачать",
            data=excel_data,
            file_name=f"{key}.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            key=f"download_{key}",
            use_container_width=True,
            help="Скачать таблицу в Excel"
        )

    return df_filtered



# ============================================================
# ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ ОТЧЕТА С ПАРАМЕТРАМИ
# ============================================================

def display_parameterized_report(
    df,
    report_name,
    show_charts,
    show_data,
    show_stats,
    params=None,
    filter_value=None
):
    """Отображает отчет с параметрами и фильтром"""

    st.subheader(
        report_name.replace('_', ' ').title()
    )

    if params:

        if isinstance(params, tuple) and len(params) == 2:
            st.caption(
                f"📅 Параметры запроса: "
                f"{params[0]} - {params[1]}"
            )

        elif isinstance(params, tuple) and len(params) == 1:
            st.caption(
                f"📅 Параметры запроса: {params[0]}"
            )

        else:
            st.caption(
                f"📅 Параметры запроса: {params}"
            )

    if filter_value:

        st.caption(
            f"🎯 Фильтр: {filter_value}"
        )

    if df.empty:

        st.warning(
            "Нет данных для указанных параметров"
        )

        return

    if len(df.columns) == 2:

        col1, col2 = df.columns[:2]

        if show_charts:

            try:

                if pd.api.types.is_datetime64_any_dtype(
                    df[col1]
                ):

                    fig = px.line(
                        df,
                        x=col1,
                        y=col2,
                        title=f"{col2} по датам",
                        template="plotly_white"
                    )

                else:

                    fig = px.bar(
                        df,
                        x=col1,
                        y=col2,
                        title=f"{col2} по категориям",
                        template="plotly_white"
                    )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            except Exception as e:

                st.warning(
                    f"Не удалось построить график: {str(e)}"
                )

        if show_data:

            st.dataframe(
                df,
                use_container_width=True
            )

        if show_stats and len(df) > 0:

            with st.expander(
                "📈 Сводная статистика"
            ):

                try:

                    numeric_cols = df.select_dtypes(
                        include=['float64', 'int64']
                    ).columns

                    if len(numeric_cols) > 0:

                        st.dataframe(
                            df[numeric_cols].describe(),
                            use_container_width=True
                        )

                    else:

                        st.info(
                            "Нет числовых данных для статистики"
                        )

                except Exception:

                    st.info(
                        "Нет данных для статистики"
                    )

    else:

        numeric_cols = df.select_dtypes(
            include=['float64', 'int64']
        ).columns

        if show_charts and len(numeric_cols) > 0:

            try:

                fig = px.bar(
                    df,
                    x=df.columns[0],
                    y=numeric_cols[0],
                    title=(
                        f"{numeric_cols[0]} "
                        f"по {df.columns[0]}"
                    ),
                    template="plotly_white"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            except Exception as e:

                st.warning(
                    f"Не удалось построить график: {str(e)}"
                )

        if show_data:

            df_filtered = filter_dataframe(
                df,
                f"search_{report_name}"
            )

            st.dataframe(
                df_filtered,
                use_container_width=True
            )

        if (
            show_stats
            and len(df) > 0
            and len(numeric_cols) > 0
        ):

            with st.expander(
                "📈 Сводная статистика"
            ):

                try:

                    st.dataframe(
                        df[numeric_cols].describe(),
                        use_container_width=True
                    )

                except Exception:

                    st.info(
                        "Нет данных для статистики"
                    )


# ============================================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# ============================================================

@st.cache_resource
def get_db_engine():    
    return Config.get_engine()


engine = get_db_engine()


# ============================================================
# ЗАГОЛОВОК
# ============================================================

st.title(
    "📊 Аналитический дашборд"
)

# ============================================================
# ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
# ============================================================

@st.cache_data
def load_data(query_name, params=None):

    try:

        query = SQL_QUERIES.get(query_name)

        if query is None:

            st.error(
                f"Запрос '{query_name}' не найден!"
            )

            return pd.DataFrame()

        if params:

            df = pd.read_sql(
                query,
                engine,
                params=params
            )

        else:

            df = pd.read_sql(
                query,
                engine
            )

        return df

    except Exception as e:

        st.error(
            f"Ошибка загрузки данных: {str(e)}"
        )

        return pd.DataFrame()



# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    status_placeholder = st.empty()


    # ========================================================
    # РУЧНОЕ ОБНОВЛЕНИЕ
    # ========================================================

    if st.button(
        "🔄 Обновить данные",
        use_container_width=True
    ):

        st.cache_data.clear()

        status_placeholder.success(
            "✅ Данные обновлены!"
        )

        st.rerun()

    # ========================================================
    # ВЫБОР ОТЧЕТОВ
    # ========================================================

    st.subheader(
        "📋 Выбор отчетов"
    )

    service_queries = []

    parameterized_reports = [
        'Статусы заявок отгрузки'
    ]

    all_reports = [
        key
        for key in SQL_QUERIES.keys()
        if key not in service_queries
    ]

    all_reports.sort()


    # ========================================================
    # MULTISELECT
    # ========================================================

    selected_reports = st.multiselect(
        "Выберите отчеты для отображения:",
        options=all_reports,
        default=st.session_state.selected_reports,
        key="reports_selector"
    )


    # ========================================================
    # СОХРАНЯЕМ ВЫБОР
    # ========================================================

    st.session_state.selected_reports = list(
        selected_reports
    )


    st.divider()


    # ========================================================
    # ПАРАМЕТРЫ ДЛЯ ОТЧЕТОВ
    # ========================================================

    order_number = ""

    if any(
        report in parameterized_reports
        for report in selected_reports
    ):

        st.subheader(
            "🔍 Параметры запросов"
        )

        order_number = st.text_input(
            "Номер заявки "
            "(для отчета Статусы заявок отгрузки):",
            value="",
            placeholder=(
                "Введите номер заявки, "
                "например: 00-00000018"
            )
        )


        if st.button(
            "✅ Применить параметры",
            use_container_width=True
        ):

            st.rerun()


        st.divider()


    # === ДИАПАЗОН ДАТЫ ДЛЯ ОТЧЕТОВ ===

    date_reports = ['Выданные клиентам заказы']

    date_from = None
    date_to = None

    if any(
        report in date_reports
        for report in selected_reports
    ):

        st.subheader("📅 Период дат")

        date_from = st.date_input(
            "Дата от:",
            value=datetime.now().date(),
            help="Начальная дата периода",
            key="date_from"
        )

        date_to = st.date_input(
            "Дата до:",
            value=datetime.now().date(),
            help="Конечная дата периода",
            key="date_to"
        )

        st.divider()


    # ========================================================
    # НАСТРОЙКИ ОТОБРАЖЕНИЯ
    # ========================================================

    st.subheader(
        "⚙️ Настройки"
    )

    col_layout = st.radio(
        "Расположение отчетов:",
        [
            "В одну колонку",
            "В две колонки"
        ],
        index=0
    )

    show_charts = st.checkbox(
        "Показывать графики",
        value=False
    )

    show_stats = st.checkbox(
        "Показывать сводную статистику",
        value=False
    )

    show_data = st.checkbox(
        "Показывать таблицы с данными",
        value=True
    )


# ============================================================
# ОБРАБОТКА ВЫБОРА ЧЕРЕЗ ПЛИТКУ
# ============================================================

if st.session_state.tile_report:

    report = st.session_state.tile_report

    if report in all_reports:

        selected_reports = [report]

        st.session_state.selected_reports = [
            report
        ]

    st.session_state.tile_report = None


# ============================================================
# ПРИМЕНЯЕМ НАСТРОЙКИ ШИРИНЫ
# ============================================================

apply_width_settings()


# ============================================================
# ЕСЛИ ОТЧЕТЫ НЕ ВЫБРАНЫ
# ============================================================

if not selected_reports:

    st.warning(
        "⚠️ Выберите хотя бы один отчет "
        "в боковой панели"
    )

    st.subheader(
        "🔥 Часто используемые отчеты"
    )

    top_reports = get_top_reports(5)

    if top_reports:

        # ====================================================
        # CSS ДЛЯ ПЛИТОК
        # ====================================================

        st.markdown(
            """
            <style>

                .tile-button .stButton button {

                    width: 100% !important;

                    min-height: 130px !important;

                    height: auto !important;

                    white-space: normal !important;

                    text-align: center !important;

                    line-height: 1.5 !important;

                    padding: 20px 12px !important;

                    background:
                        linear-gradient(
                            145deg,
                            #ffffff,
                            #f8fafc
                        ) !important;

                    border: 1px solid #e8ecf0 !important;

                    border-radius: 16px !important;

                    color: #1a1a2e !important;

                    font-weight: 500 !important;

                    font-size: 14px !important;

                    transition:
                        all
                        0.3s
                        cubic-bezier(
                            0.4,
                            0,
                            0.2,
                            1
                        ) !important;

                    box-shadow:
                        0 2px 8px
                        rgba(
                            0,
                            0,
                            0,
                            0.06
                        ) !important;

                    display: flex !important;

                    flex-direction: column !important;

                    justify-content: center !important;

                    align-items: center !important;

                    cursor: pointer !important;
                }


                .tile-button .stButton button:hover {

                    transform:
                        translateY(-6px) !important;

                    box-shadow:
                        0 12px 28px
                        rgba(
                            33,
                            150,
                            243,
                            0.2
                        ) !important;

                    border-color:
                        #2196F3 !important;

                    background:
                        linear-gradient(
                            145deg,
                            #ffffff,
                            #e3f2fd
                        ) !important;
                }


                .tile-button .stButton button:active {

                    transform:
                        translateY(-2px) !important;
                }

            </style>
            """,
            unsafe_allow_html=True
        )


        cols = st.columns(5)

        icons = [
            "📊",
            "📈",
            "📋",
            "📉",
            "📦"
        ]


        for i, (report_name, count) in enumerate(
            top_reports
        ):

            col_idx = i % 5

            with cols[col_idx]:

                with st.container():

                    st.markdown(
                        '<div class="tile-button">',
                        unsafe_allow_html=True
                    )

                    button_text = (
                        f"{icons[i % len(icons)]}\n\n"
                        f"{report_name}\n\n"
                        f"🔄 {count} запусков\n\n"
                        f"▶ Нажмите для запуска"
                    )


                    if st.button(
                        button_text,
                        key=f"tile_btn_{i}",
                        use_container_width=True
                    ):

                        # =================================================
                        # НЕ МЕНЯЕМ СОСТОЯНИЕ MULTISELECT
                        # =================================================

                        st.session_state.tile_report = (
                            report_name
                        )

                        st.rerun()


                    st.markdown(
                        '</div>',
                        unsafe_allow_html=True
                    )

    else:

        st.info(
            "Нет данных о запусках отчетов. "
            "Начните использовать отчеты, "
            "чтобы они появились здесь."
        )


# ============================================================
# ОТОБРАЖЕНИЕ ВЫБРАННЫХ ОТЧЕТОВ
# ============================================================

else:

    if col_layout == "В две колонки":

        cols = st.columns(2)

        use_columns = True

    else:

        use_columns = False


    for idx, report_name in enumerate(
        selected_reports
    ):

        params = None

        filter_value = None


        # ====================================================
        # ОТЧЕТ С ПАРАМЕТРОМ
        # ====================================================

        if report_name == 'Статусы заявок отгрузки':

            if (
                not order_number
                or not order_number.strip()
            ):

                if use_columns:

                    with cols[idx % 2]:

                        st.warning(
                            f"⚠️ Для отчета "
                            f"'{report_name}' "
                            "укажите номер заявки "
                            "в боковой панели"
                        )

                else:

                    st.warning(
                        f"⚠️ Для отчета "
                        f"'{report_name}' "
                        "укажите номер заявки "
                        "в боковой панели"
                    )

                continue


            params = (
                order_number.strip(),
            )


            df = load_data(
                report_name,
                params
            )


        # ====================================================
        # ОБРАБОТКА ОТЧЕТА С ДИАПАЗОНОМ ДАТ
        # ====================================================

        elif report_name == 'Выданные клиентам заказы':

            if not date_from or not date_to:

                if use_columns:

                    with cols[idx % 2]:

                        st.warning(
                            f"⚠️ Для отчета '{report_name}' "
                            "укажите период дат "
                            "в боковой панели"
                        )

                else:

                    st.warning(
                        f"⚠️ Для отчета '{report_name}' "
                        "укажите период дат "
                        "в боковой панели"
                    )

                continue


            # ------------------------------------------------
            # Проверяем правильность периода
            # ------------------------------------------------

            if date_from > date_to:

                if use_columns:

                    with cols[idx % 2]:

                        st.error(
                            "❌ Дата начала периода "
                            "не может быть позже даты окончания"
                        )

                else:

                    st.error(
                        "❌ Дата начала периода "
                        "не может быть позже даты окончания"
                    )

                continue


            # ------------------------------------------------
            # Передаем две даты в SQL
            # ------------------------------------------------

            params = (
                date_from.strftime('%Y-%m-%d'),
                date_to.strftime('%Y-%m-%d')
            )


            df = load_data(
                report_name,
                params
            )


        # ====================================================
        # ОБЫЧНЫЕ ОТЧЕТЫ
        # ====================================================

        else:

            df = load_data(
                report_name,
                params
            )

        # ====================================================
        # ПРОВЕРКА НА ПУСТЫЕ ДАННЫЕ
        # ====================================================

        if df.empty:

            if use_columns:

                with cols[idx % 2]:

                    st.error(
                        f"Нет данных для "
                        f"'{report_name}'"
                    )

            else:

                st.error(
                    f"Нет данных для "
                    f"'{report_name}'"
                )

            continue


        # ====================================================
        # ЛОГИРУЕМ ЗАПУСК ОТЧЕТА ОДИН РАЗ ЗА СЕССИЮ
        # ====================================================

        report_key = (
            report_name,
            tuple(params) if params else None
        )

        if report_key not in st.session_state.logged_reports:

            logger.log_action(
                'view_report',
                report_name,
                params
            )

            st.session_state.logged_reports.add(
                report_key
            )


        # ====================================================
        # ВЫВОДИМ ОТЧЕТ
        # ====================================================

        if use_columns:

            with cols[idx % 2]:

                display_parameterized_report(
                    df,
                    report_name,
                    show_charts,
                    show_data,
                    show_stats,
                    params,
                    filter_value
                )

        else:

            display_parameterized_report(
                df,
                report_name,
                show_charts,
                show_data,
                show_stats,
                params,
                filter_value
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

col1, col2, col3 = st.columns(3)


with col1:

    st.caption(
        f"📊 Всего запросов: "
        f"{len(SQL_QUERIES)}"
    )