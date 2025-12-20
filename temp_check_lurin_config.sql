-- Ver TODOS los métodos que contienen "Lurin" (con o sin tilde)
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
    );
