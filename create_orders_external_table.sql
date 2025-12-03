-- =============================================================================
-- SCRIPT PARA CREAR TABLA DE PEDIDOS EXTERNOS
-- =============================================================================
-- Tabla: woo_orders_ext
-- Propósito: Registrar pedidos de fuentes externas (no WooCommerce)
--            para tracking y reportes internos
--
-- IMPORTANTE: Esta tabla NO afecta directamente a WooCommerce, es solo
--             para registro interno y reportes consolidados
--
-- Prefijo: woo_ (no wpyz_) para distinguir de tablas de WooCommerce
-- =============================================================================

-- Crear tabla de pedidos externos
CREATE TABLE IF NOT EXISTS woo_orders_ext (
    id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,

    -- Numeración de pedido
    order_number VARCHAR(50) NOT NULL,

    -- Información temporal
    date_created_gmt DATETIME NOT NULL,
    date_updated_gmt DATETIME NOT NULL,

    -- Estado (siempre será 'completed' para externos)
    status VARCHAR(50) NOT NULL DEFAULT 'wc-completed',

    -- Información del cliente
    customer_first_name VARCHAR(255) NOT NULL,
    customer_last_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50) NOT NULL,
    customer_dni VARCHAR(20) NULL,
    customer_ruc VARCHAR(20) NULL,

    -- Dirección de entrega
    shipping_address_1 VARCHAR(255) NULL,
    shipping_city VARCHAR(100) NULL,
    shipping_state VARCHAR(100) NULL,
    shipping_postcode VARCHAR(20) NULL,
    shipping_country VARCHAR(2) DEFAULT 'PE',
    shipping_reference TEXT NULL,
    delivery_type VARCHAR(50) NULL COMMENT 'billing_domicilio, billing_agencia, billing_recojo',

    -- Información de envío
    shipping_method_title VARCHAR(255) NULL,
    shipping_cost DECIMAL(10,2) DEFAULT 0.00,

    -- Información de pago
    payment_method VARCHAR(100) NULL,
    payment_method_title VARCHAR(255) NULL,

    -- Totales del pedido
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax_total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_percentage DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    -- Notas y metadatos
    customer_note TEXT NULL,

    -- Usuario que creó el pedido
    created_by VARCHAR(100) NULL,

    -- Fuente del pedido externo
    external_source VARCHAR(100) NULL COMMENT 'Origen: marketplace, tienda física, etc',

    PRIMARY KEY (id),
    UNIQUE KEY order_number (order_number),
    KEY date_created_gmt (date_created_gmt),
    KEY status (status),
    KEY customer_email (customer_email),
    KEY created_by (created_by),
    KEY external_source (external_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Crear tabla de items de pedidos externos
CREATE TABLE IF NOT EXISTS woo_orders_ext_items (
    id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,

    -- Relación con pedido externo
    order_ext_id BIGINT(20) UNSIGNED NOT NULL,

    -- Información del producto
    product_id BIGINT(20) UNSIGNED NOT NULL COMMENT 'ID del producto en WooCommerce',
    variation_id BIGINT(20) UNSIGNED DEFAULT 0,
    product_name VARCHAR(255) NOT NULL,
    product_sku VARCHAR(100) NULL,

    -- Cantidades y precios
    quantity INT(11) NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    tax DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL,

    PRIMARY KEY (id),
    KEY order_ext_id (order_ext_id),
    KEY product_id (product_id),
    CONSTRAINT fk_order_ext_items FOREIGN KEY (order_ext_id)
        REFERENCES woo_orders_ext(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Crear índices adicionales para optimizar consultas
CREATE INDEX idx_date_created ON woo_orders_ext(date_created_gmt, status);
CREATE INDEX idx_customer ON woo_orders_ext(customer_first_name, customer_last_name);
CREATE INDEX idx_totals ON woo_orders_ext(total_amount, date_created_gmt);

-- Verificar que las tablas se crearon correctamente
SELECT
    'Tabla creada exitosamente' as resultado,
    COUNT(*) as registros_actuales
FROM woo_orders_ext;

SELECT
    'Tabla de items creada exitosamente' as resultado,
    COUNT(*) as registros_actuales
FROM woo_orders_ext_items;

-- =============================================================================
-- NOTAS IMPORTANTES:
-- =============================================================================
-- 1. Los pedidos externos NO se sincronizan con WooCommerce
-- 2. Los pedidos externos SÍ afectan el stock (se resta del inventario)
-- 3. El estado siempre será 'wc-completed'
-- 4. Se usa la misma lógica de conversión UTC-5 para fechas
-- 5. Los reportes pueden filtrar por canal (WhatsApp vs Externo)
-- =============================================================================
