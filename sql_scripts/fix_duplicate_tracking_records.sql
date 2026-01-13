-- =====================================================
-- FIX: DUPLICAR REGISTROS DE TRACKING EXISTENTES
-- =====================================================
-- Este script duplica los registros de tracking que solo
-- tienen 1 copia en wpyz_postmeta para que el plugin
-- WooCommerce Shipment Tracking los detecte correctamente
-- =====================================================

-- PASO 1: Identificar pedidos con tracking sin duplicar
-- =====================================================
SELECT 
    pm.post_id,
    pm.meta_key,
    COUNT(*) as cantidad,
    'NECESITA DUPLICAR' as accion
FROM wpyz_postmeta pm
WHERE pm.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')
GROUP BY pm.post_id, pm.meta_key
HAVING COUNT(*) = 1
ORDER BY pm.post_id DESC
LIMIT 20;


-- =====================================================
-- PASO 2: DUPLICAR REGISTROS (EJECUTAR ESTE)
-- =====================================================
-- Duplicar _tracking_number
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT post_id, meta_key, meta_value
FROM wpyz_postmeta pm
WHERE pm.meta_key = '_tracking_number'
  AND pm.post_id IN (
      SELECT DISTINCT post_id 
      FROM wpyz_postmeta 
      WHERE meta_key = '_tracking_number'
      GROUP BY post_id 
      HAVING COUNT(*) = 1
  );

-- Duplicar _tracking_provider
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT post_id, meta_key, meta_value
FROM wpyz_postmeta pm
WHERE pm.meta_key = '_tracking_provider'
  AND pm.post_id IN (
      SELECT DISTINCT post_id 
      FROM wpyz_postmeta 
      WHERE meta_key = '_tracking_provider'
      GROUP BY post_id 
      HAVING COUNT(*) = 1
  );

-- Duplicar _wc_shipment_tracking_items
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT post_id, meta_key, meta_value
FROM wpyz_postmeta pm
WHERE pm.meta_key = '_wc_shipment_tracking_items'
  AND pm.post_id IN (
      SELECT DISTINCT post_id 
      FROM wpyz_postmeta 
      WHERE meta_key = '_wc_shipment_tracking_items'
      GROUP BY post_id 
      HAVING COUNT(*) = 1
  );


-- =====================================================
-- PASO 3: VERIFICAR RESULTADO
-- =====================================================
SELECT 
    pm.post_id,
    pm.meta_key,
    COUNT(*) as cantidad_despues,
    CASE 
        WHEN COUNT(*) = 2 THEN '✓ CORREGIDO'
        WHEN COUNT(*) = 1 THEN '✗ AUN FALTA'
        ELSE 'REVISAR'
    END as estado
FROM wpyz_postmeta pm
WHERE pm.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')
  AND pm.post_id IN (41992, 41987, 41990, 41986, 41985)
GROUP BY pm.post_id, pm.meta_key
ORDER BY pm.post_id DESC, pm.meta_key;


-- =====================================================
-- INSTRUCCIONES:
-- =====================================================
-- 1. Ejecutar PASO 1 para ver cuántos pedidos necesitan duplicar
-- 2. Ejecutar PASO 2 (los 3 INSERT) para duplicar todos los registros
-- 3. Ejecutar PASO 3 para verificar que ahora tienen 2 copias
-- 4. Refrescar la página de WooCommerce para ver el tracking
-- =====================================================
