-- Verificar dirección de envío del pedido #43177
-- Para entender dónde está la referencia "Casa puerta marron"

-- 1. Verificar dirección en wpyz_wc_order_addresses
SELECT
    'Tabla: wpyz_wc_order_addresses' as fuente,
    address_type,
    address_1,
    address_2,
    city,
    state,
    postcode
FROM wpyz_wc_order_addresses
WHERE order_id = 43177 AND address_type = 'shipping';

-- 2. Verificar metadatos relacionados con dirección
SELECT
    'Tabla: wpyz_wc_orders_meta' as fuente,
    meta_key,
    meta_value
FROM wpyz_wc_orders_meta
WHERE order_id = 43177
  AND (meta_key LIKE '%shipping%address%'
       OR meta_key LIKE '%reference%'
       OR meta_key LIKE '%referencia%'
       OR meta_key = '_shipping_address_2');

-- 3. Verificar en postmeta (legacy)
SELECT
    'Tabla: wpyz_postmeta' as fuente,
    meta_key,
    meta_value
FROM wpyz_postmeta
WHERE post_id = 43177
  AND (meta_key LIKE '%shipping%address%'
       OR meta_key LIKE '%reference%'
       OR meta_key LIKE '%referencia%'
       OR meta_key = '_shipping_address_2');
