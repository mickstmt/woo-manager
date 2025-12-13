-- =====================================================
-- Poblar tipo de cambio mensual para 2025
-- =====================================================
-- Insertar un tipo de cambio para el primer día de cada mes de 2025
-- Valores aproximados - ajustar según datos reales
-- =====================================================

INSERT INTO woo_tipo_cambio (fecha, tasa_compra, tasa_venta, tasa_promedio, actualizado_por, activo, notas, fecha_actualizacion)
VALUES
    ('2025-01-01', 3.73, 3.76, 3.745, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-02-01', 3.74, 3.77, 3.755, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-03-01', 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-04-01', 3.74, 3.77, 3.755, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-05-01', 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-06-01', 3.76, 3.79, 3.775, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-07-01', 3.76, 3.79, 3.775, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-08-01', 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-09-01', 3.76, 3.79, 3.775, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-10-01', 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-11-01', 3.75, 3.78, 3.765, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW()),
    ('2025-12-01', 3.76, 3.79, 3.775, 'admin', TRUE, 'Tipo de cambio mensual - valor aproximado', NOW())
ON DUPLICATE KEY UPDATE
    tasa_compra = VALUES(tasa_compra),
    tasa_venta = VALUES(tasa_venta),
    tasa_promedio = VALUES(tasa_promedio),
    fecha_actualizacion = NOW();

-- Verificar registros insertados
SELECT
    fecha,
    tasa_compra,
    tasa_venta,
    tasa_promedio,
    actualizado_por
FROM woo_tipo_cambio
WHERE YEAR(fecha) = 2025
ORDER BY fecha;
