-- ============================================
-- Migración: Agregar campos para reset de contraseña
-- ============================================
-- Fecha: 2025-11-15
-- Descripción: Agrega campos reset_token y reset_token_expires
--              a la tabla woo_users para funcionalidad de
--              recuperación de contraseña

-- Tabla: woo_users
ALTER TABLE woo_users
ADD COLUMN reset_token VARCHAR(100) UNIQUE NULL AFTER last_login,
ADD COLUMN reset_token_expires DATETIME NULL AFTER reset_token;

-- Verificar que las columnas se crearon
DESCRIBE woo_users;

-- ============================================
-- Notas:
-- ============================================
-- - reset_token: Token único generado para reseteo (expira en 1 hora)
-- - reset_token_expires: Timestamp de expiración del token
-- - Ambos campos son NULL por defecto
-- - reset_token tiene índice UNIQUE para evitar duplicados
