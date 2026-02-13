-- ============================================
-- Query: Mensajes de Tracking de Últimos 5 Pedidos
-- ============================================
-- Este script muestra la información de tracking de los últimos 5 pedidos
-- que tienen tracking asignado, incluyendo mensajes COD completos.

SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    o.status,
    DATE_FORMAT(o.date_created_gmt, '%Y-%m-%d %H:%i') AS fecha_creacion,

    -- Información de tracking
    pm_tracking_number.meta_value AS tracking_message,
    pm_tracking_provider.meta_value AS shipping_provider,

    -- Cliente
    CONCAT(ba.first_name, ' ', ba.last_name) AS customer_name,
    ba.phone AS customer_phone,

    -- Total y COD
    o.total_amount AS total,    
    om_is_cod.meta_value AS is_cod,

    -- Costo de envío
    (SELECT SUM(CAST(oim_cost.meta_value AS DECIMAL(10,2)))
     FROM wpyz_woocommerce_order_items oi
     LEFT JOIN wpyz_woocommerce_order_itemmeta oim_cost
         ON oi.order_item_id = oim_cost.order_item_id
         AND oim_cost.meta_key = 'cost'
     WHERE oi.order_id = o.id
       AND oi.order_item_type = 'shipping'
     LIMIT 1) AS shipping_cost

FROM wpyz_wc_orders o

-- Número de pedido (W-XXXXX o nativo WooCommerce)
LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

-- Dirección de facturación (datos del cliente)
LEFT JOIN wpyz_wc_order_addresses ba
    ON o.id = ba.order_id
    AND ba.address_type = 'billing'

-- Tracking Number (puede ser mensaje completo para COD)
LEFT JOIN wpyz_postmeta pm_tracking_number
    ON o.id = pm_tracking_number.post_id
    AND pm_tracking_number.meta_key = '_tracking_number'

-- Proveedor de Envío
LEFT JOIN wpyz_postmeta pm_tracking_provider
    ON o.id = pm_tracking_provider.post_id
    AND pm_tracking_provider.meta_key = '_tracking_provider'

-- Es COD?
LEFT JOIN wpyz_wc_orders_meta om_is_cod
    ON o.id = om_is_cod.order_id
    AND om_is_cod.meta_key = '_is_cod'

-- Filtrar solo pedidos con tracking asignado
WHERE pm_tracking_number.meta_value IS NOT NULL

-- Ordenar por fecha de creación (más recientes primero)
ORDER BY o.date_created_gmt DESC

-- Limitar a los últimos 5
LIMIT 5;


-- ============================================
-- Query Alternativa: Ver tracking serializado completo
-- ============================================
-- Esta query muestra el valor serializado completo de _wc_shipment_tracking_items

SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS order_number,
    o.status,
    DATE_FORMAT(o.date_created_gmt, '%Y-%m-%d %H:%i') AS fecha_creacion,

    -- Tracking items serializados (formato PHP)
    om_tracking_items.meta_value AS tracking_items_serialized,

    -- Es COD?
    om_is_cod.meta_value AS is_cod

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

-- Tracking items (HPOS)
LEFT JOIN wpyz_wc_orders_meta om_tracking_items
    ON o.id = om_tracking_items.order_id
    AND om_tracking_items.meta_key = '_wc_shipment_tracking_items'

-- Es COD?
LEFT JOIN wpyz_wc_orders_meta om_is_cod
    ON o.id = om_is_cod.order_id
    AND om_is_cod.meta_key = '_is_cod'

WHERE om_tracking_items.meta_value IS NOT NULL

ORDER BY o.date_created_gmt DESC

LIMIT 5;


-- ============================================
-- Query Simplificada: Solo mensaje y proveedor
-- ============================================

SELECT
    o.id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS pedido,
    pm_tracking_provider.meta_value AS proveedor,
    CASE
        WHEN om_is_cod.meta_value = 'yes' THEN 'COD ✓'
        ELSE 'Normal'
    END AS tipo_pago,
    CHAR_LENGTH(pm_tracking_number.meta_value) AS longitud_mensaje,
    pm_tracking_number.meta_value AS mensaje_tracking

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_postmeta pm_tracking_number
    ON o.id = pm_tracking_number.post_id
    AND pm_tracking_number.meta_key = '_tracking_number'

LEFT JOIN wpyz_postmeta pm_tracking_provider
    ON o.id = pm_tracking_provider.post_id
    AND pm_tracking_provider.meta_key = '_tracking_provider'

LEFT JOIN wpyz_wc_orders_meta om_is_cod
    ON o.id = om_is_cod.order_id
    AND om_is_cod.meta_key = '_is_cod'

WHERE pm_tracking_number.meta_value IS NOT NULL

ORDER BY o.date_created_gmt DESC

LIMIT 5;
