"""
Script para crear las tablas del módulo de compras
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    tables = [
        '''CREATE TABLE IF NOT EXISTS woo_purchase_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_number VARCHAR(50) UNIQUE NOT NULL,
            supplier_name VARCHAR(200),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            order_date DATETIME NOT NULL,
            expected_delivery_date DATE,
            actual_delivery_date DATE,
            total_cost_usd DECIMAL(10,2),
            exchange_rate DECIMAL(6,4),
            total_cost_pen DECIMAL(10,2),
            notes TEXT,
            created_by VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_order_number (order_number),
            INDEX idx_status (status),
            INDEX idx_order_date (order_date)
        )''',

        '''CREATE TABLE IF NOT EXISTS woo_purchase_order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            purchase_order_id INT NOT NULL,
            product_id INT NOT NULL,
            product_title VARCHAR(200),
            sku VARCHAR(100),
            quantity INT NOT NULL,
            unit_cost_usd DECIMAL(10,2),
            total_cost_usd DECIMAL(10,2),
            notes TEXT,
            FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
            INDEX idx_purchase_order (purchase_order_id),
            INDEX idx_product (product_id),
            INDEX idx_sku (sku)
        )''',

        '''CREATE TABLE IF NOT EXISTS woo_purchase_order_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            purchase_order_id INT NOT NULL,
            old_status VARCHAR(20),
            new_status VARCHAR(20),
            changed_by VARCHAR(100),
            change_reason VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (purchase_order_id) REFERENCES woo_purchase_orders(id) ON DELETE CASCADE,
            INDEX idx_purchase_order (purchase_order_id),
            INDEX idx_created_at (created_at)
        )'''
    ]

    table_names = ['woo_purchase_orders', 'woo_purchase_order_items', 'woo_purchase_order_history']

    for i, table_sql in enumerate(tables):
        try:
            db.session.execute(text(table_sql))
            db.session.commit()
            print(f'[OK] Tabla {table_names[i]} creada exitosamente')
        except Exception as e:
            print(f'[ERROR] Al crear {table_names[i]}: {e}')
            db.session.rollback()

    print('\n[OK] Proceso de creacion de tablas completado')
