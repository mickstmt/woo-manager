-- Consulta de productos padres, variaciones y sus costos unitarios (FC)
-- FILTRO: Creados desde el 01 de diciembre de 2025
-- MUESTRA: Relación entre producto principal y variaciones + costo en FC
-- FIX: Colaciones de MySQL (Error 1267) corregidas con COLLATE
SELECT CASE
        WHEN p.post_type = 'product' THEN p.ID
        ELSE p.post_parent
    END AS 'Parent ID',
    CASE
        WHEN p.post_type = 'product' THEN p.post_title
        ELSE parent.post_title
    END AS 'Producto Padre',
    CASE
        WHEN p.post_type = 'product' THEN 'Producto Simple/Variable'
        ELSE p.post_title
    END AS 'Variación/Nombre',
    pm_sku.meta_value AS 'SKU',
    p.post_type AS 'Tipo Post',
    fc.FCLastCost AS 'Costo Unit (USD)',
    fc.FCLastCost * (
        SELECT tasa_promedio
        FROM woo_tipo_cambio
        WHERE activo = TRUE
        ORDER BY fecha DESC
        LIMIT 1
    ) AS 'Costo Est. (PEN)',
    DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) as 'Fecha Creación'
FROM wpyz_posts p -- Unir con el padre si es una variación
    LEFT JOIN wpyz_posts parent ON p.post_parent = parent.ID
    AND p.post_type = 'product_variation' -- Obtener el SKU
    LEFT JOIN wpyz_postmeta pm_sku ON p.ID = pm_sku.post_id
    AND pm_sku.meta_key = '_sku' -- Unir con la tabla de costos usando COLLATE
    LEFT JOIN woo_products_fccost fc ON pm_sku.meta_value COLLATE utf8mb4_unicode_ci LIKE CONCAT('%', fc.sku, '%') COLLATE utf8mb4_unicode_ci
    AND LENGTH(fc.sku) = 7
WHERE p.post_type IN ('product', 'product_variation')
    AND p.post_status = 'publish'
    AND DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) >= '2025-12-01'
ORDER BY `Parent ID` ASC,
    p.post_type DESC;