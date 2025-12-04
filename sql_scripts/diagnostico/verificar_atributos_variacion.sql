-- =============================================================================
-- SCRIPT PARA VERIFICAR ATRIBUTOS DE UNA VARIACIÓN ESPECÍFICA
-- =============================================================================
-- Propósito: Identificar de dónde vienen los atributos incorrectos (ej: "Conector")
-- =============================================================================

-- 1. Buscar la variación con SKU 1007346-SGW7 (del ejemplo de la captura)
SELECT
    '=== INFORMACIÓN DE LA VARIACIÓN ===' as info,
    p.ID as variation_id,
    p.post_title as titulo,
    p.post_parent as producto_padre_id,
    p.post_status as estado
FROM wpyz_posts p
WHERE p.post_type = 'product_variation'
    AND p.ID IN (
        SELECT post_id
        FROM wpyz_postmeta
        WHERE meta_key = '_sku'
        AND meta_value = '1007346-SGW7'
    );

-- 2. Ver TODOS los metadatos de esta variación que empiezan con 'attribute_'
SELECT
    '=== METADATOS attribute_* DE LA VARIACIÓN ===' as info,
    pm.meta_id,
    pm.post_id,
    pm.meta_key,
    pm.meta_value,
    CASE
        WHEN pm.meta_key LIKE 'attribute_pa_%' THEN CONCAT('Atributo global: ', REPLACE(pm.meta_key, 'attribute_pa_', ''))
        WHEN pm.meta_key LIKE 'attribute_%' THEN CONCAT('Atributo personalizado: ', REPLACE(pm.meta_key, 'attribute_', ''))
        ELSE 'Otro'
    END as tipo_atributo
FROM wpyz_postmeta pm
INNER JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE p.post_type = 'product_variation'
    AND p.ID IN (
        SELECT post_id
        FROM wpyz_postmeta
        WHERE meta_key = '_sku'
        AND meta_value = '1007346-SGW7'
    )
    AND pm.meta_key LIKE 'attribute_%'
ORDER BY pm.meta_key;

-- 3. Ver los atributos del PRODUCTO PADRE
SELECT
    '=== ATRIBUTOS DEL PRODUCTO PADRE ===' as info,
    pm.meta_key,
    pm.meta_value
FROM wpyz_postmeta pm
WHERE pm.post_id = (
    SELECT p.post_parent
    FROM wpyz_posts p
    WHERE p.post_type = 'product_variation'
        AND p.ID IN (
            SELECT post_id
            FROM wpyz_postmeta
            WHERE meta_key = '_sku'
            AND meta_value = '1007346-SGW7'
        )
)
    AND pm.meta_key = '_product_attributes'
LIMIT 1;

-- 4. Ver ejemplos de otras variaciones del mismo producto padre
SELECT
    '=== OTRAS VARIACIONES DEL MISMO PRODUCTO ===' as info,
    p.ID as variation_id,
    p.post_title,
    pm_sku.meta_value as sku,
    GROUP_CONCAT(
        CONCAT(pm_attr.meta_key, '=', pm_attr.meta_value)
        SEPARATOR ' | '
    ) as atributos
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_sku ON p.ID = pm_sku.post_id AND pm_sku.meta_key = '_sku'
LEFT JOIN wpyz_postmeta pm_attr ON p.ID = pm_attr.post_id AND pm_attr.meta_key LIKE 'attribute_%'
WHERE p.post_type = 'product_variation'
    AND p.post_parent = (
        SELECT parent.post_parent
        FROM wpyz_posts parent
        WHERE parent.post_type = 'product_variation'
            AND parent.ID IN (
                SELECT post_id
                FROM wpyz_postmeta
                WHERE meta_key = '_sku'
                AND meta_value = '1007346-SGW7'
            )
    )
GROUP BY p.ID, p.post_title, pm_sku.meta_value
ORDER BY p.ID;

-- 5. Buscar si existe un atributo llamado "conector" o "plateado" en algún lugar
SELECT
    '=== BÚSQUEDA DE "CONECTOR" O "PLATEADO" ===' as info,
    pm.post_id,
    p.post_title,
    p.post_type,
    pm.meta_key,
    pm.meta_value
FROM wpyz_postmeta pm
INNER JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE (
    pm.meta_key LIKE '%conector%'
    OR pm.meta_value LIKE '%conector%'
    OR pm.meta_value LIKE '%plateado%'
)
AND p.ID IN (
    -- Obtener el ID de la variación y su padre
    SELECT p2.ID FROM wpyz_posts p2 WHERE p2.ID IN (
        SELECT post_id FROM wpyz_postmeta WHERE meta_key = '_sku' AND meta_value = '1007346-SGW7'
    )
    UNION
    SELECT p2.post_parent FROM wpyz_posts p2 WHERE p2.ID IN (
        SELECT post_id FROM wpyz_postmeta WHERE meta_key = '_sku' AND meta_value = '1007346-SGW7'
    )
)
ORDER BY pm.meta_key;

-- =============================================================================
-- INTERPRETACIÓN:
-- =============================================================================
-- Las consultas anteriores nos ayudarán a identificar:
-- 1. El ID exacto de la variación con problema
-- 2. Qué metadatos attribute_* tiene registrados en la BD
-- 3. Si hay metadatos duplicados o incorrectos
-- 4. Si el problema viene del producto padre
-- 5. De dónde sale el valor "conector" o "plateado"
-- =============================================================================
