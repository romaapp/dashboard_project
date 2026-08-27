import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import Config
from queries import SQL_QUERIES
from logger import logger
import uuid

# === ИНИЦИАЛИЗАЦИЯ СЕССИИ ===
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Логируем визит
logger.log_action('visit')

# === НАСТРОЙКА СТРАНИЦЫ ===
st.set_page_config(
    page_title="Дашборд аналитики",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)



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

    # Определяем служебные запросы (которые не должны отображаться)
    service_queries = ['Список сотрудников']
    
    parameterized_reports = ['Статусы заявок отгрузки']
    filter_reports = ['Отборы сотрудников по волнам']  # Отчеты с фильтрацией
    all_reports = [key for key in SQL_QUERIES.keys() if key not in service_queries]
    all_reports.sort()
    
    selected_reports = st.multiselect(
        "Выберите отчеты для отображения:",
        options=all_reports,
        # default=['Средняя скорость отбора в час']
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
        
        # Кнопка применения параметров
        apply_params = st.button("Применить параметры", use_container_width=True)
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
if not selected_reports:
    st.warning("⚠️ Выберите хотя бы один отчет в боковой панели")
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
            # Загружаем все данные
            df = load_data(report_name, params)
            
            # Фильтруем по сотруднику если выбран
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