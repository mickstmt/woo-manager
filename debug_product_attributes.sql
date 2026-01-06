-- Debug: Ver atributos de productos en un pedido específico
-- Cambiar el order_id por el ID real del pedido que estás viendo

-- 1. Ver todos los items del pedido
SELECT
    oi.order_item_id,
    oi.order_item_name,
    oi.order_item_type
FROM wpyz_woocommerce_order_items oi
WHERE oi.order_id = 1080  -- CAMBIAR ESTE ID
  AND oi.order_item_type = 'line_item';

-- 2. Ver TODOS los meta_key y meta_value de los items
SELECT
    oi.order_item_id,
    oi.order_item_name,
    oim.meta_key,
    oim.meta_value
FROM wpyz_woocommerce_order_items oi
LEFT JOIN wpyz_woocommerce_order_itemmeta oim
    ON oi.order_item_id = oim.order_item_id
WHERE oi.order_id = 1080  -- CAMBIAR ESTE ID
  AND oi.order_item_type = 'line_item'
ORDER BY oi.order_item_id, oim.meta_key;

-- 3. Ver específicamente los atributos (meta_keys que empiezan con 'pa_' o 'attribute_')
SELECT
    oi.order_item_id,
    oi.order_item_name,
    oim.meta_key,
    oim.meta_value
FROM wpyz_woocommerce_order_items oi
LEFT JOIN wpyz_woocommerce_order_itemmeta oim
    ON oi.order_item_id = oim.order_item_id
WHERE oi.order_id = 1080  -- CAMBIAR ESTE ID
  AND oi.order_item_type = 'line_item'
  AND (oim.meta_key LIKE '%pa_%' OR oim.meta_key LIKE 'attribute_%')
ORDER BY oi.order_item_id, oim.meta_key;
