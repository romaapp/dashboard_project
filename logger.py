import sqlite3
import json
from datetime import datetime
import streamlit as st
import os

class DashboardLogger:
    """Класс для логирования действий пользователей в SQLite"""
    
    def __init__(self, db_path="logs/dashboard_logs.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Создает таблицу для логов если ее нет"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                action TEXT,
                report_name TEXT,
                params TEXT,
                session_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                ip_address TEXT,
                first_visit TEXT,
                last_visit TEXT,
                visit_count INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_action(self, action, report_name=None, params=None):
        """Логирует действие пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Получаем IP и User-Agent из Streamlit
            ip_address = st.request.remote_ip if hasattr(st, 'request') else "unknown"
            user_agent = st.request.headers.get('User-Agent', 'unknown') if hasattr(st, 'request') else "unknown"
            session_id = st.session_state.get('session_id', 'unknown')
            
            # Получаем текущее время
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Параметры в JSON
            params_json = json.dumps(params) if params else None
            
            # Вставляем запись
            cursor.execute("""
                INSERT INTO user_actions 
                (timestamp, ip_address, user_agent, action, report_name, params, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, ip_address, user_agent, action, report_name, params_json, session_id))
            
            # Обновляем или создаем сессию
            cursor.execute("""
                INSERT INTO user_sessions (session_id, ip_address, first_visit, last_visit, visit_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_visit = ?,
                    visit_count = visit_count + 1
            """, (session_id, ip_address, timestamp, timestamp, timestamp))
            
            conn.commit()
            conn.close()
        except Exception as e:
            # Не показываем ошибку пользователю, просто логируем в консоль
            print(f"Logging error: {e}")
    
    def get_statistics(self):
        """Получает статистику из логов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM user_actions")
        total_actions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM user_actions")
        unique_visitors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM user_sessions")
        unique_sessions = cursor.fetchone()[0]
        
        # Популярные отчеты
        cursor.execute("""
            SELECT report_name, COUNT(*) as count 
            FROM user_actions 
            WHERE action = 'view_report' AND report_name IS NOT NULL
            GROUP BY report_name 
            ORDER BY count DESC
        """)
        popular_reports = cursor.fetchall()
        
        # Активность по дням
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM user_actions
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        """)
        daily_activity = cursor.fetchall()
        
        # Последние действия
        cursor.execute("""
            SELECT timestamp, ip_address, action, report_name
            FROM user_actions
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        recent_actions = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_actions': total_actions,
            'unique_visitors': unique_visitors,
            'unique_sessions': unique_sessions,
            'popular_reports': popular_reports,
            'daily_activity': daily_activity,
            'recent_actions': recent_actions
        }

# Создаем глобальный экземпляр логгера
logger = DashboardLogger()