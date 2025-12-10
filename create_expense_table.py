#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para crear la tabla expense_details
Ejecutar: python create_expense_table.py
"""

from app import create_app, db
from app.models import ExpenseDetail

def create_expense_table():
    """Crear tabla expense_details"""
    app = create_app()

    with app.app_context():
        print("Creando tabla expense_details...")

        try:
            # Crear tabla
            db.create_all()

            print("✓ Tabla expense_details creada correctamente")

            # Verificar que la tabla existe
            inspector = db.inspect(db.engine)
            if 'expense_details' in inspector.get_table_names():
                print("✓ Tabla verificada exitosamente")

                # Mostrar columnas
                columns = inspector.get_columns('expense_details')
                print("\nColumnas de la tabla:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("✗ Error: La tabla no se creó correctamente")

        except Exception as e:
            print(f"✗ Error al crear la tabla: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_expense_table()
