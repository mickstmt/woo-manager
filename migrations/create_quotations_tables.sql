-- =====================================================
-- Script de Migración: Módulo de Cotizaciones
-- Fecha: 23 de Enero 2026
-- Descripción: Crea las tablas necesarias para el módulo de cotizaciones
-- =====================================================

-- Tabla principal de cotizaciones
CREATE TABLE IF NOT EXISTS woo_quotations (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    quote_number VARCHAR(50) UNIQUE NOT NULL COMMENT 'Número de cotización (formato: COT-2025-001)',
    version INT DEFAULT 1 COMMENT 'Versión de la cotización',

    -- Información del Cliente
    customer_name VARCHAR(200) NOT NULL COMMENT 'Nombre completo del cliente',
    customer_email VARCHAR(255) NOT NULL COMMENT 'Email del cliente',
    customer_phone VARCHAR(50) COMMENT 'Teléfono del cliente',
    customer_dni VARCHAR(20) COMMENT 'DNI o CE del cliente',
    customer_ruc VARCHAR(20) COMMENT 'RUC del cliente (opcional)',
    customer_address TEXT COMMENT 'Dirección completa',
    customer_city VARCHAR(100) COMMENT 'Ciudad/Distrito',
    customer_state VARCHAR(100) COMMENT 'Departamento/Provincia',

    -- Estado y Fechas
    status VARCHAR(20) NOT NULL DEFAULT 'draft' COMMENT 'Estado: draft, sent, accepted, rejected, expired, converted',
    quote_date DATETIME NOT NULL COMMENT 'Fecha de creación de la cotización',
    valid_until DATE NOT NULL COMMENT 'Fecha de vencimiento',

    -- Precios
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Subtotal de productos',
    discount_type VARCHAR(20) DEFAULT 'percentage' COMMENT 'Tipo de descuento: percentage o fixed',
    discount_value DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Valor del descuento',
    discount_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monto calculado del descuento',
    tax_rate DECIMAL(5,2) DEFAULT 18.00 COMMENT 'Tasa de IGV (%)',
    tax_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monto de IGV',
    shipping_cost DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Costo de envío',
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Total final',

    -- Términos
    payment_terms TEXT COMMENT 'Condiciones de pago',
    delivery_time VARCHAR(100) COMMENT 'Tiempo de entrega',
    notes TEXT COMMENT 'Notas internas',
    terms_conditions TEXT COMMENT 'Términos y condiciones para el PDF',

    -- Auditoría
    created_by VARCHAR(100) NOT NULL COMMENT 'Usuario que creó la cotización',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Última actualización',
    sent_at DATETIME COMMENT 'Fecha en que se envió al cliente',
    accepted_at DATETIME COMMENT 'Fecha de aceptación',
    converted_order_id BIGINT COMMENT 'ID del pedido WooCommerce si fue convertida',

    -- Índices
    INDEX idx_quote_number (quote_number),
    INDEX idx_status (status),
    INDEX idx_customer_email (customer_email),
    INDEX idx_created_at (created_at),
    INDEX idx_valid_until (valid_until),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Tabla principal de cotizaciones';

-- Tabla de items de cotización
CREATE TABLE IF NOT EXISTS woo_quotation_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quotation_id INT NOT NULL COMMENT 'FK a woo_quotations',

    -- Referencia al Producto
    product_id BIGINT NOT NULL COMMENT 'ID del producto en WooCommerce',
    variation_id BIGINT DEFAULT 0 COMMENT 'ID de variación (0 si es producto simple)',
    product_name VARCHAR(255) NOT NULL COMMENT 'Nombre del producto',
    product_sku VARCHAR(100) COMMENT 'SKU del producto',

    -- Precios (personalizables)
    quantity INT NOT NULL DEFAULT 1 COMMENT 'Cantidad',
    unit_price DECIMAL(10,2) NOT NULL COMMENT 'Precio unitario (puede ser personalizado)',
    original_price DECIMAL(10,2) COMMENT 'Precio original del catálogo',
    discount_percentage DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Descuento por línea (%)',
    subtotal DECIMAL(10,2) NOT NULL COMMENT 'Subtotal de la línea',
    tax DECIMAL(10,2) DEFAULT 0.00 COMMENT 'IGV de la línea',
    total DECIMAL(10,2) NOT NULL COMMENT 'Total de la línea',

    -- Metadata
    notes TEXT COMMENT 'Notas específicas del producto en esta cotización',
    display_order INT DEFAULT 0 COMMENT 'Orden de visualización',

    -- Relaciones
    FOREIGN KEY (quotation_id) REFERENCES woo_quotations(id) ON DELETE CASCADE,

    -- Índices
    INDEX idx_quotation_id (quotation_id),
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Items/productos de cada cotización';

-- Tabla de historial de cambios
CREATE TABLE IF NOT EXISTS woo_quotation_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quotation_id INT NOT NULL COMMENT 'FK a woo_quotations',

    -- Rastreo de Cambios
    old_status VARCHAR(20) COMMENT 'Estado anterior',
    new_status VARCHAR(20) NOT NULL COMMENT 'Nuevo estado',
    changed_by VARCHAR(100) NOT NULL COMMENT 'Usuario que hizo el cambio',
    change_reason VARCHAR(255) COMMENT 'Razón del cambio (opcional)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha del cambio',

    -- Relaciones
    FOREIGN KEY (quotation_id) REFERENCES woo_quotations(id) ON DELETE CASCADE,

    -- Índices
    INDEX idx_quotation_id (quotation_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Historial de cambios de estado en cotizaciones';

-- =====================================================
-- Datos de ejemplo (opcional, comentar si no se necesita)
-- =====================================================

-- NOTA: Descomentar si deseas crear una cotización de prueba
/*
INSERT INTO woo_quotations (
    quote_number, customer_name, customer_email, customer_phone,
    status, quote_date, valid_until, subtotal, tax_amount, total,
    created_by
) VALUES (
    'COT-2026-001',
    'Cliente de Prueba',
    'cliente@example.com',
    '987654321',
    'draft',
    NOW(),
    DATE_ADD(CURDATE(), INTERVAL 15 DAY),
    100.00,
    18.00,
    118.00,
    'admin'
);
*/
