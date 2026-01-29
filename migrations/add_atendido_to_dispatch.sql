-- ============================================
-- Migración: Agregar campos de atención a Despacho
-- Fecha: 2026-01-29
-- Descripción: Agrega is_atendido, atendido_by y atendido_at
-- ============================================

ALTER TABLE woo_dispatch_priorities
ADD COLUMN is_atendido TINYINT(1) DEFAULT 0 NOT NULL AFTER priority_level,
ADD COLUMN atendido_by VARCHAR(100) AFTER is_atendido,
ADD COLUMN atendido_at DATETIME AFTER atendido_by;

-- Verificar cambios
DESCRIBE woo_dispatch_priorities;
