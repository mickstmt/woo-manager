# create_history_table.py
from app import create_app, db
from sqlalchemy import text

app = create_app('testing')

with app.app_context():
    print("=" * 60)
    print("📝 Creando tabla de historial de cambios")
    print("=" * 60)
    
    try:
        # Crear tabla para historial de cambios de stock
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS wpyz_stock_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            product_title VARCHAR(200),
            sku VARCHAR(100),
            old_stock INT,
            new_stock INT,
            change_amount INT,
            changed_by VARCHAR(100) DEFAULT 'system',
            change_reason VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_product_id (product_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        db.session.execute(text(create_table_sql))
        db.session.commit()
        
        print("✅ Tabla wpyz_stock_history creada exitosamente")
        print("\nEstructura:")
        print("  - id: ID único del cambio")
        print("  - product_id: ID del producto modificado")
        print("  - product_title: Nombre del producto")
        print("  - sku: SKU del producto")
        print("  - old_stock: Stock anterior")
        print("  - new_stock: Stock nuevo")
        print("  - change_amount: Cantidad del cambio (+/-)")
        print("  - changed_by: Usuario que hizo el cambio")
        print("  - change_reason: Motivo del cambio")
        print("  - created_at: Fecha y hora del cambio")
        
        # Verificar que se creó
        result = db.session.execute(text("SHOW TABLES LIKE 'wpyz_stock_history'"))
        if result.fetchone():
            print("\n✅ Verificación: Tabla existe en la base de datos")
        
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al crear tabla: {e}")
        import traceback
        traceback.print_exc()