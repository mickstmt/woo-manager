from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=== BUSCANDO PEDIDO RECIENTE ===')
    print()

    # Buscar pedido más reciente
    order = db.session.execute(text("""
        SELECT
            o.id,
            o.date_created_gmt,
            o.status,
            o.total_amount,
            o.customer_note
        FROM wpyz_wc_orders o
        INNER JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
        WHERE m.meta_key = '_created_via'
            AND m.meta_value = 'woocommerce-manager'
        ORDER BY o.date_created_gmt DESC
        LIMIT 1
    """)).fetchone()

    if not order:
        print('[ERROR] No se encontro ningun pedido')
        exit(1)

    order_id = order[0]
    print(f'Order ID: {order_id}')
    print(f'Fecha: {order[1]}')
    print(f'Estado: {order[2]}')
    print(f'Total: S/. {order[3]}')
    print(f'Customer Note: {order[4] or "(vacio)"}')
    print()

    # Verificar metadata
    print('=== METADATA DEL PEDIDO ===')
    metas = db.session.execute(text("""
        SELECT meta_key, meta_value
        FROM wpyz_wc_orders_meta
        WHERE order_id = :order_id
            AND (meta_key LIKE '%note%' OR meta_key LIKE '%email%' OR meta_key = '_created_via')
        ORDER BY meta_key
    """), {'order_id': order_id}).fetchall()

    for meta in metas:
        value = meta[1][:50] if len(str(meta[1])) > 50 else meta[1]
        print(f'  {meta[0]}: {value}')
    print()

    # Verificar post_excerpt en wpyz_posts
    print('=== VERIFICAR wpyz_posts ===')
    post = db.session.execute(text("""
        SELECT post_excerpt
        FROM wpyz_posts
        WHERE ID = :order_id
    """), {'order_id': order_id}).fetchone()

    if post:
        print(f'  post_excerpt: {post[0] or "(vacio)"}')
    else:
        print('  [ERROR] No se encontro el post')
    print()

    # Verificar postmeta
    print('=== VERIFICAR wpyz_postmeta ===')
    postmetas = db.session.execute(text("""
        SELECT meta_key, meta_value
        FROM wpyz_postmeta
        WHERE post_id = :order_id
            AND meta_key LIKE '%note%'
    """), {'order_id': order_id}).fetchall()

    if postmetas:
        for pm in postmetas:
            print(f'  {pm[0]}: {pm[1] or "(vacio)"}')
    else:
        print('  (no hay metadata de notas)')
