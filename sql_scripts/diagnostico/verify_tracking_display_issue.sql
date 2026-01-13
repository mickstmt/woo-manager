-- =====================================================
-- VERIFICAR PROBLEMA DE TRACKING NO VISIBLE EN WOOCOMMERCE
-- =====================================================
-- Este script verifica por qué los pedidos shipped muestran
-- guión (-) en la columna de tracking en lugar del número
-- =====================================================

-- 1. VERIFICAR PEDIDOS RECIENTES EN ESTADO SHIPPED
-- =====================================================
SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    o.status,
    DATE_SUB(o.date_updated_gmt, INTERVAL 5 HOUR) AS last_updated_local,

    -- TRACKING: Verificar si existe
    CASE
        WHEN om_tracking.meta_value IS NOT NULL AND om_tracking.meta_value != ''
        THEN '✓ SÍ TIENE'
        ELSE '✗ NO TIENE'
    END AS tiene_tracking,

    -- Extraer número de tracking
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_provider')) AS tracking_provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].custom_tracking_provider')) AS custom_provider,

    -- JSON completo para debug
    om_tracking.meta_value AS tracking_full_json,

    -- Longitud del JSON (para ver si está vacío)
    LENGTH(om_tracking.meta_value) AS json_length

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.status IN ('wc-processing', 'wc-shipped', 'wc-completed')
ORDER BY o.date_updated_gmt DESC
LIMIT 20;


-- =====================================================
-- 2. VERIFICAR ESPECÍFICAMENTE LOS PEDIDOS DE LA CAPTURA
-- =====================================================
-- Pedidos: #41987, #41986, #41985
SELECT
    o.id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    o.status,

    -- Verificar tracking
    om_tracking.meta_value AS tracking_json,
    LENGTH(om_tracking.meta_value) AS json_length,

    -- Extraer datos
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_provider')) AS provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].custom_tracking_provider')) AS custom_provider,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].date_shipped')) AS date_shipped_timestamp

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.id IN (41987, 41986, 41985)
ORDER BY o.id DESC;


-- =====================================================
-- 3. VERIFICAR SI HAY MÚLTIPLES VERSIONES DE TRACKING
-- =====================================================
-- Algunos plugins guardan tracking en diferentes meta_keys
SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    om.meta_key,
    om.meta_value,
    LENGTH(om.meta_value) AS value_length

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om
    ON o.id = om.order_id

WHERE o.id IN (41987, 41986, 41985)
  AND (
      om.meta_key LIKE '%tracking%'
      OR om.meta_key LIKE '%shipment%'
      OR om.meta_key LIKE '%shipped%'
  )
ORDER BY o.id DESC, om.meta_key;


-- =====================================================
-- 4. VERIFICAR FORMATO DEL JSON DE TRACKING
-- =====================================================
-- Ver si el JSON está bien formado
SELECT
    o.id,
    om_tracking.meta_value AS raw_json,

    -- Intentar parsear como JSON
    JSON_VALID(om_tracking.meta_value) AS is_valid_json,

    -- Contar elementos en el array
    JSON_LENGTH(om_tracking.meta_value) AS array_length,

    -- Ver si es un array vacío
    CASE
        WHEN om_tracking.meta_value = '[]' THEN 'Array vacío'
        WHEN om_tracking.meta_value = '' THEN 'String vacío'
        WHEN om_tracking.meta_value IS NULL THEN 'NULL'
        ELSE 'Tiene datos'
    END AS estado_json

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.id IN (41987, 41986, 41985)
ORDER BY o.id DESC;


-- =====================================================
-- 5. COMPARAR PEDIDOS CON TRACKING VISIBLE VS NO VISIBLE
-- =====================================================
-- Buscar diferencias entre pedidos donde SÍ aparece el tracking
-- y donde NO aparece (muestra guión)

-- Pedidos donde SÍ se ve el tracking (necesitas identificar uno)
-- Cambia el ID por uno donde SÍ aparezca el tracking
SELECT
    'PEDIDO CON TRACKING VISIBLE' AS tipo,
    o.id,
    om_tracking.meta_value AS tracking_json,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE om_tracking.meta_value IS NOT NULL
  AND om_tracking.meta_value != ''
  AND om_tracking.meta_value != '[]'
  AND JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) IS NOT NULL
ORDER BY o.id DESC
LIMIT 1

UNION ALL

-- Pedidos donde NO se ve (muestra guión)
SELECT
    'PEDIDO SIN TRACKING VISIBLE' AS tipo,
    o.id,
    om_tracking.meta_value AS tracking_json,
    JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number')) AS tracking_number

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.id IN (41987, 41986, 41985)
ORDER BY o.id DESC
LIMIT 3;


-- =====================================================
-- 6. VERIFICAR SI EL PLUGIN DE TRACKING ESTÁ ACTIVO
-- =====================================================
-- Verificar si hay alguna configuración del plugin
SELECT
    option_name,
    option_value
FROM wpyz_options
WHERE option_name LIKE '%shipment%tracking%'
   OR option_name LIKE '%wc_shipment%'
ORDER BY option_name;


-- =====================================================
-- POSIBLES CAUSAS DEL PROBLEMA:
-- =====================================================
-- 1. El JSON está vacío: tracking_json = '[]'
-- 2. El JSON no es válido
-- 3. El tracking_number está NULL o vacío
-- 4. El plugin de WooCommerce Shipment Tracking no está leyendo
--    correctamente el meta_key '_wc_shipment_tracking_items'
-- 5. Hay un problema de cache en WooCommerce
-- 6. El formato del JSON no es el esperado por el plugin
-- =====================================================
