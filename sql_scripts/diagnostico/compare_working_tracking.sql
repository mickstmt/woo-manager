-- =====================================================
-- COMPARAR PEDIDOS CON TRACKING FUNCIONANDO
-- =====================================================
-- 41871: Tracking agregado MANUALMENTE via plugin (FUNCIONA)
-- 41622: Tracking agregado via MANAGER (FUNCIONA)
-- 41987, 41990: Tracking agregado via MANAGER (NO FUNCIONA)
-- =====================================================

-- 1. COMPARAR TODOS LOS META_KEYS DE TRACKING
-- =====================================================
SELECT
    pm.post_id AS order_id,
    
    CASE 
        WHEN pm.post_id = 41871 THEN '✓ MANUAL VIA PLUGIN'
        WHEN pm.post_id = 41622 THEN '✓ VIA MANAGER (FUNCIONA)'
        ELSE '✗ VIA MANAGER (NO FUNCIONA)'
    END AS metodo_agregado,
    
    pm.meta_key,
    
    CASE
        WHEN pm.meta_key = '_wc_shipment_tracking_items' 
        THEN CONCAT(LEFT(pm.meta_value, 150), '...')
        ELSE pm.meta_value
    END AS meta_value,
    
    LENGTH(pm.meta_value) AS longitud

FROM wpyz_postmeta pm

WHERE pm.post_id IN (41871, 41622, 41987, 41990)
  AND pm.meta_key IN (
      '_tracking_number',
      '_tracking_provider', 
      '_wc_shipment_tracking_items',
      'wc_shipment_tracking_items'
  )

ORDER BY 
    CASE 
        WHEN pm.post_id = 41871 THEN 1
        WHEN pm.post_id = 41622 THEN 2
        ELSE 3
    END,
    pm.post_id,
    pm.meta_key;


-- =====================================================
-- 2. VERIFICAR SI HAY META_KEYS ADICIONALES
-- =====================================================
-- Buscar TODOS los meta_keys que tengan 'tracking' o 'shipment'
SELECT DISTINCT
    pm.post_id AS order_id,
    
    CASE 
        WHEN pm.post_id = 41871 THEN '✓ MANUAL'
        WHEN pm.post_id = 41622 THEN '✓ MANAGER OK'
        ELSE '✗ MANAGER FAIL'
    END AS tipo,
    
    pm.meta_key,
    COUNT(*) AS cantidad_registros

FROM wpyz_postmeta pm

WHERE pm.post_id IN (41871, 41622, 41987, 41990)
  AND (
      pm.meta_key LIKE '%tracking%'
      OR pm.meta_key LIKE '%shipment%'
  )

GROUP BY pm.post_id, pm.meta_key

ORDER BY 
    CASE 
        WHEN pm.post_id = 41871 THEN 1
        WHEN pm.post_id = 41622 THEN 2
        ELSE 3
    END,
    pm.post_id,
    pm.meta_key;


-- =====================================================
-- 3. COMPARAR ESTRUCTURA JSON/SERIALIZADO
-- =====================================================
SELECT
    pm.post_id AS order_id,
    
    CASE 
        WHEN pm.post_id = 41871 THEN 'MANUAL PLUGIN'
        WHEN pm.post_id = 41622 THEN 'MANAGER OK'
        WHEN pm.post_id = 41987 THEN 'MANAGER FAIL'
        WHEN pm.post_id = 41990 THEN 'MANAGER FAIL'
    END AS metodo,
    
    -- Primeros 200 caracteres para comparar estructura
    LEFT(pm.meta_value, 200) AS estructura_tracking,
    
    -- Verificar formato
    CASE
        WHEN pm.meta_value LIKE 'a:%' THEN 'PHP Serialized (array)'
        WHEN pm.meta_value LIKE 's:%' THEN 'PHP Serialized (string)'
        WHEN pm.meta_value LIKE '[%' THEN 'JSON Array'
        WHEN pm.meta_value LIKE '{%' THEN 'JSON Object'
        ELSE 'OTRO'
    END AS formato_detectado,
    
    LENGTH(pm.meta_value) AS longitud_total

FROM wpyz_postmeta pm

WHERE pm.post_id IN (41871, 41622, 41987, 41990)
  AND pm.meta_key = '_wc_shipment_tracking_items'

ORDER BY 
    CASE 
        WHEN pm.post_id = 41871 THEN 1
        WHEN pm.post_id = 41622 THEN 2
        ELSE 3
    END,
    pm.post_id;


-- =====================================================
-- 4. COMPARAR EN HPOS TAMBIÉN
-- =====================================================
SELECT
    om.order_id,
    
    CASE 
        WHEN om.order_id = 41871 THEN 'MANUAL PLUGIN'
        WHEN om.order_id = 41622 THEN 'MANAGER OK'
        WHEN om.order_id = 41987 THEN 'MANAGER FAIL'
        WHEN om.order_id = 41990 THEN 'MANAGER FAIL'
    END AS metodo,
    
    'HPOS (wpyz_wc_orders_meta)' AS ubicacion,
    
    om.meta_key,
    
    LEFT(om.meta_value, 150) AS meta_value_preview,
    
    LENGTH(om.meta_value) AS longitud

FROM wpyz_wc_orders_meta om

WHERE om.order_id IN (41871, 41622, 41987, 41990)
  AND om.meta_key = '_wc_shipment_tracking_items'

ORDER BY 
    CASE 
        WHEN om.order_id = 41871 THEN 1
        WHEN om.order_id = 41622 THEN 2
        ELSE 3
    END,
    om.order_id;


-- =====================================================
-- 5. BUSCAR DIFERENCIAS EN META_IDS
-- =====================================================
-- Ver si hay múltiples registros del mismo meta_key
SELECT
    pm.post_id AS order_id,
    pm.meta_key,
    pm.meta_id,
    
    CASE 
        WHEN pm.post_id = 41871 THEN 'MANUAL'
        WHEN pm.post_id = 41622 THEN 'MANAGER OK'
        ELSE 'MANAGER FAIL'
    END AS tipo,
    
    LEFT(pm.meta_value, 100) AS valor

FROM wpyz_postmeta pm

WHERE pm.post_id IN (41871, 41622, 41987, 41990)
  AND pm.meta_key IN ('_wc_shipment_tracking_items', '_tracking_number', '_tracking_provider')

ORDER BY 
    pm.meta_key,
    CASE 
        WHEN pm.post_id = 41871 THEN 1
        WHEN pm.post_id = 41622 THEN 2
        ELSE 3
    END,
    pm.post_id,
    pm.meta_id;


-- =====================================================
-- INTERPRETACIÓN ESPERADA:
-- =====================================================
-- Si 41871 (manual) y 41622 (manager OK) son IDÉNTICOS:
--   → El código del manager está correcto
--   → Los pedidos 41987/41990 tienen algún problema adicional
--
-- Si 41871 (manual) tiene meta_keys ADICIONALES que 41622 no tiene:
--   → Esos meta_keys faltantes son la causa del problema
--   → Necesitamos agregar esos meta_keys en dispatch.py
--
-- Si el FORMATO es diferente (PHP vs JSON):
--   → Necesitamos cambiar phpserialize por otro formato
-- =====================================================
