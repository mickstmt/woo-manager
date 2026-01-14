-- =====================================================
-- ASIGNAR ROLE MASTER AL USUARIO DDUIREM
-- =====================================================
-- Este script asigna el role 'master' al usuario DDUIREM
-- =====================================================

-- Ver estado actual del usuario
SELECT 
    id,
    username,
    full_name,
    role,
    is_active
FROM users
WHERE username = 'DDUIREM';

-- Actualizar role a 'master'
UPDATE users
SET role = 'master'
WHERE username = 'DDUIREM';

-- Verificar el cambio
SELECT 
    id,
    username,
    full_name,
    role,
    is_active,
    'Role actualizado a master' AS status
FROM users
WHERE username = 'DDUIREM';
