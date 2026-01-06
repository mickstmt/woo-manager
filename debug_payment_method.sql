-- Script para investigar dónde se almacena el método de pago para pedidos WhatsApp recientes
-- Compara pedidos antiguos (W-00001 a W-00021) vs nuevos (W-00022+)

-- 1. Verificar si existen datos en wpyz_wc_orders_meta con claves relacionadas a payment_method
SELECT
    'Pedidos con payment method en META table' as tipo,
    om_numero.meta_value as numero_pedido,
    om_payment.meta_key,
    om_payment.meta_value
FROM wpyz_wc_orders_meta om_numero
INNER JOIN wpyz_wc_orders_meta om_payment
    ON om_numero.order_id = om_payment.order_id
WHERE om_numero.meta_key = '_order_number'
    AND om_numero.meta_value LIKE 'W-%'
    AND om_payment.meta_key IN ('_payment_method', '_payment_method_title', 'payment_method', 'payment_method_title')
ORDER BY om_numero.meta_value DESC
LIMIT 50;

-- 2. Comparar campos directos de wpyz_wc_orders para pedidos antiguos vs nuevos
SELECT
    'Campos directos en wc_orders table' as tipo,
    om_numero.meta_value as numero_pedido,
    o.payment_method,
    o.payment_method_title,
    o.date_created_gmt
FROM wpyz_wc_orders o
LEFT JOIN wpyz_wc_orders_meta om_numero
    ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'
WHERE om_numero.meta_value LIKE 'W-%'
ORDER BY om_numero.meta_value DESC
LIMIT 50;

-- 3. Ver todas las meta_keys disponibles para un pedido nuevo (ej: W-00022)
SELECT
    'Todas las meta keys para W-00022' as tipo,
    meta_key,
    meta_value
FROM wpyz_wc_orders_meta
WHERE order_id = (
    SELECT order_id
    FROM wpyz_wc_orders_meta
    WHERE meta_key = '_order_number'
        AND meta_value = 'W-00022'
    LIMIT 1
)
ORDER BY meta_key;

-- 4. Ver todas las meta_keys disponibles para un pedido antiguo (ej: W-00001)
SELECT
    'Todas las meta keys para W-00001' as tipo,
    meta_key,
    meta_value
FROM wpyz_wc_orders_meta
WHERE order_id = (
    SELECT order_id
    FROM wpyz_wc_orders_meta
    WHERE meta_key = '_order_number'
        AND meta_value = 'W-00001'
    LIMIT 1
)
ORDER BY meta_key;
