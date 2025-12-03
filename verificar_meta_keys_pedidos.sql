-- =============================================================================
-- SCRIPT PARA VERIFICAR META KEYS DE NÚMEROS DE PEDIDO
-- =============================================================================
-- Propósito: Identificar qué meta_key contiene los números con formato W-XXXXX
-- =============================================================================

-- 1. Ver todos los meta_keys relacionados con order_number de un pedido reciente
SELECT
    o.id as order_id,
    om.meta_key,
    om.meta_value,
    CASE
        WHEN om.meta_value LIKE 'W-%' THEN '✓ Formato WhatsApp'
        WHEN om.meta_value REGEXP '^[0-9]+$' THEN '✓ Número ID'
        ELSE '? Otro formato'
    END as tipo
FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
WHERE om.meta_key LIKE '%order_number%'
ORDER BY o.id DESC
LIMIT 20;

-- 2. Contar cuántos pedidos tienen cada meta_key
SELECT
    om.meta_key,
    COUNT(DISTINCT om.order_id) as cantidad_pedidos,
    COUNT(CASE WHEN om.meta_value LIKE 'W-%' THEN 1 END) as con_formato_w,
    GROUP_CONCAT(DISTINCT SUBSTRING(om.meta_value, 1, 10) ORDER BY om.order_id DESC LIMIT 5) as ejemplos
FROM wpyz_wc_orders_meta om
WHERE om.meta_key LIKE '%order_number%'
GROUP BY om.meta_key
ORDER BY cantidad_pedidos DESC;

-- 3. Ver ejemplos específicos del último pedido
SELECT
    '=== ÚLTIMO PEDIDO CREADO ===' as info,
    o.id as order_id,
    o.status,
    om.meta_key,
    om.meta_value
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
    AND om.meta_key IN ('_order_number', '_order_number_formatted', 'order_number')
ORDER BY o.date_created_gmt DESC
LIMIT 1;

-- 4. Comparar conteos usando diferentes meta_keys
SELECT '=== CONTEO CON _order_number ===' as metodo, COUNT(DISTINCT o.id) as total
FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
WHERE om.meta_key = '_order_number'
    AND om.meta_value LIKE 'W-%'
    AND o.status != 'trash'

UNION ALL

SELECT '=== CONTEO CON _order_number_formatted ===' as metodo, COUNT(DISTINCT o.id) as total
FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
WHERE om.meta_key = '_order_number_formatted'
    AND om.meta_value LIKE 'W-%'
    AND o.status != 'trash'

UNION ALL

SELECT '=== CONTEO SOLO CON _order_number (sin filtro W-) ===' as metodo, COUNT(DISTINCT o.id) as total
FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
WHERE om.meta_key = '_order_number'
    AND o.status != 'trash'

UNION ALL

SELECT '=== CONTEO TODOS LOS PEDIDOS ===' as metodo, COUNT(*) as total
FROM wpyz_wc_orders o
WHERE o.status != 'trash';

-- 5. Ver distribución de formatos en _order_number
SELECT
    CASE
        WHEN om.meta_value LIKE 'W-%' THEN 'Formato W-XXXXX (WhatsApp)'
        WHEN om.meta_value REGEXP '^[0-9]+$' THEN 'Solo números (WooCommerce normal)'
        ELSE 'Otro formato'
    END as tipo_formato,
    COUNT(*) as cantidad,
    GROUP_CONCAT(DISTINCT om.meta_value ORDER BY o.id DESC LIMIT 3) as ejemplos
FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id
WHERE om.meta_key = '_order_number'
    AND o.status != 'trash'
GROUP BY tipo_formato;

-- =============================================================================
-- RESULTADO ESPERADO:
-- =============================================================================
-- Esta consulta nos dirá si debemos usar:
-- - _order_number (más común)
-- - _order_number_formatted (alternativa)
-- Y nos mostrará cuántos pedidos tienen formato W-XXXXX vs números normales
-- =============================================================================
