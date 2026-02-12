-- Consulta de productos creados desde el 01 de diciembre de 2025 hasta hoy
-- Incluye ID, Nombre, SKU, Fecha de Creación y Estado
SELECT p.ID as 'Producto ID',
    p.post_title as 'Nombre del Producto',
    pm_sku.meta_value as 'SKU',
    DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) as 'Fecha Creación (PE)',
    p.post_status as 'Estado'
FROM wpyz_posts p
    LEFT JOIN wpyz_postmeta pm_sku ON p.ID = pm_sku.post_id
    AND pm_sku.meta_key = '_sku'
WHERE p.post_type = 'product'
    AND p.post_status != 'trash'
    AND DATE(DATE_SUB(p.post_date_gmt, INTERVAL 5 HOUR)) >= '2025-12-01'
ORDER BY p.post_date_gmt DESC;