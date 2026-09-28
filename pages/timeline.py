import os
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from styles import load_css


# ============================================================
# ЗАГРУЗКА .ENV
# ============================================================

current_dir = Path(__file__).resolve().parent
project_root = (
    current_dir.parent
    if current_dir.name == "pages"
    else current_dir
)

dotenv_path = project_root / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()


# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================

st.set_page_config(
    page_title="Timeline заявки",
    page_icon="🕐",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

st.title("🕐 Timeline заявки")

st.caption(
    "Хронология жизненного цикла отгрузки "
    "по данным WMS LogistiX"
)

st.caption(
    "Страница работает в тестовом режиме"
)

# ============================================================
# ПОДКЛЮЧЕНИЕ К БД
# ============================================================

def get_db_connection():

    host = (
        os.getenv("DB_HOST")
        or os.getenv("PGHOST")
        or "localhost"
    )

    port = (
        os.getenv("DB_PORT")
        or os.getenv("PGPORT")
        or "5432"
    )

    dbname = (
        os.getenv("DB_NAME")
        or os.getenv("PGDATABASE")
        or "wms"
    )

    user = (
        os.getenv("DB_USER")
        or os.getenv("PGUSER")
        or "logistix"
    )

    password = (
        os.getenv("DB_PASSWORD")
        or os.getenv("PGPASSWORD")
        or ""
    )

    return psycopg2.connect(
        host=host,
        port=int(port),
        database=dbname,
        user=user,
        password=password
    )


# ============================================================
# НОРМАЛИЗАЦИЯ НОМЕРА ЗАЯВКИ
# ============================================================

def normalize_order_number(value):

    value = str(value or "").strip().lower()

    result = ""

    for char in value:

        if char.isalnum():

            result += char

    return result


# ============================================================
# ПОИСК ЗАЯВОК ПО ЧАСТИ НОМЕРА
# ============================================================

@st.cache_data(ttl=60)
def search_orders(search_value):

    normalized_value = normalize_order_number(
        search_value
    )

    if len(normalized_value) < 4:

        return []

    query = """
    SELECT
        hd.purchasenumber AS purchasenumber,
        t.creationdate AS creationdate,
        hd.starteddate AS starteddate,
        hd.readydate AS readydate,
        hd.readyforcontroldate AS readyforcontroldate,
        hd.shipdate AS shipdate,
        hd.isstarted,
        hd.isreadyforshipment,
        hd.isshipped,
        hd.deliverystatus
    FROM dbo.hdr_delivery hd
    JOIN dbo.transactions t
        ON t.tid = hd.transaction_id
    WHERE
        POSITION(
            %(search_value)s IN
            regexp_replace(
                lower(hd.purchasenumber),
                '[^a-zа-яё0-9]',
                '',
                'g'
            )
        ) > 0
    ORDER BY
        length(
            regexp_replace(
                lower(hd.purchasenumber),
                '[^a-zа-яё0-9]',
                '',
                'g'
            )
        ),
        hd.purchasenumber
    LIMIT 50;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    query,
                    {
                        "search_value": normalized_value
                    }
                )

                results = cur.fetchall()

                return [
                    dict(row)
                    for row in results
                ]

    except Exception as e:

        st.error(
            f"Ошибка выполнения SQL-запроса: {e}"
        )

        return []


# ============================================================
# ПОЛУЧЕНИЕ TIMELINE КОНКРЕТНОЙ ЗАЯВКИ
# ============================================================

@st.cache_data(ttl=60)
def get_order_timeline(order_num: str):

    query = """
    SELECT
        t.creationdate AS creationdate,
        hd.starteddate AS starteddate,
        hd.readydate AS readydate,
        hd.readyforcontroldate AS readyforcontroldate,
        hd.shipdate AS shipdate,
        hd.isstarted,
        hd.isreadyforshipment,
        hd.isshipped,
        hd.deliverystatus
    FROM dbo.hdr_delivery hd
    JOIN dbo.transactions t
        ON t.tid = hd.transaction_id
    WHERE hd.purchasenumber = %(order_num)s
    LIMIT 1;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    query,
                    {
                        "order_num": order_num.strip()
                    }
                )

                result = cur.fetchone()

                if result:

                    return dict(result)

                return None

    except Exception as e:

        st.error(
            f"Ошибка выполнения SQL-запроса: {e}"
        )

        return None


# ============================================================
# ПОЛУЧЕНИЕ ЗАВИСШИХ ЗАЯВОК
# ============================================================

@st.cache_data(ttl=60)
def get_stuck_orders():

    query = """
    SELECT
        hd.purchasenumber AS purchasenumber,
        t.creationdate AS creationdate,
        hd.starteddate AS starteddate,
        hd.readydate AS readydate,
        hd.readyforcontroldate AS readyforcontroldate,
        hd.shipdate AS shipdate,
        hd.isstarted,
        hd.isreadyforshipment,
        hd.isshipped,
        hd.deliverystatus,

        CASE

            -- ------------------------------------------------
            -- Ожидание отгрузки
            -- ------------------------------------------------

            WHEN
                hd.readydate IS NOT NULL
                AND hd.shipdate IS NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - hd.readydate
                    )
                ) / 60 >= 60

            THEN 'Ожидание отгрузки'


            -- ------------------------------------------------
            -- Обработка
            -- ------------------------------------------------

            WHEN
                hd.starteddate IS NOT NULL
                AND hd.readydate IS NULL
                AND hd.shipdate IS NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - hd.starteddate
                    )
                ) / 60 >= 180

            THEN 'Обработка'


            -- ------------------------------------------------
            -- Ожидание запуска
            -- ------------------------------------------------

            WHEN
                hd.starteddate IS NULL
                AND hd.readydate IS NULL
                AND hd.shipdate IS NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - t.creationdate
                    )
                ) / 60 >= 20

            THEN 'Ожидание запуска'

        END AS stuck_stage,


        CASE

            -- ------------------------------------------------
            -- Время зависания:
            -- ожидание отгрузки
            -- ------------------------------------------------

            WHEN
                hd.readydate IS NOT NULL
                AND hd.shipdate IS NULL

            THEN EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP
                    - hd.readydate
                )
            ) / 60


            -- ------------------------------------------------
            -- Время зависания:
            -- обработка
            -- ------------------------------------------------

            WHEN
                hd.starteddate IS NOT NULL
                AND hd.readydate IS NULL
                AND hd.shipdate IS NULL

            THEN EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP
                    - hd.starteddate
                )
            ) / 60


            -- ------------------------------------------------
            -- Время зависания:
            -- ожидание запуска
            -- ------------------------------------------------

            WHEN
                hd.starteddate IS NULL
                AND hd.readydate IS NULL
                AND hd.shipdate IS NULL

            THEN EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP
                    - t.creationdate
                )
            ) / 60

        END AS stuck_minutes

    FROM dbo.hdr_delivery hd

    JOIN dbo.transactions t
        ON t.tid = hd.transaction_id

    WHERE

        -- ----------------------------------------------------
        -- Только незавершённые заявки
        -- ----------------------------------------------------

        hd.shipdate IS NULL

        AND

        (

            -- ------------------------------------------------
            -- Ожидание отгрузки > 60 минут
            -- ------------------------------------------------

            (
                hd.readydate IS NOT NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - hd.readydate
                    )
                ) / 60 >= 60
            )

            OR

            -- ------------------------------------------------
            -- Обработка > 180 минут
            -- ------------------------------------------------

            (
                hd.starteddate IS NOT NULL
                AND hd.readydate IS NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - hd.starteddate
                    )
                ) / 60 >= 180
            )

            OR

            -- ------------------------------------------------
            -- Ожидание запуска > 20 минут
            -- ------------------------------------------------

            (
                hd.starteddate IS NULL
                AND hd.readydate IS NULL
                AND EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP
                        - t.creationdate
                    )
                ) / 60 >= 20
            )
        )

    ORDER BY
        stuck_minutes DESC;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(query)

                results = cur.fetchall()

                return [
                    dict(row)
                    for row in results
                ]

    except Exception as e:

        st.error(
            f"Ошибка получения зависших заявок: {e}"
        )

        return []


# ============================================================
# ФОРМИРОВАНИЕ СОБЫТИЙ TIMELINE
# ============================================================

def build_events(order_data):

    events = []

    if not order_data:
        return events

    # --------------------------------------------------------
    # Создание заявки
    # --------------------------------------------------------

    if order_data.get("creationdate") is not None:

        events.append({
            "event_time": order_data["creationdate"],
            "status_name": "Создана",
            "is_error": False
        })

    # --------------------------------------------------------
    # Начало обработки
    # --------------------------------------------------------

    if order_data.get("starteddate") is not None:

        events.append({
            "event_time": order_data["starteddate"],
            "status_name": "Начата обработка",
            "is_error": False
        })

    # --------------------------------------------------------
    # Готовность к отгрузке
    # --------------------------------------------------------

    if order_data.get("readydate") is not None:

        events.append({
            "event_time": order_data["readydate"],
            "status_name": "Готова к отгрузке",
            "is_error": False
        })

    # --------------------------------------------------------
    # Фактическая отгрузка
    # --------------------------------------------------------

    if order_data.get("shipdate") is not None:

        events.append({
            "event_time": order_data["shipdate"],
            "status_name": "Отгружена",
            "is_error": False
        })

    return events


# ============================================================
# ФОРМАТИРОВАНИЕ ВРЕМЕНИ
# ============================================================

def format_duration(minutes):

    minutes = max(0, int(minutes))

    hours = minutes // 60
    mins = minutes % 60

    if hours > 0:

        return f"{hours} ч {mins} мин"

    return f"{mins} мин"


# ============================================================
# РАСЧЁТ ВРЕМЕНИ
# ============================================================

def calculate_metrics(order_data):

    creation = order_data.get("creationdate")
    started = order_data.get("starteddate")
    ready = order_data.get("readydate")
    ship = order_data.get("shipdate")

    now = datetime.now()

    # --------------------------------------------------------
    # Приводим значения к datetime
    # --------------------------------------------------------

    if creation is not None:

        creation = pd.to_datetime(
            creation
        ).to_pydatetime()

    if started is not None:

        started = pd.to_datetime(
            started
        ).to_pydatetime()

    if ready is not None:

        ready = pd.to_datetime(
            ready
        ).to_pydatetime()

    if ship is not None:

        ship = pd.to_datetime(
            ship
        ).to_pydatetime()

    # --------------------------------------------------------
    # Определяем завершённость
    # --------------------------------------------------------

    is_finished = ship is not None

    # --------------------------------------------------------
    # Конечное время
    # --------------------------------------------------------

    if is_finished:

        end_time = ship

    else:

        end_time = now

    # --------------------------------------------------------
    # Общее время
    # --------------------------------------------------------

    total_min = 0

    if creation is not None:

        total_min = int(
            (
                end_time - creation
            ).total_seconds() // 60
        )

    # --------------------------------------------------------
    # Ожидание запуска
    # --------------------------------------------------------

    wait_min = 0

    if (
        creation is not None
        and started is not None
    ):

        wait_min = int(
            (
                started - creation
            ).total_seconds() // 60
        )

    elif (
        creation is not None
        and started is None
    ):

        wait_min = int(
            (
                now - creation
            ).total_seconds() // 60
        )

    # --------------------------------------------------------
    # Обработка
    # --------------------------------------------------------

    processing_min = 0

    if (
        started is not None
        and ready is not None
    ):

        processing_min = int(
            (
                ready - started
            ).total_seconds() // 60
        )

    elif (
        started is not None
        and ready is None
    ):

        processing_min = int(
            (
                now - started
            ).total_seconds() // 60
        )

    # --------------------------------------------------------
    # Ожидание отгрузки
    # --------------------------------------------------------

    expedition_min = 0

    if (
        ready is not None
        and ship is not None
    ):

        expedition_min = int(
            (
                ship - ready
            ).total_seconds() // 60
        )

    elif (
        ready is not None
        and ship is None
    ):

        expedition_min = int(
            (
                now - ready
            ).total_seconds() // 60
        )

    # --------------------------------------------------------
    # Защита от отрицательных значений
    # --------------------------------------------------------

    wait_min = max(0, wait_min)
    processing_min = max(0, processing_min)
    expedition_min = max(0, expedition_min)
    total_min = max(0, total_min)

    return {
        "total_min": total_min,
        "wait_min": wait_min,
        "processing_min": processing_min,
        "expedition_min": expedition_min,
        "is_finished": is_finished
    }


# ============================================================
# ОБРАБОТКА СОБЫТИЙ
# ============================================================

def process_events(events):

    if not events:

        return None

    df = pd.DataFrame(events)

    df["event_time"] = pd.to_datetime(
        df["event_time"]
    )

    df = (
        df
        .sort_values("event_time")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Иконки
    # --------------------------------------------------------

    def resolve_icon(name, is_err):

        if (
            is_err
            or "ошибка" in str(name).lower()
        ):

            return "⚠️"

        value = str(name).lower()

        if "создан" in value:

            return "📝"

        elif "обработ" in value:

            return "▶️"

        elif "готова" in value:

            return "🚚"

        elif "отгруж" in value:

            return "📤"

        return "🔹"

    df["icon"] = df.apply(
        lambda row: resolve_icon(
            row["status_name"],
            row["is_error"]
        ),
        axis=1
    )

    return df


# ============================================================
# СОСТОЯНИЕ ПОИСКА
# ============================================================

if "timeline_order" not in st.session_state:

    st.session_state.timeline_order = ""


if "timeline_order_input" not in st.session_state:

    st.session_state.timeline_order_input = ""


if "timeline_search_results" not in st.session_state:

    st.session_state.timeline_search_results = []


# ============================================================
# ВКЛАДКИ
# ============================================================

tab_timeline, tab_stuck = st.tabs(
    [
        "🕐 Timeline заявки",
        "🔴 Зависшие заявки"
    ]
)


# ============================================================
# ВКЛАДКА — TIMELINE
# ============================================================

with tab_timeline:

    # ========================================================
    # ПОИСК ЗАЯВКИ
    # ========================================================

    with st.form("timeline_search"):

        col_in, col_btn = st.columns([3, 1])

        with col_in:

            order_number = st.text_input(
                "Номер заявки:",
                placeholder=(
                    "Введите номер заявки "
                    "или его часть"
                ),
                key="timeline_order_input"
            )

        with col_btn:

            st.markdown(
                "<div style='height: 28px;'></div>",
                unsafe_allow_html=True
            )

            search_clicked = st.form_submit_button(
                "Найти",
                type="primary",
                use_container_width=True
            )

    # ========================================================
    # ОБРАБОТКА ПОИСКА
    # ========================================================

    if search_clicked:

        entered_order = (
            st.session_state.timeline_order_input
            .strip()
        )

        normalized_order = normalize_order_number(
            entered_order
        )

        # ----------------------------------------------------
        # Пустой запрос
        # ----------------------------------------------------

        if not normalized_order:

            st.warning(
                "Введите номер заявки."
            )

            st.stop()

        # ----------------------------------------------------
        # Минимальная длина
        # ----------------------------------------------------

        if len(normalized_order) < 4:

            st.warning(
                "Для поиска введите минимум 4 символа."
            )

            st.stop()

        # ----------------------------------------------------
        # Новый поиск
        # ----------------------------------------------------

        st.session_state.timeline_order = ""

        results = search_orders(
            entered_order
        )

        st.session_state.timeline_search_results = (
            results
        )

    # ========================================================
    # РЕЗУЛЬТАТЫ ПОИСКА
    # ========================================================

    search_results = (
        st.session_state.timeline_search_results
    )

    # ========================================================
    # РОВНО ОДНА ЗАЯВКА
    # ========================================================

    if len(search_results) == 1:

        st.session_state.timeline_order = (
            search_results[0]["purchasenumber"]
        )

    # ========================================================
    # НЕСКОЛЬКО ЗАЯВОК
    # ========================================================

    elif len(search_results) > 1:

        st.info(
            f"🔎 По вашему запросу найдено "
            f"{len(search_results)} заявок. "
            f"Выберите нужную заявку:"
        )

        order_options = [
            row["purchasenumber"]
            for row in search_results
        ]

        selected_order = st.selectbox(
            "Найденные заявки:",
            order_options,
            key="timeline_selected_order"
        )

        if st.button(
            "📋 Открыть заявку",
            type="primary",
            use_container_width=False
        ):

            st.session_state.timeline_order = (
                selected_order
            )

            st.rerun()

    # ========================================================
    # НИЧЕГО НЕ НАЙДЕНО
    # ========================================================

    elif (
        search_results == []
        and search_clicked
    ):

        st.warning(
            f"По запросу "
            f"«{st.session_state.timeline_order_input}» "
            f"заявки не найдены."
        )

    # ========================================================
    # ТЕКУЩАЯ ЗАЯВКА
    # ========================================================

    current_order = (
        st.session_state.timeline_order
    )

    # ========================================================
    # ЗАГРУЗКА ЗАЯВКИ
    # ========================================================

    if current_order:

        order_data = get_order_timeline(
            current_order
        )

        # ----------------------------------------------------
        # Заявка не найдена
        # ----------------------------------------------------

        if order_data is None:

            st.warning(
                f"Заявка '{current_order}' "
                f"не найдена в базе данных."
            )

            st.stop()

        # ----------------------------------------------------
        # Формируем события
        # ----------------------------------------------------

        raw_events = build_events(
            order_data
        )

        if not raw_events:

            st.warning(
                f"Для заявки '{current_order}' "
                f"не найдено ни одного события Timeline."
            )

            st.stop()

        df_events = process_events(
            raw_events
        )

        # ----------------------------------------------------
        # Расчёт времени
        # ----------------------------------------------------

        metrics = calculate_metrics(
            order_data
        )

        # ====================================================
        # ОСНОВНОЙ БЛОК
        # ====================================================

        st.markdown("---")

        left_col, right_col = st.columns(
            [3, 3],
            gap="large"
        )

        # ====================================================
        # ЛЕВАЯ КОЛОНКА — TIMELINE
        # ====================================================

        with left_col:

            st.subheader(
                f"Заявка: `{current_order}`"
            )

            timeline_html = """
            <div style="
                border-left: 2px solid #cbd5e1;
                padding-left: 20px;
                margin-left: 10px;
                margin-top: 15px;
            ">
            """

            for _, row in df_events.iterrows():

                # --------------------------------------------
                # Дата + время
                # --------------------------------------------

                date_time_str = row[
                    "event_time"
                ].strftime(
                    "%d.%m.%Y %H:%M"
                )

                status_text = row[
                    "status_name"
                ]

                icon = row[
                    "icon"
                ]

                is_err = row[
                    "is_error"
                ]

                # --------------------------------------------
                # Цвет точки
                # --------------------------------------------

                if is_err:

                    circle_color = "#ef4444"

                    shadow_color = (
                        "rgba(239, 68, 68, 0.2)"
                    )

                else:

                    circle_color = "#3b82f6"

                    shadow_color = (
                        "rgba(59, 130, 246, 0.2)"
                    )

                # --------------------------------------------
                # HTML Timeline
                # --------------------------------------------

                timeline_html += f"""
                <div style="
                    position: relative;
                    margin-bottom: 24px;
                ">

                    <span style="
                        position: absolute;
                        left: -28px;
                        top: 3px;
                        width: 14px;
                        height: 14px;
                        border-radius: 50%;
                        background-color: {circle_color};
                        border: 2px solid white;
                        box-shadow:
                            0 0 0 3px {shadow_color};
                    "></span>

                    <span style="
                        font-family: monospace;
                        font-size: 14px;
                        color: #64748b;
                        font-weight: 600;
                        margin-right: 8px;
                    ">
                        {date_time_str}
                    </span>

                    <span style="
                        font-size: 16px;
                        margin-right: 6px;
                    ">
                        {icon}
                    </span>

                    <span style="
                        font-size: 15px;
                        font-weight: 600;
                    ">
                        {status_text}
                    </span>

                </div>
                """

            timeline_html += "</div>"

            st.html(
                timeline_html
            )

        # ====================================================
        # ПРАВАЯ КОЛОНКА — АНАЛИЗ ВРЕМЕНИ
        # ====================================================

        with right_col:

            st.subheader(
                "📊 Анализ времени"
            )

            # ------------------------------------------------
            # Текущее состояние
            # ------------------------------------------------

            if not metrics["is_finished"]:

                last_event = df_events.iloc[-1][
                    "status_name"
                ]

                st.info(
                    f"ℹ️ Заявка ещё не отгружена. "
                    f"Текущее состояние: **{last_event}**. "
                    f"Время продолжает рассчитываться."
                )

            else:

                st.success(
                    "✅ Заявка отгружена."
                )

            # ------------------------------------------------
            # Общее время
            # ------------------------------------------------

            st.metric(
                label="⏱ Общее время",
                value=format_duration(
                    metrics["total_min"]
                )
            )

            # ------------------------------------------------
            # Детальные показатели
            # ------------------------------------------------

            m1, m2 = st.columns(2)

            with m1:

                st.metric(
                    label="⏳ Ожидание запуска",
                    value=format_duration(
                        metrics["wait_min"]
                    )
                )

                st.metric(
                    label="👷 Обработка",
                    value=format_duration(
                        metrics["processing_min"]
                    )
                )

            with m2:

                st.metric(
                    label="🚚 Ожидание отгрузки",
                    value=format_duration(
                        metrics["expedition_min"]
                    ),
                    delta=(
                        f"{metrics['expedition_min']} мин"
                        if metrics["expedition_min"] > 10
                        else None
                    ),
                    delta_color="inverse"
                )


# ============================================================
# ВКЛАДКА — ЗАВИСШИЕ ЗАЯВКИ
# ============================================================

with tab_stuck:

    st.caption(
        "Заявки, которые находятся на текущем этапе "
        "дольше установленного порога."
    )

    # ========================================================
    # ПОРОГИ
    # ========================================================

    threshold_col1, threshold_col2, threshold_col3 = (
        st.columns(3)
    )

    with threshold_col1:

        st.metric(
            "⏳ Ожидание запуска",
            "20 мин"
        )

    with threshold_col2:

        st.metric(
            "👷 Обработка",
            "180 мин"
        )

    with threshold_col3:

        st.metric(
            "🚚 Ожидание отгрузки",
            "60 мин"
        )

    st.markdown("---")

    # ========================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # ========================================================

    stuck_orders = get_stuck_orders()

    # ========================================================
    # НЕТ ЗАВИСШИХ
    # ========================================================

    if not stuck_orders:

        st.success(
            "✅ Зависших заявок не найдено."
        )

    else:

        # ====================================================
        # ПРЕОБРАЗУЕМ В DATAFRAME
        # ====================================================

        df_stuck = pd.DataFrame(
            stuck_orders
        )

        # ====================================================
        # ИКОНКИ ЭТАПОВ
        # ====================================================

        def stage_display(stage):

            if stage == "Ожидание запуска":

                return "⏳ Ожидание запуска"

            if stage == "Обработка":

                return "👷 Обработка"

            if stage == "Ожидание отгрузки":

                return "🚚 Ожидание отгрузки"

            return stage

        df_stuck["stage_display"] = (
            df_stuck["stuck_stage"]
            .apply(stage_display)
        )

        # ====================================================
        # ФОРМАТИРОВАНИЕ ВРЕМЕНИ
        # ====================================================

        df_stuck["stuck_duration"] = (
            df_stuck["stuck_minutes"]
            .apply(format_duration)
        )

        # ====================================================
        # ФОРМАТИРОВАНИЕ ДАТЫ
        # ====================================================

        df_stuck["stage_started"] = None

        for index, row in df_stuck.iterrows():

            if (
                row["stuck_stage"]
                == "Ожидание запуска"
            ):

                value = row["creationdate"]

            elif (
                row["stuck_stage"]
                == "Обработка"
            ):

                value = row["starteddate"]

            elif (
                row["stuck_stage"]
                == "Ожидание отгрузки"
            ):

                value = row["readydate"]

            else:

                value = None

            if value is not None:

                value = pd.to_datetime(
                    value
                ).strftime(
                    "%d.%m.%Y %H:%M"
                )

            df_stuck.loc[
                index,
                "stage_started"
            ] = value

        # ====================================================
        # СЧЁТЧИКИ
        # ====================================================

        count_wait = len(
            df_stuck[
                df_stuck["stuck_stage"]
                == "Ожидание запуска"
            ]
        )

        count_processing = len(
            df_stuck[
                df_stuck["stuck_stage"]
                == "Обработка"
            ]
        )

        count_expedition = len(
            df_stuck[
                df_stuck["stuck_stage"]
                == "Ожидание отгрузки"
            ]
        )

        # ====================================================
        # КАРТОЧКИ
        # ====================================================

        count_col1, count_col2, count_col3, count_col4 = (
            st.columns(4)
        )

        with count_col1:

            st.metric(
                "🔴 Всего зависших",
                len(df_stuck)
            )

        with count_col2:

            st.metric(
                "⏳ Ожидание запуска",
                count_wait
            )

        with count_col3:

            st.metric(
                "👷 Обработка",
                count_processing
            )

        with count_col4:

            st.metric(
                "🚚 Ожидание отгрузки",
                count_expedition
            )

        st.markdown("---")

        # ====================================================
        # ТАБЛИЦА
        # ====================================================

        display_df = df_stuck[
            [
                "purchasenumber",
                "stage_display",
                "stage_started",
                "stuck_duration",
                "deliverystatus"
            ]
        ].copy()

        display_df.columns = [
            "Номер заявки",
            "Этап",
            "На этапе с",
            "Время зависания",
            "Статус"
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Номер заявки": st.column_config.TextColumn(
                    "Номер заявки",
                    width="medium"
                ),
                "Этап": st.column_config.TextColumn(
                    "Этап",
                    width="medium"
                ),
                "На этапе с": st.column_config.TextColumn(
                    "На этапе с",
                    width="medium"
                ),
                "Время зависания": st.column_config.TextColumn(
                    "Время зависания",
                    width="medium"
                ),
                "Статус": st.column_config.TextColumn(
                    "Статус",
                    width="small"
                )
            }
        )

        # ====================================================
        # ПОДСКАЗКА
        # ====================================================

        st.caption(
            "💡 Нажмите на номер заявки в списке поиска "
            "на вкладке «🕐 Timeline заявки», чтобы "
            "посмотреть подробную хронологию."
        )