-- ============================================================================
-- SCRIPT DE VALIDACIÓN DE MÁRGENES DE GANANCIA
-- ============================================================================
-- Propósito: Obtener datos de ganancias por pedido para validación y export a CSV
-- Uso: Ejecutar directamente en MySQL/MariaDB para validar datos del módulo de ganancias
-- Formato: Similar al script de ventas, optimizado para rendimiento
--
-- Notas importantes:
-- - Convierte UTC a hora Perú (UTC-5) con DATE_SUB(date_created_gmt, INTERVAL 5 HOUR)
-- - Usa tipo de cambio del día del pedido de la tabla woo_tipo_cambio
-- - Incluye costos de productos desde woo_products_fccost (FishbowlCost)
-- - Resta costos de envío de las ganancias
-- - Filtra pedidos válidos (excluye cancelados, reembolsados, fallidos, trash)
-- ============================================================================

SELECT
    -- Información del pedido
    o.id AS pedido_id,
    COALESCE(om_numero.meta_value, CAST(o.id AS CHAR)) AS numero_pedido,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) AS fecha_pedido,
    o.status AS estado,

    -- Cliente (billing address)
    CONCAT(ba.first_name, ' ', ba.last_name) AS cliente_nombre_completo,
    ba.email AS cliente_email,
    ba.phone AS cliente_telefono,

    -- Totales de venta
    CAST(o.total_amount AS DECIMAL(10,2)) AS total_venta_pen,

    -- Tipo de cambio (del día del pedido)
    (
        SELECT CAST(tc.tasa_promedio AS DECIMAL(6,4))
        FROM woo_tipo_cambio tc
        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
            AND tc.activo = TRUE
        ORDER BY tc.fecha DESC
        LIMIT 1
    ) AS tipo_cambio_dia,

    -- Costos de productos en USD
    (
        SELECT CAST(SUM(
            (
                SELECT SUM(fc.FCLastCost)
                FROM woo_products_fccost fc
                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                    AND LENGTH(fc.sku) = 7
            ) * CAST(oim_qty.meta_value AS DECIMAL(10,2))
        ) AS DECIMAL(10,2))
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
            ON oi.order_item_id = oim_pid.order_item_id
            AND oim_pid.meta_key = '_product_id'
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
            ON oi.order_item_id = oim_qty.order_item_id
            AND oim_qty.meta_key = '_qty'
        LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
            ON oi.order_item_id = oim_vid.order_item_id
            AND oim_vid.meta_key = '_variation_id'
        INNER JOIN wpyz_postmeta pm_sku
            ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
            AND pm_sku.meta_key = '_sku'
        WHERE oi.order_id = o.id
            AND oi.order_item_type = 'line_item'
    ) AS costo_productos_usd,

    -- Costos de productos en PEN (USD * tipo_cambio)
    CAST(
        (
            SELECT SUM(
                (
                    SELECT SUM(fc.FCLastCost)
                    FROM woo_products_fccost fc
                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                        AND LENGTH(fc.sku) = 7
                ) * CAST(oim_qty.meta_value AS DECIMAL(10,2))
            )
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
                ON oi.order_item_id = oim_pid.order_item_id
                AND oim_pid.meta_key = '_product_id'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
                ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
                ON oi.order_item_id = oim_vid.order_item_id
                AND oim_vid.meta_key = '_variation_id'
            INNER JOIN wpyz_postmeta pm_sku
                ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
            WHERE oi.order_id = o.id
                AND oi.order_item_type = 'line_item'
        ) * (
            SELECT tc.tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    AS DECIMAL(10,2)) AS costo_productos_pen,

    -- Costo de envío en PEN
    CAST(COALESCE((
        SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
        FROM wpyz_woocommerce_order_items oi_shipping
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
            ON oi_shipping.order_item_id = oim_shipping.order_item_id
        WHERE oi_shipping.order_id = o.id
            AND oi_shipping.order_item_type = 'shipping'
            AND oim_shipping.meta_key = 'cost'
    ), 0) AS DECIMAL(10,2)) AS costo_envio_pen,

    -- Ganancia neta en PEN (Venta - Costo productos - Costo envío)
    CAST(
        o.total_amount -
        (
            (
                SELECT SUM(
                    (
                        SELECT SUM(fc.FCLastCost)
                        FROM woo_products_fccost fc
                        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                            AND LENGTH(fc.sku) = 7
                    ) * CAST(oim_qty.meta_value AS DECIMAL(10,2))
                )
                FROM wpyz_woocommerce_order_items oi
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
                    ON oi.order_item_id = oim_pid.order_item_id
                    AND oim_pid.meta_key = '_product_id'
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
                    ON oi.order_item_id = oim_qty.order_item_id
                    AND oim_qty.meta_key = '_qty'
                LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
                    ON oi.order_item_id = oim_vid.order_item_id
                    AND oim_vid.meta_key = '_variation_id'
                INNER JOIN wpyz_postmeta pm_sku
                    ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                    AND pm_sku.meta_key = '_sku'
                WHERE oi.order_id = o.id
                    AND oi.order_item_type = 'line_item'
            ) * (
                SELECT tc.tasa_promedio
                FROM woo_tipo_cambio tc
                WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                    AND tc.activo = TRUE
                ORDER BY tc.fecha DESC
                LIMIT 1
            )
        ) -
        COALESCE((
            SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
            FROM wpyz_woocommerce_order_items oi_shipping
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                ON oi_shipping.order_item_id = oim_shipping.order_item_id
            WHERE oi_shipping.order_id = o.id
                AND oi_shipping.order_item_type = 'shipping'
                AND oim_shipping.meta_key = 'cost'
        ), 0)
    AS DECIMAL(10,2)) AS ganancia_neta_pen,

    -- Margen porcentual (Ganancia / Venta * 100)
    CAST(
        ROUND(
            (
                (
                    o.total_amount -
                    (
                        (
                            SELECT SUM(
                                (
                                    SELECT SUM(fc.FCLastCost)
                                    FROM woo_products_fccost fc
                                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                        AND LENGTH(fc.sku) = 7
                                ) * CAST(oim_qty.meta_value AS DECIMAL(10,2))
                            )
                            FROM wpyz_woocommerce_order_items oi
                            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
                                ON oi.order_item_id = oim_pid.order_item_id
                                AND oim_pid.meta_key = '_product_id'
                            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
                                ON oi.order_item_id = oim_qty.order_item_id
                                AND oim_qty.meta_key = '_qty'
                            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
                                ON oi.order_item_id = oim_vid.order_item_id
                                AND oim_vid.meta_key = '_variation_id'
                            INNER JOIN wpyz_postmeta pm_sku
                                ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                                AND pm_sku.meta_key = '_sku'
                            WHERE oi.order_id = o.id
                                AND oi.order_item_type = 'line_item'
                        ) * (
                            SELECT tc.tasa_promedio
                            FROM woo_tipo_cambio tc
                            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                                AND tc.activo = TRUE
                            ORDER BY tc.fecha DESC
                            LIMIT 1
                        )
                    ) -
                    COALESCE((
                        SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
                        FROM wpyz_woocommerce_order_items oi_shipping
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                            ON oi_shipping.order_item_id = oim_shipping.order_item_id
                        WHERE oi_shipping.order_id = o.id
                            AND oi_shipping.order_item_type = 'shipping'
                            AND oim_shipping.meta_key = 'cost'
                    ), 0)
                ) / NULLIF(o.total_amount, 0)
            ) * 100
        , 2)
    AS DECIMAL(10,2)) AS margen_porcentaje,

    -- Método de pago
    o.payment_method AS metodo_pago,
    o.payment_method_title AS metodo_pago_titulo,

    -- Usuario que creó el pedido (asesor)
    COALESCE(om_created.meta_value, 'WooCommerce') AS creado_por

FROM wpyz_wc_orders o

-- Join para obtener el número de pedido personalizado (si existe)
-- Cambiado a LEFT JOIN para incluir pedidos naturales de WooCommerce
LEFT JOIN wpyz_wc_orders_meta om_numero
    ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'

-- Join para dirección de facturación (billing)
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

    -- Filtrar solo pedidos tipo shop_order (excluir reembolsos, etc.)
    AND o.type = 'shop_order'

    -- Excluir pedidos en estados no válidos
    AND o.status NOT IN ('trash', 'wc-cancelled', 'wc-refunded', 'wc-failed')

-- Ordenar por fecha descendente (más recientes primero)
-- NOTA: Incluye TODOS los pedidos, incluso sin costos
-- Los pedidos sin costos mostrarán NULL en columnas de ganancia
ORDER BY fecha_pedido DESC, o.id DESC;

-- ============================================================================
-- ÍNDICES RECOMENDADOS PARA OPTIMIZACIÓN
-- ============================================================================
-- Si el query es lento, asegúrate de tener estos índices:
--
-- CREATE INDEX idx_orders_date_type_status ON wpyz_wc_orders(date_created_gmt, type, status);
-- CREATE INDEX idx_orders_meta_key_value ON wpyz_wc_orders_meta(order_id, meta_key, meta_value(100));
-- CREATE INDEX idx_order_items_order_type ON wpyz_woocommerce_order_items(order_id, order_item_type);
-- CREATE INDEX idx_order_itemmeta_item_key ON wpyz_woocommerce_order_itemmeta(order_item_id, meta_key);
-- CREATE INDEX idx_postmeta_post_key ON wpyz_postmeta(post_id, meta_key);
-- CREATE INDEX idx_fccost_sku ON woo_products_fccost(sku);
-- CREATE INDEX idx_tipo_cambio_fecha_activo ON woo_tipo_cambio(fecha, activo);
--
-- ============================================================================
