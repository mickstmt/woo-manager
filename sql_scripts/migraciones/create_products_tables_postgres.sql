-- =====================================================
-- SCRIPT DE CREACIÓN DE TABLAS PARA PRODUCTOS
-- Sistema POS/E-commerce Propio
-- PostgreSQL Version
-- =====================================================
-- Estructura SIMPLIFICADA para manejar productos
-- Diseñada para facilitar migración desde WooCommerce
-- pero con estructura moderna y optimizada
-- =====================================================

-- Cambiar por el nombre de tu base de datos
-- \c tu_base_de_datos;

-- =====================================================
-- 1. TABLA DE CATEGORÍAS
-- =====================================================
-- Tipo de taxonomía (category, tag, brand)
CREATE TYPE category_type_enum AS ENUM ('category', 'tag', 'brand');

CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(200) NOT NULL,
  description TEXT,
  parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  image_url VARCHAR(500),
  display_order INTEGER DEFAULT 0,
  type category_type_enum DEFAULT 'category', -- Tipo de taxonomía
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(slug, type) -- Slug único por tipo
);

CREATE INDEX idx_categories_parent_id ON categories(parent_id);
CREATE INDEX idx_categories_type ON categories(type);
CREATE INDEX idx_categories_is_active ON categories(is_active);

-- =====================================================
-- 2. TABLA DE PRODUCTOS
-- =====================================================
CREATE TYPE product_type_enum AS ENUM ('simple', 'variable');
CREATE TYPE product_status_enum AS ENUM ('active', 'draft', 'archived');
CREATE TYPE stock_status_enum AS ENUM ('instock', 'outofstock', 'onbackorder');

CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL UNIQUE,
  sku VARCHAR(100) UNIQUE,
  description TEXT,
  short_description VARCHAR(500),

  -- Tipo de producto
  product_type product_type_enum DEFAULT 'simple',

  -- Precio
  regular_price NUMERIC(10, 2) NOT NULL,
  sale_price NUMERIC(10, 2),
  price NUMERIC(10, 2) NOT NULL, -- Precio final (con descuento si aplica)

  -- Inventario
  manage_stock BOOLEAN DEFAULT TRUE,
  stock_quantity INTEGER DEFAULT 0,
  stock_status stock_status_enum DEFAULT 'instock',
  low_stock_threshold INTEGER DEFAULT 5,

  -- Imágenes
  image_url VARCHAR(500),
  gallery_images JSONB, -- Array de URLs de imágenes adicionales

  -- Peso y dimensiones
  weight NUMERIC(10, 2),
  length NUMERIC(10, 2),
  width NUMERIC(10, 2),
  height NUMERIC(10, 2),

  -- Categoría principal
  category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,

  -- Estado
  status product_status_enum DEFAULT 'active',
  is_featured BOOLEAN DEFAULT FALSE,

  -- SEO (Yoast)
  seo_title VARCHAR(255),
  seo_description TEXT,
  focus_keyphrase VARCHAR(255),
  seo_keywords TEXT, -- Related keyphrases y synonyms

  -- Metadatos adicionales (flexibilidad para campos extras)
  metadata JSONB,

  -- Auditoría
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by INTEGER
);

CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_product_type ON products(product_type);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_stock_status ON products(stock_status);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_created_at ON products(created_at);

-- Índice GIN para búsquedas en metadata JSONB
CREATE INDEX idx_products_metadata ON products USING GIN(metadata);

-- =====================================================
-- 3. TABLA DE ATRIBUTOS (para productos variables)
-- =====================================================
CREATE TYPE attribute_type_enum AS ENUM ('text', 'color', 'image');

CREATE TABLE IF NOT EXISTS product_attributes (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  type attribute_type_enum DEFAULT 'text',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 4. TABLA DE TÉRMINOS DE ATRIBUTOS
-- =====================================================
CREATE TABLE IF NOT EXISTS product_attribute_terms (
  id SERIAL PRIMARY KEY,
  attribute_id INTEGER NOT NULL REFERENCES product_attributes(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) NOT NULL,
  value VARCHAR(100),
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(attribute_id, slug)
);

CREATE INDEX idx_attribute_terms_attribute_id ON product_attribute_terms(attribute_id);

-- =====================================================
-- 5. TABLA DE VARIACIONES
-- =====================================================
CREATE TABLE IF NOT EXISTS product_variations (
  id SERIAL PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  sku VARCHAR(100) UNIQUE,
  description VARCHAR(500),

  -- Precio
  regular_price NUMERIC(10, 2) NOT NULL,
  sale_price NUMERIC(10, 2),
  price NUMERIC(10, 2) NOT NULL,

  -- Inventario
  manage_stock BOOLEAN DEFAULT TRUE,
  stock_quantity INTEGER DEFAULT 0,
  stock_status stock_status_enum DEFAULT 'instock',

  -- Imagen específica de esta variación
  image_url VARCHAR(500),

  -- Atributos de esta variación (JSONB)
  -- Ejemplo: {"talla": "M", "color": "Rojo"}
  attributes JSONB NOT NULL,

  -- Estado
  is_active BOOLEAN DEFAULT TRUE,

  -- Auditoría
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_variations_product_id ON product_variations(product_id);
CREATE INDEX idx_variations_sku ON product_variations(sku);
CREATE INDEX idx_variations_stock_status ON product_variations(stock_status);
CREATE INDEX idx_variations_product_price ON product_variations(product_id, price);

-- Índice GIN para búsquedas en attributes JSONB
CREATE INDEX idx_variations_attributes ON product_variations USING GIN(attributes);

-- =====================================================
-- 6. TABLA INTERMEDIA: Producto-Categoría
-- =====================================================
CREATE TABLE IF NOT EXISTS product_categories (
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  is_primary BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (product_id, category_id)
);

CREATE INDEX idx_product_categories_category_id ON product_categories(category_id);

-- =====================================================
-- TRIGGERS PARA UPDATED_AT AUTOMÁTICO
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_categories_updated_at
BEFORE UPDATE ON categories
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_variations_updated_at
BEFORE UPDATE ON product_variations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

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
('Camiseta Deportiva', 'camiseta-deportiva', 'CAM-DEP-001', 'Camiseta para deporte', 'variable', 45.00, 45.00, FALSE, 0, 2, 'active')
RETURNING id;

-- Variaciones del producto (ajustar el product_id según corresponda)
-- Nota: En producción, usarías el ID retornado del INSERT anterior
INSERT INTO product_variations (product_id, sku, regular_price, price, stock_quantity, stock_status, attributes) VALUES
(2, 'CAM-DEP-001-S-ROJO', 45.00, 45.00, 10, 'instock', '{"talla": "S", "color": "Rojo"}'::jsonb),
(2, 'CAM-DEP-001-M-ROJO', 45.00, 45.00, 15, 'instock', '{"talla": "M", "color": "Rojo"}'::jsonb),
(2, 'CAM-DEP-001-L-ROJO', 45.00, 45.00, 8, 'instock', '{"talla": "L", "color": "Rojo"}'::jsonb),
(2, 'CAM-DEP-001-S-AZUL', 45.00, 45.00, 12, 'instock', '{"talla": "S", "color": "Azul"}'::jsonb),
(2, 'CAM-DEP-001-M-AZUL', 45.00, 45.00, 20, 'instock', '{"talla": "M", "color": "Azul"}'::jsonb),
(2, 'CAM-DEP-001-L-AZUL', 45.00, 45.00, 5, 'instock', '{"talla": "L", "color": "Azul"}'::jsonb);

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
WHERE p.id = 2
  AND pv.is_active = TRUE
ORDER BY pv.id;
*/

-- Buscar productos por nombre o SKU (case-insensitive en PostgreSQL)
/*
SELECT
    id,
    name,
    sku,
    price,
    stock_quantity
FROM products
WHERE (name ILIKE '%laptop%' OR sku ILIKE '%laptop%')
  AND status = 'active'
ORDER BY name;
*/

-- Buscar variaciones por atributo específico usando JSONB
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
WHERE pv.attributes->>'talla' = 'M'
  AND pv.attributes->>'color' = 'Azul'
  AND pv.is_active = TRUE;
*/

-- Stock total por categoría
/*
SELECT
    c.name as category,
    COUNT(p.id) as total_products,
    SUM(p.stock_quantity) as total_stock,
    COUNT(CASE WHEN p.stock_status = 'instock' THEN 1 END) as in_stock_count
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
WHERE p.status = 'active'
GROUP BY c.id, c.name
ORDER BY total_stock DESC;
*/

-- Buscar en metadata JSONB
/*
SELECT
    id,
    name,
    sku,
    metadata
FROM products
WHERE metadata->>'custom_field' = 'some_value'
  AND status = 'active';
*/

-- Búsqueda full-text en PostgreSQL (más avanzada)
/*
-- Primero crear un índice de búsqueda de texto
CREATE INDEX idx_products_search ON products
USING GIN(to_tsvector('spanish', name || ' ' || COALESCE(description, '')));

-- Luego usar en búsquedas
SELECT
    id,
    name,
    sku,
    price
FROM products
WHERE to_tsvector('spanish', name || ' ' || COALESCE(description, '')) @@
      to_tsquery('spanish', 'laptop | computadora')
  AND status = 'active'
ORDER BY ts_rank(
    to_tsvector('spanish', name || ' ' || COALESCE(description, '')),
    to_tsquery('spanish', 'laptop | computadora')
) DESC;
*/

-- =====================================================
-- SCRIPT DE MIGRACIÓN DESDE WOOCOMMERCE (MySQL)
-- =====================================================
/*
-- Para migrar desde WooCommerce (MySQL) a PostgreSQL necesitarías:
-- 1. Usar herramientas como pgloader o scripts personalizados
-- 2. O exportar a CSV desde MySQL e importar a PostgreSQL

-- Ejemplo con postgres_fdw (Foreign Data Wrapper)
-- Esto permite conectar PostgreSQL directamente a MySQL

-- 1. Instalar postgres_fdw y mysql_fdw
CREATE EXTENSION mysql_fdw;

-- 2. Crear servidor remoto (MySQL/WooCommerce)
CREATE SERVER woocommerce_mysql
FOREIGN DATA WRAPPER mysql_fdw
OPTIONS (host 'mysql_host', port '3306');

-- 3. Crear user mapping
CREATE USER MAPPING FOR postgres
SERVER woocommerce_mysql
OPTIONS (username 'mysql_user', password 'mysql_password');

-- 4. Importar esquema
IMPORT FOREIGN SCHEMA woocommerce_db
FROM SERVER woocommerce_mysql
INTO public;

-- 5. Migrar categorías
INSERT INTO categories (name, slug, description, parent_id)
SELECT
    t.name,
    t.slug,
    tt.description,
    NULL
FROM wp_terms t
INNER JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
WHERE tt.taxonomy = 'product_cat';

-- 6. Migrar productos simples
INSERT INTO products (name, slug, sku, description, product_type, regular_price, sale_price, price, stock_quantity, stock_status, status)
SELECT
    p.post_title,
    p.post_name,
    (SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_sku' LIMIT 1),
    p.post_content,
    'simple',
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_regular_price' LIMIT 1) AS NUMERIC(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_sale_price' LIMIT 1) AS NUMERIC(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_price' LIMIT 1) AS NUMERIC(10,2)),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_stock' LIMIT 1) AS INTEGER),
    CAST((SELECT meta_value FROM wp_postmeta WHERE post_id = p.ID AND meta_key = '_stock_status' LIMIT 1) AS stock_status_enum),
    CASE p.post_status
        WHEN 'publish' THEN 'active'::product_status_enum
        WHEN 'draft' THEN 'draft'::product_status_enum
        ELSE 'archived'::product_status_enum
    END
FROM wp_posts p
WHERE p.post_type = 'product'
  AND p.post_status IN ('publish', 'draft');
*/

-- =====================================================
-- FUNCIONES ÚTILES
-- =====================================================

-- Función para actualizar el precio de un producto (considerando sale_price)
CREATE OR REPLACE FUNCTION update_product_price()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sale_price IS NOT NULL AND NEW.sale_price > 0 AND NEW.sale_price < NEW.regular_price THEN
        NEW.price := NEW.sale_price;
    ELSE
        NEW.price := NEW.regular_price;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_product_price
BEFORE INSERT OR UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_product_price();

CREATE TRIGGER trigger_update_variation_price
BEFORE INSERT OR UPDATE ON product_variations
FOR EACH ROW
EXECUTE FUNCTION update_product_price();

-- Función para verificar stock bajo
CREATE OR REPLACE FUNCTION check_low_stock()
RETURNS TABLE(product_id INTEGER, product_name VARCHAR, sku VARCHAR, current_stock INTEGER, threshold INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.sku,
        p.stock_quantity,
        p.low_stock_threshold
    FROM products p
    WHERE p.stock_quantity <= p.low_stock_threshold
      AND p.stock_status = 'instock'
      AND p.status = 'active'
    ORDER BY p.stock_quantity ASC;
END;
$$ LANGUAGE plpgsql;

-- Uso: SELECT * FROM check_low_stock();

-- =====================================================
-- NOTAS IMPORTANTES PARA POSTGRESQL
-- =====================================================
-- 1. PostgreSQL usa SERIAL en lugar de AUTO_INCREMENT
-- 2. JSONB es más eficiente que JSON para búsquedas
-- 3. ENUMs son type-safe pero requieren ALTER TYPE para cambios
-- 4. ILIKE es case-insensitive (vs LIKE)
-- 5. Los triggers son más robustos en PostgreSQL
-- 6. Índices GIN para búsquedas en JSONB
-- 7. Full-text search nativo y poderoso
-- 8. Foreign Data Wrappers para conectar a otras DBs
-- 9. NUMERIC es más preciso que DECIMAL para dinero
-- 10. to_tsvector/to_tsquery para búsquedas avanzadas
--
-- Diferencias clave con MySQL:
-- - AUTO_INCREMENT → SERIAL
-- - DATETIME → TIMESTAMP
-- - TINYINT(1) → BOOLEAN
-- - LONGTEXT → TEXT
-- - ENUM en tabla → CREATE TYPE ... AS ENUM
-- - JSON → JSONB (más eficiente)
-- - Triggers más flexibles y potentes
-- =====================================================
