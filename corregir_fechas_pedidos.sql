-- =============================================================================
-- SCRIPT DE CORRECCIÓN DE FECHAS DE PEDIDOS
-- =============================================================================
-- Pedidos a corregir: 39844, 39843, 39841, 39840
--
-- PROBLEMA: Estos pedidos se guardaron con la hora de Perú sin convertir a UTC,
--           causando que aparezcan con fecha del día siguiente.
--
-- SOLUCIÓN: Restar 5 horas a sus fechas para corregir el error.
--
-- INSTRUCCIONES:
-- 1. Ejecuta las consultas en orden (SELECT, luego UPDATE)
-- 2. Verifica el ANTES y DESPUÉS
-- 3. Si algo sale mal, usa la sección de ROLLBACK al final
-- =============================================================================

-- PASO 1: Ver estado actual de los pedidos ANTES de la corrección
SELECT
    'ANTES DE CORREGIR' as estado,
    p.ID,
    p.post_date as fecha_local_actual,
    p.post_date_gmt as fecha_utc_actual,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru_calculada,
    pm.meta_value as numero_pedido
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_order_number_formatted'
WHERE p.ID IN (39844, 39843, 39841, 39840)
ORDER BY p.ID;

-- PASO 2: CREAR BACKUP (IMPORTANTE - NO OMITIR)
-- Crea una tabla de respaldo por si necesitas revertir los cambios
DROP TABLE IF EXISTS wpyz_posts_backup_fechas_20251202;

CREATE TABLE wpyz_posts_backup_fechas_20251202 AS
SELECT * FROM wpyz_posts
WHERE ID IN (39844, 39843, 39841, 39840);

-- Verificar que el backup se creó correctamente
SELECT COUNT(*) as registros_respaldados
FROM wpyz_posts_backup_fechas_20251202;
-- Debería mostrar: 4 registros


-- PASO 3: ACTUALIZAR LAS FECHAS (RESTANDO 5 HORAS)
-- Ejecuta estas dos consultas UPDATE:

-- 3.1. Actualizar tabla wpyz_posts
UPDATE wpyz_posts
SET
    post_date = DATE_SUB(post_date, INTERVAL 5 HOUR),
    post_date_gmt = DATE_SUB(post_date_gmt, INTERVAL 5 HOUR),
    post_modified = NOW(),
    post_modified_gmt = UTC_TIMESTAMP()
WHERE ID IN (39844, 39843, 39841, 39840)
AND post_type = 'shop_order';
-- Debería mostrar: 4 row(s) affected

-- 3.2. Actualizar tabla wpyz_wc_orders (HPOS - WooCommerce 8.0+)
UPDATE wpyz_wc_orders
SET
    date_created_gmt = DATE_SUB(date_created_gmt, INTERVAL 5 HOUR),
    date_updated_gmt = UTC_TIMESTAMP()
WHERE id IN (39844, 39843, 39841, 39840);
-- Puede mostrar: 0 o 4 row(s) affected (dependiendo si usas HPOS)


-- PASO 4: Ver estado DESPUÉS de la corrección
SELECT
    'DESPUÉS DE CORREGIR' as estado,
    p.ID,
    p.post_date as fecha_local_corregida,
    p.post_date_gmt as fecha_utc_corregida,
    DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR) as fecha_peru_calculada,
    pm.meta_value as numero_pedido,
    CASE
        WHEN DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) = DATE(DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 HOUR))
        THEN '✓ Fecha de hoy'
        ELSE CONCAT('Fecha: ', DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)))
    END as validacion
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_order_number_formatted'
WHERE p.ID IN (39844, 39843, 39841, 39840)
ORDER BY p.ID;

-- PASO 5: Verificar que ahora aparezcan en la fecha correcta
SELECT
    'VERIFICACIÓN FINAL' as tipo,
    DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) as fecha_peru,
    COUNT(*) as cantidad_pedidos,
    GROUP_CONCAT(p.ID ORDER BY p.ID) as ids_pedidos
FROM wpyz_posts p
WHERE p.ID IN (39844, 39843, 39841, 39840)
GROUP BY DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR))
ORDER BY fecha_peru;

-- =============================================================================
-- ROLLBACK: REVERTIR CAMBIOS (Solo si algo salió mal)
-- =============================================================================
-- Si necesitas revertir los cambios, ejecuta estas consultas:

/*
-- OPCIÓN A: Revertir desde el backup
UPDATE wpyz_posts p
INNER JOIN wpyz_posts_backup_fechas_20251202 pb ON p.ID = pb.ID
SET
    p.post_date = pb.post_date,
    p.post_date_gmt = pb.post_date_gmt,
    p.post_modified = NOW(),
    p.post_modified_gmt = UTC_TIMESTAMP()
WHERE p.ID IN (39844, 39843, 39841, 39840);

-- Verificar que se revirtió correctamente
SELECT
    'DESPUÉS DE REVERTIR' as estado,
    p.ID,
    p.post_date,
    p.post_date_gmt,
    pm.meta_value as numero_pedido
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_order_number_formatted'
WHERE p.ID IN (39844, 39843, 39841, 39840);
*/

-- =============================================================================
-- LIMPIAR BACKUP (Opcional - solo después de confirmar que todo está bien)
-- =============================================================================
-- Una vez que confirmes que todo funciona correctamente, puedes eliminar el backup:
-- DROP TABLE IF EXISTS wpyz_posts_backup_fechas_20251202;
