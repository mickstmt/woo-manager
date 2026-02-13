-- ============================================
-- INVESTIGACIÓN: Pedido #42402 - Restauración automática desde Trash
-- ============================================
-- Problema: Pedido pasó de trash → pending → processing en 6 segundos
-- Fecha: 2026-02-12 11:33:14 - 11:33:20
-- Consecuencia: Despacho duplicado

-- ============================================
-- 1. Todas las notas del pedido #42402 (orden cronológico)
-- ============================================
SELECT
    c.comment_ID,
    DATE_FORMAT(c.comment_date, '%Y-%m-%d %H:%i:%s') AS fecha_hora_local,
    DATE_FORMAT(c.comment_date_gmt, '%Y-%m-%d %H:%i:%s') AS fecha_hora_utc,
    c.comment_content AS nota,
    c.comment_author AS autor,
    c.comment_type,
    c.user_id
FROM wpyz_comments c
WHERE c.comment_post_ID = 42402
  AND c.comment_type = 'order_note'
ORDER BY c.comment_date ASC;


-- ============================================
-- 2. Action Scheduler - Acciones ejecutadas cerca del incidente 
-- ============================================
-- Buscar acciones programadas que se ejecutaron entre 11:30 - 11:35
SELECT
    a.action_id,
    a.hook AS accion,
    a.args AS argumentos,
    a.status AS estado,
    DATE_FORMAT(FROM_UNIXTIME(a.scheduled_date_gmt), '%Y-%m-%d %H:%i:%s') AS fecha_programada,
    a.last_attempt_gmt,
    a.claim_id,

    -- Logs relacionados
    al.message AS log_mensaje

FROM wpyz_actionscheduler_actions a

LEFT JOIN wpyz_actionscheduler_logs al
    ON a.action_id = al.action_id

WHERE FROM_UNIXTIME(a.scheduled_date_gmt) BETWEEN '2026-02-12 11:30:00' AND '2026-02-12 11:35:00'
   OR a.args LIKE '%42402%'  -- Buscar el order_id en los argumentos

ORDER BY a.scheduled_date_gmt DESC;


-- ============================================
-- 3. Verificar si hay webhooks activos en WooCommerce
-- ============================================
SELECT
    webhook_id,
    status,
    name,
    delivery_url,
    topic,  -- order.created, order.updated, order.deleted, order.restored
    date_created,
    date_modified
FROM wpyz_wc_webhooks
WHERE status = 'active'
ORDER BY date_created DESC;


-- ============================================
-- 4. Detalles completos del pedido #42402
-- ============================================
SELECT
    o.id,
    o.status AS estado_actual,
    o.parent_order_id,
    o.type AS tipo_pedido,

    -- Fechas
    o.date_created_gmt,
    o.date_updated_gmt,
    o.date_paid_gmt,
    o.date_completed_gmt,

    -- Cliente
    o.billing_email,
    o.billing_phone,

    -- Totales
    o.total_amount,
    o.currency,

    -- Método de pago
    o.payment_method,
    o.payment_method_title,

    -- Shipping
    o.shipping_method,

    -- Otros
    om_number.meta_value AS numero_pedido,
    om_source.meta_value AS origen,
    om_is_cod.meta_value AS es_cod

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id AND om_number.meta_key = '_order_number'

LEFT JOIN wpyz_wc_orders_meta om_source
    ON o.id = om_source.order_id AND om_source.meta_key = '_order_source'

LEFT JOIN wpyz_wc_orders_meta om_is_cod
    ON o.id = om_is_cod.order_id AND om_is_cod.meta_key = '_is_cod'

WHERE o.id = 42402;


-- ============================================
-- 5. Historial de cambios en wpyz_wc_orders (si hay tabla de auditoría)
-- ============================================
-- Nota: WooCommerce normalmente NO tiene tabla de auditoría
-- pero algunos plugins pueden agregarla

SHOW TABLES LIKE '%audit%';
SHOW TABLES LIKE '%log%';
SHOW TABLES LIKE '%history%';


-- ============================================
-- 6. Verificar si hay pedidos duplicados o relacionados
-- ============================================
SELECT
    o.id,
    o.status,
    o.billing_email,
    o.billing_phone,
    o.total_amount,
    DATE_FORMAT(o.date_created_gmt, '%Y-%m-%d %H:%i:%s') AS fecha_creacion,
    om_number.meta_value AS numero_pedido

FROM wpyz_wc_orders o

LEFT JOIN wpyz_wc_orders_meta om_number
    ON o.id = om_number.order_id AND om_number.meta_key = '_order_number'

WHERE (o.billing_email = (SELECT billing_email FROM wpyz_wc_orders WHERE id = 42402)
   OR o.billing_phone = (SELECT billing_phone FROM wpyz_wc_orders WHERE id = 42402))
  AND o.date_created_gmt BETWEEN '2026-02-10 00:00:00' AND '2026-02-13 23:59:59'

ORDER BY o.date_created_gmt DESC;


-- ============================================
-- 7. Logs de la API de WooCommerce (si están habilitados)
-- ============================================
-- WooCommerce puede registrar llamadas a la API en wpyz_woocommerce_api_keys
-- y logs en archivos debug.log

SELECT
    key_id,
    description,
    permissions,  -- read, write, read_write
    user_id,
    last_access,
    truncated_key
FROM wpyz_woocommerce_api_keys
WHERE permissions IN ('write', 'read_write')
ORDER BY last_access DESC;


-- ============================================
-- 8. Buscar patrones similares en otros pedidos
-- ============================================
-- Ver si hay otros pedidos que salieron de trash automáticamente

SELECT
    c1.comment_post_ID AS order_id,
    DATE_FORMAT(c1.comment_date, '%Y-%m-%d %H:%i:%s') AS fecha_trash_to_pending,
    DATE_FORMAT(c2.comment_date, '%Y-%m-%d %H:%i:%s') AS fecha_pending_to_processing,
    TIMESTAMPDIFF(SECOND, c1.comment_date, c2.comment_date) AS segundos_entre_cambios,
    c1.comment_author AS autor_cambio1,
    c2.comment_author AS autor_cambio2

FROM wpyz_comments c1

INNER JOIN wpyz_comments c2
    ON c1.comment_post_ID = c2.comment_post_ID
    AND c2.comment_date > c1.comment_date
    AND c2.comment_content LIKE '%Pendiente%Procesando%'

WHERE c1.comment_content LIKE '%trash%Pendiente%'
  AND c1.comment_date >= '2026-02-01'

ORDER BY c1.comment_date DESC;


-- ============================================
-- 9. Verificar metadata sospechosa del pedido
-- ============================================
SELECT
    order_id,
    meta_key,
    meta_value
FROM wpyz_wc_orders_meta
WHERE order_id = 42402
  AND (
    meta_key LIKE '%webhook%'
    OR meta_key LIKE '%api%'
    OR meta_key LIKE '%restore%'
    OR meta_key LIKE '%auto%'
    OR meta_key LIKE '%cron%'
    OR meta_key LIKE '%schedule%'
  )
ORDER BY meta_key;


-- ============================================
-- 10. Última consulta: Comparar con logs de WooManager
-- ============================================
-- Verificar si hay logs en la aplicación Flask sobre este pedido

-- Esta query debe ejecutarse en los logs de la aplicación, no en MySQL
-- Buscar en: logs/app.log o donde estén los logs de Flask
-- Filtrar por:
--   - order_id: 42402
--   - Timestamp: 2026-02-12 11:30:00 - 11:35:00
--   - Palabras clave: "status", "update", "API", "webhook"
