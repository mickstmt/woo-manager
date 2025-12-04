-- =====================================================
-- SCRIPT DE EXPORTACIÓN COMPLETA DE PRODUCTO
-- Producto ID: 33343
-- =====================================================
-- Este script exporta TODOS los datos del producto
-- en un formato listo para importar a la nueva estructura
-- =====================================================

-- =====================================================
-- 1. DATOS DEL PRODUCTO PADRE
-- =====================================================
SELECT
    -- Información básica
    p.ID as product_id,
    p.post_title as name,
    p.post_name as slug,
    p.post_content as description,
    p.post_excerpt as short_description,
    p.post_status as status,

    -- Tipo de producto
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_product_type' LIMIT 1) as product_type,

    -- SKU y precios
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_regular_price' LIMIT 1) as regular_price,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sale_price' LIMIT 1) as sale_price,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) as price,

    -- Inventario
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_manage_stock' LIMIT 1) as manage_stock,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) as stock_quantity,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock_status' LIMIT 1) as stock_status,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_low_stock_amount' LIMIT 1) as low_stock_threshold,

    -- Imagen principal
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_thumbnail_id' LIMIT 1) as image_id,
    (SELECT img.guid
     FROM wpyz_postmeta pm
     INNER JOIN wpyz_posts img ON pm.meta_value = img.ID
     WHERE pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id'
     LIMIT 1
    ) as image_url,

    -- Galería de imágenes (IDs separados por coma)
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_product_image_gallery' LIMIT 1) as gallery_image_ids,

    -- Peso y dimensiones
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_weight' LIMIT 1) as weight,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_length' LIMIT 1) as length,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_width' LIMIT 1) as width,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_height' LIMIT 1) as height,

    -- Categorías (concatenadas)
    (SELECT GROUP_CONCAT(t.term_id SEPARATOR ',')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_cat'
    ) as category_ids,
    (SELECT GROUP_CONCAT(t.name SEPARATOR '|')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_cat'
    ) as category_names,

    -- Tags (concatenados)
    (SELECT GROUP_CONCAT(t.term_id SEPARATOR ',')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_tag'
    ) as tag_ids,
    (SELECT GROUP_CONCAT(t.name SEPARATOR '|')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_tag'
    ) as tag_names,

    -- Brands (concatenados)
    (SELECT GROUP_CONCAT(t.term_id SEPARATOR ',')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_brand'
    ) as brand_ids,
    (SELECT GROUP_CONCAT(t.name SEPARATOR '|')
     FROM wpyz_term_relationships tr
     INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
     INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
     WHERE tr.object_id = p.ID AND tt.taxonomy = 'product_brand'
    ) as brand_names,

    -- Atributos del producto (serializado)
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_product_attributes' LIMIT 1) as product_attributes,

    -- SEO - Yoast
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_title' LIMIT 1) as seo_title,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_metadesc' LIMIT 1) as seo_description,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_focuskw' LIMIT 1) as focus_keyphrase,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_keywordsynonyms' LIMIT 1) as related_keyphrases,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_yoast_wpseo_focuskw_text_input' LIMIT 1) as synonyms,

    -- Featured
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_featured' LIMIT 1) as is_featured,

    -- Fechas
    p.post_date as created_at,
    p.post_modified as updated_at,
    p.post_author as created_by

FROM wpyz_posts p
WHERE p.ID = 33343
  AND p.post_type = 'product'
INTO OUTFILE 'C:/tmp/producto_33343_padre.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';

-- =====================================================
-- 2. EXPORTAR VARIACIONES DEL PRODUCTO
-- =====================================================
SELECT
    pv.ID as variation_id,
    pv.post_parent as product_id,
    p.post_title as product_name,

    -- SKU y precios
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_regular_price' LIMIT 1) as regular_price,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_sale_price' LIMIT 1) as sale_price,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_price' LIMIT 1) as price,

    -- Stock
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_manage_stock' LIMIT 1) as manage_stock,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_stock' LIMIT 1) as stock_quantity,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_stock_status' LIMIT 1) as stock_status,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_low_stock_amount' LIMIT 1) as low_stock_threshold,

    -- Imagen
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_thumbnail_id' LIMIT 1) as image_id,
    (SELECT img.guid
     FROM wpyz_postmeta pm
     INNER JOIN wpyz_posts img ON pm.meta_value = img.ID
     WHERE pm.post_id = pv.ID AND pm.meta_key = '_thumbnail_id'
     LIMIT 1
    ) as image_url,

    -- Descripción de variación
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = pv.ID AND meta_key = '_variation_description' LIMIT 1) as description,

    -- Atributos (en formato JSON-like)
    (SELECT GROUP_CONCAT(CONCAT('"', REPLACE(pm.meta_key, 'attribute_', ''), '":"', pm.meta_value, '"') SEPARATOR ',')
     FROM wpyz_postmeta pm
     WHERE pm.post_id = pv.ID AND pm.meta_key LIKE 'attribute_%'
    ) as attributes_json,

    -- Estado
    pv.post_status as status,
    pv.post_date as created_at,
    pv.post_modified as updated_at

FROM wpyz_posts pv
INNER JOIN wpyz_posts p ON pv.post_parent = p.ID
WHERE pv.post_parent = 33343
  AND pv.post_type = 'product_variation'
  AND pv.post_status != 'trash'
ORDER BY pv.ID
INTO OUTFILE 'C:/tmp/producto_33343_variaciones.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';

-- =====================================================
-- 3. EXPORTAR URLS DE GALERÍA DE IMÁGENES
-- =====================================================
SELECT
    p.ID as product_id,
    img.ID as image_id,
    img.guid as image_url,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = img.ID AND meta_key = '_wp_attached_file' LIMIT 1) as file_path,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = img.ID AND meta_key = '_wp_attachment_metadata' LIMIT 1) as image_metadata
FROM wpyz_posts p
INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_product_image_gallery'
INNER JOIN wpyz_posts img ON FIND_IN_SET(img.ID, pm.meta_value) > 0
WHERE p.ID = 33343
  AND p.post_type = 'product'
INTO OUTFILE 'C:/tmp/producto_33343_galeria.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';

-- =====================================================
-- 4. EXPORTAR CATEGORÍAS ASOCIADAS (DETALLE)
-- =====================================================
SELECT
    p.ID as product_id,
    t.term_id as category_id,
    t.name as category_name,
    t.slug as category_slug,
    tt.taxonomy as taxonomy_type,
    tt.description as category_description,
    tt.parent as parent_id
FROM wpyz_posts p
INNER JOIN wpyz_term_relationships tr ON p.ID = tr.object_id
INNER JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
INNER JOIN wpyz_terms t ON tt.term_id = t.term_id
WHERE p.ID = 33343
  AND p.post_type = 'product'
  AND tt.taxonomy IN ('product_cat', 'product_tag', 'product_brand')
ORDER BY tt.taxonomy, t.name
INTO OUTFILE 'C:/tmp/producto_33343_taxonomias.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';

-- =====================================================
-- ALTERNATIVA: CONSULTA PARA VER EN PANTALLA (NO EXPORTAR)
-- =====================================================
-- Si solo quieres ver los datos sin exportar a CSV, usa esta consulta:

/*
SELECT
    p.ID,
    p.post_title,
    p.post_name,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1) as sku,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) as price,
    (SELECT meta_value FROM wpyz_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) as stock,
    (SELECT img.guid FROM wpyz_postmeta pm INNER JOIN wpyz_posts img ON pm.meta_value = img.ID WHERE pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id' LIMIT 1) as image_url
FROM wpyz_posts p
WHERE p.ID = 33343
  AND p.post_type = 'product';
*/

-- =====================================================
-- NOTAS DE USO
-- =====================================================
-- 1. Las consultas con INTO OUTFILE requieren permisos FILE en MySQL
-- 2. La ruta C:/tmp/ debe existir y MySQL debe tener permisos de escritura
-- 3. En Linux/Mac cambiar la ruta a /tmp/
-- 4. Si no tienes permisos, copia las consultas sin la parte INTO OUTFILE
--    y exporta manualmente desde tu cliente MySQL (phpMyAdmin, MySQL Workbench, etc.)
-- 5. Los archivos CSV generados están listos para importar a tu nueva BD
-- 6. El campo attributes_json en variaciones está en formato compatible con JSON
-- 7. Los separadores son: campos=coma(,) texto=comillas(") líneas=salto(\n)
-- =====================================================
