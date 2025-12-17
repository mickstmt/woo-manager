from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=== Investigando pedidos "Sin asesor" ===')
    print()

    # Buscar pedidos que NO tienen _created_by
    pedidos_sin_creator = db.session.execute(text("""
        SELECT o.id, o.date_created_gmt, o.status, o.total_amount
        FROM wpyz_wc_orders o
        LEFT JOIN wpyz_wc_orders_meta pm ON o.id = pm.order_id
            AND pm.meta_key = '_created_by'
        WHERE pm.meta_value IS NULL
            AND o.status IN ('wc-completed', 'wc-processing')
        ORDER BY o.date_created_gmt DESC
        LIMIT 10
    """)).fetchall()

    print(f'Pedidos sin _created_by: {len(pedidos_sin_creator)}')
    print()

    if pedidos_sin_creator:
        print('Ejemplos de pedidos sin _created_by:')
        for p in pedidos_sin_creator:
            print(f'  Order {p[0]} | Fecha: {p[1]} | Estado: {p[2]} | Total: S/. {p[3]}')
        print()

    # Contar total de pedidos con y sin _created_by
    totales = db.session.execute(text("""
        SELECT
            COUNT(CASE WHEN pm.meta_value IS NOT NULL THEN 1 END) as con_creator,
            COUNT(CASE WHEN pm.meta_value IS NULL THEN 1 END) as sin_creator,
            COUNT(*) as total
        FROM wpyz_wc_orders o
        LEFT JOIN wpyz_wc_orders_meta pm ON o.id = pm.order_id
            AND pm.meta_key = '_created_by'
        WHERE o.status IN ('wc-completed', 'wc-processing')
    """)).fetchone()

    print('=== Resumen ===')
    print(f'Total de pedidos: {totales[2]}')
    print(f'Con _created_by: {totales[0]} ({totales[0]/totales[2]*100:.1f}%)')
    print(f'Sin _created_by: {totales[1]} ({totales[1]/totales[2]*100:.1f}%)')
    print()

    # Ver qué valores tiene _created_by
    print('=== Valores de _created_by ===')
    valores = db.session.execute(text("""
        SELECT meta_value, COUNT(*) as cantidad
        FROM wpyz_wc_orders_meta
        WHERE meta_key = '_created_by'
        GROUP BY meta_value
        ORDER BY cantidad DESC
    """)).fetchall()

    for v in valores:
        print(f'  {v[0]}: {v[1]} pedidos')
