-- ============================================================
-- ENTENDER CÓMO FUNCIONA ADVANCED SHIPPING
-- ============================================================

-- 1. Ver un método específico (ej: ID 15353 que apareció antes con Lurín)
SELECT
    p.ID,
    p.post_title,
    pm.meta_key,
    LEFT(pm.meta_value, 1000) AS meta_value_preview
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.ID = 15353
ORDER BY pm.meta_key;

-- 2. Ver las condiciones completas del método que SÍ tiene "San Martín de Porres"
-- (necesitamos encontrar cuál es, busquemos todos los que tienen este distrito)
SELECT
    p.ID,
    p.post_title
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND pm.meta_key = '_was_shipping_method_conditions'
    AND (
        pm.meta_value LIKE '%San Martín de Porres%'
        OR pm.meta_value LIKE '%San Martin de Porres%'
    );

-- 3. Ver las condiciones del método que tiene San Martín de Porres
-- (asumiendo que hay uno, necesito ver su estructura completa)
SELECT
    p.ID,
    p.post_title,
    pm.meta_value
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND pm.meta_key = '_was_shipping_method_conditions'
    AND (
        pm.meta_value LIKE '%San Martín de Porres%'
        OR pm.meta_value LIKE '%San Martin de Porres%'
    )
LIMIT 1;

-- 4. Ver opciones del plugin Advanced Shipping en wp_options
SELECT
    option_name,
    LEFT(option_value, 500) AS option_value_preview
FROM wpyz_options
WHERE option_name LIKE '%advanced_shipping%'
    OR option_name LIKE '%was_%';
