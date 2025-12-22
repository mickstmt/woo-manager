-- =====================================================
-- Script de migración: Módulo de Compras/Reabastecimiento
-- Fecha: 2024-12-20
-- Descripción: Crea las tablas necesarias para gestionar
--              órdenes de compra y reabastecimiento de inventario
-- =====================================================

-- Tabla principal: Órdenes de Compra
CREATE TABLE IF NOT EXISTS woo_purchase_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL COMMENT 'Número de orden formato PO-YYYY-NNN',
    supplier_name VARCHAR(200) COMMENT 'Nombre del proveedor',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'Estado: pending, ordered, in_transit, received, cancelled',
    order_date DATETIME NOT NULL COMMENT 'Fecha de creación de la orden',
    expected_delivery_date DATE COMMENT 'Fecha estimada de entrega',
    actual_delivery_date DATE COMMENT 'Fecha real de entrega (cuando se marca como received)',
    total_cost_usd DECIMAL(10,2) COMMENT 'Costo total en USD',
    exchange_rate DECIMAL(6,4) COMMENT 'Tipo de cambio al momento de crear la orden',
    total_cost_pen DECIMAL(10,2) COMMENT 'Costo total en PEN (total_cost_usd * exchange_rate)',
    notes TEXT COMMENT 'Observaciones generales de la orden',
    created_by VARCHAR(100) COMMENT 'Usuario que creó la orden',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_order_number (order_number),
    INDEX idx_status (status),
    INDEX idx_order_date (order_date),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Órdenes de compra para reabastecimiento de inventario';

-- Tabla de items: Productos en cada orden
CREATE TABLE IF NOT EXISTS woo_purchase_order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL COMMENT 'FK a woo_purchase_orders',
    product_id INT NOT NULL COMMENT 'ID del producto en wpyz_posts',
    product_title VARCHAR(200) COMMENT 'Nombre del producto (snapshot al momento de la orden)',
    sku VARCHAR(100) COMMENT 'SKU del producto',
    quantity INT NOT NULL COMMENT 'Cantidad ordenada',
    unit_cost_usd DECIMAL(10,2) COMMENT 'Costo unitario en USD',
    total_cost_usd DECIMAL(10,2) COMMENT 'Costo total de la línea (quantity * unit_cost_usd)',
    notes TEXT COMMENT 'Notas específicas del producto',

    FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
    INDEX idx_purchase_order (purchase_order_id),
    INDEX idx_product (product_id),
    INDEX idx_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Items/productos de cada orden de compra';

-- Tabla de historial: Auditoría de cambios de estado
CREATE TABLE IF NOT EXISTS woo_purchase_order_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_order_id INT NOT NULL COMMENT 'FK a woo_purchase_orders',
    old_status VARCHAR(20) COMMENT 'Estado anterior',
    new_status VARCHAR(20) COMMENT 'Estado nuevo',
    changed_by VARCHAR(100) COMMENT 'Usuario que realizó el cambio',
    change_reason VARCHAR(255) COMMENT 'Razón del cambio',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
    INDEX idx_purchase_order (purchase_order_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Historial de cambios de estado de órdenes de compra';

-- Verificación de creación de tablas
SELECT
    'woo_purchase_orders' as tabla,
    COUNT(*) as registros
FROM woo_purchase_orders
UNION ALL
SELECT
    'woo_purchase_order_items' as tabla,
    COUNT(*) as registros
FROM woo_purchase_order_items
UNION ALL
SELECT
    'woo_purchase_order_history' as tabla,
    COUNT(*) as registros
FROM woo_purchase_order_history;
