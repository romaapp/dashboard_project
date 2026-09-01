import os
import sqlite3
import uuid
from datetime import datetime


# ============================================================
# ПУТИ
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "logs",
    "dashboard_logs.db"
)

ATTACHMENTS_DIR = os.path.join(
    BASE_DIR,
    "logs",
    "suggestions"
)


# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

def init_suggestions_db():
    """Создает таблицы предложений и вложений."""

    os.makedirs(
        os.path.dirname(DB_PATH),
        exist_ok=True
    )

    os.makedirs(
        ATTACHMENTS_DIR,
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS development_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT NOT NULL,
            suggestion TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            completed_by TEXT
        )
    """)

    # --------------------------------------------------------
    # Добавляем title в существующую БД
    # --------------------------------------------------------

    cursor.execute("""
        PRAGMA table_info(development_suggestions)
    """)

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if "title" not in columns:

        cursor.execute("""
            ALTER TABLE development_suggestions
            ADD COLUMN title TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestion_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suggestion_id INTEGER NOT NULL,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,

            FOREIGN KEY (suggestion_id)
                REFERENCES development_suggestions(id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# ДОБАВЛЕНИЕ ПРЕДЛОЖЕНИЯ
# ============================================================

def add_suggestion(
    title,
    author,
    suggestion,
    uploaded_files=None
):
    """Добавляет предложение и сохраняет его вложения."""

    init_suggestions_db()

    title = title.strip()
    author = author.strip()
    suggestion = suggestion.strip()

    if not title:
        raise ValueError(
            "Необходимо указать тему или краткое описание."
        )

    if not author:
        raise ValueError(
            "Необходимо указать имя."
        )

    if not suggestion:
        raise ValueError(
            "Необходимо указать текст предложения."
        )

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO development_suggestions
        (
            title,
            author,
            suggestion,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        title,
        author,
        suggestion,
        created_at
    ))

    suggestion_id = cursor.lastrowid

    # --------------------------------------------------------
    # Сохраняем вложения
    # --------------------------------------------------------

    if uploaded_files:

        suggestion_dir = os.path.join(
            ATTACHMENTS_DIR,
            str(suggestion_id)
        )

        os.makedirs(
            suggestion_dir,
            exist_ok=True
        )

        for uploaded_file in uploaded_files:

            original_name = uploaded_file.name

            extension = os.path.splitext(
                original_name
            )[1].lower()

            stored_name = (
                f"{uuid.uuid4().hex}"
                f"{extension}"
            )

            file_path = os.path.join(
                suggestion_dir,
                stored_name
            )

            with open(
                file_path,
                "wb"
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            cursor.execute("""
                INSERT INTO suggestion_files
                (
                    suggestion_id,
                    original_name,
                    stored_name,
                    file_path,
                    uploaded_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                suggestion_id,
                original_name,
                stored_name,
                file_path,
                created_at
            ))

    conn.commit()
    conn.close()

    return suggestion_id


# ============================================================
# ПОЛУЧЕНИЕ ПРЕДЛОЖЕНИЙ
# ============================================================

def get_suggestions(status="all"):
    """Возвращает список предложений."""

    init_suggestions_db()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    if status == "active":

        cursor.execute("""
            SELECT
                id,
                title,
                author,
                suggestion,
                created_at,
                completed,
                completed_at,
                completed_by
            FROM development_suggestions
            WHERE completed = 0
            ORDER BY id DESC
        """)

    elif status == "completed":

        cursor.execute("""
            SELECT
                id,
                title,
                author,
                suggestion,
                created_at,
                completed,
                completed_at,
                completed_by
            FROM development_suggestions
            WHERE completed = 1
            ORDER BY id DESC
        """)

    else:

        cursor.execute("""
            SELECT
                id,
                title,
                author,
                suggestion,
                created_at,
                completed,
                completed_at,
                completed_by
            FROM development_suggestions
            ORDER BY id DESC
        """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# ============================================================
# ПОЛУЧЕНИЕ ВЛОЖЕНИЙ
# ============================================================

def get_suggestion_files(suggestion_id):

    init_suggestions_db()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            original_name,
            stored_name,
            file_path,
            uploaded_at
        FROM suggestion_files
        WHERE suggestion_id = ?
        ORDER BY id
    """, (
        suggestion_id,
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows


# ============================================================
# ИЗМЕНЕНИЕ СТАТУСА
# ============================================================

def set_suggestion_completed(
    suggestion_id,
    completed,
    completed_by="admin"
):

    init_suggestions_db()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    if completed:

        completed_at = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            UPDATE development_suggestions
            SET
                completed = 1,
                completed_at = ?,
                completed_by = ?
            WHERE id = ?
        """, (
            completed_at,
            completed_by,
            suggestion_id
        ))

    else:

        cursor.execute("""
            UPDATE development_suggestions
            SET
                completed = 0,
                completed_at = NULL,
                completed_by = NULL
            WHERE id = ?
        """, (
            suggestion_id,
        ))

    conn.commit()
    conn.close()


# ============================================================
# УДАЛЕНИЕ
# ============================================================

def delete_suggestion(suggestion_id):

    init_suggestions_db()

    files = get_suggestion_files(
        suggestion_id
    )

    for file_data in files:

        file_path = file_data[3]

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception:
            pass

    suggestion_dir = os.path.join(
        ATTACHMENTS_DIR,
        str(suggestion_id)
    )

    try:

        if os.path.exists(suggestion_dir):
            os.rmdir(suggestion_dir)

    except Exception:
        pass

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM suggestion_files
        WHERE suggestion_id = ?
    """, (
        suggestion_id,
    ))

    cursor.execute("""
        DELETE FROM development_suggestions
        WHERE id = ?
    """, (
        suggestion_id,
    ))

    conn.commit()
    conn.close()


# ============================================================
# СТАТИСТИКА
# ============================================================

def get_suggestions_stats():

    init_suggestions_db()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM development_suggestions
    """)

    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM development_suggestions
        WHERE completed = 0
    """)

    active = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM development_suggestions
        WHERE completed = 1
    """)

    completed = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "active": active,
        "completed": completed
    }


# ============================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================

init_suggestions_db()