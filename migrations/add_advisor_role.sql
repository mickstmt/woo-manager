-- Migración: Agregar rol 'advisor' al ENUM de la tabla woo_users
-- Fecha: 2025-01-17
-- Descripción: Añade el rol 'advisor' (asesor) que puede actualizar stock y precios masivamente

-- Modificar la columna role para incluir 'advisor'
ALTER TABLE woo_users
MODIFY COLUMN role ENUM('admin', 'advisor', 'user') DEFAULT 'user';

-- Verificar cambios
SELECT DISTINCT role FROM woo_users;
