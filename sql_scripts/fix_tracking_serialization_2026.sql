-- =========================================================================
-- FIX: CORRECCIÓN DE SERIALIZACIÓN Y DUPLICADOS DE TRACKING (POST-DESPLIEGUE)
-- =========================================================================
-- Este script corrige los pedidos procesados desde el 11 de Enero de 2026
-- que sufrieron de "Doble Serialización" y falta de registros duplicados.
-- =========================================================================

-- PASO 1: CORREGIR SERIALIZACIÓN CORRUPTA (s:NNN:"a:1:{...}")
-- Solo para registros que empiezan con 's:' (doble serialización)
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
  AND p.post_date >= '2026-01-11';

-- Repetir para HPOS (si aplica)
UPDATE wpyz_wc_orders_meta om
JOIN wpyz_wc_orders o ON om.order_id = o.id
SET om.meta_value = SUBSTRING(
    om.meta_value, 
    LOCATE('"', om.meta_value) + 1, 
    CHAR_LENGTH(om.meta_value) - LOCATE('"', om.meta_value) - 1
)
WHERE om.meta_key = '_wc_shipment_tracking_items'
  AND om.meta_value LIKE 's:%'
  AND o.date_created_gmt >= '2026-01-11';


-- PASO 2: ASEGURAR DUPLICADOS EN POSTMETA
-- El plugin requiere exactamente 2 registros por cada meta_key
-- =========================================================================

-- A. Limpiar cualquier triplicado accidental (solo por seguridad)
-- [Omitido por simplicidad, asumimos que el Manager los maneja ahora]

-- B. Duplicar registros que solo tienen 1 copia
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT pm.post_id, pm.meta_key, pm.meta_value
FROM wpyz_postmeta pm
JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE pm.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')
  AND p.post_date >= '2026-01-11'
  AND pm.post_id IN (
      SELECT post_id 
      FROM wpyz_postmeta 
      WHERE meta_key = pm.meta_key
      GROUP BY post_id, meta_key
      HAVING COUNT(*) = 1
  );

-- PASO 3: VERIFICACIÓN
-- =========================================================================
SELECT 
    pm.post_id, 
    pm.meta_key, 
    LEFT(pm.meta_value, 20) as snippet,
    COUNT(*) as copias
FROM wpyz_postmeta pm
JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE pm.meta_key = '_wc_shipment_tracking_items'
  AND p.post_date >= '2026-01-11'
GROUP BY pm.post_id, pm.meta_key, pm.meta_value
ORDER BY pm.post_id DESC;
