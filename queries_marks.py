# ============================================================
# SQL-ЗАПРОСЫ — ЧЕСТНЫЙ ЗНАК
# ============================================================


# ============================================================
# ПРИНЯТЫЕ МАРКИ
# ============================================================

QUERY_ACCEPTED_MARKS = """
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

# ============================================================
# ПОИСК ОС ПО ЧАСТИ НОМЕРА
# ============================================================

QUERY_SEARCH_OS = """
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

# ============================================================
# МАРКИ ПО КОНКРЕТНОЙ ОС
# ============================================================

QUERY_MARKS_BY_OS = """
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
LEFT JOIN cis.stock AS pc
    ON s.parentcis_id = pc.cis_id
JOIN LATERAL (
    SELECT w.*
    FROM warehousesummary w
    WHERE (w.barcodeobject_id = s.barcodeobject_id
       AND w.storageobject_id = s.storageobject_id)
	   OR w.storageobject_id = s.storageobject_id
    ORDER BY
        CASE WHEN w.barcodeobject_id = s.barcodeobject_id THEN 0 ELSE 1 END,
        w.tid
    LIMIT 1
) w ON TRUE
JOIN materials AS m
    ON w.material_id = m.tid
   AND m.isam = '1'
JOIN stocktypes AS st
    ON w.stocktype_id = st.tid
JOIN locations AS l
    ON so.location_id = l.tid
LEFT JOIN tbl_warehouseincomeobjects AS tw
    ON so.tid = tw.storageobject_id
LEFT JOIN hdr_warehouseincome AS hw
    ON tw.transaction_id = hw.transaction_id
WHERE
    s.cis_level = '0'
    AND so.barcode = %s
ORDER BY m.nameen;
    """

# ============================================================
# ВСЕ ОС С МАРКАМИ
# ============================================================

QUERY_ALL_OS = """
SELECT DISTINCT
	l.locationname AS "Место",
    so.barcode AS "Номер ОС",
    m.nameen AS "Артикул",
    m.nameru AS "Наименование",
    st.nameru AS "Вид запаса",
    COUNT(s.cis_code) FILTER (WHERE s.cis_level = '0') AS "Количество КМ",
    COUNT(s.cis_code) FILTER (WHERE s.cis_level > '0') AS "Количество КИТУ",
    w.basequantity AS "Количество штук",
    hw.documentnumber AS "Входящая поставка"
FROM cis.stock AS s
JOIN storageobjects AS so
    ON s.storageobject_id = so.tid
JOIN LATERAL (
    SELECT w.*
    FROM warehousesummary w
    WHERE (w.barcodeobject_id = s.barcodeobject_id
       AND w.storageobject_id = s.storageobject_id)
	   OR (w.storageobject_id = s.storageobject_id
	   AND w.basequantity > 0)
    ORDER BY
        CASE WHEN w.barcodeobject_id = s.barcodeobject_id THEN 0 ELSE 1 END,
        w.tid
    LIMIT 1
) w ON TRUE
JOIN materials AS m
    ON w.material_id = m.tid
   AND m.isam = '1'
JOIN stocktypes AS st
    ON w.stocktype_id = st.tid
JOIN locations AS l
    ON so.location_id = l.tid
LEFT JOIN tbl_warehouseincomeobjects AS tw
    ON so.tid = tw.storageobject_id
LEFT JOIN hdr_warehouseincome AS hw
    ON tw.transaction_id = hw.transaction_id
GROUP BY l.locationname,
    so.barcode,
    m.nameen,
    m.nameru,
    st.nameru,
    hw.documentnumber,
	w.basequantity
ORDER BY m.nameen;
    """

# ============================================================
# ВСЕ ОС С ЧЕСТНЫМ ЗНАКОМ
# ============================================================

QUERY_ALL_OS_WITH_CHZ = """
WITH base AS (
    SELECT
        l.locationname,
        so.barcode,
        m.nameen,
        m.nameru AS nameru1,
        st.nameru AS nameru2,
        COUNT(s.cis_code) FILTER (
            WHERE s.cis_level = '0'
        ) AS cnt_km,
        COUNT(s.cis_code) FILTER (
            WHERE s.cis_level > '0'
        ) AS cnt_kitu,
        w.basequantity,
        hw.documentnumber,
        w.barcodeobject_id
    FROM storageobjects AS so
    JOIN warehousesummary AS w
        ON so.tid = w.storageobject_id
    AND w.basequantity > 0
    LEFT JOIN cis.stock s
        ON so.tid = s.storageobject_id
    AND ((w.barcodeobject_id = s.barcodeobject_id
    AND w.storageobject_id = s.storageobject_id)
    OR (w.storageobject_id = s.storageobject_id
    AND w.basequantity > 0))
    JOIN materials AS m
        ON w.material_id = m.tid
    AND m.isam = '1'
    JOIN stocktypes AS st
        ON w.stocktype_id = st.tid
    JOIN locations AS l
        ON so.location_id = l.tid
        AND l.tid <> '1000001'
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
        hw.documentnumber,
        w.basequantity,
        w.barcodeobject_id
)
SELECT
        locationname AS "Место",
        barcode AS "Номер ОС",
        nameen AS "Артикул",
        nameru1 AS "Наименование",
        nameru2 AS "Вид запаса",
        cnt_km AS "Количество КМ",
        cnt_kitu AS "Количество КИТУ",
        basequantity AS "Количество штук",
        documentnumber AS "Входящая поставка"
FROM base
ORDER BY nameen;
"""

# ============================================================
# КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ
# ============================================================

QUERY_CHZ_KPI = """
WITH base AS (
    SELECT
    l.locationname,
    so.barcode,
    m.nameen,
    m.nameru,
    st.nameru,
    COUNT(s.cis_code) FILTER (
        WHERE s.cis_level = '0'
    ) AS cnt_km,
    w.basequantity,
    w.barcodeobject_id
    FROM storageobjects AS so
    JOIN warehousesummary AS w
        ON so.tid = w.storageobject_id
    AND w.basequantity > 0
    LEFT JOIN cis.stock s
        ON so.tid = s.storageobject_id
    AND ((w.barcodeobject_id = s.barcodeobject_id
    AND w.storageobject_id = s.storageobject_id)
    OR w.storageobject_id = s.storageobject_id)
    JOIN materials AS m
        ON w.material_id = m.tid
    AND m.isam = '1'
    JOIN stocktypes AS st
        ON w.stocktype_id = st.tid
    JOIN locations AS l
        ON so.location_id = l.tid
        AND l.tid <> '1000001'
    GROUP BY
        l.locationname,
        so.barcode,
        m.nameen,
        m.nameru,
        st.nameru,
        w.basequantity,
        w.barcodeobject_id
)
SELECT
    COUNT(DISTINCT barcode) AS total_os,
    COUNT(DISTINCT barcode) FILTER (WHERE cnt_km > 0) AS marked_os,
    COUNT(DISTINCT barcode)
        - COUNT(DISTINCT barcode) FILTER (WHERE cnt_km > 0) AS unmarked_os,
    COUNT(DISTINCT nameen) AS total_articles,
    COUNT(DISTINCT nameen) FILTER (WHERE cnt_km > 0) AS marked_articles,
    COUNT(DISTINCT nameen) FILTER (WHERE cnt_km = 0) AS unmarked_articles,
    SUM(basequantity) AS total_pieces,
    SUM(basequantity) FILTER (WHERE cnt_km > 0) AS marked_pieces,
    SUM(basequantity) FILTER (WHERE cnt_km = 0) AS unmarked_pieces,
    SUM(cnt_km) AS total_marks,
    SUM(basequantity) - SUM(cnt_km) AS un_load_marks
FROM base;
"""

# ============================================================
# ПОИСК ПО МАРКЕ
# ============================================================

QUERY_SEARCH_BY_MARK = """
SELECT
    s.cis_code AS "КИ",
    pc.cis_code AS "КИТУ",
    so.barcode AS "Номер ОС"

FROM cis.stock AS s

JOIN storageobjects AS so
    ON s.storageobject_id = so.tid

LEFT JOIN cis.stock AS pc
    ON s.parentcis_id = pc.cis_id

WHERE
    regexp_replace(
        s.cis_code,
        '[^a-zA-Z0-9]',
        '',
        'g'
    )
    ILIKE
    '%%' || regexp_replace(
        %s,
        '[^a-zA-Z0-9]',
        '',
        'g'
    ) || '%%';
"""