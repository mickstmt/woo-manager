-- =============================================================================
-- CALCULAR GANANCIAS POR PEDIDOS EN RANGO DE FECHAS
-- =============================================================================
-- Propósito: Obtener reporte de ganancias de pedidos considerando:
--            - Precio de venta (PEN)
--            - Costo de productos (USD) convertido a PEN
--            - Tipo de cambio histórico
-- =============================================================================

-- CONFIGURAR RANGO DE FECHAS AQUÍ
SET @fecha_inicio = '2024-12-01';
SET @fecha_fin = '2024-12-04';

-- =============================================================================
-- CONSULTA PRINCIPAL: GANANCIAS POR PEDIDO
-- =============================================================================

SELECT
    o.id as pedido_id,
    om_numero.meta_value as numero_pedido,
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as fecha_pedido,
    o.status as estado,
    o.total_amount as total_venta_pen,

    -- Tipo de cambio usado (del día del pedido)
    (
        SELECT tasa_promedio
        FROM woo_tipo_cambio tc
        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
            AND tc.activo = TRUE
        ORDER BY tc.fecha DESC
        LIMIT 1
    ) as tipo_cambio,

    -- Costo total en USD (suma de costos de todos los items)
    (
        SELECT SUM(
            (
                SELECT SUM(fc.FCLastCost)
                FROM woo_products_fccost fc
                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                    AND LENGTH(fc.sku) = 7
            ) * oim_qty.meta_value
        )
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
            AND oim_pid.meta_key = '_product_id'
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
            AND oim_qty.meta_key = '_qty'
        INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
            AND pm_sku.meta_key = '_sku'
        WHERE oi.order_id = o.id
            AND oi.order_item_type = 'line_item'
    ) as costo_total_usd,

    -- Costo total en PEN (USD * tipo de cambio)
    (
        SELECT SUM(
            (
                SELECT SUM(fc.FCLastCost)
                FROM woo_products_fccost fc
                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                    AND LENGTH(fc.sku) = 7
            ) * oim_qty.meta_value
        )
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
            AND oim_pid.meta_key = '_product_id'
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
            AND oim_qty.meta_key = '_qty'
        INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
            AND pm_sku.meta_key = '_sku'
        WHERE oi.order_id = o.id
            AND oi.order_item_type = 'line_item'
    ) * (
        SELECT tasa_promedio
        FROM woo_tipo_cambio tc
        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
            AND tc.activo = TRUE
        ORDER BY tc.fecha DESC
        LIMIT 1
    ) as costo_total_pen,

    -- Ganancia (Venta - Costo)
    o.total_amount - (
        (
            SELECT SUM(
                (
                    SELECT SUM(fc.FCLastCost)
                    FROM woo_products_fccost fc
                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                        AND LENGTH(fc.sku) = 7
                ) * oim_qty.meta_value
            )
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                AND oim_pid.meta_key = '_product_id'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
            WHERE oi.order_id = o.id
                AND oi.order_item_type = 'line_item'
        ) * (
            SELECT tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    ) as ganancia_pen,

    -- Margen de ganancia (%)
    ROUND(
        (
            (o.total_amount - (
                (
                    SELECT SUM(
                        (
                            SELECT SUM(fc.FCLastCost)
                            FROM woo_products_fccost fc
                            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                AND LENGTH(fc.sku) = 7
                        ) * oim_qty.meta_value
                    )
                    FROM wpyz_woocommerce_order_items oi
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                        AND oim_pid.meta_key = '_product_id'
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                        AND oim_qty.meta_key = '_qty'
                    INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                        AND pm_sku.meta_key = '_sku'
                    WHERE oi.order_id = o.id
                        AND oi.order_item_type = 'line_item'
                ) * (
                    SELECT tasa_promedio
                    FROM woo_tipo_cambio tc
                    WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                        AND tc.activo = TRUE
                    ORDER BY tc.fecha DESC
                    LIMIT 1
                )
            )) / NULLIF(o.total_amount, 0)
        ) * 100
    , 2) as margen_porcentaje,

    -- Cliente
    ba.first_name as cliente_nombre,
    ba.last_name as cliente_apellido,
    o.billing_email as cliente_email

FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'
LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id
    AND ba.address_type = 'billing'

WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @fecha_inicio AND @fecha_fin
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')  -- Excluir pedidos cancelados

-- Filtrar solo pedidos con costo calculable
HAVING costo_total_usd IS NOT NULL

ORDER BY fecha_pedido DESC, o.id DESC;


-- =============================================================================
-- RESUMEN AGREGADO POR PERÍODO
-- =============================================================================

SELECT
    '=== RESUMEN DEL PERÍODO ===' as tipo,
    COUNT(DISTINCT o.id) as total_pedidos,
    ROUND(SUM(o.total_amount), 2) as ventas_totales_pen,
    ROUND(SUM(
        (
            SELECT SUM(
                (
                    SELECT SUM(fc.FCLastCost)
                    FROM woo_products_fccost fc
                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                        AND LENGTH(fc.sku) = 7
                ) * oim_qty.meta_value
            )
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                AND oim_pid.meta_key = '_product_id'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
            WHERE oi.order_id = o.id
                AND oi.order_item_type = 'line_item'
        )
    ), 2) as costos_totales_usd,
    ROUND(SUM(
        (
            SELECT SUM(
                (
                    SELECT SUM(fc.FCLastCost)
                    FROM woo_products_fccost fc
                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                        AND LENGTH(fc.sku) = 7
                ) * oim_qty.meta_value
            )
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                AND oim_pid.meta_key = '_product_id'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
            WHERE oi.order_id = o.id
                AND oi.order_item_type = 'line_item'
        ) * (
            SELECT tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    ), 2) as costos_totales_pen,
    ROUND(SUM(o.total_amount) - SUM(
        (
            SELECT SUM(
                (
                    SELECT SUM(fc.FCLastCost)
                    FROM woo_products_fccost fc
                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                        AND LENGTH(fc.sku) = 7
                ) * oim_qty.meta_value
            )
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                AND oim_pid.meta_key = '_product_id'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
            WHERE oi.order_id = o.id
                AND oi.order_item_type = 'line_item'
        ) * (
            SELECT tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    ), 2) as ganancias_totales_pen,
    ROUND(
        (SUM(o.total_amount) - SUM(
            (
                SELECT SUM(
                    (
                        SELECT SUM(fc.FCLastCost)
                        FROM woo_products_fccost fc
                        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                            AND LENGTH(fc.sku) = 7
                    ) * oim_qty.meta_value
                )
                FROM wpyz_woocommerce_order_items oi
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                    AND oim_pid.meta_key = '_product_id'
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                    AND oim_qty.meta_key = '_qty'
                INNER JOIN wpyz_postmeta pm_sku ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                    AND pm_sku.meta_key = '_sku'
                WHERE oi.order_id = o.id
                    AND oi.order_item_type = 'line_item'
            ) * (
                SELECT tasa_promedio
                FROM woo_tipo_cambio tc
                WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                    AND tc.activo = TRUE
                ORDER BY tc.fecha DESC
                LIMIT 1
            )
        )) / NULLIF(SUM(o.total_amount), 0) * 100
    , 2) as margen_promedio_porcentaje

FROM wpyz_wc_orders o
INNER JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'

WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN @fecha_inicio AND @fecha_fin
    AND o.status != 'trash'
    AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed');


-- =============================================================================
-- NOTAS IMPORTANTES
-- =============================================================================
-- 1. Asegurarse de tener tipo de cambio configurado en woo_tipo_cambio
-- 2. La consulta usa el tipo de cambio del día del pedido
-- 3. Solo considera pedidos con estado válido (no cancelados ni reembolsados)
-- 4. Excluye pedidos sin costos calculables (productos sin match en FashionCloud)
-- 5. Fechas en hora de Perú (UTC-5)
-- =============================================================================
