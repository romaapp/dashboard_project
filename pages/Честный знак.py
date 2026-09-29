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
    select distinct l.locationname as "Место",
        so.barcode as "Номер ОС",
        m.nameen as "Артикул",
        m.nameru as "Наименование",
        st.nameru as "Вид запаса",
        s.cis_code as "КИ", 
        pc.cis_code as "КИТУ", 
        s.receiptdate::date as "Дата приемки",
        hw.documentnumber as "Входящая поставка"
    from cis.stock as s
        join storageobjects as so on
        s.storageobject_id = so.tid
        join cis.stock as pc on
        s.parentcis_id::text = pc.cis_id::text
        join warehousesummary as w on
        so.tid = w.storageobject_id
        join materials as m on
        w.material_id = m.tid
        join stocktypes as st on
        w.stocktype_id = st.tid
        join locations as l on
        so.location_id = l.tid
        left join tbl_warehouseincomeobjects as tw on
        so.tid = tw.storageobject_id
        left join hdr_warehouseincome as hw on
        tw.transaction_id = hw.transaction_id
    where m.isam = '1' 
        and s.barcodeobject_id = w.barcodeobject_id
        and so.barcode = %s
    order by m.nameen;
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


# ============================================================
# ВКЛАДКИ
# ============================================================

tab_accepted, tab_search_os, tab_problems = st.tabs(
    [
        "🏷️ Принятые марки",
        "🔎 Подробная информация по ОС",
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
                        "Номер ОС",
                        width="medium"
                    ),

                    "КИ": st.column_config.TextColumn(
                        "КИ",
                        width="large"
                    ),

                    "КИТУ": st.column_config.TextColumn(
                        "КИТУ",
                        width="large"
                    ),

                    "Дата приемки": st.column_config.DateColumn(
                        "Дата приемки",
                        format="DD.MM.YYYY",
                        width="medium"
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
# ВКЛАДКА — Подробная информация по ОС
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

        # ----------------------------------------------------
        # Загружаем только если ещё не загружали
        # ----------------------------------------------------

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
                        "Место",
                        width="medium"
                    ),

                    "Номер ОС": st.column_config.TextColumn(
                        "Номер ОС",
                        width="large"
                    ),

                    "Артикул": st.column_config.TextColumn(
                        "Артикул",
                        width="large"
                    ),

                    "Наименование": st.column_config.TextColumn(
                        "Наименование",
                        width="medium"
                    ),

                    "Вид запаса": st.column_config.TextColumn(
                        "Вид запаса",
                        width="large"
                    ),

                    "КИ": st.column_config.TextColumn(
                        "КИ",
                        width="large"
                    ),

                    "КИТУ": st.column_config.TextColumn(
                        "КИТУ",
                        width="large"
                    ),

                    "Дата приемки": st.column_config.DateColumn(
                        "Дата приемки",
                        format="DD.MM.YYYY",
                        width="medium"
                    ),

                    "Входящая поставка": st.column_config.TextColumn(
                        "Входящая поставка",
                        width="large"
                    ),

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