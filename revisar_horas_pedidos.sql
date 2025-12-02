-- Script para revisar las horas de creación de pedidos
-- Compara la hora en la base de datos (UTC) con la hora actual

-- 1. Ver los últimos 10 pedidos con sus fechas de creación
SELECT
    p.ID as pedido_id,
    p.post_date as fecha_creacion_utc,
    p.post_date_gmt as fecha_gmt,
    p.post_status as estado,
    pm_order_number.meta_value as numero_pedido,
    -- Convertir UTC a hora de Perú (UTC-5)
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru,
    -- Mostrar diferencia con hora actual
    TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) as minutos_desde_creacion
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_order_number ON p.ID = pm_order_number.post_id
    AND pm_order_number.meta_key = '_order_number_formatted'
WHERE p.post_type = 'shop_order'
ORDER BY p.post_date_gmt DESC
LIMIT 10;

-- 2. Ver pedidos creados en las últimas 2 horas
SELECT
    p.ID as pedido_id,
    pm_order_number.meta_value as numero_pedido,
    p.post_date_gmt as fecha_utc,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru,
    pm_first_name.meta_value as nombre,
    pm_last_name.meta_value as apellido,
    pm_total.meta_value as total,
    TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) as minutos_atras
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_order_number ON p.ID = pm_order_number.post_id
    AND pm_order_number.meta_key = '_order_number_formatted'
LEFT JOIN wpyz_postmeta pm_first_name ON p.ID = pm_first_name.post_id
    AND pm_first_name.meta_key = '_billing_first_name'
LEFT JOIN wpyz_postmeta pm_last_name ON p.ID = pm_last_name.post_id
    AND pm_last_name.meta_key = '_billing_last_name'
LEFT JOIN wpyz_postmeta pm_total ON p.ID = pm_total.post_id
    AND pm_total.meta_key = '_order_total'
WHERE p.post_type = 'shop_order'
    AND p.post_date_gmt >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 2 HOUR)
ORDER BY p.post_date_gmt DESC;

-- 3. Ver hora actual del servidor vs hora actual UTC
SELECT
    NOW() as hora_servidor,
    UTC_TIMESTAMP() as hora_utc,
    DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR) as hora_peru_calculada,
    TIMEDIFF(NOW(), UTC_TIMESTAMP()) as diferencia_servidor_utc;

-- 4. Ver pedidos de hoy (en hora de Perú)
SELECT
    p.ID as pedido_id,
    pm_order_number.meta_value as numero_pedido,
    p.post_date_gmt as fecha_utc,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru,
    TIME(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) as hora_peru,
    pm_first_name.meta_value as cliente,
    pm_total.meta_value as total
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_order_number ON p.ID = pm_order_number.post_id
    AND pm_order_number.meta_key = '_order_number_formatted'
LEFT JOIN wpyz_postmeta pm_first_name ON p.ID = pm_first_name.post_id
    AND pm_first_name.meta_key = '_billing_first_name'
LEFT JOIN wpyz_postmeta pm_total ON p.ID = pm_total.post_id
    AND pm_total.meta_key = '_order_total'
WHERE p.post_type = 'shop_order'
    AND DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) = CURDATE()
ORDER BY p.post_date_gmt DESC;

-- 5. Comparar pedido más reciente con hora actual
SELECT
    'Pedido más reciente' as tipo,
    p.ID as pedido_id,
    pm_order_number.meta_value as numero_pedido,
    p.post_date_gmt as fecha_utc_guardada,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru_guardada,
    UTC_TIMESTAMP() as hora_utc_actual,
    DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR) as hora_peru_actual,
    TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) as diferencia_minutos,
    CASE
        WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) < 5 THEN '✓ Hora correcta (reciente)'
        WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) < 60 THEN '✓ Hora correcta'
        WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) > 300 THEN '✗ Revisar: más de 5 horas'
        ELSE '? Verificar'
    END as validacion
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_order_number ON p.ID = pm_order_number.post_id
    AND pm_order_number.meta_key = '_order_number_formatted'
WHERE p.post_type = 'shop_order'
ORDER BY p.post_date_gmt DESC
LIMIT 1;

-- 6. VALIDACIÓN: Ver pedidos creados en los últimos 30 minutos (para pruebas)
-- Esta consulta es útil después de crear un pedido de prueba
SELECT
    p.ID as pedido_id,
    pm_order_number.meta_value as numero_pedido,
    p.post_date_gmt as fecha_utc_guardada,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru_guardada,
    UTC_TIMESTAMP() as hora_utc_actual,
    DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR) as hora_peru_actual,
    TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) as minutos_atras,
    pm_first_name.meta_value as nombre,
    pm_last_name.meta_value as apellido,
    CONCAT(
        'Diferencia: ',
        TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()),
        ' minutos - ',
        CASE
            WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) <= 10 THEN '✓ CORRECTO'
            WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) > 300 THEN '✗ ERROR: Diferencia > 5 horas'
            ELSE '⚠ REVISAR'
        END
    ) as validacion
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_order_number ON p.ID = pm_order_number.post_id
    AND pm_order_number.meta_key = '_order_number_formatted'
LEFT JOIN wpyz_postmeta pm_first_name ON p.ID = pm_first_name.post_id
    AND pm_first_name.meta_key = '_billing_first_name'
LEFT JOIN wpyz_postmeta pm_last_name ON p.ID = pm_last_name.post_id
    AND pm_last_name.meta_key = '_billing_last_name'
WHERE p.post_type = 'shop_order'
    AND p.post_date_gmt >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 30 MINUTE)
ORDER BY p.post_date_gmt DESC;

-- 7. COMPARACIÓN DETALLADA: Último pedido vs hora actual
-- Muestra claramente si la conversión UTC está funcionando correctamente
SELECT
    '=== VALIDACIÓN DE CONVERSIÓN DE HORAS ===' as titulo,
    '' as valor
UNION ALL
SELECT 'Hora UTC actual del servidor MySQL', UTC_TIMESTAMP()
UNION ALL
SELECT 'Hora Perú actual (calculada UTC-5)', DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR)
UNION ALL
SELECT '---', '---'
UNION ALL
SELECT 'ID del último pedido', CAST(p.ID AS CHAR)
FROM wpyz_posts p WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1
UNION ALL
SELECT 'Número de pedido', pm.meta_value
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_order_number_formatted'
WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1
UNION ALL
SELECT 'Fecha UTC guardada en BD', CAST(p.post_date_gmt AS CHAR)
FROM wpyz_posts p WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1
UNION ALL
SELECT 'Fecha Perú guardada (UTC-5)', CAST(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) AS CHAR)
FROM wpyz_posts p WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1
UNION ALL
SELECT 'Minutos desde creación', CAST(TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) AS CHAR)
FROM wpyz_posts p WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1
UNION ALL
SELECT 'Resultado',
    CASE
        WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) <= 10 THEN '✓ CONVERSIÓN CORRECTA'
        WHEN TIMESTAMPDIFF(MINUTE, p.post_date_gmt, UTC_TIMESTAMP()) BETWEEN 295 AND 305 THEN '✗ ERROR: Guardando hora local en vez de UTC'
        ELSE '⚠ REVISAR: Tiempo transcurrido inusual'
    END
FROM wpyz_posts p WHERE p.post_type = 'shop_order' ORDER BY p.post_date_gmt DESC LIMIT 1;
