import os
from pathlib import Path
from datetime import date
from io import BytesIO

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
    page_title="Честный знак",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

st.title("🏷️ Честный знак")

st.caption(
    "Контроль маркировки и операций с кодами "
    "системы «Честный знак»"
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
# ПРИНЯТЫЕ МАРКИ
# ============================================================

@st.cache_data(ttl=60)
def get_accepted_marks(date_from, date_to):

    query = """
    SELECT
        so.barcode AS "Номер ОС",
        s.cis_code AS "КИ",
        pc.cis_code AS "КИТУ",
        s.receiptdate::date AS "Дата приемки"

    FROM cis.stock AS s

    JOIN storageobjects AS so
        ON s.storageobject_id = so.tid

    JOIN cis.stock AS pc
        ON s.parentcis_id::text = pc.cis_id::text

    WHERE
        s.receiptdate::date
        BETWEEN (%s)::DATE AND (%s)::DATE

    ORDER BY
        s.receiptdate;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    query,
                    (
                        date_from,
                        date_to
                    )
                )

                results = cur.fetchall()

                return pd.DataFrame(results)

    except Exception as e:

        st.error(
            f"Ошибка выполнения SQL-запроса: {e}"
        )

        return pd.DataFrame()


# ============================================================
# ПОИСК ОС ПО ЧАСТИ НОМЕРА
# ============================================================

@st.cache_data(ttl=60)
def search_os(search_value):

    search_value = str(
        search_value or ""
    ).strip()

    if not search_value:
        return []

    query = """
    SELECT DISTINCT
        so.barcode AS barcode

    FROM cis.stock AS s

    JOIN storageobjects AS so
        ON s.storageobject_id = so.tid

    WHERE
        so.barcode ILIKE %s

    ORDER BY
        so.barcode

    LIMIT 50;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    query,
                    (
                        f"%{search_value}%",
                    )
                )

                results = cur.fetchall()

                return [
                    row["barcode"]
                    for row in results
                ]

    except Exception as e:

        st.error(
            f"Ошибка поиска ОС: {e}"
        )

        return []


# ============================================================
# МАРКИ ПО КОНКРЕТНОЙ ОС
# ============================================================

@st.cache_data(ttl=60)
def get_marks_by_os(os_number):

    query = """
    SELECT DISTINCT
        l.locationname AS "Место",
        so.barcode AS "Номер ОС",
        m.nameen AS "Артикул",
        m.nameru AS "Наименование",
        st.nameru AS "Вид запаса",
        s.cis_code AS "КИ",
        pc.cis_code AS "КИТУ",
        s.receiptdate::date AS "Дата приемки",
        hw.documentnumber AS "Входящая поставка"

    FROM cis.stock AS s

    JOIN storageobjects AS so
        ON s.storageobject_id = so.tid

    JOIN cis.stock AS pc
        ON s.parentcis_id::text = pc.cis_id::text

    JOIN warehousesummary AS w
        ON so.tid = w.storageobject_id

    JOIN materials AS m
        ON w.material_id = m.tid

    JOIN stocktypes AS st
        ON w.stocktype_id = st.tid

    JOIN locations AS l
        ON so.location_id = l.tid

    LEFT JOIN tbl_warehouseincomeobjects AS tw
        ON so.tid = tw.storageobject_id

    LEFT JOIN hdr_warehouseincome AS hw
        ON tw.transaction_id = hw.transaction_id

    WHERE
        m.isam = '1'
        AND s.barcodeobject_id = w.barcodeobject_id
        AND so.barcode = %s

    ORDER BY
        m.nameen;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(
                    query,
                    (
                        os_number.strip(),
                    )
                )

                results = cur.fetchall()

                return pd.DataFrame(results)

    except Exception as e:

        st.error(
            f"Ошибка получения марок: {e}"
        )

        return pd.DataFrame()


# ============================================================
# ВСЕ ОС С МАРКАМИ
# ============================================================

@st.cache_data(ttl=60)
def get_all_os():

    query = """
    SELECT
        l.locationname AS "Место",
        so.barcode AS "Номер ОС",
        m.nameen AS "Артикул",
        m.nameru AS "Наименование",
        st.nameru AS "Вид запаса",
        COALESCE(s.cnt_km, 0) AS "Количество КМ",
        COALESCE(s.cnt_kitu, 0) AS "Количество КИТУ",
        SUM(w.basequantity) AS "Количество штук",
        hw.documentnumber AS "Входящая поставка"

    FROM storageobjects AS so

    JOIN warehousesummary AS w
        ON so.tid = w.storageobject_id
        AND w.basequantity > 0

    JOIN materials AS m
        ON w.material_id = m.tid
        AND m.isam = '1'

    JOIN stocktypes AS st
        ON w.stocktype_id = st.tid

    JOIN locations AS l
        ON so.location_id = l.tid

    JOIN (
        SELECT
            storageobject_id,
            barcodeobject_id,
            COUNT(DISTINCT cis_code) AS cnt_km,
            COUNT(DISTINCT parentcis_id) AS cnt_kitu
        FROM cis.stock
        WHERE parentcis_id IS NOT NULL
        GROUP BY
            storageobject_id,
            barcodeobject_id
    ) AS s
        ON s.storageobject_id = so.tid
        AND s.barcodeobject_id = w.barcodeobject_id

    LEFT JOIN tbl_warehouseincomeobjects AS tw
        ON so.tid = tw.storageobject_id

    LEFT JOIN hdr_warehouseincome AS hw
        ON tw.transaction_id = hw.transaction_id

    GROUP BY
        l.locationname,
        so.barcode,
        m.nameen,
        m.nameru,
        st.nameru,
        s.cnt_km,
        s.cnt_kitu,
        hw.documentnumber

    ORDER BY
        so.barcode;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(query)

                results = cur.fetchall()

                return pd.DataFrame(results)

    except Exception as e:

        st.error(
            f"Ошибка получения всех ОС: {e}"
        )

        return pd.DataFrame()


# ============================================================
# ВСЕ ОС С ЧЕСТНЫМ ЗНАКОМ
# ============================================================

@st.cache_data(ttl=60)
def get_all_os_with_chz():

    query = """
    SELECT
        l.locationname AS "Место",
        so.barcode AS "Номер ОС",
        m.nameen AS "Артикул",
        m.nameru AS "Наименование",
        st.nameru AS "Вид запаса",

        COALESCE(s.cnt_km, 0) AS "Количество КМ",
        COALESCE(s.cnt_kitu, 0) AS "Количество КИТУ",

        SUM(w.basequantity) AS "Количество штук",

        hw.documentnumber AS "Входящая поставка"

    FROM storageobjects AS so

    JOIN warehousesummary AS w
        ON so.tid = w.storageobject_id
        AND w.basequantity > 0

    JOIN materials AS m
        ON w.material_id = m.tid
        AND m.isam = '1'

    JOIN stocktypes AS st
        ON w.stocktype_id = st.tid

    JOIN locations AS l
        ON so.location_id = l.tid

    LEFT JOIN (
        SELECT
            storageobject_id,
            barcodeobject_id,
            COUNT(DISTINCT cis_code) AS cnt_km,
            COUNT(DISTINCT parentcis_id) AS cnt_kitu
        FROM cis.stock
        WHERE parentcis_id IS NOT NULL
        GROUP BY
            storageobject_id,
            barcodeobject_id
    ) AS s
        ON s.storageobject_id = so.tid
        AND s.barcodeobject_id = w.barcodeobject_id

    LEFT JOIN tbl_warehouseincomeobjects AS tw
        ON so.tid = tw.storageobject_id

    LEFT JOIN hdr_warehouseincome AS hw
        ON tw.transaction_id = hw.transaction_id

    GROUP BY
        l.locationname,
        so.barcode,
        m.nameen,
        m.nameru,
        st.nameru,
        s.cnt_km,
        s.cnt_kitu,
        hw.documentnumber

    ORDER BY
        so.barcode;
    """

    try:

        with get_db_connection() as conn:

            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:

                cur.execute(query)

                results = cur.fetchall()

                return pd.DataFrame(results)

    except Exception as e:

        st.error(
            f"Ошибка получения всех ОС с ЧЗ: {e}"
        )

        return pd.DataFrame()


# ============================================================
# EXCEL
# ============================================================

def dataframe_to_excel(
    df,
    sheet_name
):

    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name
        )

    excel_buffer.seek(0)

    return excel_buffer.getvalue()


# ============================================================
# ПОИСК ПО ТАБЛИЦЕ
# ============================================================

def filter_dataframe(
    df,
    key,
    sheet_name
):

    # --------------------------------------------------------
    # СОСТОЯНИЕ ПОИСКА
    # --------------------------------------------------------

    if f"{key}_applied" not in st.session_state:

        st.session_state[
            f"{key}_applied"
        ] = ""

    # --------------------------------------------------------
    # ПРИМЕНИТЬ ПОИСК
    # --------------------------------------------------------

    def apply_search():

        st.session_state[
            f"{key}_applied"
        ] = st.session_state.get(
            key,
            ""
        )

    # --------------------------------------------------------
    # ОЧИСТИТЬ ПОИСК
    # --------------------------------------------------------

    def clear_search():

        st.session_state[key] = ""

        st.session_state[
            f"{key}_applied"
        ] = ""

    # ========================================================
    # СТРОКА: ПОИСК + НАЙТИ + ОЧИСТИТЬ + СКАЧАТЬ
    # ========================================================

    col1, col2, col3, col4 = st.columns(
        [6, 1.2, 1.2, 1.2]
    )

    # --------------------------------------------------------
    # ПОЛЕ ПОИСКА
    # --------------------------------------------------------

    with col1:

        st.text_input(
            label="",
            key=key,
            placeholder="Введите значение для поиска...",
            on_change=apply_search
        )

    # --------------------------------------------------------
    # КНОПКА НАЙТИ
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
    # КНОПКА ОЧИСТИТЬ
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

    # ========================================================
    # ФИЛЬТРАЦИЯ
    # ========================================================

    df_filtered = df

    search_text = st.session_state[
        f"{key}_applied"
    ]

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

    # ========================================================
    # EXCEL
    # ========================================================

    excel_data = dataframe_to_excel(
        df_filtered,
        sheet_name
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
            file_name="chestny_znak_all_os.xlsx",
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
# СОСТОЯНИЕ
# ============================================================

if "chz_date_from" not in st.session_state:

    st.session_state.chz_date_from = date.today()


if "chz_date_to" not in st.session_state:

    st.session_state.chz_date_to = date.today()


if "chz_data" not in st.session_state:

    st.session_state.chz_data = pd.DataFrame()


if "chz_data_loaded" not in st.session_state:

    st.session_state.chz_data_loaded = False


# ------------------------------------------------------------
# Поиск ОС
# ------------------------------------------------------------

if "chz_os_search_results" not in st.session_state:

    st.session_state.chz_os_search_results = []


if "chz_selected_os" not in st.session_state:

    st.session_state.chz_selected_os = ""


if "chz_os_data" not in st.session_state:

    st.session_state.chz_os_data = pd.DataFrame()


if "chz_os_data_loaded" not in st.session_state:

    st.session_state.chz_os_data_loaded = False


# ------------------------------------------------------------
# Все ОС
# ------------------------------------------------------------

if "chz_all_os_data" not in st.session_state:

    st.session_state.chz_all_os_data = pd.DataFrame()


if "chz_all_os_data_loaded" not in st.session_state:

    st.session_state.chz_all_os_data_loaded = False


# ------------------------------------------------------------
# Все ОС с ЧЗ
# ------------------------------------------------------------

if "chz_all_os_chz_data" not in st.session_state:

    st.session_state.chz_all_os_chz_data = pd.DataFrame()


if "chz_all_os_chz_data_loaded" not in st.session_state:

    st.session_state.chz_all_os_chz_data_loaded = False


# ============================================================
# ВКЛАДКИ
# ============================================================

tab_accepted, tab_search_os, tab_all_os, tab_all_os_chz, tab_problems = st.tabs(
    [
        "🏷️ Принятые марки",
        "🔎 Подробная информация по ОС",
        "📦 Все ОС с марками",
        "📦 Все ОС с маркировкой",
        "⚠️ Проблемы"
    ]
)


# ============================================================
# ВКЛАДКА — ПРИНЯТЫЕ МАРКИ
# ============================================================

with tab_accepted:

    st.caption(
        "Марки, принятые на склад за выбранный период."
    )

    # ========================================================
    # ПАРАМЕТРЫ И КНОПКИ
    # ========================================================

    col_from, col_to, col_search, col_download = (
        st.columns(
            [2, 2, 1, 1],
            gap="small"
        )
    )

    with col_from:

        date_from = st.date_input(
            "Дата с",
            value=st.session_state.chz_date_from,
            format="DD.MM.YYYY",
            key="chz_date_from_widget"
        )

    with col_to:

        date_to = st.date_input(
            "Дата по",
            value=st.session_state.chz_date_to,
            format="DD.MM.YYYY",
            key="chz_date_to_widget"
        )

    with col_search:

        st.markdown(
            """
            <div style="height: 28px;"></div>
            """,
            unsafe_allow_html=True
        )

        search_accepted_clicked = st.button(
            "🔎 Найти",
            key="chz_accepted_search",
            type="primary",
            use_container_width=True
        )

    # ========================================================
    # НАЙТИ
    # ========================================================

    if search_accepted_clicked:

        if date_from > date_to:

            st.error(
                "Дата начала периода не может быть "
                "позже даты окончания."
            )

        else:

            st.session_state.chz_date_from = date_from
            st.session_state.chz_date_to = date_to

            with st.spinner(
                "Получение данных..."
            ):

                data = get_accepted_marks(
                    date_from.strftime("%Y-%m-%d"),
                    date_to.strftime("%Y-%m-%d")
                )

            st.session_state.chz_data = data
            st.session_state.chz_data_loaded = True

    # ========================================================
    # ДАННЫЕ
    # ========================================================

    df = st.session_state.chz_data

    if st.session_state.chz_data_loaded:

        if df.empty:

            st.info(
                "За выбранный период "
                "принятых марок не найдено."
            )

        else:

            st.markdown("---")

            # =================================================
            # СЧЁТЧИКИ
            # =================================================

            count_col1, count_col2, count_col3 = st.columns(
                3
            )

            with count_col1:

                st.metric(
                    "📦 Всего ОС",
                    f"{df['Номер ОС'].nunique():,}".replace(
                        ",",
                        " "
                    )
                )

            with count_col2:

                st.metric(
                    "🏷️ Уникальных КИ",
                    f"{df['КИ'].nunique():,}".replace(
                        ",",
                        " "
                    )
                )

            with count_col3:

                st.metric(
                    "🏷️ Уникальных КИТУ",
                    f"{df['КИТУ'].nunique():,}".replace(
                        ",",
                        " "
                    )
                )

            st.markdown("---")

            # =================================================
            # ТАБЛИЦА
            # =================================================

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={

                    "Номер ОС": st.column_config.TextColumn(
                        "Номер ОС"
                    ),

                    "КИ": st.column_config.TextColumn(
                        "КИ"
                    ),

                    "КИТУ": st.column_config.TextColumn(
                        "КИТУ"
                    ),

                    "Дата приемки": st.column_config.DateColumn(
                        "Дата приемки",
                        format="DD.MM.YYYY"
                    )
                }
            )

            # =================================================
            # СКАЧАТЬ
            # =================================================

            excel_data = dataframe_to_excel(
                df,
                "Принятые марки"
            )

            with col_download:

                st.markdown(
                    """
                    <div style="height: 28px;"></div>
                    """,
                    unsafe_allow_html=True
                )

                st.download_button(
                    "⇩ Скачать",
                    data=excel_data,
                    file_name=(
                        "chestny_znak_"
                        f"{st.session_state.chz_date_from}_"
                        f"{st.session_state.chz_date_to}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
                    key="chz_accepted_download",
                    use_container_width=True
                )


# ============================================================
# ВКЛАДКА — ПОДРОБНАЯ ИНФОРМАЦИЯ ПО ОС
# ============================================================

with tab_search_os:

    st.caption(
        "Поиск по части номера ОС."
    )

    # ========================================================
    # ПОЛЕ ПОИСКА
    # ========================================================

    col_input, col_search, col_download = (
        st.columns(
            [5, 1, 1],
            gap="small"
        )
    )

    with col_input:

        os_input = st.text_input(
            "Номер ОС:",
            placeholder=(
                "Введите номер ОС или его часть"
            ),
            key="chz_os_input"
        )

    with col_search:

        st.markdown(
            """
            <div style="height: 28px;"></div>
            """,
            unsafe_allow_html=True
        )

        search_os_clicked = st.button(
            "🔎 Найти",
            key="chz_os_search",
            type="primary",
            use_container_width=True
        )

    # ========================================================
    # НАЙТИ
    # ========================================================

    if search_os_clicked:

        entered_os = os_input.strip()

        if not entered_os:

            st.warning(
                "Введите номер ОС."
            )

        else:

            with st.spinner(
                "Поиск ОС..."
            ):

                results = search_os(
                    entered_os
                )

            st.session_state.chz_os_search_results = (
                results
            )

            st.session_state.chz_selected_os = ""

            st.session_state.chz_os_data = (
                pd.DataFrame()
            )

            st.session_state.chz_os_data_loaded = False

    # ========================================================
    # РЕЗУЛЬТАТЫ ПОИСКА
    # ========================================================

    os_results = (
        st.session_state.chz_os_search_results
    )

    # ========================================================
    # НИЧЕГО НЕ НАЙДЕНО
    # ========================================================

    if (
        os_results == []
        and search_os_clicked
        and os_input.strip()
    ):

        st.warning(
            f"ОС по запросу "
            f"«{os_input}» "
            f"не найдены."
        )

    # ========================================================
    # НАЙДЕНА ОДНА ОС
    # ========================================================

    elif len(os_results) == 1:

        st.session_state.chz_selected_os = (
            os_results[0]
        )

    # ========================================================
    # НАЙДЕНО НЕСКОЛЬКО ОС
    # ========================================================

    elif len(os_results) > 1:

        st.info(
            f"🔎 По вашему запросу найдено "
            f"{len(os_results)} ОС. "
            f"Выберите нужную:"
        )

        selected_os = st.selectbox(
            "Найденные ОС:",
            os_results,
            key="chz_os_select"
        )

        if st.button(
            "📋 Открыть ОС",
            key="chz_open_os",
            type="primary"
        ):

            st.session_state.chz_selected_os = (
                selected_os
            )

            st.rerun()

    # ========================================================
    # ТЕКУЩАЯ ОС
    # ========================================================

    current_os = (
        st.session_state.chz_selected_os
    )

    # ========================================================
    # ПОЛУЧЕНИЕ МАРОК
    # ========================================================

    if current_os:

        if not st.session_state.chz_os_data_loaded:

            with st.spinner(
                "Получение марок..."
            ):

                df_os = get_marks_by_os(
                    current_os
                )

            st.session_state.chz_os_data = df_os
            st.session_state.chz_os_data_loaded = True

    # ========================================================
    # ВЫВОД РЕЗУЛЬТАТА
    # ========================================================

    if st.session_state.chz_os_data_loaded:

        df_os = st.session_state.chz_os_data

        if df_os.empty:

            st.warning(
                f"Для ОС "
                f"«{current_os}» "
                f"марки не найдены."
            )

        else:

            st.markdown("---")

            # =================================================
            # СЧЁТЧИКИ
            # =================================================

            info_col1, info_col2, info_col3 = st.columns(
                3
            )

            with info_col1:

                st.metric(
                    "📦 Номер ОС",
                    current_os
                )

            with info_col2:

                st.metric(
                    "🏷️ Количество КИ",
                    f"{len(df_os):,}".replace(
                        ",",
                        " "
                    )
                )

            with info_col3:

                st.metric(
                    "🏷️ Уникальных КИТУ",
                    f"{df_os['КИТУ'].nunique():,}".replace(
                        ",",
                        " "
                    )
                )

            st.markdown("---")

            # =================================================
            # ТАБЛИЦА
            # =================================================

            st.dataframe(
                df_os,
                use_container_width=True,
                hide_index=True,
                column_config={

                    "Место": st.column_config.TextColumn(
                        "Место"
                    ),

                    "Номер ОС": st.column_config.TextColumn(
                        "Номер ОС"
                    ),

                    "Артикул": st.column_config.TextColumn(
                        "Артикул"
                    ),

                    "Наименование": st.column_config.TextColumn(
                        "Наименование"
                    ),

                    "Вид запаса": st.column_config.TextColumn(
                        "Вид запаса"
                    ),

                    "КИ": st.column_config.TextColumn(
                        "КИ"
                    ),

                    "КИТУ": st.column_config.TextColumn(
                        "КИТУ"
                    ),

                    "Дата приемки": st.column_config.DateColumn(
                        "Дата приемки",
                        format="DD.MM.YYYY"
                    ),

                    "Входящая поставка": st.column_config.TextColumn(
                        "Входящая поставка"
                    )

                }
            )

            # =================================================
            # СКАЧАТЬ
            # =================================================

            excel_data = dataframe_to_excel(
                df_os,
                "Марки по ОС"
            )

            with col_download:

                st.markdown(
                    """
                    <div style="height: 28px;"></div>
                    """,
                    unsafe_allow_html=True
                )

                st.download_button(
                    "⇩ Скачать",
                    data=excel_data,
                    file_name=(
                        f"marks_{current_os}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
                    key="chz_os_download",
                    use_container_width=True
                )


# ============================================================
# ВКЛАДКА — ВСЕ ОС
# ============================================================

with tab_all_os:

    st.caption(
        "Все ОС с маркированной продукцией."
    )

    # ========================================================
    # ЗАГРУЗКА ДАННЫХ
    # ========================================================

    col_load_all = st.columns(
        [1]
    )[0]

    with col_load_all:

        load_all_os_clicked = st.button(
            "🔎 Загрузить данные",
            key="chz_all_os_search",
            type="primary",
            use_container_width=True
        )

    # ========================================================
    # ЗАГРУЗКА
    # ========================================================

    if load_all_os_clicked:

        with st.spinner(
            "Получение всех ОС..."
        ):

            df_all_os = get_all_os()

        st.session_state.chz_all_os_data = df_all_os
        st.session_state.chz_all_os_data_loaded = True

        # После новой загрузки очищаем предыдущий поиск
        st.session_state.chz_all_os_search_input = ""
        st.session_state.chz_all_os_search_input_applied = ""

    # ========================================================
    # ВЫВОД ДАННЫХ
    # ========================================================

    if st.session_state.chz_all_os_data_loaded:

        df_all_os = st.session_state.chz_all_os_data

        if df_all_os.empty:

            st.info(
                "Маркированных ОС не найдено."
            )

        else:

            # =================================================
            # ПОИСК + ОЧИСТКА + СКАЧИВАНИЕ
            # =================================================

            df_display_all_os = filter_dataframe(
                df_all_os,
                "chz_all_os_search_input",
                "Все ОС"
            )

            st.markdown("---")

            # =================================================
            # СЧЁТЧИКИ
            # =================================================

            count_all_col1, count_all_col2, count_all_col3 = (
                st.columns(3)
            )

            with count_all_col1:

                st.metric(
                    "📦 Всего ОС",
                    f"{df_all_os['Номер ОС'].nunique():,}".replace(
                        ",",
                        " "
                    )
                )

            with count_all_col2:

                st.metric(
                    "🏷️ Всего КМ",
                    f"{df_all_os['Количество КМ'].sum():,}".replace(
                        ",",
                        " "
                    )
                )

            with count_all_col3:

                st.metric(
                    "🏷️ Всего КИТУ",
                    f"{df_all_os['Количество КИТУ'].sum():,}".replace(
                        ",",
                        " "
                    )
                )

            # =================================================
            # РЕЗУЛЬТАТ ПОИСКА
            # =================================================

            if (
                st.session_state[
                    "chz_all_os_search_input_applied"
                ]
            ):

                st.caption(
                    f"🔎 Найдено строк: "
                    f"{len(df_display_all_os):,}".replace(
                        ",",
                        " "
                    )
                )

            st.markdown("---")

            # =================================================
            # ТАБЛИЦА
            # =================================================

            st.dataframe(
                df_display_all_os,
                use_container_width=True,
                hide_index=True,
                column_config={

                    "Место": st.column_config.TextColumn(
                        "Место"
                    ),

                    "Номер ОС": st.column_config.TextColumn(
                        "Номер ОС"
                    ),

                    "Артикул": st.column_config.TextColumn(
                        "Артикул"
                    ),

                    "Наименование": st.column_config.TextColumn(
                        "Наименование"
                    ),

                    "Вид запаса": st.column_config.TextColumn(
                        "Вид запаса"
                    ),

                    "Количество КМ": st.column_config.NumberColumn(
                        "Количество КМ",
                        format="%d"
                    ),

                    "Количество КИТУ": st.column_config.NumberColumn(
                        "Количество КИТУ",
                        format="%d"
                    ),

                    "Количество штук": st.column_config.NumberColumn(
                        "Количество штук",
                        format="%d"
                    ),

                    "Входящая поставка": st.column_config.TextColumn(
                        "Входящая поставка"
                    )
                }
            )


# ============================================================
# ВКЛАДКА — ВСЕ ОС С МАРКИРОВАННЫМ ТОВАРОМ
# ============================================================

with tab_all_os_chz:

    st.caption(
        "Все ОС, содержащие маркированную продукцию "
        "«Честного знака»."
    )

    # ========================================================
    # ЗАГРУЗКА ДАННЫХ
    # ========================================================

    col_load_all_chz = st.columns(
        [1]
    )[0]

    with col_load_all_chz:

        load_all_os_chz_clicked = st.button(
            "🔎 Загрузить данные",
            key="chz_all_os_chz_search",
            type="primary",
            use_container_width=True
        )

    # ========================================================
    # ЗАГРУЗКА
    # ========================================================

    if load_all_os_chz_clicked:

        with st.spinner(
            "Получение всех ОС с ЧЗ..."
        ):

            df_all_os_chz = get_all_os_with_chz()

        st.session_state.chz_all_os_chz_data = (
            df_all_os_chz
        )

        st.session_state.chz_all_os_chz_data_loaded = True

        # После новой загрузки очищаем предыдущий поиск

        st.session_state.chz_all_os_chz_search_input = ""

        st.session_state.chz_all_os_chz_search_input_applied = ""

    # ========================================================
    # ВЫВОД ДАННЫХ
    # ========================================================

    if st.session_state.chz_all_os_chz_data_loaded:

        df_all_os_chz = (
            st.session_state.chz_all_os_chz_data
        )

        if df_all_os_chz.empty:

            st.info(
                "ОС с маркированной продукцией "
                "«Честного знака» не найдено."
            )

        else:

            # =================================================
            # ПОИСК + ОЧИСТКА + СКАЧИВАНИЕ
            # =================================================

            df_display_all_os_chz = filter_dataframe(
                df_all_os_chz,
                "chz_all_os_chz_search_input",
                "Все ОС с ЧЗ"
            )

            st.markdown("---")

            # =================================================
            # СЧЁТЧИКИ
            # =================================================

            # Все уникальные ОС
            total_os = df_all_os_chz["Номер ОС"].nunique()

            # ОС, у которых есть хотя бы одна маркированная позиция
            marked_os = (
                df_all_os_chz.loc[
                    pd.to_numeric(
                        df_all_os_chz["Количество КМ"],
                        errors="coerce"
                    ).fillna(0) > 0,
                    "Номер ОС"
                ]
                .nunique()
            )

            # Немаркированные ОС = все ОС минус маркированные
            unmarked_os = total_os - marked_os


            # =================================================
            # ОСТАЛОСЬ ПРОМАРКИРОВАТЬ ШТУК
            # =================================================

            total_pieces = (
                pd.to_numeric(
                    df_all_os_chz["Количество штук"],
                    errors="coerce"
                )
                .fillna(0)
                .sum()
            )

            total_km = (
                pd.to_numeric(
                    df_all_os_chz["Количество КМ"],
                    errors="coerce"
                )
                .fillna(0)
                .sum()
            )

            remaining_to_mark = round(total_pieces - total_km)


            # =================================================
            # ОТОБРАЖЕНИЕ СЧЁТЧИКОВ
            # =================================================

            count_chz_col1, count_chz_col2, count_chz_col3, count_chz_col4 = st.columns(4)

            with count_chz_col1:
                st.metric(
                    "📦 Всего ОС",
                    f"{total_os:,}".replace(",", " ")
                )

            with count_chz_col2:
                st.metric(
                    "🏷️ Маркированных ОС",
                    f"{marked_os:,}".replace(",", " ")
                )

            with count_chz_col3:
                st.metric(
                    "📦 Немаркированных ОС",
                    f"{unmarked_os:,}".replace(",", " ")
                )

            with count_chz_col4:
                st.metric(
                    "🔖 Осталось промаркировать штук",
                    f"{remaining_to_mark:,}".replace(",", " ")
                )

            # =================================================
            # РЕЗУЛЬТАТ ПОИСКА
            # =================================================

            if (
                st.session_state[
                    "chz_all_os_chz_search_input_applied"
                ]
            ):

                st.caption(
                    f"🔎 Найдено строк: "
                    f"{len(df_display_all_os_chz):,}".replace(
                        ",",
                        " "
                    )
                )

            st.markdown("---")

            # =================================================
            # ТАБЛИЦА
            # =================================================

            st.dataframe(
                df_display_all_os_chz,
                use_container_width=True,
                hide_index=True,
                column_config={

                    "Место": st.column_config.TextColumn(
                        "Место"
                    ),

                    "Номер ОС": st.column_config.TextColumn(
                        "Номер ОС"
                    ),

                    "Артикул": st.column_config.TextColumn(
                        "Артикул"
                    ),

                    "Наименование": st.column_config.TextColumn(
                        "Наименование"
                    ),

                    "Вид запаса": st.column_config.TextColumn(
                        "Вид запаса"
                    ),

                    "Количество КМ": st.column_config.NumberColumn(
                        "Количество КМ",
                        format="%d"
                    ),

                    "Количество КИТУ": st.column_config.NumberColumn(
                        "Количество КИТУ",
                        format="%d"
                    ),

                    "Количество штук": st.column_config.NumberColumn(
                        "Количество штук",
                        format="%d"
                    ),

                    "Входящая поставка": st.column_config.TextColumn(
                        "Входящая поставка"
                    )
                }
            )


# ============================================================
# ВКЛАДКА — ПРОБЛЕМЫ
# ============================================================

with tab_problems:

    st.caption(
        "Проблемы и ошибки, связанные с системой "
        "«Честный знак»."
    )

    st.info(
        "Раздел подготовлен для добавления "
        "контроля проблем «Честного знака»."
    )