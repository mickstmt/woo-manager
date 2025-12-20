-- ============================================================
-- ANALIZAR PEDIDO 40682 - MÉTODO DE ENVÍO
-- ============================================================

-- 1. Ver información básica del pedido
SELECT
    o.id,
    o.status,
    o.total_amount,
    o.date_created_gmt
FROM wpyz_wc_orders o
WHERE o.id = 40682;

-- 2. Ver TODOS los metadatos del pedido
SELECT
    om.meta_key,
    om.meta_value
FROM wpyz_wc_orders_meta om
WHERE om.order_id = 40682
ORDER BY om.meta_key;

-- 3. Ver dirección de envío del pedido
SELECT
    oa.address_type,
    oa.first_name,
    oa.last_name,
    oa.address_1,
    oa.address_2,
    oa.city,
    oa.state,
    oa.postcode,
    oa.country
FROM wpyz_wc_order_addresses oa
WHERE oa.order_id = 40682;

-- 4. Ver items del pedido (incluyendo shipping)
SELECT
    oi.order_item_id,
    oi.order_item_name,
    oi.order_item_type
FROM wpyz_woocommerce_order_items oi
WHERE oi.order_id = 40682
ORDER BY oi.order_item_type, oi.order_item_id;

-- 5. Ver metadatos de TODOS los items (productos Y shipping)
SELECT
    oi.order_item_id,
    oi.order_item_name,
    oi.order_item_type,
    oim.meta_key,
    oim.meta_value
FROM wpyz_woocommerce_order_items oi
INNER JOIN wpyz_woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
WHERE oi.order_id = 40682
ORDER BY oi.order_item_type, oi.order_item_id, oim.meta_key;

-- 6. Ver SOLO el item de shipping y sus metadatos
SELECT
    oi.order_item_id,
    oi.order_item_name AS shipping_method_title,
    oim.meta_key,
    oim.meta_value
FROM wpyz_woocommerce_order_items oi
LEFT JOIN wpyz_woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
WHERE oi.order_id = 40682
    AND oi.order_item_type = 'shipping'
ORDER BY oim.meta_key;

-- 7. Buscar el método de envío en wpyz_posts usando el method_id del shipping item
-- (Primero necesitamos el method_id del query anterior, pero intentemos con pattern matching)
SELECT
    p.ID,
    p.post_title,
    p.post_type,
    p.post_status
FROM wpyz_posts p
WHERE p.post_type = 'was'
    AND p.post_status = 'publish'
    AND (
        p.post_title LIKE '%Rápido%'
        OR p.post_title LIKE '%Rapido%'
        OR p.post_title LIKE '%1 día%'
        OR p.post_title LIKE '%1 dia%'
    )
ORDER BY p.ID;
