-- =====================================================
-- CONSULTA COMPLETA DE PRODUCTO EN WOOCOMMERCE
-- Prefijo de tablas: wpyz_
-- =====================================================
-- Esta consulta obtiene TODOS los campos de un producto
-- incluyendo información de plugins (Yoast SEO, Brands)
-- =====================================================

-- =====================================================
-- 1. CONSULTA PRODUCTO SIMPLE O VARIABLE (PADRE)
-- =====================================================
-- Reemplazar 123 por el ID del producto

SELECT
    -- Información básica
    p.ID as product_id,
    p.post_title as titulo,
    p.post_content as descripcion_larga,
    p.post_excerpt as descripcion_corta,
    p.post_name as slug,
    p.post_status as estado,

    -- Tipo de producto
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_product_type' LIMIT 1) as tipo_producto,

    -- Precio
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_regular_price' LIMIT 1) as precio_regular,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sale_price' LIMIT 1) as precio_oferta,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) as precio_actual,

    -- Inventario
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) as stock_cantidad,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock_status' LIMIT 1) as stock_estado,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_low_stock_amount' LIMIT 1) as umbral_stock_bajo,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_manage_stock' LIMIT 1) as gestionar_stock,

    -- Imagen principal
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_thumbnail_id' LIMIT 1) as imagen_id,
    (SELECT img.guid
     FROM wpyz_postmeta pm
     INNER JOIN wpyz_posts img ON pm.meta_value = img.ID
     WHERE pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id'
     LIMIT 1
    ) as imagen_url,

    -- Peso y dimensiones
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_weight' LIMIT 1) as peso,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_length' LIMIT 1) as largo,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_width' LIMIT 1) as ancho,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_height' LIMIT 1) as alto,

    -- Atributos del producto
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_product_attributes' LIMIT 1) as atributos_producto,

    -- Categorías (concatenadas)
    (SELECT GROUP_CONCAT(t.name SEPARATOR ', ')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_cat'
    ) as categorias,

    -- Tags (concatenados)
    (SELECT GROUP_CONCAT(t.name SEPARATOR ', ')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_tag'
    ) as tags,

    -- Brands (concatenados) - Plugin
    (SELECT GROUP_CONCAT(t.name SEPARATOR ', ')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_brand'
    ) as marcas,

    -- Yoast SEO - Plugin
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_focuskw' LIMIT 1) as focus_keyphrase,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_metadesc' LIMIT 1) as meta_description,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_keywordsynonyms' LIMIT 1) as related_keyphrases,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_focuskw_text_input' LIMIT 1) as synonyms,

    -- Fechas
    p.post_date as fecha_creacion,
    p.post_modified as fecha_modificacion

FROM wpyz_posts p
WHERE p.ID = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND p.post_type = 'product';

-- =====================================================
-- 2. CONSULTA DE VARIACIONES DE UN PRODUCTO
-- =====================================================
-- Ver todas las variaciones de un producto variable

SELECT
    pv.ID as variation_id,
    pv.post_title as titulo_variacion,
    p.post_title as producto_padre,

    -- SKU y precios
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_regular_price' LIMIT 1) as precio_regular,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_sale_price' LIMIT 1) as precio_oferta,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_price' LIMIT 1) as precio_actual,

    -- Stock
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_stock' LIMIT 1) as stock_cantidad,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_stock_status' LIMIT 1) as stock_estado,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_low_stock_amount' LIMIT 1) as umbral_stock_bajo,

    -- Imagen de la variación
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_thumbnail_id' LIMIT 1) as imagen_id,
    (SELECT img.guid
     FROM wpyz_postmeta pm
     INNER JOIN wpyz_posts img ON pm.meta_value = img.ID
     WHERE pm.post_id = pv.ID AND pm.meta_key = '_thumbnail_id'
     LIMIT 1
    ) as imagen_url,

    -- Atributos de la variación (ej: talla, color)
    (SELECT GROUP_CONCAT(CONCAT(REPLACE(pm.meta_key, 'attribute_', ''), ': ', pm.meta_value) SEPARATOR ', ')
     FROM wpyz_postmeta pm
     WHERE pm.post_id = pv.ID AND pm.meta_key LIKE 'attribute_%'
    ) as atributos,

    -- Descripción de variación
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_variation_description' LIMIT 1) as descripcion,

    pv.post_status as estado

FROM wpyz_posts pv
INNER JOIN wpyz_posts p ON pv.post_parent = p.ID
WHERE pv.post_parent = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO PADRE
  AND pv.post_type = 'product_variation'
  AND pv.post_status != 'trash'
ORDER BY pv.ID;

-- =====================================================
-- 3. CONSULTA COMPLETA: PRODUCTO + VARIACIONES
-- =====================================================
-- Producto padre con todas sus variaciones en una sola consulta

-- Primero el producto padre
SELECT
    p.ID as id,
    'PRODUCTO PADRE' as tipo,
    p.post_title as producto,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) as precio,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) as stock,
    NULL as atributos
FROM wpyz_posts p
WHERE p.ID = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND p.post_type = 'product'

UNION ALL

-- Luego las variaciones
SELECT
    pv.ID as id,
    'VARIACIÓN' as tipo,
    p.post_title as producto,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_price' LIMIT 1) as precio,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_stock' LIMIT 1) as stock,
    (SELECT GROUP_CONCAT(CONCAT(REPLACE(pm.meta_key, 'attribute_', ''), '=', pm.meta_value) SEPARATOR ', ')
     FROM wpyz_postmeta pm
     WHERE pm.post_id = pv.ID AND pm.meta_key LIKE 'attribute_%'
    ) as atributos
FROM wpyz_posts pv
INNER JOIN wpyz_posts p ON pv.post_parent = p.ID
WHERE pv.post_parent = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND pv.post_type = 'product_variation'
  AND pv.post_status != 'trash'

ORDER BY
    CASE tipo WHEN 'PRODUCTO PADRE' THEN 0 ELSE 1 END,
    id;

-- =====================================================
-- 4. OBTENER URLS DE IMÁGENES
-- =====================================================
-- Obtener las URLs reales de las imágenes del producto

SELECT
    p.ID as product_id,
    p.post_title as producto,
    img.ID as imagen_id,
    img.guid as url_imagen,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = img.ID AND meta_key = '_wp_attached_file' LIMIT 1) as ruta_archivo
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_thumbnail_id'
INNER JOIN wpyz_posts img ON pm.meta_value = img.ID
WHERE p.ID = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND p.post_type = 'product';

-- =====================================================
-- 5. OBTENER GALERÍA DE IMÁGENES
-- =====================================================
-- Ver todas las imágenes adicionales del producto

SELECT
    p.ID as product_id,
    p.post_title as producto,
    img.ID as imagen_id,
    img.guid as url_imagen
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_product_image_gallery'
INNER JOIN wpyz_posts img ON FIND_IN_SET(img.ID, pm.meta_value) > 0
WHERE p.ID = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND p.post_type = 'product';

-- =====================================================
-- 6. CONSULTA PARA EXPORTAR PRODUCTO COMPLETO
-- =====================================================
-- Formato más limpio para exportación

SELECT
    p.ID,
    p.post_title,
    p.post_content,
    p.post_excerpt,
    p.post_name,
    pm_type.meta_value as product_type,
    pm_sku.meta_value as sku,
    pm_price.meta_value as price,
    pm_regular.meta_value as regular_price,
    pm_sale.meta_value as sale_price,
    pm_stock.meta_value as stock_quantity,
    pm_stock_status.meta_value as stock_status,
    pm_low.meta_value as low_stock_threshold,
    pm_weight.meta_value as weight,
    pm_length.meta_value as length,
    pm_width.meta_value as width,
    pm_height.meta_value as height,
    pm_thumb.meta_value as thumbnail_id,
    pm_yoast_focus.meta_value as focus_keyphrase,
    pm_yoast_meta.meta_value as meta_description
FROM wpyz_posts p
LEFT JOIN wpyz_postmeta pm_type ON p.ID = pm_type.post_id AND pm_type.meta_key = '_product_type'
LEFT JOIN wpyz_postmeta pm_sku ON p.ID = pm_sku.post_id AND pm_sku.meta_key = '_sku'
LEFT JOIN wpyz_postmeta pm_price ON p.ID = pm_price.post_id AND pm_price.meta_key = '_price'
LEFT JOIN wpyz_postmeta pm_regular ON p.ID = pm_regular.post_id AND pm_regular.meta_key = '_regular_price'
LEFT JOIN wpyz_postmeta pm_sale ON p.ID = pm_sale.post_id AND pm_sale.meta_key = '_sale_price'
LEFT JOIN wpyz_postmeta pm_stock ON p.ID = pm_stock.post_id AND pm_stock.meta_key = '_stock'
LEFT JOIN wpyz_postmeta pm_stock_status ON p.ID = pm_stock_status.post_id AND pm_stock_status.meta_key = '_stock_status'
LEFT JOIN wpyz_postmeta pm_low ON p.ID = pm_low.post_id AND pm_low.meta_key = '_low_stock_amount'
LEFT JOIN wpyz_postmeta pm_weight ON p.ID = pm_weight.post_id AND pm_weight.meta_key = '_weight'
LEFT JOIN wpyz_postmeta pm_length ON p.ID = pm_length.post_id AND pm_length.meta_key = '_length'
LEFT JOIN wpyz_postmeta pm_width ON p.ID = pm_width.post_id AND pm_width.meta_key = '_width'
LEFT JOIN wpyz_postmeta pm_height ON p.ID = pm_height.post_id AND pm_height.meta_key = '_height'
LEFT JOIN wpyz_postmeta pm_thumb ON p.ID = pm_thumb.post_id AND pm_thumb.meta_key = '_thumbnail_id'
LEFT JOIN wpyz_postmeta pm_yoast_focus ON p.ID = pm_yoast_focus.post_id AND pm_yoast_focus.meta_key = '_yoast_wpseo_focuskw'
LEFT JOIN wpyz_postmeta pm_yoast_meta ON p.ID = pm_yoast_meta.post_id AND pm_yoast_meta.meta_key = '_yoast_wpseo_metadesc'
WHERE p.ID = 33343 -- CAMBIAR POR EL ID DEL PRODUCTO
  AND p.post_type = 'product';

-- =====================================================
-- NOTAS
-- =====================================================
-- 1. Reemplazar 123 por el ID del producto que deseas consultar
-- 2. Los campos de Yoast SEO solo aparecerán si tienes el plugin instalado
-- 3. El campo 'brands' depende del plugin de marcas que uses
-- 4. Los atributos en _product_attributes están serializados (formato PHP)
-- 5. Para ver la URL completa de imágenes, concatena el dominio + guid
-- 6. _thumbnail_id es el ID de la imagen en wpyz_posts
-- 7. GROUP_CONCAT tiene límite de 1024 chars (ajustar con SET group_concat_max_len)
-- =====================================================
