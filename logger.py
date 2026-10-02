import sqlite3
import json
from datetime import datetime, timedelta
import streamlit as st
import os


class DashboardLogger:
    """Класс для логирования действий пользователей в SQLite"""

    def __init__(self, db_path=None):

        # ========================================================
        # ПУТЬ К БАЗЕ ДАННЫХ
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

        self._init_db()

    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ БАЗЫ
    # ============================================================

    def _init_db(self):
        """Создает таблицы и выполняет необходимые миграции."""

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
                    session_id TEXT
                )
            """)

            # ----------------------------------------------------
            # ПРОВЕРЯЕМ ПОЛЯ user_actions
            # ----------------------------------------------------

            cursor.execute("""
                PRAGMA table_info(user_actions)
            """)

            columns = [
                row[1]
                for row in cursor.fetchall()
            ]

            # ----------------------------------------------------
            # USER_ID
            # ----------------------------------------------------

            if "user_id" not in columns:

                cursor.execute("""
                    ALTER TABLE user_actions
                    ADD COLUMN user_id INTEGER
                """)

            # ----------------------------------------------------
            # СЕССИИ ПОЛЬЗОВАТЕЛЕЙ
            # ----------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    ip_address TEXT,
                    user_id INTEGER,
                    first_visit TEXT,
                    last_visit TEXT,
                    visit_count INTEGER DEFAULT 1
                )
            """)

            # ----------------------------------------------------
            # МИГРАЦИЯ СУЩЕСТВУЮЩЕЙ user_sessions
            # ----------------------------------------------------

            cursor.execute("""
                PRAGMA table_info(user_sessions)
            """)

            session_columns = [
                row[1]
                for row in cursor.fetchall()
            ]

            if "user_id" not in session_columns:

                cursor.execute("""
                    ALTER TABLE user_sessions
                    ADD COLUMN user_id INTEGER
                """)

            # ----------------------------------------------------
            # ПОЛЬЗОВАТЕЛИ ДАШБОРДА
            # ----------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT NOT NULL UNIQUE,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """)

            conn.commit()
            conn.close()

            print(
                f"LOGGER: database initialized: "
                f"{os.path.abspath(self.db_path)}"
            )

        except Exception as e:

            print(
                f"LOGGER INIT ERROR: {e}"
            )

            print(
                f"LOGGER DB: "
                f"{os.path.abspath(self.db_path)}"
            )

    # ============================================================
    # ПОЛЬЗОВАТЕЛИ
    # ============================================================

    def register_user(self, login):
        """
        Регистрирует нового пользователя.

        Возвращает:
        (True, user_id)  - пользователь успешно создан
        (False, message) - ошибка
        """

        conn = None

        try:

            login = login.strip()

            if not login:
                return False, "Введите логин"

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            created_at = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            cursor.execute("""
                INSERT INTO users (
                    login,
                    is_active,
                    created_at,
                    last_login
                )
                VALUES (?, 1, ?, NULL)
            """, (
                login,
                created_at
            ))

            user_id = cursor.lastrowid

            conn.commit()

            return True, user_id

        except sqlite3.IntegrityError:

            return False, (
                "Пользователь с таким логином "
                "уже существует"
            )

        except Exception as e:

            print(
                f"REGISTER USER ERROR: {e}"
            )

            return False, (
                "Ошибка регистрации пользователя"
            )

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

    # ============================================================
    # АКТИВНЫЕ ПОЛЬЗОВАТЕЛИ
    # ============================================================

    def get_active_users(self):
        """
        Возвращает активных пользователей.

        Формат:
        [
            (user_id, login),
            ...
        ]
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    user_id,
                    login
                FROM users
                WHERE is_active = 1
                ORDER BY login
            """)

            return cursor.fetchall()

        except Exception as e:

            print(
                f"GET ACTIVE USERS ERROR: {e}"
            )

            return []

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

    # ============================================================
    # ВСЕ ПОЛЬЗОВАТЕЛИ
    # ============================================================

    def get_all_users(self):
        """
        Возвращает всех пользователей.

        Формат:
        [
            (user_id, login, is_active, created_at, last_login),
            ...
        ]
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    user_id,
                    login,
                    is_active,
                    created_at,
                    last_login
                FROM users
                ORDER BY login
            """)

            return cursor.fetchall()

        except Exception as e:

            print(
                f"GET ALL USERS ERROR: {e}"
            )

            return []

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

    # ============================================================
    # АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    def set_user_active(self, user_id, is_active):
        """
        Включает или выключает пользователя.

        is_active:
        True  - активен
        False - неактивен
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET is_active = ?
                WHERE user_id = ?
            """, (
                1 if is_active else 0,
                user_id
            ))

            conn.commit()

            return True

        except Exception as e:

            print(
                f"SET USER ACTIVE ERROR: {e}"
            )

            return False

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

    # ============================================================
    # УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
    # ============================================================

    def delete_user(self, user_id):
        """
        Удаляет пользователя из таблицы users.

        История действий пользователя
        при этом не удаляется.
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM users
                WHERE user_id = ?
            """, (
                user_id,
            ))

            conn.commit()

            return True

        except Exception as e:

            print(
                f"DELETE USER ERROR: {e}"
            )

            return False

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

    # ============================================================
    # ПОСЛЕДНИЙ ВХОД
    # ============================================================

    def update_last_login(self, user_id):
        """Обновляет дату и время последнего входа."""

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            last_login = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            cursor.execute("""
                UPDATE users
                SET last_login = ?
                WHERE user_id = ?
            """, (
                last_login,
                user_id
            ))

            conn.commit()

            return True

        except Exception as e:

            print(
                f"UPDATE LAST LOGIN ERROR: {e}"
            )

            return False

        finally:

            if conn is not None:

                try:
                    conn.close()
                except Exception:
                    pass

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

            ctx = get_script_run_ctx()

            if ctx is None:

                print(
                    "LOGGER IP: Streamlit context not found"
                )

                return "unknown"

            runtime = get_instance()

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

            client = session_info.client

            if client is None:

                print(
                    "LOGGER IP: client not found"
                )

                return "unknown"

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
            # ПОДКЛЮЧЕНИЕ
            # ----------------------------------------------------

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # IP
            # ----------------------------------------------------

            ip_address = self._get_client_ip()

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
            # USER ID
            # ----------------------------------------------------

            user_id = st.session_state.get(
                "user_id"
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
                    user_id
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
                user_id
            ))

            inserted_id = cursor.lastrowid

            print(
                f"LOGGER INSERT: "
                f"id={inserted_id}, "
                f"action={action}, "
                f"user_id={user_id}, "
                f"ip={ip_address}, "
                f"session={session_id}"
            )

            # ----------------------------------------------------
            # ОБНОВЛЯЕМ СЕССИЮ
            # ----------------------------------------------------

            if session_id != "unknown":

                cursor.execute("""
                    INSERT INTO user_sessions
                    (
                        session_id,
                        ip_address,
                        user_id,
                        first_visit,
                        last_visit,
                        visit_count
                    )
                    VALUES (?, ?, ?, ?, ?, 1)

                    ON CONFLICT(session_id)
                    DO UPDATE SET
                        last_visit = ?,
                        ip_address = ?,
                        user_id = ?,
                        visit_count = visit_count + 1
                """, (
                    session_id,
                    ip_address,
                    user_id,
                    timestamp,
                    timestamp,
                    timestamp,
                    ip_address,
                    user_id
                ))

            # ----------------------------------------------------
            # COMMIT
            # ----------------------------------------------------

            conn.commit()

            print(
                f"LOGGER COMMIT OK: "
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
        Получает пользователей, которые были активны
        за последние N минут.

        ВАЖНО:
        Пользователь определяется по user_id,
        а НЕ по IP.

        Возвращает:
        [
            (user_id, login, ip_address, last_visit),
            ...
        ]
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

            # ----------------------------------------------------
            # Получаем все активные сессии пользователей
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    us.user_id,
                    u.login,
                    us.ip_address,
                    us.last_visit

                FROM user_sessions AS us

                INNER JOIN users AS u
                    ON us.user_id = u.user_id

                WHERE
                    us.last_visit >= ?
                    AND us.user_id IS NOT NULL

                ORDER BY
                    us.last_visit DESC
            """, (
                cutoff,
            ))

            rows = cursor.fetchall()

            # ----------------------------------------------------
            # Оставляем только одну строку на пользователя.
            #
            # Если один пользователь имеет несколько сессий,
            # он всё равно считается одним пользователем.
            # ----------------------------------------------------

            online_users = []

            seen_users = set()

            for row in rows:

                user_id = row[0]

                if user_id in seen_users:
                    continue

                seen_users.add(user_id)

                online_users.append(row)

            return online_users

        except Exception as e:

            print(
                f"Ошибка получения онлайн пользователей: {e}"
            )

            return []

        finally:

            if conn is not None:

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
            #
            # Считаем по USER_ID,
            # а не по IP.
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM user_actions
                WHERE user_id IS NOT NULL
            """)

            unique_visitors = cursor.fetchone()[0]

            # ----------------------------------------------------
            # УНИКАЛЬНЫЕ СЕССИИ
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT session_id)
                FROM user_sessions
                WHERE session_id IS NOT NULL
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
            #
            # Считаем уникальные USER_ID.
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM user_actions
                WHERE timestamp LIKE ?
                AND user_id IS NOT NULL
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
                    COUNT(*) as count

                FROM user_actions

                WHERE action = 'view_report'
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
                    DATE(timestamp) as date,
                    COUNT(*) as count

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
                    ua.timestamp,
                    ua.ip_address,
                    ua.action,
                    ua.report_name,
                    u.login
                FROM user_actions AS ua

                LEFT JOIN users AS u
                    ON ua.user_id = u.user_id

                ORDER BY ua.timestamp DESC

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
                f"LOGGER DB: "
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