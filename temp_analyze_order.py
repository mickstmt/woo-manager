from app import create_app, db
from sqlalchemy import text
from decimal import Decimal

app = create_app()
with app.app_context():
    print('=== ANALISIS DE PEDIDO W-00183 ===')
    print()

    # Buscar el pedido
    order = db.session.execute(text("""
        SELECT
            o.id,
            o.total_amount,
            o.tax_amount
        FROM wpyz_wc_orders o
        INNER JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
        WHERE m.meta_key = '_manager_order_number'
            AND m.meta_value = 'W-00183'
    """)).fetchone()

    if not order:
        print('[ERROR] No se encontro el pedido W-00183')
        exit(1)

    order_id = order[0]
    total_order = Decimal(str(order[1]))
    tax_amount = Decimal(str(order[2] or 0))

    # Obtener costo de envío de los items
    shipping_item = db.session.execute(text("""
        SELECT SUM(CAST(oim.meta_value AS DECIMAL(10,2)))
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
        WHERE oi.order_id = :order_id
            AND oi.order_item_type = 'shipping'
            AND oim.meta_key = 'cost'
    """), {'order_id': order_id}).fetchone()

    shipping_total = Decimal(str(shipping_item[0] or 0)) if shipping_item else Decimal('0')

    print(f'Order ID: {order_id}')
    print(f'Total del Pedido: S/. {total_order}')
    print(f'Costo de Envio: S/. {shipping_total}')
    print(f'Impuestos (IGV): S/. {tax_amount}')
    print()

    # Obtener items del pedido
    print('=== ITEMS DEL PEDIDO ===')
    print()

    items = db.session.execute(text("""
        SELECT
            oi.order_item_id,
            oi.order_item_name,
            MAX(CASE WHEN oim.meta_key = '_product_id' THEN oim.meta_value END) as product_id,
            MAX(CASE WHEN oim.meta_key = '_variation_id' THEN oim.meta_value END) as variation_id,
            MAX(CASE WHEN oim.meta_key = '_qty' THEN oim.meta_value END) as quantity,
            MAX(CASE WHEN oim.meta_key = '_line_total' THEN oim.meta_value END) as line_total,
            MAX(CASE WHEN oim.meta_key = '_line_tax' THEN oim.meta_value END) as line_tax
        FROM wpyz_woocommerce_order_items oi
        INNER JOIN wpyz_woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id
        WHERE oi.order_id = :order_id
            AND oi.order_item_type = 'line_item'
        GROUP BY oi.order_item_id, oi.order_item_name
    """), {'order_id': order_id}).fetchall()

    subtotal_products = Decimal('0')
    total_with_tax = Decimal('0')

    for item in items:
        product_id = item[2]
        variation_id = item[3]
        quantity = Decimal(str(item[4]))
        line_total = Decimal(str(item[5]))
        line_tax = Decimal(str(item[6] or 0))
        line_total_with_tax = line_total + line_tax

        # Determinar qué producto/variación buscar para el SKU
        target_id = variation_id if variation_id and variation_id != '0' else product_id

        # Obtener SKU
        sku_result = db.session.execute(text("""
            SELECT meta_value
            FROM wpyz_postmeta
            WHERE post_id = :target_id
                AND meta_key = '_sku'
        """), {'target_id': target_id}).fetchone()

        sku = sku_result[0] if sku_result else 'N/A'

        # Calcular precio unitario (sin IGV y con IGV)
        price_per_unit = line_total / quantity if quantity > 0 else Decimal('0')
        price_per_unit_with_tax = line_total_with_tax / quantity if quantity > 0 else Decimal('0')

        print(f'Producto: {item[1]}')
        print(f'  SKU: {sku}')
        print(f'  Cantidad: {quantity}')
        print(f'  Precio Unit. (sin IGV): S/. {price_per_unit:.2f}')
        print(f'  Precio Unit. (con IGV): S/. {price_per_unit_with_tax:.2f}')
        print(f'  Subtotal (sin IGV): S/. {line_total:.2f}')
        print(f'  IGV: S/. {line_tax:.2f}')
        print(f'  Total (con IGV): S/. {line_total_with_tax:.2f}')
        print()

        subtotal_products += line_total
        total_with_tax += line_total_with_tax

    print('=== RESUMEN DE TOTALES ===')
    print()
    print(f'Subtotal Productos (sin IGV): S/. {subtotal_products:.2f}')
    print(f'IGV de Productos: S/. {tax_amount:.2f}')
    print(f'Total Productos (con IGV): S/. {total_with_tax:.2f}')
    print(f'Costo de Envio: S/. {shipping_total:.2f}')
    print(f'TOTAL PEDIDO: S/. {total_order:.2f}')
    print()

    # Verificar si coincide
    calculated_total = total_with_tax + shipping_total
    print(f'Calculo: S/. {total_with_tax:.2f} (productos) + S/. {shipping_total:.2f} (envio) = S/. {calculated_total:.2f}')

    if abs(calculated_total - total_order) < Decimal('0.01'):
        print('[OK] Los totales coinciden correctamente')
    else:
        print(f'[WARNING] Diferencia: S/. {abs(calculated_total - total_order):.2f}')
    print()

    # Ahora verificar cómo se calculan las ganancias en el reporte
    print('=== COMO SE CALCULA EN EL REPORTE DE GANANCIAS ===')
    print()
    print('Verificando que incluye el envio en las ventas...')

    # El reporte usa o.total_amount que incluye PRODUCTOS + ENVIO
    print(f'o.total_amount = S/. {total_order:.2f}')
    print(f'Esto INCLUYE productos (S/. {total_with_tax:.2f}) + envio (S/. {shipping_total:.2f})')
    print()
    print('[IMPORTANTE] El reporte de ganancias SI incluye el costo de envio')
    print('             en las ventas totales, pero NO resta el costo de envio')
    print('             de las ganancias (asume que el envio no tiene costo).')
