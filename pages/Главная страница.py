import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
from config import Config
from queries import SQL_QUERIES
from logger import logger
from styles import load_css
from streamlit_extras.card_selector import card_selector
import os
import sqlite3


# ============================================================
# СТИЛИ
# ============================================================

load_css()


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
            os.path.dirname(os.path.dirname(__file__)),
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
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ИЗБРАННЫХ ОТЧЕТОВ
# ============================================================

def get_current_user_favorites():
    """Получает избранные отчеты текущего пользователя."""

    user_id = st.session_state.get("user_id")

    if not user_id:
        return []

    try:

        return logger.get_user_favorites(user_id)

    except Exception as e:

        print(
            f"Ошибка получения избранных отчетов: {e}"
        )

        return []


# ============================================================
# ФУНКЦИЯ ДЛЯ ПЕРЕКЛЮЧЕНИЯ ИЗБРАННОГО
# ============================================================

def toggle_report_favorite(report_name):
    """Добавляет или удаляет отчет из избранного."""

    user_id = st.session_state.get("user_id")

    if not user_id:
        return

    logger.toggle_favorite(
        user_id,
        report_name
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
            lambda column: column.str.contains(
                search_text,
                case=False,
                na=False,
                regex=False
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
# ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ НАЗВАНИЯ ИЗБРАННОГО ОТЧЕТА
# ============================================================

def display_report_header(report_name):
    """
    Отображает название отчета и кнопку
    добавления/удаления из избранного.
    """

    user_id = st.session_state.get("user_id")

    if not user_id:
        st.subheader(
            report_name.replace('_', ' ').title()
        )
        return

    is_favorite = logger.is_favorite(
        user_id,
        report_name
    )

    # --------------------------------------------------------
    # Название + кнопка избранного
    # --------------------------------------------------------

    col_title, col_favorite = st.columns(
        [7, 3]
    )

    with col_title:

        st.subheader(
            report_name.replace('_', ' ').title()
        )

    with col_favorite:

        # Немного выравниваем кнопку относительно заголовка
        st.markdown(
            """
            <div style="height: 8px;"></div>
            """,
            unsafe_allow_html=True
        )

        if is_favorite:

            if st.button(
                ":material/star_half: Удалить из избранного",
                key=f"favorite_remove_{report_name}",
                use_container_width=True
            ):

                toggle_report_favorite(
                    report_name
                )

                st.rerun()

        else:

            if st.button(
                ":material/star: Добавить в избранное",
                key=f"favorite_add_{report_name}",
                use_container_width=True
            ):

                toggle_report_favorite(
                    report_name
                )

                st.rerun()


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
    """Отображает отчет с параметрами и фильтром."""

    # --------------------------------------------------------
    # ЗАГОЛОВОК + ИЗБРАННОЕ
    # --------------------------------------------------------

    display_report_header(
        report_name
    )

    # --------------------------------------------------------
    # ПАРАМЕТРЫ
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ФИЛЬТР
    # --------------------------------------------------------

    if filter_value:

        st.caption(
            f"🎯 Фильтр: {filter_value}"
        )

    # --------------------------------------------------------
    # ПРОВЕРКА ДАННЫХ
    # --------------------------------------------------------

    if df.empty:

        st.warning(
            "Нет данных для указанных параметров"
        )

        return

    # ========================================================
    # ТАБЛИЦА ИЗ ДВУХ КОЛОНОК
    # ========================================================

    if len(df.columns) == 2:

        col1, col2 = df.columns[:2]

        # ----------------------------------------------------
        # ГРАФИК
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ТАБЛИЦА
        # ----------------------------------------------------

        if show_data:

            df_filtered = filter_dataframe(
                df,
                f"search_{report_name}"
            )

            df_filtered = df_filtered.copy()

            df_filtered.index = range(
                1,
                len(df_filtered) + 1
            )

            st.dataframe(
                df_filtered,
                use_container_width=True
            )

        # ----------------------------------------------------
        # СТАТИСТИКА
        # ----------------------------------------------------

        if show_stats and len(df) > 0:

            with st.expander(
                "📈 Сводная статистика"
            ):

                try:

                    numeric_cols = df.select_dtypes(
                        include="number"
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

    # ========================================================
    # ОТЧЕТ С БОЛЬШИМ КОЛИЧЕСТВОМ КОЛОНОК
    # ========================================================

    else:

        numeric_cols = df.select_dtypes(
            include="number"
        ).columns

        # ----------------------------------------------------
        # ГРАФИК
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ТАБЛИЦА
        # ----------------------------------------------------

        if show_data:

            df_filtered = filter_dataframe(
                df,
                f"search_{report_name}"
            )

            df_filtered = df_filtered.copy()

            df_filtered.index = range(
                1,
                len(df_filtered) + 1
            )

            st.dataframe(
                df_filtered,
                use_container_width=True
            )

        # ----------------------------------------------------
        # СТАТИСТИКА
        # ----------------------------------------------------

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
    "🏠 Главная страница"
)


# ============================================================
# ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ
# ============================================================

@st.cache_data
def load_data(query_name, params=None):

    try:

        query = SQL_QUERIES.get(
            query_name
        )

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
        ":material/refresh: Обновить данные",
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
        ":material/add_chart: Выбор отчетов"
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
    # ОБРАБОТКА ВЫБОРА ЧЕРЕЗ ПЛИТКУ
    # ========================================================

    if st.session_state.tile_report:

        report = st.session_state.tile_report

        if report in all_reports:

            current_reports = (
                st.session_state.selected_reports.copy()
            )

            if report not in current_reports:

                current_reports.append(
                    report
                )

            st.session_state.selected_reports = (
                current_reports
            )

            st.session_state.reports_selector = (
                current_reports
            )

        st.session_state.tile_report = None

    # ========================================================
    # ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ MULTISELECT
    # ========================================================

    if "reports_selector" not in st.session_state:

        st.session_state.reports_selector = (
            st.session_state.selected_reports.copy()
        )

    # ========================================================
    # ВЫБОР ОТЧЕТОВ
    # ========================================================

    selected_reports = st.multiselect(
        "Выберите отчеты для отображения:",
        options=all_reports,
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

    # ========================================================
    # ДИАПАЗОН ДАТЫ ДЛЯ ОТЧЕТОВ
    # ========================================================

    date_reports = [
        'Выданные клиентам заказы',
        'Объём-расчёт количества мест',
        'Расчёт количества мест с ВГХ',
        'Артикулы, отбирающиеся упаковками',
        'Производительность комплектации',
        'Смена вида запаса',
        'Дефициты заявок отгрузки'
    ]

    date_from = None
    date_to = None

    if any(
        report in date_reports
        for report in selected_reports
    ):

        st.subheader(
            ":material/calendar_clock: Период дат"
        )

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
        ":material/settings: Настройки"
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
# ЕСЛИ ОТЧЕТЫ НЕ ВЫБРАНЫ
# ============================================================

if not selected_reports:

    st.warning(
        ":material/feedback: Выберите хотя бы один отчет"
    )

    # ========================================================
    # ИЗБРАННЫЕ ОТЧЕТЫ
    # ========================================================

    favorite_reports = get_current_user_favorites()

    # Оставляем только существующие отчеты
    favorite_reports = [
        report
        for report in favorite_reports
        if report in all_reports
    ]

    if favorite_reports:

        st.subheader(
            ":material/interests: Избранные отчеты"
        )

        # ----------------------------------------------------
        # По 5 карточек в каждой строке
        # ----------------------------------------------------

        for row_start in range(
            0,
            len(favorite_reports),
            5
        ):

            row_reports = favorite_reports[
                row_start:row_start + 5
            ]

            favorite_card_options = []

            for i, report_name in enumerate(
                row_reports
            ):

                favorite_card_options.append(
                    {
                        "title": report_name
                    }
                )

            selected_favorite = card_selector(
                favorite_card_options,
                key=f"favorite_reports_card_selector_{row_start}"
            )

            if selected_favorite is not None:

                selected_report = row_reports[
                    selected_favorite
                ]

                st.session_state.tile_report = (
                    selected_report
                )

                st.rerun()


    # ========================================================
    # ЧАСТО ИСПОЛЬЗУЕМЫЕ ОТЧЕТЫ
    # ========================================================

    st.subheader(
        ":material/local_fire_department: Часто используемые отчеты"
    )

    top_reports = get_top_reports(5)

    if top_reports:

        card_icons = [
            ":material/analytics:",
            ":material/query_stats:",
            ":material/assignment:",
            ":material/bar_chart:",
            ":material/inventory_2:"
        ]

        card_options = []

        for i, (report_name, count) in enumerate(
            top_reports
        ):

            card_options.append(
                {
                    "icon": card_icons[
                        i % len(card_icons)
                    ],
                    "title": report_name,
                    "description": f"{count} запусков"
                }
            )

        selected_card = card_selector(
            card_options,
            key="top_reports_card_selector"
        )

        if selected_card is not None:

            selected_report = top_reports[
                selected_card
            ][0]

            st.session_state.tile_report = (
                selected_report
            )

            st.rerun()

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

                        display_report_header(
                            report_name
                        )

                        st.warning(
                            f"⚠️ Для отчета "
                            f"'{report_name}' "
                            "укажите номер заявки "
                            "в боковой панели"
                        )

                else:

                    display_report_header(
                        report_name
                    )

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

        elif report_name in date_reports:

            if not date_from or not date_to:

                if use_columns:

                    with cols[idx % 2]:

                        display_report_header(
                            report_name
                        )

                        st.warning(
                            f"⚠️ Для отчета "
                            f"'{report_name}' "
                            "укажите период дат "
                            "в боковой панели"
                        )

                else:

                    display_report_header(
                        report_name
                    )

                    st.warning(
                        f"⚠️ Для отчета "
                        f"'{report_name}' "
                        "укажите период дат "
                        "в боковой панели"
                    )

                continue

            if date_from > date_to:

                if use_columns:

                    with cols[idx % 2]:

                        display_report_header(
                            report_name
                        )

                        st.error(
                            "❌ Дата начала периода "
                            "не может быть позже даты окончания"
                        )

                else:

                    display_report_header(
                        report_name
                    )

                    st.error(
                        "❌ Дата начала периода "
                        "не может быть позже даты окончания"
                    )

                continue

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

                    display_report_header(
                        report_name
                    )

                    st.error(
                        f"Нет данных для "
                        f"'{report_name}'"
                    )

            else:

                display_report_header(
                    report_name
                )

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

        if report_key not in (
            st.session_state.logged_reports
        ):

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

    st.markdown(
        f"""
        <div style="
            font-size: 0.8rem;
            color: var(--text-color);
        ">
            📊 Всего запросов: {len(SQL_QUERIES)}
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:

    st.markdown(
        """
        <div style="
            text-align: right;
            font-size: 0.8rem;
            color: var(--text-color);
        ">
            <a
                href="https://github.com/romaapp/dashboard_project"
                target="_blank"
                style="
                    color: inherit;
                    text-decoration: none;
                "
            >
                💻 GitHub проекта
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )