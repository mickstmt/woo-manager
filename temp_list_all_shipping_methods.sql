-- ============================================================
-- LISTAR TODOS LOS MÉTODOS DE ENVÍO ACTIVOS
-- ============================================================

-- Ver todos los métodos con su ID y título del post
SELECT
    p.ID,
    p.post_title,
    p.post_status,
    p.post_date
FROM wpyz_posts p
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
ORDER BY p.ID;

-- ============================================================
-- Ver el shipping_title (nombre que se muestra) de cada método
-- ============================================================
SELECT
    p.ID,
    p.post_title AS post_title,
    pm_method.meta_value AS shipping_method_data
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_method ON p.ID = pm_method.post_id
    AND pm_method.meta_key = '_was_shipping_method'
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
ORDER BY p.ID;

-- ============================================================
-- Buscar el método que contiene "1 día" en el título
-- ============================================================
SELECT
    p.ID,
    p.post_title
FROM wpyz_posts p
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND (
        p.post_title LIKE '%1 día%'
        OR p.post_title LIKE '%1 dia%'
    );

-- ============================================================
-- Ver condiciones del método que contiene "1 día"
-- ============================================================
SELECT
    p.ID,
    p.post_title,
    pm.meta_key,
    LEFT(pm.meta_value, 500) AS meta_value_preview
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND (
        p.post_title LIKE '%1 día%'
        OR p.post_title LIKE '%1 dia%'
    )
    AND pm.meta_key IN ('_was_shipping_method', '_was_shipping_method_conditions')
ORDER BY p.ID, pm.meta_key;
