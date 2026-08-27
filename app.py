import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import Config
from queries import SQL_QUERIES
from logger import logger
import uuid
import os
import sqlite3

# === ИНИЦИАЛИЗАЦИЯ СЕССИИ ===
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# === ИНИЦИАЛИЗАЦИЯ ДЛЯ ИЗБРАННЫХ ОТЧЕТОВ ===
if 'selected_reports' not in st.session_state:
    st.session_state.selected_reports = []

# Логируем визит
logger.log_action('visit')

# === НАСТРОЙКА СТРАНИЦЫ ===
st.set_page_config(
    page_title="Дашборд аналитики",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ТОП-5 ОТЧЕТОВ ===
def get_top_reports(limit=5):
    """Получает топ-5 самых запускаемых отчетов из логов"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), "logs", "dashboard_logs.db")
        
        if not os.path.exists(db_path):
            return []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_actions'")
        if not cursor.fetchone():
            conn.close()
            return []
        
        cursor.execute("""
            SELECT report_name, COUNT(*) as count
            FROM user_actions
            WHERE action = 'view_report' AND report_name IS NOT NULL AND report_name != ''
            GROUP BY report_name
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        top_reports = cursor.fetchall()
        conn.close()
        
        return top_reports
    except Exception as e:
        print(f"Ошибка получения топ-отчетов: {e}")
        return []

# === CSS ДЛЯ УПРАВЛЕНИЯ ШИРИНОЙ ===
def apply_width_settings(mode):
    """Применяет настройки ширины"""
    if mode == "Узкая":
        css = """
        <style>
            .main > div {
                max-width: 800px !important;
                margin: 0 auto !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        </style>
        """
    elif mode == "Стандартная":
        css = """
        <style>
            .main > div {
                max-width: 1200px !important;
                margin: 0 auto !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
        </style>
        """
    else:  # "Широкая"
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
            .element-container {
                width: 100% !important;
            }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# === ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ ОТЧЕТА ===
def display_report(df, report_name, show_charts, show_data, show_stats):
    """Отображает один отчет с настройками"""
    st.subheader(report_name.replace('_', ' ').title())
    
    if len(df.columns) == 2:
        col1, col2 = df.columns[:2]
        
        if show_charts:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col1]):
                    fig = px.line(df, x=col1, y=col2, 
                                 title=f"{col2} по датам",
                                 template="plotly_white")
                else:
                    fig = px.bar(df, x=col1, y=col2, 
                               title=f"{col2} по категориям",
                               template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Не удалось построить график: {str(e)}")
        
        if show_data:
            st.dataframe(df, use_container_width=True)
        
        if show_stats and len(df) > 0:
            with st.expander("📈 Сводная статистика"):
                try:
                    st.dataframe(df.describe(), use_container_width=True)
                except:
                    st.info("Нет данных для статистики")
    
    else:
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        if show_charts and len(numeric_cols) > 0:
            try:
                fig = px.bar(df, x=df.columns[0], y=numeric_cols[0], 
                           title=f"{numeric_cols[0]} по {df.columns[0]}",
                           template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Не удалось построить график: {str(e)}")
        
        if show_data:
            st.dataframe(df, use_container_width=True)
        
        if show_stats and len(df) > 0 and len(numeric_cols) > 0:
            with st.expander("📈 Сводная статистика"):
                try:
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                except:
                    st.info("Нет данных для статистики")
    
    st.divider()

# === ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ ОТЧЕТА С ПАРАМЕТРАМИ ===
def display_parameterized_report(df, report_name, show_charts, show_data, show_stats, params=None, filter_value=None):
    """Отображает отчет с параметрами и фильтром"""
    st.subheader(report_name.replace('_', ' ').title())
    
    if params:
        st.caption(f"🔍 Параметры запроса: {params}")
    
    if filter_value:
        st.caption(f"🎯 Фильтр: {filter_value}")
    
    if df.empty:
        st.warning("Нет данных для указанных параметров")
        return
    
    if len(df.columns) == 2:
        col1, col2 = df.columns[:2]
        
        if show_charts:
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col1]):
                    fig = px.line(df, x=col1, y=col2, 
                                 title=f"{col2} по датам",
                                 template="plotly_white")
                else:
                    fig = px.bar(df, x=col1, y=col2, 
                               title=f"{col2} по категориям",
                               template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Не удалось построить график: {str(e)}")
        
        if show_data:
            st.dataframe(df, use_container_width=True)
        
        if show_stats and len(df) > 0:
            with st.expander("📈 Сводная статистика"):
                try:
                    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                    if len(numeric_cols) > 0:
                        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                    else:
                        st.info("Нет числовых данных для статистики")
                except:
                    st.info("Нет данных для статистики")
    
    else:
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        if show_charts and len(numeric_cols) > 0:
            try:
                fig = px.bar(df, x=df.columns[0], y=numeric_cols[0], 
                           title=f"{numeric_cols[0]} по {df.columns[0]}",
                           template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Не удалось построить график: {str(e)}")
        
        if show_data:
            st.dataframe(df, use_container_width=True)
        
        if show_stats and len(df) > 0 and len(numeric_cols) > 0:
            with st.expander("📈 Сводная статистика"):
                try:
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                except:
                    st.info("Нет данных для статистики")
    
    st.divider()

# === ИНИЦИАЛИЗАЦИЯ ПОДКЛЮЧЕНИЯ ===
engine = Config.get_engine()

# === ЗАГОЛОВОК ===
st.title("📊 Аналитический дашборд")
st.caption(f"Данные обновляются автоматически каждые 5 минут. Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === ФУНКЦИЯ ЗАГРУЗКИ ДАННЫХ ===
@st.cache_data(ttl=300)
def load_data(query_name, params=None):
    try:
        query = SQL_QUERIES.get(query_name)
        if query is None:
            st.error(f"Запрос '{query_name}' не найден!")
            return pd.DataFrame()
        
        if params:
            df = pd.read_sql(query, engine, params=params)
        else:
            df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {str(e)}")
        return pd.DataFrame()

# === ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ СПИСКА СОТРУДНИКОВ ===
@st.cache_data(ttl=300)
def load_employees():
    """Загружает список сотрудников из БД"""
    try:
        query = SQL_QUERIES.get('Список сотрудников')
        if query:
            df = pd.read_sql(query, engine)
            return df["Сотрудник"].tolist()
        return []
    except Exception as e:
        st.error(f"Ошибка загрузки списка сотрудников: {str(e)}")
        return []

# === БОКОВАЯ ПАНЕЛЬ С НАСТРОЙКАМИ ===
with st.sidebar:
    st.header("⚙️ Настройки")

    status_placeholder = st.empty()
    
    if st.button("🔄 Обновить данные сейчас", use_container_width=True):
        st.cache_data.clear()
        status_placeholder.success("✅ Данные обновлены!")
        import time
        time.sleep(2)
        status_placeholder.empty()
    
    st.caption("💡 Данные обновляются автоматически каждые 5 минут")
    
    # === ВЫБОР ОТЧЕТОВ ===
    st.subheader("📋 Выбор отчетов")

    service_queries = ['Список сотрудников']
    parameterized_reports = ['Статусы заявок отгрузки']
    filter_reports = ['Отборы сотрудников по волнам']
    all_reports = [key for key in SQL_QUERIES.keys() if key not in service_queries]
    all_reports.sort()
    
    selected_reports = st.multiselect(
        "Выберите отчеты для отображения:",
        options=all_reports,
        default=[]
    )
    
    st.divider()
    
    # === ПАРАМЕТРЫ ДЛЯ ОТЧЕТОВ ===
    order_number = ""
    if any(report in parameterized_reports for report in selected_reports):
        st.subheader("🔍 Параметры запросов")
        order_number = st.text_input(
            "Номер заявки (для отчета Статусы заявок отгрузки):",
            value="",
            placeholder="Введите номер заявки, например: 00-00000018"
        )
        st.divider()
    
    # === ФИЛЬТРЫ ДЛЯ ОТЧЕТОВ ===
    selected_employee = None
    if any(report in filter_reports for report in selected_reports):
        st.subheader("🎯 Фильтры")
        
        employees = load_employees()
        
        if employees:
            selected_employee = st.selectbox(
                "Выберите сотрудника для фильтрации:",
                options=["Все сотрудники"] + employees,
                index=0
            )
        else:
            st.info("Нет данных о сотрудниках")
        
        st.divider()

    # === НАСТРОЙКИ ОТОБРАЖЕНИЯ ===
    st.subheader("🖥️ Настройки отображения")
    
    col_layout = st.radio(
        "Расположение отчетов:",
        ["В одну колонку", "В две колонки"],
        index=0
    )
    
    show_charts = st.checkbox("Показывать графики", value=False)
    show_stats = st.checkbox("Показывать сводную статистику", value=False)
    show_data = st.checkbox("Показывать таблицы с данными", value=True)

# === ПРИМЕНЯЕМ НАСТРОЙКИ ШИРИНЫ ===
apply_width_settings("Широкая")

# === ОСНОВНАЯ ОБЛАСТЬ ===
# Используем selected_reports из st.session_state если есть
if st.session_state.selected_reports:
    selected_reports = selected_reports + st.session_state.selected_reports
    # Очищаем session_state после использования
    st.session_state.selected_reports = []

if not selected_reports:
    st.warning("⚠️ Выберите хотя бы один отчет в боковой панели")
    
    st.subheader("🔥 Часто используемые отчеты")
    
    top_reports = get_top_reports(5)
    
    if top_reports:
        # CSS только для плиток (ограничено классом .tile-button)
        st.markdown("""
        <style>
            .tile-button .stButton button {
                width: 100% !important;
                min-height: 130px !important;
                height: auto !important;
                white-space: normal !important;
                text-align: center !important;
                line-height: 1.5 !important;
                padding: 20px 12px !important;
                background: linear-gradient(145deg, #ffffff, #f8fafc) !important;
                border: 1px solid #e8ecf0 !important;
                border-radius: 16px !important;
                color: #1a1a2e !important;
                font-weight: 500 !important;
                font-size: 14px !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
                align-items: center !important;
                cursor: pointer !important;
            }
            .tile-button .stButton button:hover {
                transform: translateY(-6px) !important;
                box-shadow: 0 12px 28px rgba(33, 150, 243, 0.2) !important;
                border-color: #2196F3 !important;
                background: linear-gradient(145deg, #ffffff, #e3f2fd) !important;
            }
            .tile-button .stButton button:active {
                transform: translateY(-2px) !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        cols = st.columns(5)
        icons = ["📊", "📈", "📋", "📉", "📦"]
        
        for i, (report_name, count) in enumerate(top_reports):
            col_idx = i % 5
            with cols[col_idx]:
                # Оборачиваем кнопку в контейнер с классом tile-button
                with st.container():
                    st.markdown('<div class="tile-button">', unsafe_allow_html=True)
                    
                    button_text = f"{icons[i % len(icons)]}\n\n{report_name}\n\n🔄 {count} запусков\n\n▶ Нажмите для запуска"
                    
                    if st.button(button_text, key=f"tile_btn_{i}", use_container_width=True):
                        if report_name not in st.session_state.selected_reports:
                            st.session_state.selected_reports.append(report_name)
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Нет данных о запусках отчетов. Начните использовать отчеты, чтобы они появились здесь.")
else:
    if col_layout == "В две колонки":
        cols = st.columns(2)
        use_columns = True
    else:
        use_columns = False
    
    for idx, report_name in enumerate(selected_reports):
        params = None
        filter_value = None
        
        # === ОБРАБОТКА ОТЧЕТА С ПАРАМЕТРОМ (Номер заявки) ===
        if report_name == 'Статусы заявок отгрузки':
            if not order_number or not order_number.strip():
                if use_columns:
                    with cols[idx % 2]:
                        st.warning(f"⚠️ Для отчета '{report_name}' укажите номер заявки в боковой панели")
                else:
                    st.warning(f"⚠️ Для отчета '{report_name}' укажите номер заявки в боковой панели")
                continue
            params = (order_number.strip(),)
            df = load_data(report_name, params)
        
        # === ОБРАБОТКА ОТЧЕТА С ФИЛЬТРАЦИЕЙ ПО СОТРУДНИКУ ===
        elif report_name == 'Отборы сотрудников по волнам':
            df = load_data(report_name, params)
            
            if not df.empty and selected_employee and selected_employee != "Все сотрудники":
                df = df[df["Сотрудник"] == selected_employee]
                filter_value = f"Сотрудник: {selected_employee}"
        
        # === ОБЫЧНЫЕ ОТЧЕТЫ ===
        else:
            df = load_data(report_name, params)
        
        # Проверка на пустые данные
        if df.empty:
            if use_columns:
                with cols[idx % 2]:
                    st.error(f"Нет данных для '{report_name}'")
            else:
                st.error(f"Нет данных для '{report_name}'")
            continue
        
        # Логируем просмотр отчета
        logger.log_action('view_report', report_name, params)
        
        # Выводим отчет
        if use_columns:
            with cols[idx % 2]:
                display_parameterized_report(df, report_name, show_charts, show_data, show_stats, params, filter_value)
        else:
            display_parameterized_report(df, report_name, show_charts, show_data, show_stats, params, filter_value)

# === FOOTER ===
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"📊 Всего запросов: {len(SQL_QUERIES)}")
with col2:
    st.caption(f"🔄 Обновление: каждые 5 минут")
with col3:
    st.caption(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")