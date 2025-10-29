-- =====================================================
-- TABLA DE HISTORIAL DE PRECIOS
-- WooCommerce Manager
-- =====================================================
--
-- Esta tabla registra todos los cambios de precios
-- para auditoría y trazabilidad
--
-- Prefijo: woo_ (tablas customizadas, no WooCommerce)
-- =====================================================

USE izis_db;  -- Cambiar por el nombre de tu base de datos

-- Crear tabla de historial de precios
CREATE TABLE IF NOT EXISTS woo_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Identificación del producto
    product_id INT NOT NULL,
    product_title VARCHAR(200),
    sku VARCHAR(100),

    -- Precios anteriores
    old_regular_price DECIMAL(10,2),
    old_sale_price DECIMAL(10,2),
    old_price DECIMAL(10,2),

    -- Precios nuevos
    new_regular_price DECIMAL(10,2),
    new_sale_price DECIMAL(10,2),
    new_price DECIMAL(10,2),

    -- Auditoría
    changed_by VARCHAR(100) DEFAULT 'system',
    change_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Índices para búsqueda rápida
    INDEX idx_product_id (product_id),
    INDEX idx_created_at (created_at),
    INDEX idx_changed_by (changed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificar que se creó correctamente
SELECT
    table_name,
    engine,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'woo_price_history';

-- Ver estructura de la tabla
DESCRIBE woo_price_history;
