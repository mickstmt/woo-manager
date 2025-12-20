-- ============================================================================
-- SCRIPT DE VALIDACIÓN DE GANANCIAS POR PRODUCTO
-- ============================================================================
-- Propósito: Obtener detalle de productos vendidos con sus costos y márgenes
-- Uso: Ejecutar directamente en MySQL/MariaDB para validar márgenes por producto
-- Formato: Similar al script de ventas, agrupado por producto
--
-- Notas importantes:
-- - Agrupa por producto para ver cuáles son más rentables
-- - Calcula ganancia total y margen porcentual por producto
-- - Incluye cantidad vendida y total de pedidos
-- - Ordena por ganancia (de mayor a menor)
-- ============================================================================

SELECT
    -- Información del producto
    oi.order_item_name AS producto_nombre,
    pm_sku.meta_value AS producto_sku,

    -- Cantidades
    COUNT(DISTINCT o.id) AS total_pedidos,
    CAST(SUM(CAST(oim_qty.meta_value AS DECIMAL(10,2))) AS UNSIGNED) AS cantidad_total_vendida,

    -- Costo unitario en USD (desde Fishbowl)
    CAST((
        SELECT AVG(fc.FCLastCost)
        FROM woo_products_fccost fc
        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
            AND LENGTH(fc.sku) = 7
    ) AS DECIMAL(10,2)) AS costo_unitario_usd,

    -- Tipo de cambio promedio usado
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

    -- Totales en PEN
    CAST(SUM(CAST(oim_subtotal.meta_value AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS ventas_totales_pen,

    CAST(SUM(
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
    ) AS DECIMAL(10,2)) AS costos_totales_pen,

    -- Ganancia total en PEN
    CAST(
        SUM(CAST(oim_subtotal.meta_value AS DECIMAL(10,2))) -
        SUM(
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
    AS DECIMAL(10,2)) AS ganancia_total_pen,

    -- Margen porcentual
    CAST(
        ROUND(
            (
                (
                    SUM(CAST(oim_subtotal.meta_value AS DECIMAL(10,2))) -
                    SUM(
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
                ) / NULLIF(SUM(CAST(oim_subtotal.meta_value AS DECIMAL(10,2))), 0)
            ) * 100
        , 2)
    AS DECIMAL(10,2)) AS margen_porcentaje

FROM wpyz_wc_orders o

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

-- Join para obtener ID de variación (si aplica)
LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
    ON oi.order_item_id = oim_vid.order_item_id
    AND oim_vid.meta_key = '_variation_id'

-- Join para obtener SKU (del producto o variación)
LEFT JOIN wpyz_postmeta pm_sku
    ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
    AND pm_sku.meta_key = '_sku'

WHERE
    -- Filtro de fechas (MODIFICAR ESTAS FECHAS SEGÚN NECESITES)
    DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN '2024-12-01' AND '2024-12-31'

    -- Filtrar solo pedidos tipo shop_order
    AND o.type = 'shop_order'

    -- Excluir pedidos en estados no válidos
    AND o.status NOT IN ('trash', 'wc-cancelled', 'wc-refunded', 'wc-failed')

-- Agrupar por producto
GROUP BY
    oi.order_item_name,
    pm_sku.meta_value

-- Ordenar por ganancia (de mayor a menor rentabilidad)
-- NOTA: Incluye TODOS los productos, incluso sin costos
-- Los productos sin costos mostrarán NULL en columnas de ganancia
ORDER BY ganancia_total_pen DESC;

-- ============================================================================
-- NOTAS DE USO:
-- ============================================================================
-- 1. Este script te muestra qué productos generan más ganancia
-- 2. Puedes identificar productos con margen bajo (< 15%)
-- 3. Compara los resultados con el módulo de ganancias de la aplicación
-- 4. Para exportar a CSV en MySQL Workbench:
--    - Ejecuta el query
--    - Click derecho en resultados > Export > CSV
-- ============================================================================
