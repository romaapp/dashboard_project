# Здесь вы можете хранить все свои SQL-запросы
SQL_QUERIES = {
    'Не выданные заявки': """
        select
	distinct hd.purchasenumber as "Номер заявки",
	hd.addresseedebtorname as "Грузополучатель",
	hd.routename as "Транспорт",
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
	count(distinct hm.material_id) as y
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
	ct.cnt <= 2) as "Меньше 2 отборов",
	count(ct.cnt) filter (
where
	ct.cnt <= 5 and ct.cnt > 2) as "От 3 до 5 отборов",
	count(ct.cnt) filter (
where
	ct.cnt <= 10 and ct.cnt > 5) as "От 5 до 10 отборов",
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
    
    'Список сотрудников': """
        SELECT DISTINCT
            hm.targetlocationname as "Сотрудник"
        FROM hdr_materialpicking as hm
        WHERE hm.finishdate::date = current_date
        ORDER BY hm.targetlocationname
    """,

	    'Средняя скорость отбора в час': """
        select 
	    hm.targetlocationname as "Сотрудник",
	    count(hm.tid) as "Общее количество отборов",
	    ROUND(count(hm.tid)/(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - CURRENT_DATE - INTERVAL '5 hours')) / 3600),2) as "Средняя скорость отбора в час"
        from hdr_materialpicking as hm
        where hm.finishdate::date = current_date
        group by 	
	    hm.targetlocationname
        order by 
	    hm.targetlocationname
    """

}

# === ОТЧЕТЫ ДЛЯ СТРАНИЦЫ АВТООБНОВЛЕНИЯ - КЛИЕНТАМ ===
AUTO_REFRESH_CLIENTS = {

    'Выдача клиенту': """
select
	d.deliverynumber as "Номер заявки",
	d.debtorpartnername as "Грузополучатель",
	d.extrafield3 as "Заказ клиента",
	d.deliverydate::date as "Дата отгрузки",
	COUNT(td.material_id) as "Арт. всего",
	COUNT(*) filter (
where
	td.sys_pickedbasequantity is null) as "Осталось арт.",
	case
	when COUNT(td.material_id) = COUNT(td.sys_pickedbasequantity)
	then 'Да' 
	else 'Нет'
	end as "Собран"
from
	hdr_deliveryrequest as d
join tbl_deliveryrequestmaterials as td on
	td.transaction_id = d.transaction_id
--Проверка на вычерки и тип поставки
where  td.shortagereason_id is null
and d.deliverytype_id = 7
and d.deliverysubtype_id = '109'
and d.deliverydate::date >= CURRENT_DATE
and d.deliverydate::date <= CURRENT_DATE+1
group by 	
	d.deliverynumber,
	d.debtorpartnername,
	d.extrafield3,
	d.deliverydate
order by 
"Собран" desc,
d.deliverydate desc,
d.deliverynumber
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
	count(distinct hm.material_id) as y
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
