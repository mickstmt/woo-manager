-- Verificar el rol actual del usuario mickstmt
SELECT id, username, email, role, is_active
FROM woo_users
WHERE username = 'mickstmt';

-- Cambiar el rol a 'advisor'
UPDATE woo_users
SET role = 'advisor'
WHERE username = 'mickstmt';

-- Verificar que se cambió correctamente
SELECT id, username, email, role, is_active
FROM woo_users
WHERE username = 'mickstmt';
