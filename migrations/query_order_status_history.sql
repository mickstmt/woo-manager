-- ============================================
-- Query: Historial de Cambios de Estado de Pedidos
-- ============================================
-- WooCommerce registra cada cambio de estado como una "nota de pedido"
-- en la tabla wpyz_comments con comment_type = 'order_note'

-- ============================================
-- 1. Historial completo de cambios de estado de un pedido específico
-- ============================================
-- Reemplaza 42402 con el ID del pedido que quieres consultar

SELECT
    c.comment_ID,
    c.comment_post_ID AS order_id,

    -- Fecha y hora del cambio
    c.comment_date AS fecha_hora_local,
    c.comment_date_gmt AS fecha_hora_utc,

    -- Contenido de la nota (incluye cambio de estado)
    c.comment_content AS nota,

    -- Autor del cambio (usuario o 'WooCommerce' si fue automático)
    c.comment_author AS autor,

    -- Tipo de nota (order_note = nota de pedido)
    c.comment_type

FROM wpyz_comments c

WHERE c.comment_post_ID = 42402  -- ← Cambiar por el ID del pedido
  AND c.comment_type = 'order_note'

ORDER BY c.comment_date ASC;


-- ============================================
-- 2. Cambios de estado de los últimos 10 pedidos
-- ============================================
-- Muestra todos los cambios de estado de los pedidos más recientes

SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS pedido,
    o.status AS estado_actual,

    -- Fecha del cambio
    DATE_FORMAT(c.comment_date, '%Y-%m-%d %H:%i:%s') AS fecha_cambio,

    -- Nota del cambio (ej: "Order status changed from processing to completed")
    c.comment_content AS detalle_cambio,

    c.comment_author AS quien_cambio

FROM wpyz_wc_orders o

-- Número de pedido
LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

-- Notas de pedido (cambios de estado)
LEFT JOIN wpyz_comments c
    ON o.id = c.comment_post_ID
    AND c.comment_type = 'order_note'
    AND c.comment_content LIKE '%status%'  -- Solo cambios de estado

WHERE c.comment_ID IS NOT NULL

ORDER BY o.id DESC, c.comment_date ASC

LIMIT 50;


-- ============================================
-- 3. Resumen de tiempos por estado de un pedido
-- ============================================
-- Muestra cuánto tiempo estuvo el pedido en cada estado

WITH status_changes AS (
    SELECT
        c.comment_post_ID AS order_id,
        c.comment_date AS fecha_cambio,
        c.comment_content,

        -- Extraer estado anterior y nuevo del texto
        CASE
            WHEN c.comment_content LIKE '%from%to%' THEN
                SUBSTRING_INDEX(SUBSTRING_INDEX(c.comment_content, 'from ', -1), ' to', 1)
            ELSE NULL
        END AS estado_anterior,

        CASE
            WHEN c.comment_content LIKE '%from%to%' THEN
                SUBSTRING_INDEX(SUBSTRING_INDEX(c.comment_content, 'to ', -1), '.', 1)
            ELSE NULL
        END AS estado_nuevo

    FROM wpyz_comments c
    WHERE c.comment_post_ID = 42402  -- ← Cambiar por el ID del pedido
      AND c.comment_type = 'order_note'
      AND c.comment_content LIKE '%status%'
    ORDER BY c.comment_date ASC
)
SELECT
    order_id,
    estado_nuevo AS estado,
    fecha_cambio AS fecha_inicio,
    LEAD(fecha_cambio) OVER (ORDER BY fecha_cambio) AS fecha_fin,
    TIMESTAMPDIFF(HOUR,
        fecha_cambio,
        LEAD(fecha_cambio) OVER (ORDER BY fecha_cambio)
    ) AS horas_en_estado,
    comment_content AS detalle
FROM status_changes
ORDER BY fecha_cambio ASC;


-- ============================================
-- 4. Identificar pedidos que tardaron más en procesarse
-- ============================================
-- Muestra pedidos que tardaron más de X horas entre creación y completado

SELECT
    o.id AS order_id,
    COALESCE(om_number.meta_value, CONCAT('#', o.id)) AS pedido,
    o.status AS estado_actual,

    -- Fechas clave
    o.date_created_gmt AS fecha_creacion,
    MAX(CASE WHEN c.comment_content LIKE '%completed%'
        THEN c.comment_date_gmt END) AS fecha_completado,

    -- Tiempo de procesamiento
    TIMESTAMPDIFF(HOUR,
        o.date_created_gmt,
        MAX(CASE WHEN c.comment_content LIKE '%completed%'
            THEN c.comment_date_gmt END)
    ) AS horas_procesamiento

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id
    AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_comments c
    ON o.id = c.comment_post_ID
    AND c.comment_type = 'order_note'

WHERE o.status = 'wc-completed'

GROUP BY o.id, om_number.meta_value, o.status, o.date_created_gmt

HAVING fecha_completado IS NOT NULL
   AND horas_procesamiento > 24  -- Más de 24 horas

ORDER BY horas_procesamiento DESC

LIMIT 20;


-- ============================================
-- 5. Ver TODAS las notas de un pedido (no solo cambios de estado)
-- ============================================

SELECT
    c.comment_ID,
    DATE_FORMAT(c.comment_date, '%Y-%m-%d %H:%i:%s') AS fecha,
    c.comment_author AS autor,
    c.comment_content AS nota,

    -- Metadatos de la nota
    cm_system.meta_value AS es_nota_sistema,
    cm_added_by.meta_value AS agregada_por

FROM wpyz_comments c

-- Metadato: ¿Es nota del sistema?
LEFT JOIN wpyz_commentmeta cm_system
    ON c.comment_ID = cm_system.comment_id
    AND cm_system.meta_key = 'is_customer_note'

-- Metadato: ¿Quién la agregó?
LEFT JOIN wpyz_commentmeta cm_added_by
    ON c.comment_ID = cm_added_by.comment_id
    AND cm_added_by.meta_key = 'added_by'

WHERE c.comment_post_ID = 42402  -- ← Cambiar por el ID del pedido
  AND c.comment_type = 'order_note'

ORDER BY c.comment_date ASC;


-- ============================================
-- 6. Estadísticas de cambios de estado por día
-- ============================================
-- Útil para ver cuántos pedidos cambian de estado cada día

SELECT
    DATE(c.comment_date) AS fecha,

    COUNT(CASE WHEN c.comment_content LIKE '%pending%' THEN 1 END) AS cambios_a_pendiente,
    COUNT(CASE WHEN c.comment_content LIKE '%processing%' THEN 1 END) AS cambios_a_procesando,
    COUNT(CASE WHEN c.comment_content LIKE '%completed%' THEN 1 END) AS cambios_a_completado,
    COUNT(CASE WHEN c.comment_content LIKE '%cancelled%' THEN 1 END) AS cambios_a_cancelado,

    COUNT(*) AS total_cambios

FROM wpyz_comments c

WHERE c.comment_type = 'order_note'
  AND c.comment_content LIKE '%status%'
  AND c.comment_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)  -- Últimos 30 días

GROUP BY DATE(c.comment_date)

ORDER BY fecha DESC;
