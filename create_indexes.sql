-- =====================================================
-- SCRIPT DE ÍNDICES PARA OPTIMIZACIÓN DE RENDIMIENTO
-- WooCommerce Manager
-- =====================================================
--
-- INSTRUCCIONES:
-- 1. Ejecutar PRIMERO en BD de desarrollo (local)
-- 2. Medir mejoras de rendimiento
-- 3. Si funciona bien, ejecutar en producción
--
-- IMPORTANTE:
-- - Estos índices mejoran dramáticamente las búsquedas
-- - Pueden tardar unos minutos en tablas grandes
-- - No afectan los datos, solo mejoran velocidad
-- =====================================================

USE izis_db;  -- Cambiar por el nombre de tu base de datos

-- Deshabilitar validación estricta temporalmente
SET SESSION sql_mode = '';

-- =====================================================
-- 1. ÍNDICE CRÍTICO: Búsquedas por meta_key + meta_value
-- =====================================================
-- Este es el más importante: acelera búsquedas por SKU, precio, stock
-- Mejora estimada: 10-100x en búsquedas

-- Verificar si ya existe
SELECT COUNT(*) as 'index_exists'
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'wpyz_postmeta'
  AND index_name = 'idx_meta_key_value';

-- Crear índice compuesto en meta_key + meta_value
-- NOTA: meta_value(100) indexa solo los primeros 100 caracteres
CREATE INDEX idx_meta_key_value
ON wpyz_postmeta(meta_key, meta_value(100));

-- =====================================================
-- 2. ÍNDICE: Filtros de productos por tipo y estado
-- =====================================================
-- Acelera filtros como: post_type='product' AND post_status='publish'
-- Mejora estimada: 3-10x

CREATE INDEX idx_posts_type_status
ON wpyz_posts(post_type, post_status);

-- =====================================================
-- 3. ÍNDICE: Búsqueda de variaciones por producto padre
-- =====================================================
-- Acelera búsqueda de variaciones: WHERE post_parent = X
-- Mejora estimada: 5-20x

CREATE INDEX idx_posts_parent
ON wpyz_posts(post_parent);

-- =====================================================
-- 4. ÍNDICE: Ordenamiento por fecha
-- =====================================================
-- Acelera listados ordenados por fecha de creación
-- Mejora estimada: 2-5x

CREATE INDEX idx_posts_date
ON wpyz_posts(post_date);

-- =====================================================
-- 5. ÍNDICE: Meta por post_id (probablemente ya existe)
-- =====================================================
-- WooCommerce suele crearlo, pero verificamos

CREATE INDEX idx_postmeta_post_id
ON wpyz_postmeta(post_id);

-- =====================================================
-- VERIFICACIÓN: Ver todos los índices creados
-- =====================================================
SELECT
    table_name,
    index_name,
    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
    index_type,
    ROUND(stat_value * @@innodb_page_size / 1024 / 1024, 2) as size_mb
FROM information_schema.statistics
LEFT JOIN mysql.innodb_index_stats ON (
    statistics.table_name = innodb_index_stats.table_name
    AND statistics.index_name = innodb_index_stats.index_name
    AND stat_name = 'size'
)
WHERE statistics.table_schema = DATABASE()
  AND statistics.table_name IN ('wpyz_posts', 'wpyz_postmeta')
GROUP BY table_name, index_name, index_type
ORDER BY table_name, index_name;

-- =====================================================
-- ANÁLISIS: Ver uso de espacio
-- =====================================================
SELECT
    table_name,
    ROUND(data_length / 1024 / 1024, 2) AS data_size_mb,
    ROUND(index_length / 1024 / 1024, 2) AS index_size_mb,
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_size_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('wpyz_posts', 'wpyz_postmeta')
ORDER BY (data_length + index_length) DESC;

-- =====================================================
-- OPTIMIZACIÓN ADICIONAL (OPCIONAL)
-- =====================================================
-- Si la tabla es muy grande, optimizar después de crear índices

-- OPTIMIZE TABLE wpyz_postmeta;
-- OPTIMIZE TABLE wpyz_posts;

-- =====================================================
-- NOTAS FINALES
-- =====================================================
-- 1. Los índices ocupan espacio en disco (normal)
-- 2. Pueden hacer inserts/updates ligeramente más lentos (despreciable)
-- 3. Mejoran DRAMÁTICAMENTE las lecturas (tu caso de uso principal)
-- 4. Se mantienen automáticamente, no necesitas hacer nada después
--
-- RECOMENDACIÓN:
-- - Ejecutar durante horas de bajo tráfico
-- - En producción puede tardar 5-15 minutos según tamaño de BD
-- =====================================================

-- Restaurar sql_mode
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
