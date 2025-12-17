from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=== Análisis del pedido W-00024 (3 items) ===')
    print()

    # Obtener ID del pedido
    order_id = db.session.execute(text("""
        SELECT o.id
        FROM wpyz_wc_orders o
        INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id AND om.meta_key = '_order_number'
        WHERE om.meta_value = 'W-00024'
    """)).scalar()

    print(f'Order ID: {order_id}')
    print()

    # Items del pedido
    items = db.session.execute(text("""
        SELECT
            oi.order_item_id,
            oi.order_item_name,
            oim_qty.meta_value as cantidad,
            pm_sku.meta_value as sku,
            oim_pid.meta_value as product_id
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
            ON oi.order_item_id = oim_pid.order_item_id
            AND oim_pid.meta_key = '_product_id'
        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
            ON oi.order_item_id = oim_qty.order_item_id
            AND oim_qty.meta_key = '_qty'
        LEFT JOIN wpyz_postmeta pm_sku
            ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
            AND pm_sku.meta_key = '_sku'
        WHERE oi.order_id = :order_id
            AND oi.order_item_type = 'line_item'
    """), {'order_id': order_id}).fetchall()

    print(f'Total items: {len(items)}')
    print()

    total_costo = 0

    for i, item in enumerate(items, 1):
        print(f'{i}. Item ID: {item[0]}')
        print(f'   Nombre: {item[1]}')
        print(f'   Product ID: {item[4]} | Cantidad: {item[2]}')
        print(f'   SKU WooCommerce: {item[3] or "SIN SKU"}')

        if item[3]:
            # Buscar en FashionCloud con LIKE (método del query)
            print(f'   Buscando: "{item[3]}" LIKE CONCAT("%", fc.sku, "%") AND LENGTH = 7')

            fc_matches = db.session.execute(text("""
                SELECT fc.sku, fc.FCLastCost
                FROM woo_products_fccost fc
                WHERE :sku COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                    AND LENGTH(fc.sku) = 7
            """), {'sku': item[3]}).fetchall()

            if fc_matches:
                print(f'   [OK] Encontrados: {len(fc_matches)} matches')
                subtotal = 0
                for match in fc_matches:
                    costo_linea = float(match[1]) * int(item[2])
                    print(f'      - FC SKU: {match[0]} | Costo: ${match[1]} x {item[2]} = ${costo_linea}')
                    subtotal += costo_linea

                # El query usa SUM() entonces suma TODOS los matches
                print(f'   SUBTOTAL (suma de matches): ${subtotal}')
                total_costo += subtotal
            else:
                print(f'   [X] NO encontrado en FashionCloud')
        else:
            print(f'   [!] Sin SKU')

        print()

    print('='*70)
    print(f'COSTO TOTAL ESPERADO: ${total_costo}')
    print('='*70)
    print()

    # Ahora ejecutar el query EXACTO del reporte
    print('Ejecutando query del reporte...')
    result = db.session.execute(text("""
        SELECT
            (
                SELECT SUM(
                    (
                        SELECT SUM(fc.FCLastCost)
                        FROM woo_products_fccost fc
                        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                            AND LENGTH(fc.sku) = 7
                    ) * oim_qty.meta_value
                )
                FROM wpyz_woocommerce_order_items oi
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
                    ON oi.order_item_id = oim_pid.order_item_id
                    AND oim_pid.meta_key = '_product_id'
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
                    ON oi.order_item_id = oim_qty.order_item_id
                    AND oim_qty.meta_key = '_qty'
                INNER JOIN wpyz_postmeta pm_sku
                    ON CAST(oim_pid.meta_value AS UNSIGNED) = pm_sku.post_id
                    AND pm_sku.meta_key = '_sku'
                WHERE oi.order_id = :order_id
                    AND oi.order_item_type = 'line_item'
            ) as costo_total_usd
    """), {'order_id': order_id}).scalar()

    print(f'COSTO QUERY REPORTE: ${result or 0}')
    print()

    if result != total_costo:
        print('[!] HAY DIFERENCIA!')
        print(f'   Esperado: ${total_costo}')
        print(f'   Query devuelve: ${result or 0}')
