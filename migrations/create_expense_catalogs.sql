-- ============================================================
-- CREAR TABLAS DE CATÁLOGOS PARA GASTOS DETALLADOS
-- ============================================================

-- 1. Tabla de Tipos de Gasto
CREATE TABLE IF NOT EXISTS expense_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    activo TINYINT(1) DEFAULT 1,
    orden INT DEFAULT 0,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_activo (activo),
    INDEX idx_orden (orden)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tabla de Categorías (vinculadas a Tipos de Gasto)
CREATE TABLE IF NOT EXISTS expense_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_type_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo TINYINT(1) DEFAULT 1,
    orden INT DEFAULT 0,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (expense_type_id) REFERENCES expense_types(id) ON DELETE CASCADE,
    UNIQUE KEY unique_type_nombre (expense_type_id, nombre),
    INDEX idx_type (expense_type_id),
    INDEX idx_activo (activo),
    INDEX idx_orden (orden)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabla de Descripciones Predefinidas (opcional, para sugerencias)
CREATE TABLE IF NOT EXISTS expense_descriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_category_id INT,
    descripcion TEXT NOT NULL,
    activo TINYINT(1) DEFAULT 1,
    uso_count INT DEFAULT 0,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (expense_category_id) REFERENCES expense_categories(id) ON DELETE SET NULL,
    INDEX idx_category (expense_category_id),
    INDEX idx_activo (activo),
    INDEX idx_uso (uso_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- DATOS INICIALES DE EJEMPLO
-- ============================================================

-- Tipos de Gasto iniciales
INSERT INTO expense_types (nombre, descripcion, orden, created_by) VALUES
('Operativo', 'Gastos operativos del negocio', 1, 'system'),
('Marketing', 'Gastos de marketing y publicidad', 2, 'system'),
('Administrativo', 'Gastos administrativos', 3, 'system'),
('Logística', 'Gastos de envíos y logística', 4, 'system'),
('Otros', 'Otros gastos no categorizados', 99, 'system');

-- Categorías para "Operativo"
INSERT INTO expense_categories (expense_type_id, nombre, orden, created_by)
SELECT id, 'Servicios', 1, 'system' FROM expense_types WHERE nombre = 'Operativo'
UNION ALL
SELECT id, 'Suministros', 2, 'system' FROM expense_types WHERE nombre = 'Operativo'
UNION ALL
SELECT id, 'Mantenimiento', 3, 'system' FROM expense_types WHERE nombre = 'Operativo'
UNION ALL
SELECT id, 'Otros', 99, 'system' FROM expense_types WHERE nombre = 'Operativo';

-- Categorías para "Marketing"
INSERT INTO expense_categories (expense_type_id, nombre, orden, created_by)
SELECT id, 'Publicidad Digital', 1, 'system' FROM expense_types WHERE nombre = 'Marketing'
UNION ALL
SELECT id, 'Redes Sociales', 2, 'system' FROM expense_types WHERE nombre = 'Marketing'
UNION ALL
SELECT id, 'Material Promocional', 3, 'system' FROM expense_types WHERE nombre = 'Marketing'
UNION ALL
SELECT id, 'Otros', 99, 'system' FROM expense_types WHERE nombre = 'Marketing';

-- Categorías para "Administrativo"
INSERT INTO expense_categories (expense_type_id, nombre, orden, created_by)
SELECT id, 'Papelería', 1, 'system' FROM expense_types WHERE nombre = 'Administrativo'
UNION ALL
SELECT id, 'Software', 2, 'system' FROM expense_types WHERE nombre = 'Administrativo'
UNION ALL
SELECT id, 'Servicios Profesionales', 3, 'system' FROM expense_types WHERE nombre = 'Administrativo'
UNION ALL
SELECT id, 'Otros', 99, 'system' FROM expense_types WHERE nombre = 'Administrativo';

-- Categorías para "Logística"
INSERT INTO expense_categories (expense_type_id, nombre, orden, created_by)
SELECT id, 'Envíos Nacionales', 1, 'system' FROM expense_types WHERE nombre = 'Logística'
UNION ALL
SELECT id, 'Envíos Internacionales', 2, 'system' FROM expense_types WHERE nombre = 'Logística'
UNION ALL
SELECT id, 'Embalaje', 3, 'system' FROM expense_types WHERE nombre = 'Logística'
UNION ALL
SELECT id, 'Otros', 99, 'system' FROM expense_types WHERE nombre = 'Logística';

-- Categorías para "Otros"
INSERT INTO expense_categories (expense_type_id, nombre, orden, created_by)
SELECT id, 'Otros', 1, 'system' FROM expense_types WHERE nombre = 'Otros';

-- Verificar creación
SELECT 'Tipos creados:' as info, COUNT(*) as total FROM expense_types;
SELECT 'Categorías creadas:' as info, COUNT(*) as total FROM expense_categories;
