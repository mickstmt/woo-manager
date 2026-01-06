-- Debug: Ver pedidos en estado wc-processing con sus fechas en GMT y hora local

SELECT
    o.id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) as order_number,
    o.date_created_gmt as fecha_gmt,
    DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR) as fecha_peru,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as fecha_peru_solo_dia,
    o.status,
    o.total_amount
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'
WHERE o.status = 'wc-processing'
ORDER BY o.date_created_gmt DESC
LIMIT 20;

-- Probar el filtro específico que está usando el usuario
SELECT
    COUNT(*) as total_pedidos,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as fecha_local
FROM wpyz_wc_orders o
WHERE o.status = 'wc-processing'
    AND DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2026-01-01' AND '2026-01-06'
GROUP BY DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
ORDER BY fecha_local;
