-- Verificar y actualizar role del usuario Jleon

-- 1. Ver estado actual
SELECT id, username, role, is_active
FROM woo_users
WHERE username = 'Jleon';

-- 2. Si el role NO es 'master', ejecutar esto:
-- UPDATE woo_users SET role = 'master' WHERE username = 'Jleon';

-- 3. Verificar actualización
SELECT id, username, role, is_active
FROM woo_users
WHERE username = 'Jleon';
