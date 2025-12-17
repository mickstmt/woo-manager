from app import create_app, db
from sqlalchemy import text
import requests
from requests.auth import HTTPBasicAuth

app = create_app()
with app.app_context():
    print('=== DIAGNÓSTICO DE ENVÍO DE CORREOS ===')
    print()

    # 1. Verificar configuración de WooCommerce API
    print('1. CONFIGURACIÓN DE WOOCOMMERCE API')
    print('-' * 50)
    wc_url = app.config.get('WC_API_URL')
    consumer_key = app.config.get('WC_CONSUMER_KEY')
    consumer_secret = app.config.get('WC_CONSUMER_SECRET')

    print(f'WC_API_URL: {wc_url}')
    print(f'WC_CONSUMER_KEY configurado: {bool(consumer_key)}')
    print(f'WC_CONSUMER_SECRET configurado: {bool(consumer_secret)}')

    if consumer_key:
        print(f'WC_CONSUMER_KEY (preview): {consumer_key[:10]}...')
    print()

    if not all([wc_url, consumer_key, consumer_secret]):
        print('[ERROR] Credenciales de WooCommerce no configuradas correctamente')
        exit(1)

    # 2. Buscar el pedido más reciente creado por WhatsApp
    print('2. PEDIDO MÁS RECIENTE DE WHATSAPP')
    print('-' * 50)

    recent_order = db.session.execute(text("""
        SELECT o.id, o.date_created_gmt, o.status, o.total_amount
        FROM wpyz_wc_orders o
        INNER JOIN wpyz_wc_orders_meta m ON o.id = m.order_id
        WHERE m.meta_key = '_created_via'
            AND m.meta_value = 'woocommerce-manager'
        ORDER BY o.date_created_gmt DESC
        LIMIT 1
    """)).fetchone()

    if not recent_order:
        print('[ERROR] No se encontraron pedidos de WhatsApp')
        exit(1)

    order_id = recent_order[0]
    print(f'Order ID: {order_id}')
    print(f'Fecha: {recent_order[1]}')
    print(f'Estado: {recent_order[2]}')
    print(f'Total: S/. {recent_order[3]}')
    print()

    # 3. Verificar información del cliente
    print('3. INFORMACIÓN DEL CLIENTE')
    print('-' * 50)

    customer_info = db.session.execute(text("""
        SELECT meta_key, meta_value
        FROM wpyz_wc_orders_meta
        WHERE order_id = :order_id
            AND (meta_key LIKE '_billing_%' OR meta_key = '_customer_user')
        ORDER BY meta_key
    """), {'order_id': order_id}).fetchall()

    customer_email = None
    for meta in customer_info:
        print(f'{meta[0]}: {meta[1]}')
        if meta[0] == '_billing_email':
            customer_email = meta[1]
    print()

    if not customer_email:
        print('[WARNING] No se encontro email del cliente')
    else:
        print(f'[OK] Email del cliente: {customer_email}')
    print()

    # 4. Probar conexión con WooCommerce API
    print('4. PRUEBA DE CONEXIÓN CON WOOCOMMERCE API')
    print('-' * 50)

    api_url = f"{wc_url}/wp-json/wc/v3/orders/{order_id}"
    auth = HTTPBasicAuth(consumer_key, consumer_secret)

    try:
        response = requests.get(api_url, auth=auth, timeout=10)
        print(f'Status Code: {response.status_code}')

        if response.status_code == 200:
            order_data = response.json()
            print('[OK] Conexion exitosa')
            print(f'Order Number: {order_data.get("number")}')
            print(f'Status: {order_data.get("status")}')
            print(f'Customer Email: {order_data.get("billing", {}).get("email")}')
            print()

            # 5. Intentar disparar el correo (cambio de estado)
            print('5. INTENTO DE ENVIO DE CORREO')
            print('-' * 50)
            print('Intentando cambiar estado a pending...')

            # Paso 1: pending
            response_pending = requests.put(
                api_url,
                json={'status': 'pending'},
                auth=auth,
                timeout=10
            )

            print(f'Response pending: {response_pending.status_code}')
            if response_pending.status_code != 200:
                print(f'[ERROR] {response_pending.text}')
            else:
                print('[OK] Cambio a pending exitoso')

            import time
            time.sleep(1)

            # Paso 2: processing
            print('Intentando cambiar estado a processing...')
            response_processing = requests.put(
                api_url,
                json={'status': 'processing', 'set_paid': True},
                auth=auth,
                timeout=10
            )

            print(f'Response processing: {response_processing.status_code}')
            if response_processing.status_code != 200:
                print(f'[ERROR] {response_processing.text}')
            else:
                print('[OK] Cambio a processing exitoso')
                print('[OK] Correo deberia haberse enviado')

        else:
            print(f'[ERROR] Error de conexion: {response.status_code}')
            print(f'Response: {response.text[:500]}')

    except Exception as e:
        print(f'[ERROR] Excepcion: {str(e)}')
        import traceback
        print(traceback.format_exc())
