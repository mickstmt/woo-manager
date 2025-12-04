-- =============================================================================
-- CREAR TABLA DE TIPO DE CAMBIO USD/PEN
-- =============================================================================
-- Propósito: Almacenar histórico de tipo de cambio para calcular costos y ganancias
-- =============================================================================

CREATE TABLE IF NOT EXISTS woo_tipo_cambio (
    id INT PRIMARY KEY AUTO_INCREMENT,
    fecha DATE NOT NULL,
    tasa_compra DECIMAL(6,4) NOT NULL COMMENT 'Tasa de compra USD -> PEN',
    tasa_venta DECIMAL(6,4) NOT NULL COMMENT 'Tasa de venta PEN -> USD',
    tasa_promedio DECIMAL(6,4) NOT NULL COMMENT 'Promedio (compra + venta) / 2',
    actualizado_por VARCHAR(100) NOT NULL COMMENT 'Usuario que actualizó',
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE COMMENT 'Solo un registro activo por fecha',
    notas TEXT COMMENT 'Notas adicionales',

    UNIQUE KEY idx_fecha_activo (fecha, activo),
    INDEX idx_fecha (fecha),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
COMMENT='Histórico de tipo de cambio USD/PEN para cálculo de ganancias';

-- Insertar tipo de cambio inicial (ajustar según tipo actual)
INSERT INTO woo_tipo_cambio (fecha, tasa_compra, tasa_venta, tasa_promedio, actualizado_por, activo, notas)
VALUES
    (CURDATE(), 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio inicial - ajustar según mercado')
ON DUPLICATE KEY UPDATE
    tasa_compra = VALUES(tasa_compra),
    tasa_venta = VALUES(tasa_venta),
    tasa_promedio = VALUES(tasa_promedio);

-- =============================================================================
-- EJEMPLOS DE USO
-- =============================================================================

-- Ver tipo de cambio actual
SELECT * FROM woo_tipo_cambio WHERE activo = TRUE ORDER BY fecha DESC LIMIT 1;

-- Ver histórico
SELECT
    fecha,
    tasa_compra,
    tasa_venta,
    tasa_promedio,
    actualizado_por,
    DATE_FORMAT(fecha_actualizacion, '%d/%m/%Y %H:%i') as actualizado
FROM woo_tipo_cambio
ORDER BY fecha DESC
LIMIT 30;

-- =============================================================================
-- NOTAS
-- =============================================================================
-- 1. Actualizar diariamente o cuando haya cambios significativos
-- 2. tasa_promedio se usa para cálculos de costo (USD -> PEN)
-- 3. Mantener histórico permite recalcular ganancias de pedidos pasados
-- 4. Solo debe haber un registro activo por fecha
-- =============================================================================
