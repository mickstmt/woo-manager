"""
Migración: Poblar tipo de cambio mensual para 2025

Este script agrega un tipo de cambio (primer día de cada mes) para el año 2025.
Los valores son promedios aproximados basados en tasas históricas USD/PEN.

Ejecutar: python migrations/populate_tipo_cambio_2025.py
"""

from app import create_app, db
from app.models import TipoCambio
from datetime import date
from decimal import Decimal

def populate_exchange_rates():
    app = create_app()

    with app.app_context():
        # Tipo de cambio promedio por mes (primer día de cada mes)
        # Valores aproximados para 2025 - ajustar según datos reales
        exchange_rates = [
            # (fecha, tasa_compra, tasa_venta)
            (date(2025, 1, 1), Decimal('3.73'), Decimal('3.76')),   # Enero
            (date(2025, 2, 1), Decimal('3.74'), Decimal('3.77')),   # Febrero
            (date(2025, 3, 1), Decimal('3.75'), Decimal('3.78')),   # Marzo
            (date(2025, 4, 1), Decimal('3.74'), Decimal('3.77')),   # Abril
            (date(2025, 5, 1), Decimal('3.75'), Decimal('3.78')),   # Mayo
            (date(2025, 6, 1), Decimal('3.76'), Decimal('3.79')),   # Junio
            (date(2025, 7, 1), Decimal('3.76'), Decimal('3.79')),   # Julio
            (date(2025, 8, 1), Decimal('3.75'), Decimal('3.78')),   # Agosto
            (date(2025, 9, 1), Decimal('3.76'), Decimal('3.79')),   # Septiembre
            (date(2025, 10, 1), Decimal('3.75'), Decimal('3.78')),  # Octubre
            (date(2025, 11, 1), Decimal('3.75'), Decimal('3.78')),  # Noviembre
            (date(2025, 12, 1), Decimal('3.76'), Decimal('3.79')),  # Diciembre
        ]

        print("=" * 60)
        print("Poblando tipos de cambio para 2025")
        print("=" * 60)
        print()

        inserted = 0
        updated = 0
        skipped = 0

        for fecha, tasa_compra, tasa_venta in exchange_rates:
            tasa_promedio = (tasa_compra + tasa_venta) / 2

            # Verificar si ya existe
            existing = TipoCambio.query.filter_by(fecha=fecha, activo=True).first()

            if existing:
                # Actualizar si los valores son diferentes
                if (existing.tasa_compra != tasa_compra or
                    existing.tasa_venta != tasa_venta):
                    existing.tasa_compra = tasa_compra
                    existing.tasa_venta = tasa_venta
                    existing.tasa_promedio = tasa_promedio
                    existing.actualizado_por = 'system_migration'

                    print(f"[OK] Actualizado: {fecha} - Compra: {tasa_compra}, Venta: {tasa_venta}, Promedio: {tasa_promedio}")
                    updated += 1
                else:
                    print(f"- Ya existe:   {fecha} - Compra: {tasa_compra}, Venta: {tasa_venta}, Promedio: {tasa_promedio}")
                    skipped += 1
            else:
                # Crear nuevo registro
                tipo_cambio = TipoCambio(
                    fecha=fecha,
                    tasa_compra=tasa_compra,
                    tasa_venta=tasa_venta,
                    tasa_promedio=tasa_promedio,
                    actualizado_por='system_migration',
                    activo=True,
                    notas='Tipo de cambio mensual - valores aproximados'
                )
                db.session.add(tipo_cambio)

                print(f"+ Insertado:   {fecha} - Compra: {tasa_compra}, Venta: {tasa_venta}, Promedio: {tasa_promedio}")
                inserted += 1

        # Commit de todos los cambios
        try:
            db.session.commit()
            print()
            print("=" * 60)
            print("MIGRACION COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            print(f"  Registros insertados: {inserted}")
            print(f"  Registros actualizados: {updated}")
            print(f"  Registros omitidos: {skipped}")
            print(f"  Total procesado: {len(exchange_rates)}")
            print()

            # Mostrar resumen de la tabla
            print("Resumen de tipos de cambio en la base de datos:")
            total = TipoCambio.query.filter_by(activo=True).count()
            print(f"  Total de registros activos: {total}")

            # Mostrar rango de fechas
            from sqlalchemy import func
            min_fecha = db.session.query(func.min(TipoCambio.fecha)).filter_by(activo=True).scalar()
            max_fecha = db.session.query(func.max(TipoCambio.fecha)).filter_by(activo=True).scalar()
            print(f"  Rango de fechas: {min_fecha} a {max_fecha}")
            print()

        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print("ERROR AL GUARDAR CAMBIOS")
            print("=" * 60)
            print(f"  {str(e)}")
            print()
            raise

if __name__ == '__main__':
    populate_exchange_rates()
