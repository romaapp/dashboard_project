# Здесь вы можете хранить все свои SQL-запросы
SQL_QUERIES = {
    'Не выданные заявки': """
select
	distinct hd.purchasenumber as "Номер заявки",
	hd.addresseedebtorname as "Грузополучатель",
	hd.routename as "Транспорт",
	hd.comment as "Комментарий",
	TO_CHAR(hd.shipmentdate, 'dd.mm.yyyy') as "Плановая дата отгрузки",
	CURRENT_DATE - hd.shipmentdate::date as "Количество дней",
	TO_CHAR(hd.shipmentdate, 'dd.mm.yyyy') || ' (заявок: ' || COUNT(*) over (partition by CURRENT_DATE - hd.shipmentdate::date) || ')' as "Дата и кол-во заявок"
from
	hdr_delivery as hd
where
	hd.isshipped = 0
	and CURRENT_DATE - hd.shipmentdate::date >1
order by
	"Количество дней" desc
    """,
    
    'Неотобранные артикулы с разбивкой на подтипы': """
        select
	d.deliverysubtype as "Подтип поставки",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE) as "Осталось арт. на сегодня",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+1) as "Осталось арт. на завтра",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+2) as "Осталось арт. на послезавтра",
	COUNT(td.material_id) filter (
where
	td.sys_pickedbasequantity is null and d.deliverydate::date >= CURRENT_DATE) as "Неотобранных арт. всего"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
group by d.deliverysubtype
    """,
    
    'Статистика по отобранным и неотобранным артикулам': """
with mh as (
	select count(hm.material_id) as x,
	count(distinct hm.row_id) as y
	from hdr_materialpicking hm
	where hm.finishdate::date = current_date
	)
select
	mh.x as "К-о отборов в операциях",
	mh.y as "К-во уникальных отобранных арт.",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE) as "Осталось арт. на сегодня",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+1) as "Осталось арт. на завтра",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+2) as "Осталось арт. на послезавтра",
	COUNT(td.material_id) filter (
where
	td.sys_pickedbasequantity is null and d.deliverydate::date >= CURRENT_DATE) as "Неотобранных арт. всего"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
	cross join mh
-- Проверка на вычерки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
group by mh.x, mh.y
    """,

	    'Статусы заявок отгрузки': """
        SELECT
            d.purchasenumber,
            ts.status_code,
            tts.status_name,
            u.login,
            ts.record_date
        FROM transaction_statuses_log as ts
        JOIN users as u ON u.people_id = ts.people_id
        JOIN hdr_delivery as d ON d.transaction_id = ts.transaction_id
        JOIN transaction_type_statuses as tts ON ts.status_code = tts.status_code
        WHERE d.purchasenumber = %s  -- ← Плейсхолдер для параметра
        ORDER BY record_date ASC
    """,

		    'Количество отборов сотрудников по волнам': """
        select
	ct.name as "Сотрудник",
	count(ct.cnt) filter (
where
	ct.cnt <= 2) as "До 2 отборов",
	count(ct.cnt) filter (
where
	ct.cnt <= 5 and ct.cnt > 2) as "От 3 до 5 отборов",
	count(ct.cnt) filter (
where
	ct.cnt <= 10 and ct.cnt > 5) as "От 6 до 10 отборов",
	count(ct.cnt) filter (
where
	ct.cnt > 10) as "Больше 10 отборов"
from (
select 
	hm.targetlocationname as name,
	count(hm.tid) as cnt,
	hm.wave_id,
	hm.wavetare_id
from hdr_materialpicking as hm
where hm.finishdate::date = current_date
group by 	
	hm.targetlocationname,
	hm.wave_id,
	hm.wavetare_id
) as ct
group by ct.name
order by 
	ct.name
    """,

	    'Отборы сотрудников по волнам': """
        SELECT 
            hm.targetlocationname as "Сотрудник",
            count(hm.tid) as "Количество отборов в таре",
            hm.wave_id as "Номер волны",
            hm.targetstorageobjectname as "Номер тары"
        FROM hdr_materialpicking as hm
        WHERE hm.finishdate::date = current_date
        GROUP BY 	
            hm.targetlocationname,
            hm.wave_id,
            hm.targetstorageobjectname
        ORDER BY 
            hm.targetlocationname,
            hm.wave_id
    """,
    

	    'Средняя скорость отбора в час': """
select 
	hm.targetlocationname as "Сотрудник",
	count(hm.tid) as "Общее количество отборов",
	ROUND(count(hm.tid)/(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CURRENT_DATE - INTERVAL '5 hours')) / 3600),2) as "Средняя скорость отбора в час",
	count(distinct hm.material_id) as "Количество артикулов",
	ROUND(count(distinct hm.material_id)/(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CURRENT_DATE - INTERVAL '5 hours')) / 3600),2) as "Количество артикулов в час", 
	ROUND(sum(hm.nettoweight),1) as "Общий вес"
from hdr_materialpicking as hm
where hm.finishdate::date = current_date
group by 	
	hm.targetlocationname
order by 
	hm.targetlocationname
    """,

'Выданные клиентам заказы': """
    SELECT
        CASE 
            WHEN hd.shipdate::DATE IS NULL
            THEN 'Заказ не отгружен'
            ELSE TO_CHAR(hd.shipdate::DATE, 'DD.MM.YYYY')
        END AS "Дата отгрузки",
        d.deliverynumber AS "Номер заявки",
        d.debtorpartnername AS "Грузополучатель",
        d.extrafield3 AS "Заказ клиента",
        COUNT(*) FILTER (
            WHERE td.sys_pickedbasequantity IS NOT NULL
        ) AS "К-во арт."
    FROM
        hdr_deliveryrequest AS d
    JOIN tbl_deliveryrequestmaterials AS td ON
        td.transaction_id = d.transaction_id
    JOIN hdr_delivery AS hd ON
        hd.purchasenumber = d.deliverynumber
    WHERE
        td.shortagereason_id IS NULL
        AND d.deliverytype_id = 7
        AND d.deliverysubtype_id = '109'

        -- Промежуток дат
        AND TO_DATE(
            SUBSTRING(
                d.transportnumber FROM '\d{2}\.\d{2}\.\d{4}'
            ),
            'DD.MM.YYYY'
        ) BETWEEN %s AND %s

        AND hd.isreadyforshipment = '1'

    GROUP BY
        d.deliverynumber,
        d.debtorpartnername,
        d.extrafield3,
        hd.shipdate::date

    ORDER BY
        "Дата отгрузки",
        d.deliverynumber
""",

	    'Операции по ресурсам': """
        select
	d.shipmentdate::date as "Дата отгрузки",
	p.nameru as "Производственный ресурс",
	count(hm.tid) as "Количество заданий"
from hdr_materialpicking as hm
join waves as w
	on hm.wave_id = w.tid
join wavetypes as wt
	on w.wavetype_id = wt.tid
join productionresourcegroups as p
	on wt.productionresourcegroup_id = p.tid
join tbl_deliveryrequestmaterials as td on
	hm.row_id = td.tid
join hdr_delivery as d on
	td.deliverytransaction_id = d.transaction_id
where 
	hm.taskdate is null 
	and td.shortagereason_id is null
group by 
	d.shipmentdate::date,
	p.nameru
order by d.shipmentdate::date, p.nameru
    """,

	    'Неотобранные артикулы(Заказы в работе)': """
select
	tz.nameen as "Технозона",
	COUNT(hm.material_id)  as "Количество артикулов"
from
	hdr_materialpicking as hm
join locations as l on
	l.tid = hm.sourcelocation_id
join technozones as tz on
	tz.tid = l.routezone_id
where 
hm.taskdate is null
group by 
tz.nameen
    """,

	    'Количество неотобранных артикулов': """
select
	d.deliverydate::date as "Дата отгрузки",
	COUNT(*)  as "Количество артикулов"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverydate::date >= CURRENT_DATE
and d.deliverytype_id = 7
and d.deliverysubtype is not null
and td.sys_pickedbasequantity is null
group by d.deliverydate::date
    """,

	    'Расчёт количества мест с ВГХ': """
select
	d.deliverydate::date as "Дата отгрузки",
	d.debtorpartnername as "Контрагент",
	td.materialname as "Артикул",
	sum(td.quantity) over (partition by d.debtorpartnername, td.materialname) as "Количество",
	(sum(td.quantity) over (partition by d.debtorpartnername, td.materialname))*mu.nettoweight as "Вес",
	(sum(td.quantity) over (partition by d.debtorpartnername, td.materialname))*mu.unitvolume as "Объем",
	CAST(ROUND(mu.length, 3) AS VARCHAR) || '/' || CAST(ROUND(mu.width, 3) AS VARCHAR) || '/' || CAST(ROUND(mu.height, 3) AS VARCHAR) as "ВГХ(д,ш,в)",
	case when 
	mu.length > 7 or mu.width > 7 or mu.height > 7 or mu.length = 0.001 or mu.width = 0.001 or mu.length is null or mu.width is null or mu.height is null
	then 'Проверить ВГХ'
	else ''
	end as "Верные ВГХ?"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
join materialunits as mu on
	td.materialunit_id = mu.tid
join materials as m on
	mu.material_id = m.tid
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
and d.deliverydate::date BETWEEN (%s)::DATE AND %s::DATE	
order by td.materialname asc
    """,

	    'Объём-расчёт количества мест': """
select tmp.deldate as "Дата отгрузки",
	tmp.dpn as "Контрагент",
	ROUND(SUM(tmp.wght),2) as "Вес",
	ROUND(SUM(tmp.vol),4) as "Объем",
	CEIL(SUM(tmp.wght)/750) as "Паллет по весу",
	CEIL(SUM(tmp.vol)/1.344) as "Паллет по объему",
	CEIL(SUM(tmp.vol)/1.344)+max(tmp.pog)::numeric as "По объему с погонажом"
	from(
select
	d.deliverydate::date as deldate,
	d.debtorpartnername as dpn,
	td.materialname as art,
	sum(td.quantity) over (partition by d.debtorpartnername, td.materialname) as qty,
	(sum(td.quantity) over (partition by d.debtorpartnername, td.materialname))*mu.nettoweight as wght,
	(sum(td.quantity) over (partition by d.debtorpartnername, td.materialname))*mu.unitvolume as vol,
	m.materialgroup_id,
	case 
	when m.materialgroup_id = '162' then '5'
	when m.materialgroup_id = '165' then '5'
	when m.materialgroup_id = '166' then '4'
	when m.materialgroup_id = '163' then '3'
	when m.materialgroup_id = '164' then '2'
	else '0' 
	end as pog
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
join materialunits as mu on
	td.materialunit_id = mu.tid
join materials as m on
	mu.material_id = m.tid
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
and d.deliverydate::date BETWEEN (%s)::DATE AND %s::DATE
) as tmp
group by tmp.deldate,
	tmp.dpn
order by tmp.dpn
    """,

	    'Артикулы, отбирающиеся упаковками': """
select
	distinct mu.material_id as "ID артикула",
	m.nameen as "Артикул",
	m.nameru as "Наименование",
	count(td.tid) over (partition by mu.material_id) as "Количество отборов"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
join materialunits as mu on
	td.materialunit_id = mu.tid
join materials as m on
	mu.material_id = m.tid
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
and mu.unitkoeff > 1
and d.deliverydate::date BETWEEN (%s)::DATE AND %s::DATE
order by m.nameen
    """,

	    'Производительность комплектации': """
WITH operations AS (
    SELECT
        mp.targetlocationname AS ФИО,
        mp.sourcelocationname,
        coalesce(case when dbo.MaterialUnitPickingGroup(mp.MaterialUnit_id) = 'QW' then mp.NettoWeight else null end, mp.BaseQuantity / mu.UnitKoeff * mu.NettoWeight) as вес,
        mp.BaseQuantity / mu.UnitKoeff * mu.UnitVolume as объём,
        mp.taskdate AS начало_операции,
        mp.finishdate AS окончание_операции,
        mp.material_id as артикула,
        mp.finishdate - mp.taskdate AS время_операции,
        LAG(mp.finishdate) OVER (
            PARTITION BY mp.targetlocationname
            ORDER BY mp.taskdate, mp.finishdate
        ) AS окончание_предыдущей_операции,
        CASE 
            WHEN tz.nameru IN ('Зона отбора с фронтальных стеллажей (13)', N'Зона хранения и отбора ЛВЖ', N'Зона хранения крупногабарита (3)') THEN 'Фронт'
            WHEN tz.nameru IN (N'30.Зона отбора погонажа 2м', N'28.Зона отбора погонажа 3м', N'36.Зона отбора погонажа 4м', N'35.Зона отбора погонажа 5м', N'26.Зона отбора погонажа 6м', N'37.Зона отбора погонажа MIX', N'Зона хранения и отбора погонажа (5)') THEN 'Погонаж'
            WHEN tz.nameru IN (N'Мезонин, 1 этаж, блок М1, зона 1', N'Мезонин, 1 этаж, блок М1, зона 2', N'Мезонин, 1 этаж, блок М1, зона 3', N'Мезонин, 1 этаж, блок М2, зона 1', N'Мезонин, 1 этаж, блок М2, зона 2', N'Мезонин, 1 этаж, блок М2, зона 3') THEN 'Мезонин'
            ELSE 'Другое'
        END AS зона
    FROM hdr_materialpicking mp
    JOIN locations l ON mp.sourcelocation_id = l.tid
    JOIN technozones tz ON l.technozone_id = tz.tid
    JOIN Materials m ON m.tid = mp.material_id
    JOIN MaterialUnits mu ON mp.AlternateMaterialUnit_id = mu.tid
    JOIN Units u ON u.tid = mu.unit_id AND u.nameru = mp.alternatematerialunitname
    WHERE tz.nameru in( 'Зона отбора с фронтальных стеллажей (13)',N'30.Зона отбора погонажа 2м',N'28.Зона отбора погонажа 3м',N'36.Зона отбора погонажа 4м',
       N'35.Зона отбора погонажа 5м',N'26.Зона отбора погонажа 6м',N'37.Зона отбора погонажа MIX',N'Зона хранения и отбора погонажа (5)',
       N'Мезонин, 1 этаж, блок М1, зона 1',N'Мезонин, 1 этаж, блок М1, зона 2',N'Мезонин, 1 этаж, блок М1, зона 3',N'Мезонин, 
       1 этаж, блок М2, зона 1',N'Мезонин, 1 этаж, блок М2, зона 2',N'Мезонин, 1 этаж, блок М2, зона 3',N'Зона хранения и отбора ЛВЖ',
       N'Зона хранения крупногабарита (3)' ,N'Мезонин, 1 этаж, блок М2, зона 1')
	  AND mp.finishdate::date BETWEEN  (%s)::TIMESTAMP AND %s::TIMESTAMP
	      AND mp.taskdate IS NOT NULL
      AND mp.finishdate IS NOT NULL
      AND mp.targetlocationname IS NOT NULL
    GROUP BY 
        mp.targetlocationname,
        mp.sourcelocationname,
        mp.nettoweight,
        mp.basequantity,
        mp.taskdate,
        mp.finishdate,
        mp.material_id,
        mp.materialunit_id,
        mu.UnitKoeff,
        mu.NettoWeight,
        mu.unitvolume,
        CASE 
            WHEN tz.nameru IN ('Зона отбора с фронтальных стеллажей (13)', N'Зона хранения и отбора ЛВЖ', N'Зона хранения крупногабарита (3)') THEN 'Фронт'
            WHEN tz.nameru IN (N'30.Зона отбора погонажа 2м', N'28.Зона отбора погонажа 3м', N'36.Зона отбора погонажа 4м', N'35.Зона отбора погонажа 5м', N'26.Зона отбора погонажа 6м', N'37.Зона отбора погонажа MIX', N'Зона хранения и отбора погонажа (5)') THEN 'Погонаж'
            WHEN tz.nameru IN (N'Мезонин, 1 этаж, блок М1, зона 1', N'Мезонин, 1 этаж, блок М1, зона 2', N'Мезонин, 1 этаж, блок М1, зона 3', N'Мезонин, 1 этаж, блок М2, зона 1', N'Мезонин, 1 этаж, блок М2, зона 2', N'Мезонин, 1 этаж, блок М2, зона 3') THEN 'Мезонин'
            ELSE 'Другое'
        END
),
operations_with_pause AS (
    SELECT
        ФИО,
        sourcelocationname,
        начало_операции,
        окончание_операции,
        время_операции,
        артикула,
        вес,
        объём,
        зона,
        CASE
            WHEN окончание_предыдущей_операции IS NULL THEN INTERVAL '0'
            WHEN начало_операции > окончание_предыдущей_операции THEN начало_операции - окончание_предыдущей_операции
            ELSE INTERVAL '0'
        END AS время_простоя
    FROM operations
)
SELECT
    ФИО,
    COUNT(sourcelocationname) AS "К-во операций",
                ROUND(
        COUNT(sourcelocationname)::numeric
        /
        NULLIF(
            EXTRACT(
                EPOCH FROM (
                    (MAX(окончание_операции) - MIN(начало_операции))
                    - COALESCE(
                        SUM(
                            CASE
                                WHEN время_простоя > INTERVAL '10 minutes' THEN время_простоя
                                ELSE INTERVAL '0'
                            END
                        ),
                        INTERVAL '0'
                    )
                )
            ) / 3600.0,
            0
        ),
        2
    ) AS "Производительность по операциям",
    round(sum(вес)) AS "Вес",
    ROUND(SUM(объём), 2) AS "Объём",
    COUNT(distinct (sourcelocationname, артикула,CAST(окончание_операции AS date))) AS "К-во артикулов",
                                 ROUND(
        COUNT(distinct (sourcelocationname, артикула,CAST(окончание_операции AS date)))::numeric
        /
        NULLIF(
            EXTRACT(
                EPOCH FROM (
                    (MAX(окончание_операции) - MIN(начало_операции))
                    - COALESCE(
                        SUM(
                            CASE
                                WHEN время_простоя > INTERVAL '10 minutes' THEN время_простоя
                                ELSE INTERVAL '0'
                            END
                        ),
                        INTERVAL '0'
                    )
                )
            ) / 3600.0,
            0
        ),
        2
    ) AS "Производительность по артикулам",
    зона as "Зона",
  TO_CHAR(
    SUM(
        CASE
            WHEN время_простоя > INTERVAL '10 minutes' THEN время_простоя
            ELSE INTERVAL '0'
        END
    ),
    'HH24:MI:SS'
) AS "Время простоя более 10 минут",
    COUNT(*) FILTER (WHERE время_простоя > INTERVAL '10 minutes') AS "К-во простоев более 10 минут"
FROM operations_with_pause
GROUP BY ФИО, Зона
ORDER BY "К-во операций" desc
    """

}

# === ОТЧЕТЫ ДЛЯ СТРАНИЦЫ АВТООБНОВЛЕНИЯ - КЛИЕНТАМ ===
AUTO_REFRESH_CLIENTS = {

    'Выдача клиенту': """
select
	d.deliverynumber as "Номер заявки",
	d.debtorpartnername as "Грузополучатель",
	d.extrafield3 as "Заказ клиента",
	(COUNT(*) filter (
where
	td.sys_pickedbasequantity is not null)*100/COUNT(td.material_id)) || '%%' as "Процент",
    case
	when hd.isreadyforshipment = '1'
	then 'Готов к выдаче' 
	when (COUNT(*) filter (
where
	td.sys_pickedbasequantity is not null)/COUNT(td.material_id)) = '1'
	then 'Упаковывается'
	else 'Собирается'
	end as "Статус"
from
	hdr_deliveryrequest as d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
join hdr_delivery as hd on
	hd.purchasenumber = d.deliverynumber
--Проверки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype_id = '109'
and hd.taskpriority = '5000'
and d.transportnumber is null
and d.deliverydate::date >= CURRENT_DATE-10
group by 	
	d.deliverynumber,
	d.debtorpartnername,
	d.extrafield3,
	hd.isreadyforshipment
order by d.deliverynumber 
    """

}
	

# === ОТЧЕТЫ ДЛЯ СТРАНИЦЫ АВТООБНОВЛЕНИЯ - OUT ===
AUTO_REFRESH_OUT = {

    'Неотобранные артикулы с разбивкой на подтипы': """
        select
	d.deliverysubtype as "Подтип поставки",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE) as "Осталось арт. на сегодня",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+1) as "Осталось арт. на завтра",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+2) as "Осталось арт. на послезавтра",
	COUNT(td.material_id) filter (
where
	td.sys_pickedbasequantity is null and d.deliverydate::date >= CURRENT_DATE) as "Неотобранных арт. всего"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
group by d.deliverysubtype
    """,

    'Статистика по отобранным и неотобранным артикулам': """
with mh as (
	select count(hm.material_id) as x,
	count(distinct hm.row_id) as y
	from hdr_materialpicking hm
	where hm.finishdate::date = current_date
	)
select
	mh.x as "К-о отборов в операциях",
	mh.y as "К-во уникальных отобранных арт.",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE) as "Осталось арт. на сегодня",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+1) as "Осталось арт. на завтра",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null
	and d.deliverydate::date = CURRENT_DATE+2) as "Осталось арт. на послезавтра",
	COUNT(td.material_id) filter (
where
	td.sys_pickedbasequantity is null and d.deliverydate::date >= CURRENT_DATE) as "Неотобранных арт. всего"
from
	hdr_deliveryrequest d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
	cross join mh
-- Проверка на вычерки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype is not null
group by mh.x, mh.y
    """

}
