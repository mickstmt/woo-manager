-- ============================================================
-- CONSULTAR PEDIDOS POR RANGO DE FECHAS
-- ============================================================
-- Reemplaza las fechas YYYY-MM-DD según tu necesidad
-- ============================================================

SET @start_date = '2025-01-01';
SET @end_date = '2025-01-31';

-- Consulta principal de pedidos
SELECT
    o.id AS order_id,
    COALESCE(om_manager.meta_value, om_numero.meta_value, o.id) AS numero_pedido,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS fecha_pedido,
    o.status,
    o.total_amount,
    CONCAT(ba.first_name, ' ', ba.last_name) AS cliente,
    ba.email AS email_cliente,
    CASE
        WHEN om_manager.meta_value IS NOT NULL THEN 'woocommerce-manager'
        WHEN om_created.meta_value IS NOT NULL THEN om_created.meta_value
        ELSE 'woocommerce'
    END AS created_via,
    om_payment.meta_value AS metodo_pago
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'
LEFT JOIN wpyz_wc_orders_meta om_manager ON o.id = om_manager.order_id
    AND om_manager.meta_key = '_manager_order_number'
LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id
    AND ba.address_type = 'billing'
LEFT JOIN wpyz_wc_orders_meta om_created ON o.id = om_created.order_id
    AND om_created.meta_key = '_created_via'
LEFT JOIN wpyz_wc_orders_meta om_payment ON o.id = om_payment.order_id
    AND om_payment.meta_key = '_payment_method_title'
WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
ORDER BY o.date_created_gmt DESC;

-- ============================================================
-- RESUMEN: Total de pedidos y monto
-- ============================================================
SELECT
    COUNT(DISTINCT o.id) AS total_pedidos,
    ROUND(SUM(o.total_amount), 2) AS monto_total_pen
FROM wpyz_wc_orders o
WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed');

-- ============================================================
-- RESUMEN: Por estado
-- ============================================================
SELECT
    o.status,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*)
        FROM wpyz_wc_orders
        WHERE DATE(DATE_SUB(date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
            AND status != 'trash'
            AND status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
    ), 2) AS porcentaje,
    ROUND(SUM(o.total_amount), 2) AS monto_total
FROM wpyz_wc_orders o
WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
GROUP BY o.status
ORDER BY cantidad DESC;

-- ============================================================
-- RESUMEN: Por origen (created_via)
-- ============================================================
SELECT
    CASE
        WHEN om_manager.meta_value IS NOT NULL THEN 'woocommerce-manager'
        WHEN om_created.meta_value IS NOT NULL THEN om_created.meta_value
        ELSE 'woocommerce'
    END AS origen,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*)
        FROM wpyz_wc_orders
        WHERE DATE(DATE_SUB(date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
            AND status != 'trash'
            AND status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
    ), 2) AS porcentaje,
    ROUND(SUM(o.total_amount), 2) AS monto_total
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om_manager ON o.id = om_manager.order_id
    AND om_manager.meta_key = '_manager_order_number'
LEFT JOIN wpyz_wc_orders_meta om_created ON o.id = om_created.order_id
    AND om_created.meta_key = '_created_via'
WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
GROUP BY origen
ORDER BY cantidad DESC;

-- ============================================================
-- OPCIONAL: Pedidos con detalles de items
-- ============================================================
-- Descomenta si necesitas ver los productos de cada pedido
/*
SELECT
    o.id AS order_id,
    COALESCE(om_manager.meta_value, om_numero.meta_value, o.id) AS numero_pedido,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS fecha_pedido,
    oi.order_item_name AS producto,
    oim_qty.meta_value AS cantidad,
    oim_total.meta_value AS line_total
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'
LEFT JOIN wpyz_wc_orders_meta om_manager ON o.id = om_manager.order_id
    AND om_manager.meta_key = '_manager_order_number'
INNER JOIN wpyz_woocommerce_order_items oi ON o.id = oi.order_id
    AND oi.order_item_type = 'line_item'
LEFT JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
    AND oim_qty.meta_key = '_qty'
LEFT JOIN wpyz_woocommerce_order_itemmeta oim_total ON oi.order_item_id = oim_total.order_item_id
    AND oim_total.meta_key = '_line_total'
WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @start_date AND @end_date
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
ORDER BY o.date_created_gmt DESC, oi.order_item_id;
*/
