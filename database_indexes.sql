-- ============================================
-- Índices de Base de Datos para Optimización
-- ============================================
-- Estos índices mejoran significativamente el rendimiento
-- de las consultas en la creación de pedidos.
--
-- INSTRUCCIONES:
-- 1. Hacer backup de la base de datos antes de ejecutar
-- 2. Ejecutar estos comandos en MySQL/MariaDB
-- 3. Verificar que los índices se crearon correctamente

-- ============================================
-- 1. Índice compuesto en wpyz_postmeta
-- ============================================
-- Mejora las consultas de metadata de productos y pedidos
-- Usado en: Stock updates, product meta queries
-- Impacto: Reduce tiempo de consulta de O(n) a O(log n)

-- Verificar si el índice ya existe
SELECT COUNT(*) as index_exists
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'wpyz_postmeta'
  AND index_name = 'idx_post_meta';

-- Crear índice si no existe
ALTER TABLE wpyz_postmeta
ADD INDEX idx_post_meta (post_id, meta_key);

-- ============================================
-- 2. Índice compuesto en wpyz_posts
-- ============================================
-- Mejora las consultas de productos padres y variaciones
-- Usado en: Variation lookups, product hierarchy queries
-- Impacto: Acelera búsqueda de variaciones de productos

-- Verificar si el índice ya existe
SELECT COUNT(*) as index_exists
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'wpyz_posts'
  AND index_name = 'idx_parent_type';

-- Crear índice si no existe
ALTER TABLE wpyz_posts
ADD INDEX idx_parent_type (post_parent, post_type);

-- ============================================
-- 3. Índice compuesto en wpyz_woocommerce_order_itemmeta
-- ============================================
-- Mejora las consultas de metadata de items de pedidos
-- Usado en: Order item meta insertions and lookups
-- Impacto: Acelera inserción y búsqueda de metadata de items

-- Verificar si el índice ya existe
SELECT COUNT(*) as index_exists
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'wpyz_woocommerce_order_itemmeta'
  AND index_name = 'idx_item_meta';

-- Crear índice si no existe
ALTER TABLE wpyz_woocommerce_order_itemmeta
ADD INDEX idx_item_meta (order_item_id, meta_key);

-- ============================================
-- Verificación Final
-- ============================================
-- Listar todos los índices creados

SHOW INDEX FROM wpyz_postmeta WHERE Key_name = 'idx_post_meta';
SHOW INDEX FROM wpyz_posts WHERE Key_name = 'idx_parent_type';
SHOW INDEX FROM wpyz_woocommerce_order_itemmeta WHERE Key_name = 'idx_item_meta';

-- ============================================
-- Análisis de Tablas (Opcional)
-- ============================================
-- Ejecutar después de crear índices para optimizar estadísticas

ANALYZE TABLE wpyz_postmeta;
ANALYZE TABLE wpyz_posts;
ANALYZE TABLE wpyz_woocommerce_order_itemmeta;

-- ============================================
-- Notas de Rendimiento
-- ============================================
-- Antes de los índices:
--   - Consultas de metadata: Full table scan (lento)
--   - Tiempo por pedido: ~25-30 segundos
--
-- Después de los índices:
--   - Consultas de metadata: Index scan (rápido)
--   - Tiempo estimado por pedido: ~1-2 segundos
--
-- Mejora esperada: 10-15x más rápido
