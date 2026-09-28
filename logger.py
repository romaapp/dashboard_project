import sqlite3
import json
from datetime import datetime, timedelta
import streamlit as st
import os

from sqlalchemy import text
from config import Config


class DashboardLogger:
    """Класс для логирования действий пользователей в SQLite
    с определением пользователя через WMS PostgreSQL.
    """

    def __init__(self, db_path=None):

        # ========================================================
        # ПУТЬ К БАЗЕ ДАННЫХ DASHBOARD
        # ========================================================

        if db_path is None:

            project_dir = os.path.dirname(
                os.path.abspath(__file__)
            )

            db_path = os.path.join(
                project_dir,
                "logs",
                "dashboard_logs.db"
            )

        self.db_path = db_path

        # ========================================================
        # ИНИЦИАЛИЗАЦИЯ SQLITE
        # ========================================================

        self._init_db()

    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ БАЗЫ
    # ============================================================

    def _init_db(self):
        """Создает таблицы для логов, если их нет."""

        try:

            os.makedirs(
                os.path.dirname(
                    os.path.abspath(self.db_path)
                ),
                exist_ok=True
            )

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЕЙ
            # ----------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    action TEXT,
                    report_name TEXT,
                    params TEXT,
                    session_id TEXT,
                    wms_login TEXT
                )
            """)

            # ----------------------------------------------------
            # СЕССИИ ПОЛЬЗОВАТЕЛЕЙ
            # ----------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    ip_address TEXT,
                    first_visit TEXT,
                    last_visit TEXT,
                    visit_count INTEGER DEFAULT 1,
                    wms_login TEXT
                )
            """)

            # ----------------------------------------------------
            # ПРОВЕРЯЕМ СТАРУЮ СХЕМУ
            # ----------------------------------------------------

            cursor.execute(
                "PRAGMA table_info(user_actions)"
            )

            action_columns = [
                row[1]
                for row in cursor.fetchall()
            ]

            if "wms_login" not in action_columns:

                cursor.execute("""
                    ALTER TABLE user_actions
                    ADD COLUMN wms_login TEXT
                """)

            # ----------------------------------------------------

            cursor.execute(
                "PRAGMA table_info(user_sessions)"
            )

            session_columns = [
                row[1]
                for row in cursor.fetchall()
            ]

            if "wms_login" not in session_columns:

                cursor.execute("""
                    ALTER TABLE user_sessions
                    ADD COLUMN wms_login TEXT
                """)

            # ----------------------------------------------------

            conn.commit()
            conn.close()

            print(
                "LOGGER: database initialized: "
                f"{os.path.abspath(self.db_path)}"
            )

        except Exception as e:

            print(
                f"LOGGER INIT ERROR: {e}"
            )

            print(
                "LOGGER DB: "
                f"{os.path.abspath(self.db_path)}"
            )

    # ============================================================
    # ПОЛУЧЕНИЕ IP-АДРЕСА
    # ============================================================

    def _get_client_ip(self):
        """
        Получает IP текущего пользователя
        непосредственно из WebSocket Streamlit.
        """

        try:

            from streamlit.runtime.scriptrunner import (
                get_script_run_ctx
            )

            from streamlit.runtime import get_instance

            # ----------------------------------------------------
            # STREAMLIT CONTEXT
            # ----------------------------------------------------

            ctx = get_script_run_ctx()

            if ctx is None:

                print(
                    "LOGGER IP: Streamlit context not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # RUNTIME
            # ----------------------------------------------------

            runtime = get_instance()

            # ----------------------------------------------------
            # SESSION INFO
            # ----------------------------------------------------

            session_info = (
                runtime._session_mgr.get_session_info(
                    ctx.session_id
                )
            )

            if session_info is None:

                print(
                    "LOGGER IP: session info not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # CLIENT
            # ----------------------------------------------------

            client = session_info.client

            if client is None:

                print(
                    "LOGGER IP: client not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # WEBSOCKET
            # ----------------------------------------------------

            websocket = getattr(
                client,
                "_websocket",
                None
            )

            if websocket is None:

                print(
                    "LOGGER IP: websocket not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # REMOTE CLIENT
            # ----------------------------------------------------

            remote_client = websocket.client

            if remote_client is None:

                print(
                    "LOGGER IP: remote client not found"
                )

                return "unknown"

            client_ip = remote_client.host

            print(
                f"LOGGER IP: {client_ip}"
            )

            return client_ip

        except Exception as e:

            print(
                f"LOGGER IP ERROR: {e}"
            )

            return "unknown"

    # ============================================================
    # ПОЛУЧЕНИЕ LOGIN ИЗ WMS
    # ============================================================

    def get_wms_login(self, ip_address):
        """
        Определяет пользователя WMS по IP.

        Учитываются только сессии:

        - recorddate = сегодня
        - isactive = 1
        - lastactiondate за последние 5 минут

        Если у одного IP несколько пользователей,
        login объединяются через " / ".
        """

        # --------------------------------------------------------
        # ПРОВЕРКА IP
        # --------------------------------------------------------

        if not ip_address:
            return None

        if ip_address in (
            "unknown",
            "127.0.0.1"
        ):
            return None

        engine = None

        try:

            # ----------------------------------------------------
            # ПОДКЛЮЧЕНИЕ К WMS POSTGRESQL
            # ----------------------------------------------------

            engine = Config.get_engine()

            # ----------------------------------------------------
            # ЗАПРОС
            # ----------------------------------------------------

            query = text("""
                WITH active_sessions AS (

                    SELECT
                        s.*,

                        ROW_NUMBER() OVER (
                            PARTITION BY s.sessionguid
                            ORDER BY s.lastactiondate DESC
                        ) AS rn

                    FROM sessions s

                    WHERE
                        s.recorddate::date = CURRENT_DATE
                        AND s.isactive = 1
                )

                SELECT
                    STRING_AGG(
                        DISTINCT u.login,
                        ' / '
                        ORDER BY u.login
                    ) AS login

                FROM active_sessions s

                JOIN users u
                    ON u.tid = s.user_id

                WHERE
                    s.rn = 1

                    AND s.remote_addr = :ip_address

                    AND s.lastactiondate >=
                        NOW() - INTERVAL '5 minutes'

                    AND s.remote_addr IS NOT NULL
            """)

            # ----------------------------------------------------
            # ВЫПОЛНЯЕМ ЗАПРОС
            # ----------------------------------------------------

            with engine.connect() as connection:

                result = connection.execute(
                    query,
                    {
                        "ip_address": ip_address
                    }
                )

                row = result.fetchone()

            # ----------------------------------------------------
            # LOGIN НАЙДЕН
            # ----------------------------------------------------

            if row and row[0]:

                wms_login = row[0]

                print(
                    "WMS LOGIN: "
                    f"IP={ip_address} "
                    f"LOGIN={wms_login}"
                )

                return wms_login

            # ----------------------------------------------------
            # LOGIN НЕ НАЙДЕН
            # ----------------------------------------------------

            print(
                "WMS LOGIN: "
                f"IP={ip_address} "
                "пользователь не найден"
            )

            return None

        except Exception as e:

            print(
                "WMS LOGIN ERROR: "
                f"{e}"
            )

            return None

        finally:

            # ----------------------------------------------------
            # SQLAlchemy engine
            # ----------------------------------------------------

            # Engine управляет своим connection pool,
            # поэтому вручную закрывать его здесь не нужно.

            pass

    # ============================================================
    # ЛОГИРОВАНИЕ ДЕЙСТВИЯ
    # ============================================================

    def log_action(
        self,
        action,
        report_name=None,
        params=None
    ):
        """Логирует действие пользователя."""

        conn = None

        try:

            # ----------------------------------------------------
            # SQLITE
            # ----------------------------------------------------

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # IP ПОЛЬЗОВАТЕЛЯ
            # ----------------------------------------------------

            ip_address = self._get_client_ip()

            # ----------------------------------------------------
            # LOGIN WMS
            # ----------------------------------------------------

            wms_login = self.get_wms_login(
                ip_address
            )

            # ----------------------------------------------------
            # USER-AGENT
            # ----------------------------------------------------

            try:

                user_agent = st.context.headers.get(
                    "User-Agent",
                    "unknown"
                )

            except Exception:

                user_agent = "unknown"

            # ----------------------------------------------------
            # SESSION ID
            # ----------------------------------------------------

            session_id = st.session_state.get(
                "session_id",
                "unknown"
            )

            # ----------------------------------------------------
            # ВРЕМЯ
            # ----------------------------------------------------

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # ----------------------------------------------------
            # ПАРАМЕТРЫ
            # ----------------------------------------------------

            params_json = (
                json.dumps(
                    params,
                    ensure_ascii=False
                )
                if params
                else None
            )

            # ----------------------------------------------------
            # ЗАПИСЬ ДЕЙСТВИЯ
            # ----------------------------------------------------

            cursor.execute("""
                INSERT INTO user_actions
                (
                    timestamp,
                    ip_address,
                    user_agent,
                    action,
                    report_name,
                    params,
                    session_id,
                    wms_login
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                ip_address,
                user_agent,
                action,
                report_name,
                params_json,
                session_id,
                wms_login
            ))

            inserted_id = cursor.lastrowid

            print(
                "LOGGER INSERT: "
                f"id={inserted_id}, "
                f"action={action}, "
                f"ip={ip_address}, "
                f"login={wms_login}, "
                f"session={session_id}"
            )

            # ----------------------------------------------------
            # ОБНОВЛЕНИЕ СЕССИИ
            # ----------------------------------------------------

            if session_id != "unknown":

                cursor.execute("""
                    INSERT INTO user_sessions
                    (
                        session_id,
                        ip_address,
                        first_visit,
                        last_visit,
                        visit_count,
                        wms_login
                    )
                    VALUES (?, ?, ?, ?, 1, ?)

                    ON CONFLICT(session_id)
                    DO UPDATE SET
                        last_visit = ?,
                        ip_address = ?,
                        wms_login = ?,
                        visit_count =
                            user_sessions.visit_count + 1
                """, (
                    session_id,
                    ip_address,
                    timestamp,
                    timestamp,
                    wms_login,
                    timestamp,
                    ip_address,
                    wms_login
                ))

            # ----------------------------------------------------
            # COMMIT
            # ----------------------------------------------------

            conn.commit()

            print(
                "LOGGER COMMIT OK: "
                f"{os.path.abspath(self.db_path)}"
            )

        except Exception as e:

            print(
                "========================================"
            )

            print(
                f"LOGGER ERROR: {e}"
            )

            print(
                f"LOGGER DB: "
                f"{os.path.abspath(self.db_path)}"
            )

            print(
                f"LOGGER ACTION: {action}"
            )

            print(
                "========================================"
            )

        finally:

            if conn is not None:

                try:
                    conn.close()

                except Exception:
                    pass

    # ============================================================
    # ПОЛЬЗОВАТЕЛИ ОНЛАЙН
    # ============================================================

    def get_online_users(self, minutes=5):
        """
        Получает пользователей Dashboard,
        активных за последние N минут.
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            cutoff = (
                datetime.now()
                - timedelta(minutes=minutes)
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            cursor.execute("""
                SELECT
                    ip_address,
                    MAX(last_visit) AS last_visit,
                    MAX(wms_login) AS wms_login

                FROM user_sessions

                WHERE
                    last_visit >= ?

                    AND ip_address IS NOT NULL

                    AND ip_address NOT IN (
                        '127.0.0.1',
                        'unknown'
                    )

                GROUP BY ip_address

                ORDER BY last_visit DESC
            """, (
                cutoff,
            ))

            return cursor.fetchall()

        except Exception as e:

            print(
                "Ошибка получения "
                f"онлайн пользователей: {e}"
            )

            return []

        finally:

            if conn:

                conn.close()

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    def get_statistics(self):
        """Получает статистику из логов."""

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # ВСЕГО ДЕЙСТВИЙ
            # ----------------------------------------------------

            cursor.execute(
                "SELECT COUNT(*) FROM user_actions"
            )

            total_actions = cursor.fetchone()[0]

            # ----------------------------------------------------
            # УНИКАЛЬНЫЕ ПОСЕТИТЕЛИ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT ip_address)

                FROM user_actions

                WHERE
                    ip_address IS NOT NULL

                    AND ip_address NOT IN (
                        'unknown',
                        '127.0.0.1'
                    )
            """)

            unique_visitors = cursor.fetchone()[0]

            # ----------------------------------------------------
            # УНИКАЛЬНЫЕ СЕССИИ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT session_id)

                FROM user_sessions

                WHERE
                    session_id IS NOT NULL
                    AND session_id != 'unknown'
            """)

            unique_sessions = cursor.fetchone()[0]

            # ----------------------------------------------------
            # ДЕЙСТВИЯ СЕГОДНЯ
            # ----------------------------------------------------

            today = datetime.now().strftime(
                "%Y-%m-%d"
            )

            cursor.execute("""
                SELECT COUNT(*)

                FROM user_actions

                WHERE timestamp LIKE ?
            """, (
                today + "%",
            ))

            today_actions = cursor.fetchone()[0]

            # ----------------------------------------------------
            # ПОСЕТИТЕЛИ СЕГОДНЯ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT ip_address)

                FROM user_actions

                WHERE
                    timestamp LIKE ?

                    AND ip_address IS NOT NULL

                    AND ip_address NOT IN (
                        'unknown',
                        '127.0.0.1'
                    )
            """, (
                today + "%",
            ))

            today_visitors = cursor.fetchone()[0]

            # ----------------------------------------------------
            # ПОПУЛЯРНЫЕ ОТЧЕТЫ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    report_name,
                    COUNT(*) AS count

                FROM user_actions

                WHERE
                    action = 'view_report'
                    AND report_name IS NOT NULL

                GROUP BY report_name

                ORDER BY count DESC
            """)

            popular_reports = cursor.fetchall()

            # ----------------------------------------------------
            # АКТИВНОСТЬ ПО ДНЯМ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    DATE(timestamp) AS date,
                    COUNT(*) AS count

                FROM user_actions

                GROUP BY DATE(timestamp)

                ORDER BY date DESC

                LIMIT 30
            """)

            daily_activity = cursor.fetchall()

            # ----------------------------------------------------
            # ПОСЛЕДНИЕ ДЕЙСТВИЯ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    timestamp,
                    ip_address,
                    action,
                    report_name,
                    wms_login

                FROM user_actions

                ORDER BY timestamp DESC

                LIMIT 50
            """)

            recent_actions = cursor.fetchall()

            # ----------------------------------------------------
            # ВОЗВРАТ
            # ----------------------------------------------------

            return {
                "total_actions": total_actions,
                "unique_visitors": unique_visitors,
                "unique_sessions": unique_sessions,
                "today_actions": today_actions,
                "today_visitors": today_visitors,
                "popular_reports": popular_reports,
                "daily_activity": daily_activity,
                "recent_actions": recent_actions
            }

        except Exception as e:

            print(
                f"LOGGER STATISTICS ERROR: {e}"
            )

            print(
                "LOGGER DB: "
                f"{os.path.abspath(self.db_path)}"
            )

            return {
                "total_actions": 0,
                "unique_visitors": 0,
                "unique_sessions": 0,
                "today_actions": 0,
                "today_visitors": 0,
                "popular_reports": [],
                "daily_activity": [],
                "recent_actions": []
            }

        finally:

            if conn is not None:

                try:
                    conn.close()

                except Exception:
                    pass


# ============================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ============================================================

logger = DashboardLogger()