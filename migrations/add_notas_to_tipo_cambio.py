"""
Migración: Agregar columna 'notas' a woo_tipo_cambio

Ejecutar: python migrations/add_notas_to_tipo_cambio.py
"""

from app import create_app, db
from sqlalchemy import text

def add_notas_column():
    app = create_app()

    with app.app_context():
        try:
            # Verificar si la columna ya existe
            check_column = text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'woo_tipo_cambio'
                AND COLUMN_NAME = 'notas'
            """)

            result = db.session.execute(check_column).fetchone()

            if result[0] > 0:
                print("✓ La columna 'notas' ya existe en woo_tipo_cambio")
                return

            # Agregar la columna
            print("Agregando columna 'notas' a woo_tipo_cambio...")
            alter_table = text("""
                ALTER TABLE woo_tipo_cambio
                ADD COLUMN notas TEXT NULL
                COMMENT 'Observaciones o notas sobre el tipo de cambio'
            """)

            db.session.execute(alter_table)
            db.session.commit()

            print("✓ Columna 'notas' agregada exitosamente")

            # Verificar
            verify = text("""
                DESCRIBE woo_tipo_cambio
            """)

            columns = db.session.execute(verify).fetchall()
            print("\nColumnas de woo_tipo_cambio:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Error al agregar columna: {str(e)}")
            raise

if __name__ == '__main__':
    add_notas_column()
