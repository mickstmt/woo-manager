-- =====================================================
-- ANÁLISIS DE FORMATO DE TRACKING
-- =====================================================
-- Verificar si el problema es el formato del JSON
-- o la lectura del plugin de WooCommerce
-- =====================================================

-- 1. VERIFICAR FORMATO EXACTO DEL TRACKING
-- =====================================================
SELECT
    o.id AS order_id,
    o.status,
    
    -- Ver el contenido exacto
    om_tracking.meta_value AS tracking_raw,
    
    -- Verificar longitud
    LENGTH(om_tracking.meta_value) AS longitud,
    
    -- Verificar primeros caracteres (PHP serialized empieza con "a:" o "s:")
    LEFT(om_tracking.meta_value, 10) AS primeros_10_chars,
    
    -- Verificar si es JSON válido
    JSON_VALID(om_tracking.meta_value) AS es_json_valido,
    
    -- Si fuera JSON, extraer tracking number
    CASE
        WHEN JSON_VALID(om_tracking.meta_value) = 1
        THEN JSON_UNQUOTE(JSON_EXTRACT(om_tracking.meta_value, '$[0].tracking_number'))
        ELSE 'NO ES JSON'
    END AS tracking_number_si_json

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE o.id IN (41987, 41986, 41985, 41984)
ORDER BY o.id DESC;


-- =====================================================
-- 2. BUSCAR UN PEDIDO DONDE SÍ APAREZCA EL TRACKING
-- =====================================================
-- Si existe algún pedido donde SÍ se vea el tracking,
-- comparar su formato con los problemáticos

SELECT
    o.id AS order_id,
    o.status,
    'TIENE TRACKING EN HPOS' AS nota,
    
    -- Primeros caracteres para identificar formato
    LEFT(om_tracking.meta_value, 50) AS inicio_del_valor,
    
    -- Verificar si es JSON
    JSON_VALID(om_tracking.meta_value) AS es_json,
    
    -- Longitud
    LENGTH(om_tracking.meta_value) AS longitud

FROM wpyz_wc_orders o

INNER JOIN wpyz_wc_orders_meta om_tracking
    ON o.id = om_tracking.order_id
    AND om_tracking.meta_key = '_wc_shipment_tracking_items'

WHERE om_tracking.meta_value IS NOT NULL
  AND om_tracking.meta_value != ''
  AND om_tracking.meta_value != '[]'

ORDER BY o.id DESC
LIMIT 10;


-- =====================================================
-- 3. VERIFICAR SI HAY OTROS META_KEYS DE TRACKING
-- =====================================================
-- Algunos plugins usan diferentes meta_keys

SELECT DISTINCT
    meta_key,
    COUNT(*) AS cantidad_pedidos
    
FROM wpyz_wc_orders_meta

WHERE (
    meta_key LIKE '%tracking%'
    OR meta_key LIKE '%shipment%'
    OR meta_key LIKE '%courier%'
)

GROUP BY meta_key
ORDER BY cantidad_pedidos DESC;


-- =====================================================
-- 4. VERIFICAR CONFIGURACIÓN DE HPOS
-- =====================================================
-- Ver si HPOS está habilitado y configurado correctamente

SELECT
    option_name,
    option_value
    
FROM wpyz_options

WHERE option_name IN (
    'woocommerce_custom_orders_table_enabled',
    'woocommerce_custom_orders_table_data_sync_enabled',
    'woocommerce_feature_custom_order_tables_enabled'
)

ORDER BY option_name;


-- =====================================================
-- 5. VERIFICAR PLUGIN DE SHIPMENT TRACKING
-- =====================================================
SELECT
    option_name,
    LEFT(option_value, 200) AS valor_truncado
    
FROM wpyz_options

WHERE option_name LIKE '%shipment%'
   OR option_name LIKE '%tracking%'
   
ORDER BY option_name
LIMIT 20;


-- =====================================================
-- DIAGNÓSTICO ESPERADO:
-- =====================================================
-- Si primeros_10_chars empieza con 'a:' o 's:' → Es PHP serializado
-- Si es_json_valido = 1 → Es JSON
-- 
-- WooCommerce Shipment Tracking con HPOS debería aceptar:
--   - JSON: [{"tracking_number":"...","tracking_provider":"..."}]
--   - PHP serializado: a:1:{i:0;a:6:{s:15:"tracking_number";...}}
--
-- Si el plugin NO muestra el tracking pero los datos existen,
-- puede ser:
--   1. Versión desactualizada del plugin
--   2. Cache de WooCommerce
--   3. Incompatibilidad con HPOS
--   4. El plugin espera meta_key diferente
-- =====================================================
