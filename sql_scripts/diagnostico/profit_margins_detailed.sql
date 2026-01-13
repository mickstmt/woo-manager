-- ============================================================================
-- SCRIPT DE VALIDACIÓN DE GANANCIAS - DETALLE LÍNEA POR LÍNEA
-- ============================================================================
-- Propósito: Obtener detalle granular de cada producto en cada pedido
-- Uso: Ejecutar directamente en MySQL/MariaDB para auditoría detallada
-- Formato: Una fila por cada producto en cada pedido
--
-- Notas importantes:
-- - Vista más detallada posible: cada línea de pedido
-- - Útil para validar costos unitarios específicos
-- - Permite identificar productos sin SKU o sin costo
-- - Ideal para debugging y validación contra el módulo web
-- ============================================================================

SELECT
    -- Información del pedido
    o.id AS pedido_id,
    COALESCE(om_numero.meta_value, CAST(o.id AS CHAR)) AS numero_pedido,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS fecha_pedido,
    o.status AS estado_pedido,

    -- Información del producto
    oi.order_item_name AS producto_nombre,
    pm_sku.meta_value AS producto_sku,
    CAST(oim_pid.meta_value AS UNSIGNED) AS producto_id,
    CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), 0) AS UNSIGNED) AS variacion_id,

    -- Cantidades y precios de venta
    CAST(oim_qty.meta_value AS UNSIGNED) AS cantidad,
    CAST(oim_subtotal.meta_value AS DECIMAL(10,2)) AS subtotal_linea_pen,
    CAST(oim_total.meta_value AS DECIMAL(10,2)) AS total_linea_pen,
    CAST((CAST(oim_subtotal.meta_value AS DECIMAL(10,2)) / CAST(oim_qty.meta_value AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS precio_unitario_pen,

    -- Tipo de cambio del día
    (
        SELECT CAST(tc.tasa_promedio AS DECIMAL(6,4))
        FROM woo_tipo_cambio tc
        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
            AND tc.activo = TRUE
        ORDER BY tc.fecha DESC
        LIMIT 1
    ) AS tipo_cambio_dia,

    -- Costo del producto en USD (desde Fishbowl)
    (
        SELECT CAST(SUM(fc.FCLastCost) AS DECIMAL(10,2))
        FROM woo_products_fccost fc
        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
            AND LENGTH(fc.sku) = 7
    ) AS costo_unitario_usd,

    -- Costo total de esta línea en USD
    CAST(
        (
            SELECT SUM(fc.FCLastCost)
            FROM woo_products_fccost fc
            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                AND LENGTH(fc.sku) = 7
        ) * CAST(oim_qty.meta_value AS DECIMAL(10,2))
    AS DECIMAL(10,2)) AS costo_total_linea_usd,

    -- Costo total de esta línea en PEN
    CAST(
        (
            SELECT SUM(fc.FCLastCost)
            FROM woo_products_fccost fc
            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                AND LENGTH(fc.sku) = 7
        ) * CAST(oim_qty.meta_value AS DECIMAL(10,2)) * (
            SELECT tc.tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    AS DECIMAL(10,2)) AS costo_total_linea_pen,

    -- Ganancia de esta línea en PEN
    CAST(
        CAST(oim_subtotal.meta_value AS DECIMAL(10,2)) -
        (
            (
                SELECT SUM(fc.FCLastCost)
                FROM woo_products_fccost fc
                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                    AND LENGTH(fc.sku) = 7
            ) * CAST(oim_qty.meta_value AS DECIMAL(10,2)) * (
                SELECT tc.tasa_promedio
                FROM woo_tipo_cambio tc
                WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                    AND tc.activo = TRUE
                ORDER BY tc.fecha DESC
                LIMIT 1
            )
        )
    AS DECIMAL(10,2)) AS ganancia_linea_pen,

    -- Margen porcentual de esta línea
    CAST(
        ROUND(
            (
                (
                    CAST(oim_subtotal.meta_value AS DECIMAL(10,2)) -
                    (
                        (
                            SELECT SUM(fc.FCLastCost)
                            FROM woo_products_fccost fc
                            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                AND LENGTH(fc.sku) = 7
                        ) * CAST(oim_qty.meta_value AS DECIMAL(10,2)) * (
                            SELECT tc.tasa_promedio
                            FROM woo_tipo_cambio tc
                            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                                AND tc.activo = TRUE
                            ORDER BY tc.fecha DESC
                            LIMIT 1
                        )
                    )
                ) / NULLIF(CAST(oim_subtotal.meta_value AS DECIMAL(10,2)), 0)
            ) * 100
        , 2)
    AS DECIMAL(10,2)) AS margen_porcentaje,

    -- Flags de validación
    CASE WHEN pm_sku.meta_value IS NULL THEN 'SIN SKU' ELSE 'OK' END AS tiene_sku,
    CASE WHEN (
        SELECT SUM(fc.FCLastCost)
        FROM woo_products_fccost fc
        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
            AND LENGTH(fc.sku) = 7
    ) IS NULL THEN 'SIN COSTO' ELSE 'OK' END AS tiene_costo,

    -- Cliente
    CONCAT(ba.first_name, ' ', ba.last_name) AS cliente_nombre,

    -- Usuario que creó el pedido
    COALESCE(om_created.meta_value, 'WooCommerce') AS creado_por

FROM wpyz_wc_orders o

-- Join para obtener el número de pedido personalizado (si existe)
-- Cambiado a LEFT JOIN para incluir pedidos naturales de WooCommerce
LEFT JOIN wpyz_wc_orders_meta om_numero
    ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'

-- Join con items del pedido
INNER JOIN wpyz_woocommerce_order_items oi
    ON o.id = oi.order_id
    AND oi.order_item_type = 'line_item'

-- Join para obtener ID del producto
INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
    ON oi.order_item_id = oim_pid.order_item_id
    AND oim_pid.meta_key = '_product_id'

-- Join para obtener cantidad
INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
    ON oi.order_item_id = oim_qty.order_item_id
    AND oim_qty.meta_key = '_qty'

-- Join para obtener subtotal
INNER JOIN wpyz_woocommerce_order_itemmeta oim_subtotal
    ON oi.order_item_id = oim_subtotal.order_item_id
    AND oim_subtotal.meta_key = '_line_subtotal'

-- Join para obtener total
INNER JOIN wpyz_woocommerce_order_itemmeta oim_total
    ON oi.order_item_id = oim_total.order_item_id
    AND oim_total.meta_key = '_line_total'

-- Join para obtener ID de variación (si aplica)
LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
    ON oi.order_item_id = oim_vid.order_item_id
    AND oim_vid.meta_key = '_variation_id'

-- Join para obtener SKU (del producto o variación)
LEFT JOIN wpyz_postmeta pm_sku
    ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
    AND pm_sku.meta_key = '_sku'

-- Join para dirección de facturación
LEFT JOIN wpyz_wc_order_addresses ba
    ON o.id = ba.order_id
    AND ba.address_type = 'billing'

-- Join para obtener quién creó el pedido
LEFT JOIN wpyz_wc_orders_meta om_created
    ON o.id = om_created.order_id
    AND om_created.meta_key = '_created_by'

WHERE
    -- Filtro de fechas (MODIFICAR ESTAS FECHAS SEGÚN NECESITES)
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-31'

    -- Filtrar solo pedidos tipo shop_order
    AND o.type = 'shop_order'

    -- Excluir pedidos en estados no válidos
    AND o.status NOT IN ('trash', 'wc-cancelled', 'wc-refunded', 'wc-failed')

-- Ordenar por fecha y pedido
ORDER BY fecha_pedido DESC, o.id DESC, oi.order_item_id ASC;

-- ============================================================================
-- NOTAS DE USO:
-- ============================================================================
-- 1. Vista más granular: cada línea de pedido con su margen individual
-- 2. Usa las columnas tiene_sku y tiene_costo para identificar problemas
-- 3. Productos sin SKU o sin costo mostrarán NULL en ganancia
-- 4. Compara línea por línea con el módulo web de ganancias
-- 5. Para filtrar solo productos con problemas:
--    Agrega al WHERE: AND (pm_sku.meta_value IS NULL OR ... IS NULL)
-- 6. Para ver solo productos rentables:
--    Agrega HAVING margen_porcentaje > 0
-- 7. Para ver solo productos con margen bajo (< 15%):
--    Agrega HAVING margen_porcentaje < 15 AND margen_porcentaje > 0
-- ============================================================================
