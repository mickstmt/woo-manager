-- =====================================================
-- SCRIPT DE ÍNDICES PARA OPTIMIZACIÓN DE RENDIMIENTO
-- WooCommerce Manager
-- Prefijo de tablas: wp_
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
-- - Script seguro: verifica antes de crear cada índice
-- =====================================================

-- Cambiar por el nombre de tu base de datos
-- USE tu_base_de_datos;

-- Deshabilitar validación estricta temporalmente
SET SESSION sql_mode = '';

-- =====================================================
-- SECCIÓN 1: ÍNDICES PARA PRODUCTOS (wp_posts y wp_postmeta)
-- =====================================================

-- =====================================================
-- 1. ÍNDICE CRÍTICO: Búsquedas por meta_key + meta_value
-- =====================================================
-- Este es el más importante: acelera búsquedas por SKU, precio, stock
-- Mejora estimada: 10-100x en búsquedas

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_postmeta'
    AND index_name = 'idx_meta_key_value');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_meta_key_value already exists''',
    'CREATE INDEX idx_meta_key_value ON wp_postmeta(meta_key, meta_value(100))');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 2. ÍNDICE: Filtros de productos por tipo y estado
-- =====================================================

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_posts'
    AND index_name = 'idx_posts_type_status');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_posts_type_status already exists''',
    'CREATE INDEX idx_posts_type_status ON wp_posts(post_type, post_status)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 3. ÍNDICE: Búsqueda de variaciones por producto padre
-- =====================================================

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_posts'
    AND index_name = 'idx_posts_parent');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_posts_parent already exists''',
    'CREATE INDEX idx_posts_parent ON wp_posts(post_parent)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 4. ÍNDICE: Ordenamiento por fecha
-- =====================================================

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_posts'
    AND index_name = 'idx_posts_date');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_posts_date already exists''',
    'CREATE INDEX idx_posts_date ON wp_posts(post_date)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- 5. ÍNDICE: Meta por post_id
-- =====================================================

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_postmeta'
    AND index_name = 'idx_postmeta_post_id');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_postmeta_post_id already exists''',
    'CREATE INDEX idx_postmeta_post_id ON wp_postmeta(post_id)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- SECCIÓN 2: ÍNDICES PARA PEDIDOS (wp_wc_orders)
-- =====================================================

-- Índices en wp_wc_orders
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders'
    AND index_name = 'idx_orders_status');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_status already exists''',
    'CREATE INDEX idx_orders_status ON wp_wc_orders(status)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders'
    AND index_name = 'idx_orders_date_created');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_date_created already exists''',
    'CREATE INDEX idx_orders_date_created ON wp_wc_orders(date_created_gmt)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders'
    AND index_name = 'idx_orders_billing_email');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_billing_email already exists''',
    'CREATE INDEX idx_orders_billing_email ON wp_wc_orders(billing_email)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Índices en wp_wc_orders_meta
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders_meta'
    AND index_name = 'idx_orders_meta_order_id');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_meta_order_id already exists''',
    'CREATE INDEX idx_orders_meta_order_id ON wp_wc_orders_meta(order_id)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders_meta'
    AND index_name = 'idx_orders_meta_key');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_meta_key already exists''',
    'CREATE INDEX idx_orders_meta_key ON wp_wc_orders_meta(meta_key)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_orders_meta'
    AND index_name = 'idx_orders_meta_order_key');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_orders_meta_order_key already exists''',
    'CREATE INDEX idx_orders_meta_order_key ON wp_wc_orders_meta(order_id, meta_key)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Índices en wp_woocommerce_order_items
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_woocommerce_order_items'
    AND index_name = 'idx_order_items_order_id');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_order_items_order_id already exists''',
    'CREATE INDEX idx_order_items_order_id ON wp_woocommerce_order_items(order_id)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_woocommerce_order_items'
    AND index_name = 'idx_order_items_type');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_order_items_type already exists''',
    'CREATE INDEX idx_order_items_type ON wp_woocommerce_order_items(order_item_type)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Índices en wp_wc_order_addresses
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_order_addresses'
    AND index_name = 'idx_addresses_order_id');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_addresses_order_id already exists''',
    'CREATE INDEX idx_addresses_order_id ON wp_wc_order_addresses(order_id)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_order_addresses'
    AND index_name = 'idx_addresses_type');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_addresses_type already exists''',
    'CREATE INDEX idx_addresses_type ON wp_wc_order_addresses(address_type)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_order_addresses'
    AND index_name = 'idx_addresses_email');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_addresses_email already exists''',
    'CREATE INDEX idx_addresses_email ON wp_wc_order_addresses(email)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @exist := (SELECT COUNT(*) FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = 'wp_wc_order_addresses'
    AND index_name = 'idx_addresses_phone');
SET @sqlstmt := IF(@exist > 0, 'SELECT ''Index idx_addresses_phone already exists''',
    'CREATE INDEX idx_addresses_phone ON wp_wc_order_addresses(phone)');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- =====================================================
-- VERIFICACIÓN: Ver todos los índices creados
-- =====================================================

SELECT '=== ÍNDICES EN TABLAS DE PRODUCTOS ===' AS '';

SELECT
    table_name,
    index_name,
    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
    index_type
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name IN ('wp_posts', 'wp_postmeta')
  AND index_name LIKE 'idx_%'
GROUP BY table_name, index_name, index_type
ORDER BY table_name, index_name;

SELECT '=== ÍNDICES EN TABLAS DE PEDIDOS ===' AS '';

SELECT
    table_name,
    index_name,
    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
    index_type
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name IN ('wp_wc_orders', 'wp_wc_orders_meta', 'wp_woocommerce_order_items', 'wp_wc_order_addresses')
  AND index_name LIKE 'idx_%'
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
  AND table_name IN (
      'wp_posts',
      'wp_postmeta',
      'wp_wc_orders',
      'wp_wc_orders_meta',
      'wp_woocommerce_order_items',
      'wp_wc_order_addresses'
  )
ORDER BY (data_length + index_length) DESC;

-- =====================================================
-- OPTIMIZACIÓN ADICIONAL (OPCIONAL)
-- =====================================================
-- Si las tablas son muy grandes, optimizar después de crear índices

-- OPTIMIZE TABLE wp_postmeta;
-- OPTIMIZE TABLE wp_posts;
-- OPTIMIZE TABLE wp_wc_orders;
-- OPTIMIZE TABLE wp_wc_orders_meta;
-- OPTIMIZE TABLE wp_woocommerce_order_items;
-- OPTIMIZE TABLE wp_wc_order_addresses;

-- =====================================================
-- NOTAS FINALES
-- =====================================================
-- 1. Los índices ocupan espacio en disco (normal)
-- 2. Pueden hacer inserts/updates ligeramente más lentos (despreciable)
-- 3. Mejoran DRAMÁTICAMENTE las lecturas (tu caso de uso principal)
-- 4. Se mantienen automáticamente, no necesitas hacer nada después
-- 5. Script verifica índices existentes antes de crearlos
--
-- RECOMENDACIÓN:
-- - Ejecutar durante horas de bajo tráfico
-- - En producción puede tardar 5-15 minutos según tamaño de BD
-- =====================================================

-- Restaurar sql_mode
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
