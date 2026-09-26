import sqlite3
import json
import re
import subprocess
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
        """Создает таблицы для логов, если их нет"""

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
            # СЕССИИ ПОЛЬЗОВАТЕЛЕЙ
            # ----------------------------------------------------

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
            # Получаем текущий Streamlit context
            # ----------------------------------------------------

            ctx = get_script_run_ctx()

            if ctx is None:

                print(
                    "LOGGER IP: Streamlit context not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # Получаем runtime
            # ----------------------------------------------------

            runtime = get_instance()

            # ----------------------------------------------------
            # Получаем информацию о текущей сессии
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
            # Получаем клиента
            # ----------------------------------------------------

            client = session_info.client

            if client is None:

                print(
                    "LOGGER IP: client not found"
                )

                return "unknown"

            # ----------------------------------------------------
            # Получаем WebSocket
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
            # Получаем адрес клиента
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
    # ЛОГИРОВАНИЕ ДЕЙСТВИЯ
    # ============================================================

    def log_action(
        self,
        action,
        report_name=None,
        params=None
    ):
        """Логирует действие пользователя"""

        conn = None

        try:

            # ----------------------------------------------------
            # Подключение к БД
            # ----------------------------------------------------

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # IP пользователя
            # ----------------------------------------------------

            ip_address = self._get_client_ip()

            # ----------------------------------------------------
            # User-Agent
            # ----------------------------------------------------

            try:

                user_agent = st.context.headers.get(
                    "User-Agent",
                    "unknown"
                )

            except Exception:

                user_agent = "unknown"

            # ----------------------------------------------------
            # Session ID
            # ----------------------------------------------------

            session_id = st.session_state.get(
                "session_id",
                "unknown"
            )

            # ----------------------------------------------------
            # Время
            # ----------------------------------------------------

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # ----------------------------------------------------
            # Параметры
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
            # Запись действия
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
                    session_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                ip_address,
                user_agent,
                action,
                report_name,
                params_json,
                session_id
            ))

            # ----------------------------------------------------
            # Проверяем INSERT
            # ----------------------------------------------------

            inserted_id = cursor.lastrowid

            print(
                f"LOGGER INSERT: "
                f"id={inserted_id}, "
                f"action={action}, "
                f"ip={ip_address}, "
                f"session={session_id}"
            )

            # ----------------------------------------------------
            # Обновляем информацию о сессии
            # ----------------------------------------------------

            if session_id != "unknown":

                cursor.execute("""
                    INSERT INTO user_sessions
                    (
                        session_id,
                        ip_address,
                        first_visit,
                        last_visit,
                        visit_count
                    )
                    VALUES (?, ?, ?, ?, 1)

                    ON CONFLICT(session_id)
                    DO UPDATE SET
                        last_visit = ?,
                        ip_address = ?
                """, (
                    session_id,
                    ip_address,
                    timestamp,
                    timestamp,
                    timestamp,
                    ip_address
                ))

            # ----------------------------------------------------
            # Фиксируем транзакцию
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
    # ОПРЕДЕЛЕНИЕ ИМЕНИ КОМПЬЮТЕРА ПО IP
    # ============================================================

    def _resolve_hostname(self, ip_address):
        """
        Определяет имя компьютера по IP-адресу.

        Например:

            192.168.225.40
                    ↓
            fr-ts14.omco.ru

        Возвращает короткое имя компьютера:
            FR-TS14

        Если определить имя не удалось:
            возвращает IP.
        """

        try:

            import socket

            hostname = socket.gethostbyaddr(
                ip_address
            )[0]

            if hostname:

                short_hostname = hostname.split(
                    "."
                )[0]

                print(
                    f"LOGGER HOSTNAME: "
                    f"{ip_address} -> {short_hostname}"
                )

                return short_hostname

        except Exception as e:

            print(
                f"LOGGER HOSTNAME ERROR: "
                f"{ip_address}: {e}"
            )

        return ip_address

    # ============================================================
    # ПОЛЬЗОВАТЕЛИ WINDOWS НА УДАЛЕННОМ КОМПЬЮТЕРЕ
    # ============================================================

    def get_windows_users(self, ip_address):
        """
        Получает пользователей Windows через quser.

        Сначала определяется имя компьютера по IP,
        затем выполняется:

            quser /server:COMPUTER

        Возвращает список словарей:

        [
            {
                "username": "...",
                "session": "...",
                "session_id": "...",
                "status": "Активно",
                "idle": "...",
                "login_time": "...",
                "computer": "FR-TS14"
            }
        ]

        """

        computer_name = self._resolve_hostname(
            ip_address
        )

        try:

            # ----------------------------------------------------
            # Выполняем quser
            # ----------------------------------------------------

            result = subprocess.run(
                [
                    "quser",
                    "/server:" + computer_name
                ],
                capture_output=True,
                text=True,
                encoding="cp866",
                errors="replace",
                timeout=5
            )

            # ----------------------------------------------------
            # Проверяем результат
            # ----------------------------------------------------

            if result.returncode != 0:

                print(
                    f"LOGGER QUSER ERROR: "
                    f"{computer_name}: "
                    f"{result.stderr}"
                )

                return []

            output = result.stdout

            print(
                f"LOGGER QUSER OUTPUT "
                f"{computer_name}:\n{output}"
            )

            users = []

            # ----------------------------------------------------
            # Разбираем строки
            # ----------------------------------------------------

            lines = output.splitlines()

            for line in lines:

                line = line.rstrip()

                if not line:
                    continue

                # ------------------------------------------------
                # Пропускаем заголовок
                # ------------------------------------------------

                if (
                    "ПОЛЬЗОВАТЕЛЬ" in line
                    or "USER" in line.upper()
                ):
                    continue

                # ------------------------------------------------
                # Пропускаем служебные строки
                # ------------------------------------------------

                if (
                    "СЕАНС" in line
                    or "SESSIONNAME" in line.upper()
                ):
                    continue

                # ------------------------------------------------
                # Если строка начинается с ">"
                # это текущая сессия
                # ------------------------------------------------

                line = line.lstrip(">")

                # ------------------------------------------------
                # Разбираем по группам пробелов
                # ------------------------------------------------

                parts = re.split(
                    r"\s{2,}",
                    line.strip()
                )

                if len(parts) < 3:
                    continue

                # ------------------------------------------------
                # Возможные форматы:
                #
                # username
                # session
                # id
                # status
                # idle
                # login_time
                #
                # Для отключенной сессии session
                # может отсутствовать.
                # ------------------------------------------------

                username = parts[0].strip()

                if not username:
                    continue

                # ------------------------------------------------
                # Исключаем служебные строки
                # ------------------------------------------------

                if username.lower() in [
                    "services",
                    "console",
                    "rdp-tcp",
                ]:

                    continue

                # ------------------------------------------------
                # Определяем структуру строки
                # ------------------------------------------------

                session_name = ""
                session_id = ""
                status = ""
                idle = ""
                login_time = ""

                # ------------------------------------------------
                # Ищем числовой ID сессии
                # ------------------------------------------------

                id_index = None

                for index, part in enumerate(parts):

                    if re.fullmatch(
                        r"\d+",
                        part
                    ):

                        id_index = index
                        break

                if id_index is not None:

                    session_id = parts[id_index]

                    if id_index >= 1:

                        session_name = parts[
                            id_index - 1
                        ]

                    if id_index + 1 < len(parts):

                        status = parts[
                            id_index + 1
                        ]

                    if id_index + 2 < len(parts):

                        idle = parts[
                            id_index + 2
                        ]

                    if id_index + 3 < len(parts):

                        login_time = " ".join(
                            parts[id_index + 3:]
                        )

                # ------------------------------------------------
                # Если ID не нашли
                # ------------------------------------------------

                else:

                    continue

                users.append({
                    "username": username,
                    "session": session_name,
                    "session_id": session_id,
                    "status": status,
                    "idle": idle,
                    "login_time": login_time,
                    "computer": computer_name
                })

            print(
                f"LOGGER QUSER USERS: "
                f"{computer_name} -> {users}"
            )

            return users

        except subprocess.TimeoutExpired:

            print(
                f"LOGGER QUSER TIMEOUT: "
                f"{computer_name}"
            )

            return []

        except FileNotFoundError:

            print(
                "LOGGER QUSER ERROR: "
                "команда quser не найдена"
            )

            return []

        except Exception as e:

            print(
                f"LOGGER QUSER ERROR: "
                f"{computer_name}: {e}"
            )

            return []

    # ============================================================
    # ОНЛАЙН ПОЛЬЗОВАТЕЛИ + WINDOWS LOGIN
    # ============================================================

    def get_online_users_with_accounts(
        self,
        minutes=5
    ):
        """
        Получает пользователей, которые сейчас используют
        дашборд, и пытается определить их Windows login.

        Возвращает:

        [
            {
                "ip_address": "...",
                "last_visit": "...",
                "computer": "...",
                "username": "...",
                "session": "...",
                "session_id": "...",
                "status": "...",
                "idle": "...",
                "login_time": "..."
            }
        ]

        ВАЖНО:

        Один IP может соответствовать нескольким
        Windows-сессиям, поэтому на один IP может
        приходиться несколько записей.
        """

        # --------------------------------------------------------
        # Получаем текущих посетителей дашборда
        # --------------------------------------------------------

        online_users = self.get_online_users(
            minutes=minutes
        )

        result = []

        # --------------------------------------------------------
        # Для каждого IP определяем Windows-пользователей
        # --------------------------------------------------------

        for ip_address, last_visit in online_users:

            windows_users = self.get_windows_users(
                ip_address
            )

            # ----------------------------------------------------
            # Если пользователей определить удалось
            # ----------------------------------------------------

            if windows_users:

                for user in windows_users:

                    result.append({
                        "ip_address": ip_address,
                        "last_visit": last_visit,
                        "computer": user["computer"],
                        "username": user["username"],
                        "session": user["session"],
                        "session_id": user["session_id"],
                        "status": user["status"],
                        "idle": user["idle"],
                        "login_time": user["login_time"]
                    })

            # ----------------------------------------------------
            # Если quser ничего не вернул
            # ----------------------------------------------------

            else:

                computer_name = self._resolve_hostname(
                    ip_address
                )

                result.append({
                    "ip_address": ip_address,
                    "last_visit": last_visit,
                    "computer": computer_name,
                    "username": "Не определен",
                    "session": "",
                    "session_id": "",
                    "status": "",
                    "idle": "",
                    "login_time": ""
                })

        return result

    # ============================================================
    # ПОЛЬЗОВАТЕЛИ ОНЛАЙН
    # ============================================================

    def get_online_users(self, minutes=5):
        """
        Получает пользователей, которые были активны
        за последние N минут.

        Возвращает:

        [
            (ip_address, last_visit),
            ...
        ]

        Этот метод специально оставлен в прежнем формате,
        чтобы существующий admin.py продолжил работать
        без изменений.
        """

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # Время, после которого пользователь считается
            # неактивным
            # ----------------------------------------------------

            cutoff = (
                datetime.now()
                - timedelta(minutes=minutes)
            ).strftime("%Y-%m-%d %H:%M:%S")

            # ----------------------------------------------------
            # Получаем последнюю активность по каждому IP
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    ip_address,
                    MAX(last_visit) AS last_visit

                FROM user_sessions

                WHERE last_visit >= ?

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

            online_users = cursor.fetchall()

            return online_users

        except Exception as e:

            print(
                f"Ошибка получения онлайн пользователей: {e}"
            )

            return []

        finally:

            if conn:

                conn.close()

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    def get_statistics(self):
        """Получает статистику из логов"""

        conn = None

        try:

            conn = sqlite3.connect(
                self.db_path
            )

            cursor = conn.cursor()

            # ----------------------------------------------------
            # Всего действий
            # ----------------------------------------------------

            cursor.execute(
                "SELECT COUNT(*) FROM user_actions"
            )

            total_actions = cursor.fetchone()[0]

            # ----------------------------------------------------
            # Уникальные посетители
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT ip_address)

                FROM user_actions

                WHERE ip_address IS NOT NULL

                AND ip_address NOT IN (
                    'unknown',
                    '127.0.0.1'
                )
            """)

            unique_visitors = cursor.fetchone()[0]

            # ----------------------------------------------------
            # Уникальные сессии
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT session_id)

                FROM user_sessions

                WHERE session_id IS NOT NULL

                AND session_id != 'unknown'
            """)

            unique_sessions = cursor.fetchone()[0]

            # ----------------------------------------------------
            # Действия сегодня
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
            # Посетители сегодня
            # ----------------------------------------------------

            cursor.execute("""
                SELECT COUNT(DISTINCT ip_address)

                FROM user_actions

                WHERE timestamp LIKE ?

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
            # Популярные отчеты
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
            # Активность по дням
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
            # Пользователи по дням
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    DATE(timestamp) as date,
                    COUNT(DISTINCT ip_address) as count

                FROM user_actions

                WHERE ip_address IS NOT NULL

                AND ip_address NOT IN (
                    'unknown',
                    '127.0.0.1'
                )

                GROUP BY DATE(timestamp)

                ORDER BY date DESC

                LIMIT 30
            """)

            daily_visitors = cursor.fetchall()

            # ----------------------------------------------------
            # Последние действия
            # ----------------------------------------------------

            cursor.execute("""
                SELECT
                    timestamp,
                    ip_address,
                    action,
                    report_name

                FROM user_actions

                ORDER BY timestamp DESC

                LIMIT 50
            """)

            recent_actions = cursor.fetchall()

            # ----------------------------------------------------
            # Возвращаем статистику
            # ----------------------------------------------------

            return {
                "total_actions": total_actions,
                "unique_visitors": unique_visitors,
                "unique_sessions": unique_sessions,
                "today_actions": today_actions,
                "today_visitors": today_visitors,
                "popular_reports": popular_reports,
                "daily_activity": daily_activity,
                "daily_visitors": daily_visitors,
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
                "daily_visitors": [],
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