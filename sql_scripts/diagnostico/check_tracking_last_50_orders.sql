-- =====================================================
-- ANÁLISIS DE TRACKING EN ÚLTIMOS 50 PEDIDOS
-- =====================================================
-- Este script muestra cómo se almacena la información
-- de tracking (guía de envío) en WooCommerce
-- =====================================================

-- 1. VER TRACKING EN ÚLTIMOS 50 PEDIDOS (PRINCIPAL)
-- =====================================================
SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    o.status,
    DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR) AS date_created_local,

    -- Método de envío
    (SELECT oi.order_item_name
     FROM wpyz_woocommerce_order_items oi
     WHERE oi.order_id = o.id
       AND oi.order_item_type = 'shipping'
     LIMIT 1) AS shipping_method,

    -- Tracking almacenado en metadata
    om_tracking.meta_value AS tracking_items_json,

    -- Descomponer el JSON de tracking (si existe)
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_provider')) AS tracking_provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].custom_tracking_provider')) AS custom_provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_link')) AS tracking_link,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].date_shipped')) AS date_shipped

FROM wpyz_wc_orders o

-- Número de pedido (W-XXXXX)
LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

-- Tracking items (almacenado como JSON serializado)
LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status = 'wc-processing'
ORDER BY o.id DESC
LIMIT 50;


-- =====================================================
-- 2. VER SOLO PEDIDOS CON TRACKING
-- =====================================================
SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,

    -- Tracking descompuesto
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_provider')) AS tracking_provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].custom_tracking_provider')) AS custom_provider,

    -- Fecha de envío
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].date_shipped')) AS date_shipped,

    -- JSON completo para ver estructura
    om_tracking.meta_value AS tracking_full_json

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status = 'wc-processing'
  AND om_tracking.meta_value IS NOT NULL
  AND om_tracking.meta_value != ''
ORDER BY o.id DESC
LIMIT 50;


-- =====================================================
-- 3. CONTAR PEDIDOS CON Y SIN TRACKING
-- =====================================================
SELECT
    COUNT(*) AS total_pedidos_processing,

    SUM(CASE
        WHEN om_tracking.meta_value IS NOT NULL AND om_tracking.meta_value != ''
        THEN 1 ELSE 0
    END) AS pedidos_con_tracking,

    SUM(CASE
        WHEN om_tracking.meta_value IS NULL OR om_tracking.meta_value = ''
        THEN 1 ELSE 0
    END) AS pedidos_sin_tracking,

    ROUND(
        (SUM(CASE WHEN om_tracking.meta_value IS NOT NULL AND om_tracking.meta_value != '' THEN 1 ELSE 0 END) * 100.0)
        / COUNT(*),
        2
    ) AS porcentaje_con_tracking

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status = 'wc-processing';


-- =====================================================
-- 4. VER ESTRUCTURA COMPLETA DE UN PEDIDO CON TRACKING
-- =====================================================
-- Cambia el 12345 por un ID real de pedido con tracking
SELECT
    o.id,
    o.status,
    om.meta_key,
    om.meta_value,
    LENGTH(om.meta_value) AS value_length

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om
    ON o.id = om.order_id

WHERE o.id = (
    -- Obtener el último pedido con tracking
    SELECT o2.id
    FROM wpyz_wc_orders o2
    INNER JOIN wpyz_wc_orders_meta om2
        ON o2.id = om2.order_id
        AND om2.meta_key = '_wc_shipment_tracking_items'
    WHERE o2.status = 'wc-processing'
      AND om2.meta_value IS NOT NULL
      AND om2.meta_value != ''
    ORDER BY o2.id DESC
    LIMIT 1
)
ORDER BY
    CASE om.meta_key
        WHEN '_wc_shipment_tracking_items' THEN 1
        WHEN '_order_number' THEN 2
        ELSE 3
    END,
    om.meta_key;


-- =====================================================
-- 5. ANALIZAR PROVIDERS DE TRACKING MÁS USADOS
-- =====================================================
SELECT
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_provider')) AS provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].custom_tracking_provider')) AS custom_provider,
    COUNT(*) AS cantidad,

    -- Últimos 3 trackings como ejemplo
    GROUP_CONCAT(
        JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number'))
        ORDER BY o.id DESC
        SEPARATOR ', '
    ) AS ultimos_tracking_numbers

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status = 'wc-processing'
  AND om_tracking.meta_value IS NOT NULL
  AND om_tracking.meta_value != ''

GROUP BY provider, custom_provider
ORDER BY cantidad DESC;


-- =====================================================
-- 6. PEDIDOS SIN TRACKING EN ÚLTIMOS 7 DÍAS
-- =====================================================
SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR) AS date_created_local,
    TIMESTAMPDIFF(HOUR, o.date_created_gmt, UTC_TIMESTAMP()) AS horas_desde_creacion,

    (SELECT oi.order_item_name
     FROM wpyz_woocommerce_order_items oi
     WHERE oi.order_id = o.id
       AND oi.order_item_type = 'shipping'
     LIMIT 1) AS shipping_method

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status = 'wc-processing'
  AND (om_tracking.meta_value IS NULL OR om_tracking.meta_value = '')
  AND o.date_created_gmt >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 7 DAY)

ORDER BY o.id DESC
LIMIT 50;


-- =====================================================
-- NOTAS SOBRE LA ESTRUCTURA DE TRACKING:
-- =====================================================
-- El tracking se almacena en:
--   meta_key = '_wc_shipment_tracking_items'
--   meta_value = JSON serializado con formato:
--
--   [
--     {
--       "tracking_provider": "Custom Provider",
--       "custom_tracking_provider": "DINSIDES",
--       "custom_tracking_link": "https://...",
--       "tracking_number": "GUIA123456",
--       "date_shipped": "1736726400",  // Unix timestamp
--       "tracking_id": "abc123xyz"
--     }
--   ]
--
-- Para extraer datos del JSON usar:
--   JSON_EXTRACT(meta_value, '$[0].tracking_number')
--   JSON_UNQUOTE() para remover comillas
-- =====================================================
