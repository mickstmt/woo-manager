-- Migración: Crear tabla expense_details
-- Fecha: 2025-12-10
-- Descripción: Tabla para Gastos Detallados (solo accesible para usuarios Master)

CREATE TABLE IF NOT EXISTS expense_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL COMMENT 'Fecha del gasto',
    tipo_gasto VARCHAR(100) NOT NULL COMMENT 'Tipo de gasto',
    categoria VARCHAR(100) NOT NULL COMMENT 'Categoría del gasto',
    descripcion TEXT NOT NULL COMMENT 'Descripción detallada',
    monto DECIMAL(10, 2) NOT NULL COMMENT 'Monto del gasto',

    -- Auditoría
    created_by VARCHAR(100) NOT NULL COMMENT 'Usuario que creó el registro',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    updated_by VARCHAR(100) DEFAULT NULL COMMENT 'Usuario que actualizó por última vez',
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'Fecha de última actualización',

    -- Índices
    INDEX idx_fecha (fecha),
    INDEX idx_tipo_gasto (tipo_gasto),
    INDEX idx_categoria (categoria),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Gastos detallados - Solo accesible para usuarios Master';
