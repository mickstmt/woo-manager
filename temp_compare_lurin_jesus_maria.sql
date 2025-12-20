-- ============================================================
-- COMPARAR LURÍN VS JESÚS MARÍA EN MÉTODOS DE ENVÍO
-- ============================================================

-- 1. Buscar "Jesús María" en las condiciones (funciona)
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
        pm.meta_value LIKE '%Jesús María%'
        OR pm.meta_value LIKE '%Jesus Maria%'
        OR pm.meta_value LIKE '%JESÚS MARÍA%'
        OR pm.meta_value LIKE '%jesus maria%'
    );

-- 2. Buscar "Lurín" en las condiciones (no funciona)
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
        pm.meta_value LIKE '%Lurín%'
        OR pm.meta_value LIKE '%Lurin%'
        OR pm.meta_value LIKE '%LURÍN%'
        OR pm.meta_value LIKE '%lurin%'
    );

-- 3. Ver EXACTAMENTE cómo está guardado en el método "Envío 1 día hábil"
-- (buscar por el título del método)
SELECT
    p.ID,
    p.post_title,
    pm.meta_key,
    pm.meta_value
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND p.post_title LIKE '%1 día%'
    AND pm.meta_key = '_was_shipping_method_conditions';

-- 4. Extraer SOLO la lista de ciudades del método "Envío 1 día hábil"
-- Buscar el patrón "s:5:\"value\";s:" seguido de la longitud y los distritos
SELECT
    p.ID,
    p.post_title,
    -- Extraer desde "value" hasta encontrar los distritos
    SUBSTRING(
        pm.meta_value,
        LOCATE('s:5:"value";', pm.meta_value),
        500
    ) AS ciudades_raw
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND p.post_title LIKE '%1 día%'
    AND pm.meta_key = '_was_shipping_method_conditions';

-- 5. Verificar si "Lurin" o "Lurín" están en CUALQUIER parte de las conditions
SELECT
    p.ID,
    p.post_title,
    CASE
        WHEN pm.meta_value LIKE '%Lurín%' THEN 'Contiene: Lurín (con tilde)'
        WHEN pm.meta_value LIKE '%Lurin%' THEN 'Contiene: Lurin (sin tilde)'
        ELSE 'NO CONTIENE Lurin/Lurín'
    END AS resultado,
    LENGTH(pm.meta_value) AS longitud_total
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND p.post_title LIKE '%1 día%'
    AND pm.meta_key = '_was_shipping_method_conditions';
