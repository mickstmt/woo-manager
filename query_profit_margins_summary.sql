-- ============================================================================
-- SCRIPT DE VALIDACIÓN DE GANANCIAS - RESUMEN EJECUTIVO
-- ============================================================================
-- Propósito: Obtener totales y promedios consolidados del período
-- Uso: Ejecutar directamente en MySQL/MariaDB para validar resúmenes
-- Formato: Una sola fila con métricas clave del período
--
-- Notas importantes:
-- - Resumen consolidado de todo el período
-- - Ideal para comparar con los totales del dashboard web
-- - Incluye costos de productos Y costos de envío
-- - Calcula margen promedio ponderado
-- ============================================================================

SELECT
    -- Período
    '2024-12-01' AS fecha_inicio,
    '2024-12-31' AS fecha_fin,

    -- Contadores
    COUNT(DISTINCT o.id) AS total_pedidos,
    COUNT(DISTINCT CASE WHEN o.status = 'wc-completed' THEN o.id END) AS pedidos_completados,
    COUNT(DISTINCT CASE WHEN o.status = 'wc-processing' THEN o.id END) AS pedidos_en_proceso,

    -- Totales de venta en PEN
    CAST(SUM(o.total_amount) AS DECIMAL(10,2)) AS ventas_totales_pen,
    CAST(AVG(o.total_amount) AS DECIMAL(10,2)) AS ticket_promedio_pen,

    -- Tipo de cambio promedio del período
    CAST(AVG(
        (
            SELECT tc.tasa_promedio
            FROM woo_tipo_cambio tc
            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                AND tc.activo = TRUE
            ORDER BY tc.fecha DESC
            LIMIT 1
        )
    ) AS DECIMAL(6,4)) AS tipo_cambio_promedio,

    -- Costos de productos en USD
    CAST(SUM(
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
        )
    ) AS DECIMAL(10,2)) AS costos_productos_usd,

    -- Costos de productos en PEN
    CAST(SUM(
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
    ) AS DECIMAL(10,2)) AS costos_productos_pen,

    -- Costos de envío en PEN
    CAST(SUM(
        COALESCE((
            SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
            FROM wpyz_woocommerce_order_items oi_shipping
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                ON oi_shipping.order_item_id = oim_shipping.order_item_id
            WHERE oi_shipping.order_id = o.id
                AND oi_shipping.order_item_type = 'shipping'
                AND oim_shipping.meta_key = 'cost'
        ), 0)
    ) AS DECIMAL(10,2)) AS costos_envio_pen,

    -- Ganancia neta total en PEN (Ventas - Costos productos - Costos envío)
    CAST(
        SUM(o.total_amount) -
        SUM(
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
        SUM(
            COALESCE((
                SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
                FROM wpyz_woocommerce_order_items oi_shipping
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                    ON oi_shipping.order_item_id = oim_shipping.order_item_id
                WHERE oi_shipping.order_id = o.id
                    AND oi_shipping.order_item_type = 'shipping'
                    AND oim_shipping.meta_key = 'cost'
            ), 0)
        )
    AS DECIMAL(10,2)) AS ganancia_neta_total_pen,

    -- Margen porcentual promedio (ponderado por ventas)
    CAST(
        ROUND(
            (
                (
                    SUM(o.total_amount) -
                    SUM(
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
                    SUM(
                        COALESCE((
                            SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
                            FROM wpyz_woocommerce_order_items oi_shipping
                            INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                                ON oi_shipping.order_item_id = oim_shipping.order_item_id
                            WHERE oi_shipping.order_id = o.id
                                AND oi_shipping.order_item_type = 'shipping'
                                AND oim_shipping.meta_key = 'cost'
                        ), 0)
                    )
                ) / NULLIF(SUM(o.total_amount), 0)
            ) * 100
        , 2)
    AS DECIMAL(10,2)) AS margen_promedio_porcentaje,

    -- Ganancia promedio por pedido
    CAST(
        (
            SUM(o.total_amount) -
            SUM(
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
            SUM(
                COALESCE((
                    SELECT SUM(CAST(oim_shipping.meta_value AS DECIMAL(10,2)))
                    FROM wpyz_woocommerce_order_items oi_shipping
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_shipping
                        ON oi_shipping.order_item_id = oim_shipping.order_item_id
                    WHERE oi_shipping.order_id = o.id
                        AND oi_shipping.order_item_type = 'shipping'
                        AND oim_shipping.meta_key = 'cost'
                ), 0)
            )
        ) / NULLIF(COUNT(DISTINCT o.id), 0)
    AS DECIMAL(10,2)) AS ganancia_promedio_por_pedido

FROM wpyz_wc_orders o

-- Join para obtener el número de pedido personalizado (si existe)
-- Cambiado a LEFT JOIN para incluir pedidos naturales de WooCommerce
LEFT JOIN wpyz_wc_orders_meta om_numero
    ON o.id = om_numero.order_id
    AND om_numero.meta_key = '_order_number'

WHERE
    -- Filtro de fechas (MODIFICAR ESTAS FECHAS SEGÚN NECESITES)
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-31'

    -- Filtrar solo pedidos tipo shop_order (excluye shop_order_refund, etc.)
    AND o.type = 'shop_order'

    -- Excluir pedidos en estados no válidos
    AND o.status NOT IN ('trash', 'wc-cancelled', 'wc-refunded', 'wc-failed');

-- NOTA: Este resumen incluye TODOS los pedidos de wpyz_wc_orders
-- Incluye pedidos naturales de WooCommerce Y pedidos de WhatsApp (WooCommerce Manager)
-- Los pedidos sin costos afectarán los totales mostrando ganancia como venta total

-- ============================================================================
-- NOTAS DE USO:
-- ============================================================================
-- 1. Este script retorna UNA SOLA FILA con todos los totales del período
-- 2. Compara estos totales con el dashboard web de ganancias
-- 3. Los valores deben coincidir exactamente si la lógica es correcta
-- 4. Si hay diferencias, usa los otros scripts para debugging
-- 5. Las fechas se pueden cambiar en el WHERE (línea 194)
--
-- MÉTRICAS CLAVE A VALIDAR:
-- - total_pedidos: Cantidad de pedidos en el período
-- - ventas_totales_pen: Total facturado en PEN
-- - costos_productos_pen: Total de costos de productos en PEN
-- - costos_envio_pen: Total de costos de envío en PEN
-- - ganancia_neta_total_pen: Ganancia después de restar todos los costos
-- - margen_promedio_porcentaje: Margen promedio del período (%)
-- ============================================================================
