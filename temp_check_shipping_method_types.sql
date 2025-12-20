-- Ver todos los metadatos de los métodos que mencionaste
-- "Envío Olva 3 a 4 días" (ID 15355)
-- "Envío Shalom 10" (ID 29884)
-- "Envío 1 día hábil" (necesitamos encontrar el ID exacto)

-- 1. Ver TODOS los métodos que tienen "Olva" o "Shalom" o "1 día"
SELECT
    p.ID,
    p.post_title
FROM wpyz_posts p
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND (
        p.post_title LIKE '%Olva%'
        OR p.post_title LIKE '%Shalom%'
        OR p.post_title LIKE '%1 día%'
        OR p.post_title LIKE '%1 dia%'
    )
ORDER BY p.post_title;

-- 2. Ver el contenido de _was_shipping_method para entender la estructura
SELECT
    p.ID,
    p.post_title,
    pm.meta_value
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND pm.meta_key = '_was_shipping_method'
    AND (
        p.post_title LIKE '%Olva%'
        OR p.post_title LIKE '%Shalom%'
        OR p.post_title LIKE '%1 día%'
    )
LIMIT 5;
