-- =============================================================================
-- SCRIPT PARA LIMPIAR ATRIBUTO HUÉRFANO "pa_conector"
-- =============================================================================
-- Problema: Existe attribute_pa_conector en la BD pero no en WooCommerce
-- Solución: Eliminar estos metadatos huérfanos de las variaciones
-- =============================================================================

-- PASO 1: BACKUP - Guardar los datos antes de eliminar (EJECUTAR PRIMERO)
-- =============================================================================
-- Esta tabla temporal guarda una copia de seguridad por si algo sale mal
-- =============================================================================

CREATE TEMPORARY TABLE IF NOT EXISTS backup_atributos_conector AS
SELECT
    pm.meta_id,
    pm.post_id,
    pm.meta_key,
    pm.meta_value,
    p.post_title,
    NOW() as backup_fecha
FROM wpyz_postmeta pm
INNER JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE pm.meta_key = 'attribute_pa_conector'
    AND p.post_type = 'product_variation';

-- Verificar cuántos registros se respaldaron
SELECT
    '=== BACKUP CREADO ===' as info,
    COUNT(*) as registros_respaldados,
    GROUP_CONCAT(DISTINCT post_id ORDER BY post_id) as variation_ids
FROM backup_atributos_conector;

-- Ver el contenido del backup
SELECT * FROM backup_atributos_conector;


-- PASO 2: ELIMINAR - Borrar los metadatos huérfanos (EJECUTAR DESPUÉS DEL BACKUP)
-- =============================================================================
-- ADVERTENCIA: Esta operación eliminará datos. Asegúrate de haber hecho backup primero.
-- =============================================================================

/*
DELETE FROM wpyz_postmeta
WHERE meta_key = 'attribute_pa_conector'
    AND post_id IN (
        SELECT ID
        FROM wpyz_posts
        WHERE post_type = 'product_variation'
    );
*/

-- NOTA: El DELETE está comentado por seguridad.
-- Descomenta las líneas anteriores SOLO después de:
-- 1. Haber ejecutado el PASO 1 (backup)
-- 2. Haber verificado que el backup tiene los datos correctos
-- 3. Estar completamente seguro de que quieres eliminar estos metadatos


-- PASO 3: VERIFICACIÓN - Comprobar que se eliminaron correctamente
-- =============================================================================

-- Verificar que ya no existen metadatos attribute_pa_conector
SELECT
    '=== VERIFICACIÓN POST-ELIMINACIÓN ===' as info,
    COUNT(*) as registros_restantes
FROM wpyz_postmeta pm
INNER JOIN wpyz_posts p ON pm.post_id = p.ID
WHERE pm.meta_key = 'attribute_pa_conector'
    AND p.post_type = 'product_variation';

-- Si el resultado es 0, la limpieza fue exitosa
-- Si es > 0, algo salió mal y debes investigar


-- PASO 4 (OPCIONAL): ROLLBACK - Restaurar desde backup si algo salió mal
-- =============================================================================
-- SOLO ejecutar si necesitas revertir los cambios
-- =============================================================================

/*
INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
SELECT post_id, meta_key, meta_value
FROM backup_atributos_conector;
*/


-- =============================================================================
-- INSTRUCCIONES DE USO:
-- =============================================================================
-- 1. Ejecuta SOLO el PASO 1 (desde CREATE TEMPORARY hasta SELECT * FROM backup)
-- 2. Verifica que el backup tiene los 6 registros esperados (uno por variación)
-- 3. Si todo está bien, descomenta y ejecuta el DELETE del PASO 2
-- 4. Ejecuta el PASO 3 para verificar que se eliminaron correctamente
-- 5. Prueba tu aplicación para verificar que el atributo "Conector" ya no aparece
-- 6. Si algo sale mal, ejecuta el PASO 4 (rollback) para restaurar
-- =============================================================================

-- RESULTADO ESPERADO:
-- Después de ejecutar este script, las variaciones solo deberían tener:
-- - attribute_color (Color: Azul, Blanco, Café, etc.)
-- Y NO deberían tener:
-- - attribute_pa_conector (este era el huérfano)
-- =============================================================================
