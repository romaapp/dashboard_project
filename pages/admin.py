import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from logger import logger

# === НАСТРОЙКА СТРАНИЦЫ ===
st.set_page_config(
    page_title="Статистика использования",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)



# === ПРОВЕРКА ПАРОЛЯ ===
def check_password():
    """Проверка пароля для доступа к админ-панели"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 Административный доступ")
        st.markdown("Введите пароль для доступа")
        
        password = st.text_input("Пароль:", type="password")
        
        if st.button("Войти"):
            # Можете изменить пароль здесь
            if password == "mdm_admin":
                st.session_state.admin_authenticated = True
                st.success("✅ Доступ разрешен!")
                st.rerun()
            else:
                st.error("❌ Неверный пароль!")
        return False
    return True

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    st.title("📈 Статистика использования дашборда")
    st.caption(f"Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Кнопка возврата на главную
    if st.button("⬅️ На главную"):
        st.switch_page("app.py")
    
    st.divider()
    
    # Получаем статистику
    stats = logger.get_statistics()
    
    # === ВЕРХНИЕ МЕТРИКИ ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Уникальных посетителей", stats['unique_visitors'])
    
    with col2:
        st.metric("📊 Всего действий", stats['total_actions'])
    
    with col3:
        st.metric("🔄 Сессий", stats['unique_sessions'])
    
    with col4:
        # Активность за сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        today_actions = sum(1 for action in stats['recent_actions'] if action[0].startswith(today))
        st.metric("📅 Действий сегодня", today_actions)
    
    st.divider()
    
    # === ПОПУЛЯРНЫЕ ОТЧЕТЫ ===
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔥 Популярные отчеты")
        if stats['popular_reports']:
            df_popular = pd.DataFrame(stats['popular_reports'], columns=['Отчет', 'Просмотров'])
            st.dataframe(df_popular, use_container_width=True)
            
            # График популярности
            if len(df_popular) > 0:
                fig = px.bar(df_popular, x='Отчет', y='Просмотров', 
                           title="Популярность отчетов",
                           template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о просмотренных отчетах")
    
    with col2:
        st.subheader("📅 Ежедневная активность")
        if stats['daily_activity']:
            df_daily = pd.DataFrame(stats['daily_activity'], columns=['Дата', 'Действий'])
            df_daily['Дата'] = pd.to_datetime(df_daily['Дата'])
            df_daily = df_daily.sort_values('Дата')
            
            fig = px.line(df_daily, x='Дата', y='Действий', 
                         title="Активность по дням (последние 30 дней)",
                         template="plotly_white")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_daily, use_container_width=True)
        else:
            st.info("Нет данных об активности")
    
    st.divider()
    
    # === ПОСЛЕДНИЕ ДЕЙСТВИЯ ===
    st.subheader("🕐 Последние действия")
    
    if stats['recent_actions']:
        df_actions = pd.DataFrame(stats['recent_actions'], 
                                 columns=['Время', 'IP адрес', 'Действие', 'Отчет'])
        st.dataframe(df_actions, use_container_width=True)
        
        # Фильтр по IP
        st.subheader("🔍 Фильтр по IP адресу")
        ip_list = df_actions['IP адрес'].unique()
        selected_ip = st.selectbox("Выберите IP для фильтрации:", ['Все'] + list(ip_list))
        
        if selected_ip != 'Все':
            filtered_df = df_actions[df_actions['IP адрес'] == selected_ip]
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Нет записей о действиях")

# === ЗАПУСК ===
if check_password():
    main()
else:
    st.stop()