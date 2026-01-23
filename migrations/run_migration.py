#!/usr/bin/env python
"""
Script para ejecutar la migración de cotizaciones
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def run_migration():
    """Ejecutar el script SQL de migración"""
    app = create_app()

    # Leer el archivo SQL
    sql_file = os.path.join(os.path.dirname(__file__), 'create_quotations_tables.sql')

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Limpiar comentarios
    import re
    # Remover comentarios de bloque /* */
    sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    # Remover comentarios de línea --
    sql_content = re.sub(r'--.*?\n', '\n', sql_content)

    # Dividir en statements individuales (separados por ;)
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

    with app.app_context():
        try:
            for statement in statements:
                if statement:
                    print(f"Ejecutando: {statement[:80]}...")
                    db.session.execute(text(statement))

            db.session.commit()
            print("\nMigracion completada exitosamente")
            print("Tablas creadas:")
            print("   - woo_quotations")
            print("   - woo_quotation_items")
            print("   - woo_quotation_history")

        except Exception as e:
            db.session.rollback()
            print(f"\nError durante la migracion: {e}")
            sys.exit(1)

if __name__ == '__main__':
    run_migration()
