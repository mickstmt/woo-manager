from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=== Analizando _created_by ===')
    print()

    # Buscar ejemplos de _created_by
    samples = db.session.execute(text("""
        SELECT order_id, meta_value
        FROM wpyz_wc_orders_meta
        WHERE meta_key = '_created_by'
        LIMIT 20
    """)).fetchall()

    print(f'Ejemplos de _created_by: {len(samples)} encontrados')
    for s in samples:
        print(f'  Order {s[0]}: {s[1]}')
    print()

    # Verificar si coincide con woo_users.id
    if samples:
        user_id = samples[0][1]
        print(f'=== Verificando user_id {user_id} ===')
        user = db.session.execute(text("""
            SELECT id, username, full_name, role
            FROM woo_users
            WHERE id = :id
        """), {'id': user_id}).fetchone()

        if user:
            print(f'  ID: {user[0]}')
            print(f'  Username: {user[1]}')
            print(f'  Nombre: {user[2]}')
            print(f'  Rol: {user[3]}')
        else:
            print('  No encontrado en woo_users')
