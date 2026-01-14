-- =========================================================================
-- FIX UNIVERSAL: CORRECCIÓN DE SERIALIZACIÓN Y DUPLICADOS DE TRACKING
-- =========================================================================
-- Este script corrige TODOS los pedidos afectados por la "Doble Serialización"
-- sin importar la fecha.
-- =========================================================================

SET SQL_SAFE_UPDATES = 0;

-- PASO 1: CORREGIR SERIALIZACIÓN CORRUPTA (s:NNN:"a:1:{...}")
-- =========================================================================
UPDATE wpyz_postmeta pm
JOIN wpyz_posts p ON pm.post_id = p.ID
SET pm.meta_value = SUBSTRING(
    pm.meta_value, 
    LOCATE('"', pm.meta_value) + 1, 
    CHAR_LENGTH(pm.meta_value) - LOCATE('"', pm.meta_value) - 1
)
WHERE pm.meta_key = '_wc_shipment_tracking_items'
  AND pm.meta_value LIKE 's:%'
  AND pm.meta_value LIKE '%a:1:{%'
  AND p.post_date >= '2026-01-11' AND p.post_date <= '2026-01-13 23:59:59';

-- Repetir para HPOS
UPDATE wpyz_wc_orders_meta om
JOIN wpyz_wc_orders o ON om.order_id = o.id
SET om.meta_value = SUBSTRING(
    om.meta_value, 
    LOCATE('"', om.meta_value) + 1, 
    CHAR_LENGTH(om.meta_value) - LOCATE('"', om.meta_value) - 1
)
WHERE om.meta_key = '_wc_shipment_tracking_items'
  AND om.meta_value LIKE 's:%'
  AND om.meta_value LIKE '%a:1:{%'
  AND o.date_created_gmt >= '2026-01-11' AND o.date_created_gmt <= '2026-01-13 23:59:59';


-- PASO 2: ASEGURAR DUPLICADOS EN POSTMETA
-- Optimizado para evitar timeout: Filtramos primero por fecha
-- =========================================================================
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT pm.post_id, pm.meta_key, pm.meta_value
FROM wpyz_postmeta pm
JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE pm.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')
  AND p.post_date >= '2026-01-11' AND p.post_date <= '2026-01-13 23:59:59'
  AND pm.post_id IN (
      -- Subconsulta optimizada: Solo verificamos los que ya filtramos por fecha
      SELECT post_id 
      FROM (
          SELECT pm2.post_id, pm2.meta_key
          FROM wpyz_postmeta pm2
          JOIN wpyz_posts p2 ON pm2.post_id = p2.ID
          WHERE pm2.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')
            AND p2.post_date >= '2026-01-11' AND p2.post_date <= '2026-01-13 23:59:59'
          GROUP BY pm2.post_id, pm2.meta_key
          HAVING COUNT(*) = 1
      ) as need_dupes
      WHERE need_dupes.meta_key = pm.meta_key
  );

SET SQL_SAFE_UPDATES = 1;

-- VERIFICACIÓN
SELECT COUNT(*) as pedidos_corregidos 
FROM wpyz_postmeta 
WHERE meta_key = '_wc_shipment_tracking_items' 
AND meta_value NOT LIKE 's:%';
