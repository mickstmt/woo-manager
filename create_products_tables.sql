-- =====================================================
-- SCRIPT DE CREACIÓN DE TABLAS PARA PRODUCTOS
-- Sistema POS/E-commerce Propio
-- =====================================================
-- Estructura SIMPLIFICADA para manejar productos
-- Diseñada para facilitar migración desde WooCommerce
-- pero con estructura moderna y optimizada
-- =====================================================

-- Cambiar por el nombre de tu base de datos
-- USE tu_base_de_datos;

SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. TABLA DE CATEGORÍAS
-- =====================================================
CREATE TABLE IF NOT EXISTS `categories` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(200) NOT NULL,
  `slug` VARCHAR(200) NOT NULL,
  `description` TEXT,
  `parent_id` INT UNSIGNED DEFAULT NULL,
  `image_url` VARCHAR(500),
  `display_order` INT DEFAULT 0,
  `type` ENUM('category', 'tag', 'brand') DEFAULT 'category', -- Tipo de taxonomía
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug_type` (`slug`, `type`), -- Slug único por tipo
  KEY `parent_id` (`parent_id`),
  KEY `type` (`type`),
  KEY `is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 2. TABLA DE PRODUCTOS
-- =====================================================
CREATE TABLE IF NOT EXISTS `products` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `slug` VARCHAR(255) NOT NULL,
  `sku` VARCHAR(100) UNIQUE,
  `description` TEXT,
  `short_description` VARCHAR(500),

  -- Tipo de producto
  `product_type` ENUM('simple', 'variable') DEFAULT 'simple',

  -- Precio
  `regular_price` DECIMAL(10, 2) NOT NULL,
  `sale_price` DECIMAL(10, 2) DEFAULT NULL,
  `price` DECIMAL(10, 2) NOT NULL, -- Precio final (con descuento si aplica)

  -- Inventario
  `manage_stock` BOOLEAN DEFAULT TRUE,
  `stock_quantity` INT DEFAULT 0,
  `stock_status` ENUM('instock', 'outofstock', 'onbackorder') DEFAULT 'instock',
  `low_stock_threshold` INT DEFAULT 5,

  -- Imágenes
  `image_url` VARCHAR(500),
  `gallery_images` JSON, -- Array de URLs de imágenes adicionales

  -- Peso y dimensiones
  `weight` DECIMAL(10, 2),
  `length` DECIMAL(10, 2),
  `width` DECIMAL(10, 2),
  `height` DECIMAL(10, 2),

  -- Categoría principal
  `category_id` INT UNSIGNED,

  -- Estado
  `status` ENUM('active', 'draft', 'archived') DEFAULT 'active',
  `is_featured` BOOLEAN DEFAULT FALSE,

  -- SEO (Yoast)
  `seo_title` VARCHAR(255),
  `seo_description` TEXT,
  `focus_keyphrase` VARCHAR(255),
  `seo_keywords` TEXT, -- Related keyphrases y synonyms

  -- Metadatos adicionales (flexibilidad para campos extras)
  `metadata` JSON,

  -- Auditoría
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_by` INT UNSIGNED,

  PRIMARY KEY (`id`),
  UNIQUE KEY `sku` (`sku`),
  UNIQUE KEY `slug` (`slug`),
  KEY `product_type` (`product_type`),
  KEY `category_id` (`category_id`),
  KEY `status` (`status`),
  KEY `stock_status` (`stock_status`),
  FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. TABLA DE ATRIBUTOS (para productos variables)
-- =====================================================
-- Ejemplo: Talla, Color, Material
CREATE TABLE IF NOT EXISTS `product_attributes` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL, -- "Talla", "Color", etc.
  `slug` VARCHAR(100) NOT NULL,
  `type` ENUM('text', 'color', 'image') DEFAULT 'text',
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 4. TABLA DE TÉRMINOS DE ATRIBUTOS
-- =====================================================
-- Ejemplo: S, M, L (para Talla) o Rojo, Azul (para Color)
CREATE TABLE IF NOT EXISTS `product_attribute_terms` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `attribute_id` INT UNSIGNED NOT NULL,
  `name` VARCHAR(100) NOT NULL, -- "S", "M", "Rojo", etc.
  `slug` VARCHAR(100) NOT NULL,
  `value` VARCHAR(100), -- Para colores: código hex, para otros: mismo que name
  `display_order` INT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `attribute_id` (`attribute_id`),
  UNIQUE KEY `attribute_slug_term_slug` (`attribute_id`, `slug`),
  FOREIGN KEY (`attribute_id`) REFERENCES `product_attributes`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 5. TABLA DE VARIACIONES
-- =====================================================
-- Solo para productos con product_type='variable'
CREATE TABLE IF NOT EXISTS `product_variations` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` INT UNSIGNED NOT NULL, -- Producto padre
  `sku` VARCHAR(100) UNIQUE,
  `description` VARCHAR(500),

  -- Precio
  `regular_price` DECIMAL(10, 2) NOT NULL,
  `sale_price` DECIMAL(10, 2) DEFAULT NULL,
  `price` DECIMAL(10, 2) NOT NULL,

  -- Inventario
  `manage_stock` BOOLEAN DEFAULT TRUE,
  `stock_quantity` INT DEFAULT 0,
  `stock_status` ENUM('instock', 'outofstock', 'onbackorder') DEFAULT 'instock',

  -- Imagen específica de esta variación
  `image_url` VARCHAR(500),

  -- Atributos de esta variación (JSON)
  -- Ejemplo: {"talla": "M", "color": "Rojo"}
  `attributes` JSON NOT NULL,

  -- Estado
  `is_active` BOOLEAN DEFAULT TRUE,

  -- Auditoría
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (`id`),
  UNIQUE KEY `sku` (`sku`),
  KEY `product_id` (`product_id`),
  KEY `stock_status` (`stock_status`),
  FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 6. TABLA INTERMEDIA: Producto-Categoría (múltiples categorías)
-- =====================================================
CREATE TABLE IF NOT EXISTS `product_categories` (
  `product_id` INT UNSIGNED NOT NULL,
  `category_id` INT UNSIGNED NOT NULL,
  `is_primary` BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (`product_id`, `category_id`),
  KEY `category_id` (`category_id`),
  FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 7. ÍNDICES DE OPTIMIZACIÓN
-- =====================================================
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_created_at ON products(created_at);
CREATE INDEX idx_variations_product_price ON product_variations(product_id, price);

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- DATOS DE EJEMPLO
-- =====================================================

-- Categorías
INSERT INTO categories (name, slug, description) VALUES
('Electrónica', 'electronica', 'Productos electrónicos'),
('Ropa', 'ropa', 'Prendas de vestir'),
('Calzado', 'calzado', 'Zapatos y zapatillas');

-- Producto Simple
INSERT INTO products (name, slug, sku, description, product_type, regular_price, sale_price, price, stock_quantity, stock_status, category_id, status)
VALUES
('Laptop HP 15-dw3000', 'laptop-hp-15-dw3000', 'LAP-HP-001', 'Laptop HP con procesador Intel i5', 'simple', 2500.00, 2200.00, 2200.00, 15, 'instock', 1, 'active');

-- Atributos
INSERT INTO product_attributes (name, slug, type) VALUES
('Talla', 'talla', 'text'),
('Color', 'color', 'color');

-- Términos de atributos
INSERT INTO product_attribute_terms (attribute_id, name, slug, value) VALUES
(1, 'S', 's', 'S'),
(1, 'M', 'm', 'M'),
(1, 'L', 'l', 'L'),
(2, 'Rojo', 'rojo', '#FF0000'),
(2, 'Azul', 'azul', '#0000FF'),
(2, 'Negro', 'negro', '#000000');

-- Producto Variable
INSERT INTO products (name, slug, sku, description, product_type, regular_price, price, manage_stock, stock_quantity, category_id, status)
VALUES
('Camiseta Deportiva', 'camiseta-deportiva', 'CAM-DEP-001', 'Camiseta para deporte', 'variable', 45.00, 45.00, FALSE, 0, 2, 'active');

SET @parent_id = LAST_INSERT_ID();

-- Variaciones del producto
INSERT INTO product_variations (product_id, sku, regular_price, price, stock_quantity, stock_status, attributes) VALUES
(@parent_id, 'CAM-DEP-001-S-ROJO', 45.00, 45.00, 10, 'instock', '{"talla": "S", "color": "Rojo"}'),
(@parent_id, 'CAM-DEP-001-M-ROJO', 45.00, 45.00, 15, 'instock', '{"talla": "M", "color": "Rojo"}'),
(@parent_id, 'CAM-DEP-001-L-ROJO', 45.00, 45.00, 8, 'instock', '{"talla": "L", "color": "Rojo"}'),
(@parent_id, 'CAM-DEP-001-S-AZUL', 45.00, 45.00, 12, 'instock', '{"talla": "S", "color": "Azul"}'),
(@parent_id, 'CAM-DEP-001-M-AZUL', 45.00, 45.00, 20, 'instock', '{"talla": "M", "color": "Azul"}'),
(@parent_id, 'CAM-DEP-001-L-AZUL', 45.00, 45.00, 5, 'instock', '{"talla": "L", "color": "Azul"}');

-- =====================================================
-- CONSULTAS ÚTILES
-- =====================================================

-- Ver todos los productos con su categoría
/*
SELECT
    p.id,
    p.name,
    p.sku,
    p.price,
    p.stock_quantity,
    p.stock_status,
    c.name as category
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
WHERE p.status = 'active'
ORDER BY p.name;
*/

-- Ver productos con stock bajo
/*
SELECT
    id,
    name,
    sku,
    stock_quantity,
    low_stock_threshold
FROM products
WHERE stock_quantity <= low_stock_threshold
  AND stock_status = 'instock'
  AND status = 'active'
ORDER BY stock_quantity ASC;
*/

-- Ver todas las variaciones de un producto
/*
SELECT
    pv.id,
    p.name as product_name,
    pv.sku,
    pv.price,
    pv.stock_quantity,
    pv.attributes
FROM product_variations pv
INNER JOIN products p ON pv.product_id = p.id
WHERE p.id = 1
  AND pv.is_active = TRUE
ORDER BY pv.id;
*/

-- Buscar productos por nombre o SKU
/*
SELECT
    id,
    name,
    sku,
    price,
    stock_quantity
FROM products
WHERE (name LIKE '%laptop%' OR sku LIKE '%laptop%')
  AND status = 'active'
ORDER BY name;
*/

-- Productos más vendidos (requiere tabla de ventas)
/*
-- Esta consulta necesitaría una tabla de order_items
-- Es solo un ejemplo de estructura
*/

-- Stock total por categoría
/*
SELECT
    c.name as category,
    COUNT(p.id) as total_products,
    SUM(p.stock_quantity) as total_stock,
    SUM(CASE WHEN p.stock_status = 'instock' THEN 1 ELSE 0 END) as in_stock_count
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
WHERE p.status = 'active'
GROUP BY c.id, c.name
ORDER BY total_stock DESC;
*/

-- =====================================================
-- SCRIPT DE MIGRACIÓN DESDE WOOCOMMERCE
-- =====================================================
/*
-- Este sería el script para migrar productos desde WooCommerce
-- Asumiendo que tienes acceso a ambas bases de datos

-- MIGRAR CATEGORÍAS
INSERT INTO categories (name, slug, description, parent_id)
SELECT
    t.name,
    t.slug,
    tt.description,
    NULL -- Puedes mapear parent_id si lo necesitas
FROM wp_terms t
INNER JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
WHERE tt.taxonomy = 'product_cat';

-- MIGRAR PRODUCTOS SIMPLES
INSERT INTO products (name, slug, sku, description, product_type, regular_price, sale_price, price, stock_quantity, stock_status, status)
SELECT
    p.post_title,
    p.post_name,
    (SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1),
    p.post_content,
    'simple',
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_regular_price' LIMIT 1) AS DECIMAL(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_sale_price' LIMIT 1) AS DECIMAL(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) AS DECIMAL(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) AS UNSIGNED),
    (SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_stock_status' LIMIT 1),
    CASE p.post_status WHEN 'publish' THEN 'active' WHEN 'draft' THEN 'draft' ELSE 'archived' END
FROM wp_posts p
WHERE p.post_type = 'product'
  AND p.post_status IN ('publish', 'draft');

-- MIGRAR VARIACIONES
-- Similar al anterior pero para product_variations
-- Necesitarías mapear los atributos de WooCommerce a JSON
*/

-- =====================================================
-- NOTAS IMPORTANTES
-- =====================================================
-- 1. Estructura MODERNA y SIMPLE, no replica WooCommerce
-- 2. Usa tipos de datos SQL estándar (JSON, ENUM, etc.)
-- 3. Nombres de tablas en inglés y descriptivos
-- 4. Campos esenciales para e-commerce/POS
-- 5. Campo metadata (JSON) para flexibilidad futura
-- 6. Índices optimizados para búsquedas comunes
-- 7. Relaciones con foreign keys para integridad
-- 8. Timestamps automáticos para auditoría
-- 9. Fácil de migrar DESDE WooCommerce
-- 10. Más fácil de mantener y consultar que WooCommerce
--
-- Campos principales:
-- - SKU: Código único del producto
-- - price: Precio final de venta
-- - stock_quantity: Cantidad disponible
-- - stock_status: Estado del inventario
-- - attributes (JSON): Atributos de variaciones
-- - metadata (JSON): Campos personalizados adicionales
-- =====================================================
