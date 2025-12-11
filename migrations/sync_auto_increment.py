"""
Script para sincronizar el AUTO_INCREMENT de wpyz_wc_orders con wpyz_posts

Este script resuelve el problema de colisiones de ID cuando se crean pedidos
y el AUTO_INCREMENT de wpyz_wc_orders genera IDs que ya existen en wpyz_posts
(por ejemplo, cuando se suben archivos adjuntos en WordPress).

Uso:
    python migrations/sync_auto_increment.py
"""

from app import create_app
from app.models import db
from sqlalchemy import text

def sync_auto_increment():
    """
    Sincroniza el AUTO_INCREMENT de wpyz_wc_orders para que sea mayor
    que el MAX ID de wpyz_posts, evitando colisiones de ID.
    """
    app = create_app()
    with app.app_context():
        # Obtener el MAX ID de wpyz_posts
        max_posts = db.session.execute(
            text('SELECT MAX(ID) FROM wpyz_posts')
        ).scalar() or 0

        # Obtener el MAX ID de wpyz_wc_orders
        max_orders = db.session.execute(
            text('SELECT MAX(id) FROM wpyz_wc_orders')
        ).scalar() or 0

        # Obtener el AUTO_INCREMENT actual
        current_auto = db.session.execute(
            text("""
                SELECT AUTO_INCREMENT
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'wpyz_wc_orders'
            """)
        ).scalar() or 0

        # Calcular el nuevo AUTO_INCREMENT (debe ser mayor que ambos MAX)
        new_auto_inc = max(max_posts, max_orders) + 1

        print(f"Estado actual:")
        print(f"  MAX ID en wpyz_posts: {max_posts}")
        print(f"  MAX ID en wpyz_wc_orders: {max_orders}")
        print(f"  AUTO_INCREMENT actual: {current_auto}")
        print(f"  Nuevo AUTO_INCREMENT: {new_auto_inc}")

        if new_auto_inc > current_auto:
            print(f"\nAjustando AUTO_INCREMENT a {new_auto_inc}...")
            db.session.execute(
                text(f'ALTER TABLE wpyz_wc_orders AUTO_INCREMENT = {new_auto_inc}')
            )
            db.session.commit()
            print("✓ AUTO_INCREMENT sincronizado correctamente")
        else:
            print("\n✓ AUTO_INCREMENT ya está sincronizado, no se requieren cambios")

if __name__ == '__main__':
    sync_auto_increment()
