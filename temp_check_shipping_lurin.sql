-- ============================================================
-- VERIFICAR MÉTODOS DE ENVÍO PARA LURÍN
-- ============================================================

-- 1. Ver todos los métodos de envío activos
SELECT
    p.ID,
    p.post_title,
    p.post_status,
    p.post_type
FROM wpyz_posts p
WHERE p.post_type = 'was'
ORDER BY p.ID;

-- 2. Ver metadatos de cada método (especialmente conditions)
SELECT
    p.ID,
    p.post_title,
    pm.meta_key,
    LEFT(pm.meta_value, 200) AS meta_value_preview
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND pm.meta_key IN ('_was_shipping_method', '_was_shipping_method_conditions')
ORDER BY p.ID, pm.meta_key;

-- 3. Buscar específicamente "Lurin" en las condiciones (con y sin tilde)
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
        pm.meta_value LIKE '%Lurin%'
        OR pm.meta_value LIKE '%Lurín%'
        OR pm.meta_value LIKE '%LURIN%'
        OR pm.meta_value LIKE '%LURÍN%'
    );

-- 4. Ver el método "Envío 1 día hábil" específicamente (si existe)
SELECT
    p.ID,
    p.post_title,
    pm.meta_key,
    pm.meta_value
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND p.post_title LIKE '%1 día%'
ORDER BY pm.meta_key;
