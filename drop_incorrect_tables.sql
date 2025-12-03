-- =============================================================================
-- SCRIPT PARA ELIMINAR TABLAS INCORRECTAS
-- =============================================================================
-- Propósito: Eliminar tablas creadas con prefijo wpyz_woo_ que fueron
--            creadas por error antes de la corrección
--
-- Tablas a eliminar:
-- - wpyz_woo_orders_ext
-- - wpyz_woo_orders_ext_items
--
-- IMPORTANTE: Este script es seguro de ejecutar incluso si las tablas
--             no existen (usa IF EXISTS)
-- =============================================================================

-- Ver si las tablas existen antes de eliminarlas
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    CREATE_TIME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME IN ('wpyz_woo_orders_ext', 'wpyz_woo_orders_ext_items')
ORDER BY TABLE_NAME;

-- =============================================================================
-- ELIMINACIÓN DE TABLAS
-- =============================================================================

-- Eliminar tabla de items primero (por la foreign key)
DROP TABLE IF EXISTS wpyz_woo_orders_ext_items;

-- Eliminar tabla de pedidos externos
DROP TABLE IF EXISTS wpyz_woo_orders_ext;

-- =============================================================================
-- VERIFICACIÓN
-- =============================================================================

-- Verificar que las tablas fueron eliminadas
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN '✓ Tablas eliminadas exitosamente'
        ELSE '✗ Aún existen tablas con prefijo wpyz_woo_'
    END as resultado,
    COUNT(*) as tablas_restantes
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME LIKE 'wpyz_woo_%';

-- Listar todas las tablas personalizadas (woo_) que SÍ deberían existir
SELECT
    '=== TABLAS PERSONALIZADAS (woo_) ===' as info,
    '' as tabla
UNION ALL
SELECT
    'Tabla existente:' as info,
    TABLE_NAME as tabla
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME LIKE 'woo_%'
ORDER BY tabla;

-- =============================================================================
-- NOTAS
-- =============================================================================
-- Después de ejecutar este script, ejecuta create_orders_external_table.sql
-- para crear las tablas con el prefijo correcto (woo_)
-- =============================================================================
