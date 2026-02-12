-- Migración: Agregar campo is_cod a pedidos externos
-- Fecha: 2026-02-12
-- Descripción: Agregar soporte para pago contraentrega (COD) en pedidos externos

-- Agregar columna is_cod a woo_orders_ext
ALTER TABLE woo_orders_ext
ADD COLUMN is_cod BOOLEAN DEFAULT FALSE NOT NULL;

-- Crear índice para consultas rápidas
CREATE INDEX idx_woo_orders_ext_is_cod ON woo_orders_ext(is_cod);

-- Comentario en la columna
ALTER TABLE woo_orders_ext
MODIFY COLUMN is_cod BOOLEAN DEFAULT FALSE NOT NULL
COMMENT 'Indica si el pedido es pago contraentrega (Cash On Delivery)';
