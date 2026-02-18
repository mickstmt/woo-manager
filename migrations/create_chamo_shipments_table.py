# create_chamo_shipments_table.py
"""
Script de migración para crear la tabla woo_chamo_shipments

Esta tabla registra todos los envíos realizados por CHAMO courier
para control de facturación y billing.

Ejecutar: python migrations/create_chamo_shipments_table.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

# Usar development environment (local database)
app = create_app('development')

with app.app_context():
    print("=" * 60)
    print("Creating CHAMO shipments registry table")
    print("=" * 60)

    try:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS woo_chamo_shipments (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,

            -- Identificación del pedido
            order_id BIGINT UNSIGNED NOT NULL,
            order_number VARCHAR(50) NOT NULL,

            -- Detalles del envío
            tracking_number TEXT NOT NULL COMMENT 'Mensaje de tracking enviado',
            delivery_date DATE NOT NULL COMMENT 'Fecha de entrega programada',
            shipping_provider VARCHAR(100) DEFAULT 'Motorizado Izi',

            -- Información del cliente
            customer_name VARCHAR(200),
            customer_phone VARCHAR(50),
            customer_email VARCHAR(320),
            customer_address TEXT,
            customer_district VARCHAR(100),

            -- Detalles financieros (para facturación)
            order_total DECIMAL(10,2) NOT NULL COMMENT 'Total del pedido',
            shipping_cost DECIMAL(10,2) DEFAULT 0 COMMENT 'Costo de envío ya pagado',
            cod_amount DECIMAL(10,2) DEFAULT 0 COMMENT 'Monto a cobrar en entrega',
            is_cod TINYINT(1) DEFAULT 0 COMMENT 'Es contraentrega',

            -- Metadata del envío
            sent_by VARCHAR(100) NOT NULL COMMENT 'Usuario que envió tracking',
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Cuándo se envió',
            sent_via ENUM('individual', 'bulk') DEFAULT 'individual' COMMENT 'Método de envío',
            column_at_send VARCHAR(100) DEFAULT 'Motorizado (CHAMO)' COMMENT 'Columna al enviar',
            notes TEXT,

            -- Índices para queries eficientes
            INDEX idx_order_id (order_id),
            INDEX idx_order_number (order_number),
            INDEX idx_delivery_date (delivery_date),
            INDEX idx_sent_at (sent_at),
            INDEX idx_sent_by (sent_by),
            INDEX idx_is_cod (is_cod),

            -- Prevenir duplicados exactos
            UNIQUE KEY unique_order_shipment (order_id, sent_at)

        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
        COMMENT='Registry of all CHAMO courier shipments for billing and control';
        """

        db.session.execute(text(create_table_sql))
        db.session.commit()

        print("[OK] Table woo_chamo_shipments created successfully")

        # Verificar que la tabla existe
        result = db.session.execute(text("SHOW TABLES LIKE 'woo_chamo_shipments'"))
        if result.fetchone():
            print("\n[OK] Verification: Table exists in database")

            # Mostrar estructura de la tabla
            print("\nTable structure:")
            columns = db.session.execute(text("DESCRIBE woo_chamo_shipments"))
            print("\nColumns:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} {'(NULL)' if col[2] == 'YES' else '(NOT NULL)'}")

            # Mostrar índices
            indexes = db.session.execute(text("SHOW INDEXES FROM woo_chamo_shipments"))
            print("\nIndexes:")
            for idx in indexes:
                print(f"  - {idx[2]} on {idx[4]}")

        print("\n" + "=" * 60)
        print("[OK] MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Error creating table: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
