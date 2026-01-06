-- =====================================================
-- Script de Diagnóstico: Productos con Costo $0.00
-- =====================================================
-- Propósito: Investigar por qué ciertos productos muestran costo unitario en $0.00
-- Fecha: 2025-12-22
-- =====================================================

-- Productos de ejemplo con problema
SET @sku1 = '1007479-1007210-U';
SET @sku2 = '1007479-1007216-U';
SET @sku3 = '1007479-1007212-U';
SET @sku4 = '1007479-1007214-U';

-- =====================================================
-- 1. Verificar si los SKUs existen en wpyz_posts
-- =====================================================
SELECT
    'SKUs en wpyz_posts' as check_name,
    p.ID,
    p.post_title,
    p.post_type,
    p.post_status,
    pm.meta_value as sku
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sku'
WHERE pm.meta_value IN (@sku1, @sku2, @sku3, @sku4)
ORDER BY pm.meta_value;

-- =====================================================
-- 2. Verificar si los SKUs existen en woo_products_fccost
-- =====================================================
SELECT
    'SKUs en woo_products_fccost' as check_name,
    sku,
    desc1,
    color,
    size,
    FCLastCost,
    fecha_importacion
FROM woo_products_fccost
WHERE sku IN (@sku1, @sku2, @sku3, @sku4)
ORDER BY sku;

-- =====================================================
-- 3. Verificar SKUs similares (sin guiones, variaciones)
-- =====================================================
SELECT
    'SKUs similares en fccost (búsqueda LIKE)' as check_name,
    sku,
    desc1,
    FCLastCost,
    fecha_importacion
FROM woo_products_fccost
WHERE sku LIKE '1007479%'
ORDER BY sku
LIMIT 20;

-- =====================================================
-- 4. Verificar collation de columnas SKU
-- =====================================================
SELECT
    'Collation de pm.meta_value (_sku)' as check_name,
    COLLATION(pm.meta_value) as collation_name
FROM wpyz_postmeta pm
WHERE pm.meta_key = '_sku'
LIMIT 1;

SELECT
    'Collation de fc.sku' as check_name,
    COLLATION(fc.sku) as collation_name
FROM woo_products_fccost fc
LIMIT 1;

-- =====================================================
-- 5. Probar JOIN con y sin COLLATE para ver diferencias
-- =====================================================
-- JOIN sin COLLATE (puede fallar)
SELECT
    'JOIN sin COLLATE' as check_name,
    pm.meta_value as sku_woocommerce,
    fc.sku as sku_fccost,
    fc.FCLastCost
FROM wpyz_postmeta pm
LEFT JOIN woo_products_fccost fc ON pm.meta_value = fc.sku
WHERE pm.meta_key = '_sku'
  AND pm.meta_value IN (@sku1, @sku2, @sku3, @sku4);

-- JOIN con COLLATE utf8mb4_unicode_520_ci
SELECT
    'JOIN con COLLATE utf8mb4_unicode_520_ci' as check_name,
    pm.meta_value as sku_woocommerce,
    fc.sku as sku_fccost,
    fc.FCLastCost
FROM wpyz_postmeta pm
LEFT JOIN woo_products_fccost fc
    ON pm.meta_value COLLATE utf8mb4_unicode_520_ci = fc.sku COLLATE utf8mb4_unicode_520_ci
WHERE pm.meta_key = '_sku'
  AND pm.meta_value IN (@sku1, @sku2, @sku3, @sku4);

-- =====================================================
-- 6. Verificar espacios en blanco o caracteres invisibles
-- =====================================================
SELECT
    'Verificar espacios en SKUs de WooCommerce' as check_name,
    pm.meta_value as sku,
    LENGTH(pm.meta_value) as longitud,
    CHAR_LENGTH(pm.meta_value) as char_length,
    HEX(pm.meta_value) as hex_value
FROM wpyz_postmeta pm
WHERE pm.meta_key = '_sku'
  AND pm.meta_value IN (@sku1, @sku2, @sku3, @sku4);

SELECT
    'Verificar espacios en SKUs de fccost' as check_name,
    fc.sku,
    LENGTH(fc.sku) as longitud,
    CHAR_LENGTH(fc.sku) as char_length,
    HEX(fc.sku) as hex_value
FROM woo_products_fccost fc
WHERE fc.sku LIKE '1007479%'
LIMIT 10;

-- =====================================================
-- 7. Buscar todos los SKUs de estos productos en fccost
-- =====================================================
SELECT
    'Todos los registros de fccost con prefijo 1007479' as check_name,
    sku,
    desc1,
    color,
    size,
    FCLastCost,
    fecha_importacion
FROM woo_products_fccost
WHERE sku LIKE '1007479%'
ORDER BY sku;

-- =====================================================
-- 8. Verificar si FCLastCost es NULL o 0
-- =====================================================
SELECT
    'Distribución de FCLastCost en tabla fccost' as check_name,
    CASE
        WHEN FCLastCost IS NULL THEN 'NULL'
        WHEN FCLastCost = 0 THEN 'ZERO'
        WHEN FCLastCost > 0 THEN 'POSITIVE'
        ELSE 'OTHER'
    END as cost_status,
    COUNT(*) as cantidad
FROM woo_products_fccost
GROUP BY cost_status;

-- =====================================================
-- 9. Estadísticas generales de la tabla fccost
-- =====================================================
SELECT
    'Estadísticas generales de woo_products_fccost' as check_name,
    COUNT(*) as total_registros,
    COUNT(DISTINCT sku) as skus_unicos,
    AVG(FCLastCost) as costo_promedio,
    MIN(FCLastCost) as costo_minimo,
    MAX(FCLastCost) as costo_maximo,
    SUM(CASE WHEN FCLastCost = 0 OR FCLastCost IS NULL THEN 1 ELSE 0 END) as productos_sin_costo
FROM woo_products_fccost;

-- =====================================================
-- 10. Query completo de diagnóstico para estos productos
-- =====================================================
SELECT
    'Diagnóstico completo' as check_name,
    p.ID as product_id,
    p.post_title as product_name,
    pm_sku.meta_value as sku_woocommerce,
    pm_stock.meta_value as current_stock,
    sh.new_stock as history_stock,
    sh.changed_by as last_updated_by,
    fc.sku as sku_fccost,
    fc.FCLastCost as costo_fccost,
    fc.desc1 as descripcion_fccost,
    CASE
        WHEN fc.sku IS NULL THEN 'SKU no encontrado en fccost'
        WHEN fc.FCLastCost IS NULL THEN 'FCLastCost es NULL'
        WHEN fc.FCLastCost = 0 THEN 'FCLastCost es ZERO'
        ELSE 'OK'
    END as diagnostico
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm_sku
    ON p.ID = pm_sku.post_id
    AND pm_sku.meta_key = '_sku'
LEFT JOIN wpyz_postmeta pm_stock
    ON p.ID = pm_stock.post_id
    AND pm_stock.meta_key = '_stock'
INNER JOIN (
    SELECT
        product_id,
        new_stock,
        changed_by,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY created_at DESC) as rn
    FROM wpyz_stock_history
    WHERE new_stock = 0
) sh ON p.ID = sh.product_id AND sh.rn = 1
LEFT JOIN woo_products_fccost fc
    ON pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci = fc.sku COLLATE utf8mb4_unicode_520_ci
WHERE pm_sku.meta_value IN (@sku1, @sku2, @sku3, @sku4)
ORDER BY pm_sku.meta_value;
