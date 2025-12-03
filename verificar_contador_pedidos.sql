-- =============================================================================
-- SCRIPT PARA VERIFICAR CONTADOR DE PEDIDOS WHATSAPP
-- =============================================================================
-- Propósito: Validar que el contador solo cuente pedidos de WhatsApp (W-XXXXX)
--            y excluya pedidos en estado "trash"
-- =============================================================================

-- 1. Contar TODOS los pedidos (sin filtro)
SELECT
    '=== TODOS LOS PEDIDOS (SIN FILTRO) ===' as tipo,
    COUNT(*) as total
FROM wpyz_wc_orders;

-- 2. Contar solo pedidos de WhatsApp (W-XXXXX) sin filtro de estado
SELECT
    '=== PEDIDOS WHATSAPP (W-XXXXX) - SIN FILTRO DE TRASH ===' as tipo,
    COUNT(*) as total
FROM wpyz_wc_orders o
JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
WHERE m.meta_key = '_order_number_formatted'
    AND m.meta_value LIKE 'W-%';

-- 3. Contar pedidos de WhatsApp CORRECTAMENTE (excluyendo trash)
SELECT
    '=== PEDIDOS WHATSAPP (W-XXXXX) - EXCLUYENDO TRASH ===' as tipo,
    COUNT(*) as total
FROM wpyz_wc_orders o
JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
WHERE m.meta_key = '_order_number_formatted'
    AND m.meta_value LIKE 'W-%'
    AND o.status != 'trash';

-- 4. Ver distribución por estado de pedidos WhatsApp
SELECT
    '=== DISTRIBUCIÓN POR ESTADO (PEDIDOS WHATSAPP) ===' as tipo,
    o.status,
    COUNT(*) as cantidad,
    CONCAT(ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*)
        FROM wpyz_wc_orders o2
        JOIN wpyz_wc_orders_meta m2 ON o2.id = m2.order_id
        WHERE m2.meta_key = '_order_number_formatted'
            AND m2.meta_value LIKE 'W-%'
    ), 2), '%') as porcentaje
FROM wpyz_wc_orders o
JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
WHERE m.meta_key = '_order_number_formatted'
    AND m.meta_value LIKE 'W-%'
GROUP BY o.status
ORDER BY cantidad DESC;

-- 5. Ver pedidos que NO son WhatsApp (para entender la diferencia)
SELECT
    '=== PEDIDOS NO-WHATSAPP ===' as tipo,
    COUNT(*) as total
FROM wpyz_wc_orders o
WHERE o.id NOT IN (
    SELECT order_id
    FROM wpyz_wc_orders_meta
    WHERE meta_key = '_order_number_formatted'
        AND meta_value LIKE 'W-%'
);

-- 6. Ver ejemplos de pedidos WhatsApp con diferentes estados
SELECT
    '=== EJEMPLOS DE PEDIDOS WHATSAPP ===' as tipo,
    o.id,
    m.meta_value as numero_pedido,
    o.status,
    DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR) as fecha_peru,
    o.total_amount
FROM wpyz_wc_orders o
JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
WHERE m.meta_key = '_order_number_formatted'
    AND m.meta_value LIKE 'W-%'
ORDER BY o.date_created_gmt DESC
LIMIT 10;

-- 7. Ver pedidos en trash (para verificar que se excluyen)
SELECT
    '=== PEDIDOS WHATSAPP EN TRASH ===' as tipo,
    COUNT(*) as total_en_trash
FROM wpyz_wc_orders o
JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
WHERE m.meta_key = '_order_number_formatted'
    AND m.meta_value LIKE 'W-%'
    AND o.status = 'trash';

-- =============================================================================
-- RESUMEN ESPERADO
-- =============================================================================
-- El contador del badge debería mostrar el valor de la consulta #3:
-- "PEDIDOS WHATSAPP (W-XXXXX) - EXCLUYENDO TRASH"
--
-- Esto excluye:
-- 1. Pedidos que no tienen formato W-XXXXX (pedidos normales de WooCommerce)
-- 2. Pedidos WhatsApp que están en estado "trash"
-- =============================================================================
