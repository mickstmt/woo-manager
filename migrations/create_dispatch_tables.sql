-- ============================================
-- Migración: Módulo de Despacho Kanban
-- Fecha: 2025-12-23
-- Descripción: Crear tablas para gestión de despachos
-- ============================================

-- Tabla para historial de cambios de método de envío
-- Sin foreign key constraint para evitar problemas de compatibilidad
CREATE TABLE IF NOT EXISTS woo_dispatch_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    order_number VARCHAR(50) NOT NULL,

    -- Cambio de método de envío
    previous_shipping_method VARCHAR(100),
    new_shipping_method VARCHAR(100) NOT NULL,

    -- Trazabilidad
    changed_by VARCHAR(100) NOT NULL COMMENT 'Usuario que realizó el cambio',
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Notas de despacho
    dispatch_note TEXT,

    -- Índices para optimizar consultas
    INDEX idx_order_id (order_id),
    INDEX idx_order_number (order_number),
    INDEX idx_changed_at (changed_at),
    INDEX idx_changed_by (changed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Historial de cambios de método de envío en módulo de despacho';

-- Tabla para gestión de prioridades de pedidos
-- Sin foreign key constraint para evitar problemas de compatibilidad
CREATE TABLE IF NOT EXISTS woo_dispatch_priorities (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL UNIQUE,
    order_number VARCHAR(50) NOT NULL,

    -- Configuración de prioridad
    is_priority TINYINT(1) DEFAULT 0,
    priority_level ENUM('normal', 'high', 'urgent') DEFAULT 'normal',

    -- Metadata de prioridad
    marked_by VARCHAR(100) COMMENT 'Usuario que marcó como prioritario',
    marked_at DATETIME COMMENT 'Fecha cuando se marcó',
    priority_note TEXT COMMENT 'Razón por la cual es prioritario',

    -- Índices
    INDEX idx_order_id (order_id),
    INDEX idx_order_number (order_number),
    INDEX idx_is_priority (is_priority),
    INDEX idx_priority_level (priority_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Gestión de prioridades de pedidos en módulo de despacho';

-- Verificar creación exitosa
SELECT 'Tablas creadas exitosamente' AS status,
       COUNT(*) AS total_tables
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('woo_dispatch_history', 'woo_dispatch_priorities');
