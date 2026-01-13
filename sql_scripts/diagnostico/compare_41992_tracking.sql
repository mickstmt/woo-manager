-- =====================================================
-- COMPARAR PEDIDO 41992 (NUEVO - NO FUNCIONA)
-- CON PEDIDOS QUE SÍ FUNCIONAN
-- =====================================================

-- 1. VER TODOS LOS META_KEYS DE TRACKING DEL 41992
-- =====================================================
SELECT
    pm.post_id AS order_id,
    '41992 - NUEVO (NO FUNCIONA)' AS descripcion,
    pm.meta_key,
    pm.meta_id,
    LEFT(pm.meta_value, 100) AS meta_value,
    LENGTH(pm.meta_value) AS longitud

FROM wpyz_postmeta pm

WHERE pm.post_id = 41992
  AND pm.meta_key IN (
      '_tracking_number',
      '_tracking_provider', 
      '_wc_shipment_tracking_items'
  )

ORDER BY pm.meta_key, pm.meta_id;


-- =====================================================
-- 2. CONTAR DUPLICADOS EN 41992 VS 41622
-- =====================================================
SELECT 
    post_id,
    CASE 
        WHEN post_id = 41622 THEN '✓ FUNCIONA'
        WHEN post_id = 41992 THEN '✗ NO FUNCIONA (NUEVO)'
        ELSE 'OTRO'
    END AS estado,
    meta_key,
    COUNT(*) as cantidad_registros,
    GROUP_CONCAT(meta_id ORDER BY meta_id) as meta_ids

FROM wpyz_postmeta

WHERE post_id IN (41622, 41992)
  AND meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')

GROUP BY post_id, meta_key

ORDER BY 
    CASE WHEN post_id = 41622 THEN 1 ELSE 2 END,
    post_id, 
    meta_key;


-- =====================================================
-- 3. VER CONTENIDO EXACTO DEL 41992
-- =====================================================
SELECT
    pm.meta_key,
    pm.meta_value AS valor_completo,
    LENGTH(pm.meta_value) AS longitud,
    
    -- Verificar formato
    CASE
        WHEN pm.meta_value LIKE 'a:%' THEN 'PHP Serialized (array)'
        WHEN pm.meta_value LIKE 's:%' THEN 'PHP Serialized (string)'
        WHEN pm.meta_value LIKE '[%' THEN 'JSON Array'
        WHEN pm.meta_value LIKE '{%' THEN 'JSON Object'
        ELSE 'OTRO'
    END AS formato

FROM wpyz_postmeta pm

WHERE pm.post_id = 41992
  AND pm.meta_key = '_wc_shipment_tracking_items';


-- =====================================================
-- 4. VERIFICAR SI ESTÁ EN HPOS TAMBIÉN
-- =====================================================
SELECT
    om.order_id,
    '41992 en HPOS' AS ubicacion,
    om.meta_key,
    LEFT(om.meta_value, 150) AS meta_value_preview,
    LENGTH(om.meta_value) AS longitud

FROM wpyz_wc_orders_meta om

WHERE om.order_id = 41992
  AND om.meta_key = '_wc_shipment_tracking_items';


-- =====================================================
-- 5. COMPARAR TIMESTAMPS DE CREACIÓN
-- =====================================================
-- Ver si los meta_ids están en orden cronológico
SELECT
    pm.post_id,
    pm.meta_key,
    pm.meta_id,
    LEFT(pm.meta_value, 80) AS valor,
    
    CASE 
        WHEN pm.post_id = 41622 THEN 'FUNCIONA'
        WHEN pm.post_id = 41992 THEN 'NO FUNCIONA'
    END AS estado

FROM wpyz_postmeta pm

WHERE pm.post_id IN (41622, 41992)
  AND pm.meta_key IN ('_tracking_number', '_tracking_provider', '_wc_shipment_tracking_items')

ORDER BY pm.post_id, pm.meta_key, pm.meta_id;


-- =====================================================
-- DIAGNÓSTICO ESPERADO:
-- =====================================================
-- Si 41992 NO tiene duplicados:
--   → El código de duplicados NO se ejecutó correctamente
--   → Verificar si el deploy se hizo bien
--
-- Si 41992 SÍ tiene duplicados pero NO funciona:
--   → Puede haber otro problema (cache, plugin, etc.)
--
-- Si 41992 tiene diferente formato que 41622:
--   → Problema en cómo se serializa
-- =====================================================
