from app import create_app, db
from sqlalchemy import text
from datetime import datetime

app = create_app()
with app.app_context():
    print('=== CONSULTAR PEDIDOS POR RANGO DE FECHAS ===')
    print()

    # Solicitar fechas al usuario
    print('Ingresa las fechas en formato YYYY-MM-DD')
    start_date = input('Fecha inicio: ').strip()
    end_date = input('Fecha fin: ').strip()

    # Validar formato de fechas
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print('[ERROR] Formato de fecha invalido. Use YYYY-MM-DD')
        exit(1)

    print()
    print(f'=== BUSCANDO PEDIDOS DEL {start_date} AL {end_date} ===')
    print()

    # Query para obtener pedidos
    query = text("""
        SELECT
            o.id,
            om_numero.meta_value as numero_pedido,
            DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as fecha_pedido,
            o.status,
            o.total_amount,
            CONCAT(ba.first_name, ' ', ba.last_name) as cliente,
            om_created.meta_value as created_via
        FROM wpyz_wc_orders o
        INNER JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
            AND om_numero.meta_key = '_order_number'
        LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id
            AND ba.address_type = 'billing'
        LEFT JOIN wpyz_wc_orders_meta om_created ON o.id = om_created.order_id
            AND om_created.meta_key = '_created_via'
        WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
        ORDER BY o.date_created_gmt DESC
    """)

    orders = db.session.execute(query, {
        'start_date': start_date,
        'end_date': end_date
    }).fetchall()

    if not orders:
        print('[INFO] No se encontraron pedidos en ese rango de fechas')
        exit(0)

    print(f'Total de pedidos encontrados: {len(orders)}')
    print()
    print('-' * 120)
    print(f'{"ID":<8} {"Número":<12} {"Fecha":<12} {"Estado":<18} {"Total":<12} {"Origen":<20} {"Cliente"}')
    print('-' * 120)

    total_amount = 0
    status_count = {}
    origin_count = {}

    for order in orders:
        order_id = order[0]
        numero = order[1] or 'N/A'
        fecha = str(order[2])
        status = order[3]
        total = float(order[4] or 0)
        cliente = order[5] or 'Sin nombre'
        origin = order[6] or 'woocommerce'

        # Acumular estadísticas
        total_amount += total
        status_count[status] = status_count.get(status, 0) + 1
        origin_count[origin] = origin_count.get(origin, 0) + 1

        # Formatear estado
        status_display = status.replace('wc-', '')

        print(f'{order_id:<8} {numero:<12} {fecha:<12} {status_display:<18} S/. {total:<9.2f} {origin:<20} {cliente[:40]}')

    print('-' * 120)
    print()

    # Mostrar resumen
    print('=== RESUMEN ===')
    print()
    print(f'Total de pedidos: {len(orders)}')
    print(f'Monto total: S/. {total_amount:,.2f}')
    print()

    print('Por estado:')
    for status, count in sorted(status_count.items(), key=lambda x: x[1], reverse=True):
        status_display = status.replace('wc-', '')
        percentage = (count / len(orders)) * 100
        print(f'  {status_display:<18}: {count:>4} ({percentage:>5.1f}%)')
    print()

    print('Por origen:')
    for origin, count in sorted(origin_count.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(orders)) * 100
        print(f'  {origin:<20}: {count:>4} ({percentage:>5.1f}%)')
    print()

    # Preguntar si desea exportar
    export = input('¿Desea exportar los resultados a CSV? (s/n): ').strip().lower()
    if export == 's':
        import csv
        filename = f'pedidos_{start_date}_to_{end_date}.csv'

        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Número', 'Fecha', 'Estado', 'Total', 'Origen', 'Cliente'])

            for order in orders:
                writer.writerow([
                    order[0],
                    order[1] or 'N/A',
                    str(order[2]),
                    order[3].replace('wc-', ''),
                    float(order[4] or 0),
                    order[6] or 'woocommerce',
                    order[5] or 'Sin nombre'
                ])

        print(f'[OK] Archivo exportado: {filename}')
