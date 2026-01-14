import sys
import os
from sqlalchemy import text
import datetime

# Agregar el directorio padre al path para poder importar la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Order
from woocommerce import API

def resend_tracking_emails(days_back=30, specific_order_ids=None):
    """
    Reenvía la información de tracking a WooCommerce para forzar el envío de correos.
    Puede buscar por días atrás o por una lista de IDs específicos.
    """
    app = create_app('production') # Usar configuración de producción por defecto
    
    with app.app_context():
        # 1. Conectar con API de WooCommerce
        wc_api = API(
            url=app.config['WC_API_URL'],
            consumer_key=app.config['WC_CONSUMER_KEY'],
            consumer_secret=app.config['WC_CONSUMER_SECRET'],
            version="wc/v3",
            timeout=30
        )
        
        # 2. Construir Query
        base_query = """
            SELECT 
                o.id,
                o.billing_email,
                pm_track.meta_value as tracking_number,
                pm_prov.meta_value as provider,
                pm_items.meta_value as tracking_items
            FROM wpyz_wc_orders o
            JOIN wpyz_postmeta pm_track ON o.id = pm_track.post_id AND pm_track.meta_key = '_tracking_number'
            JOIN wpyz_postmeta pm_prov ON o.id = pm_prov.post_id AND pm_prov.meta_key = '_tracking_provider'
            JOIN wpyz_postmeta pm_items ON o.id = pm_items.post_id AND pm_items.meta_key = '_wc_shipment_tracking_items'
            WHERE o.status = 'wc-completed'
        """
        
        params = {}
        
        if specific_order_ids:
            print(f"🔄 Iniciando reenvío para PEDIDOS ESPECÍFICOS: {specific_order_ids}")
            base_query += " AND o.id IN :order_ids"
            params['order_ids'] = tuple(specific_order_ids)
        else:
            print(f"🔄 Iniciando reenvío de correos para pedidos de los últimos {days_back} días...")
            start_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
            base_query += " AND o.date_created_gmt >= :start_date"
            params['start_date'] = start_date

        base_query += " GROUP BY o.id"
        
        query = text(base_query)
        orders = db.session.execute(query, params).fetchall()
        
        print(f"📦 Encontrados {len(orders)} pedidos con tracking.")
        
        success_count = 0
        error_count = 0
        
        for row in orders:
            order_id = row[0]
            email = row[1]
            tracking_number = row[2]
            provider = row[3]
            
            print(f"Processing Order #{order_id} ({email})...")
            
            try:
                # Reconstruimos el objeto Python simple
                tracking_data_list = [{
                    'tracking_number': tracking_number,
                    'tracking_provider': provider,
                    'date_shipped': datetime.datetime.now().strftime('%Y-%m-%d')
                }]
                
                wc_api.put(f"orders/{order_id}", {
                    "meta_data": [
                        {"key": "_tracking_number", "value": tracking_number},
                        {"key": "_tracking_provider", "value": provider},
                        {"key": "_wc_shipment_tracking_items", "value": tracking_data_list}
                    ]
                })
                
                print(f"✅ [OK] Pedido #{order_id} actualizado en WooCommerce.")
                success_count += 1
                
            except Exception as e:
                print(f"❌ [ERROR] Falló pedido #{order_id}: {str(e)}")
                error_count += 1
                
        print("\n========================================")
        print(f"Resumen Final:")
        print(f"✅ Exitosos: {success_count}")
        print(f"❌ Fallidos: {error_count}")
        print("========================================")

if __name__ == '__main__':
    # Modo flexible de argumentos
    args = sys.argv[1:]
    
    specific_ids = []
    days = 7
    
    # Detectar si hay IDs específicos (argumentos que no son flags o que son lista)
    # Si el primer argumento contiene comas, es una lista de IDs
    if len(args) > 0 and ',' in args[0]:
        try:
            specific_ids = [int(x.strip()) for x in args[0].split(',') if x.strip()]
        except ValueError:
            print("Error: Los IDs deben ser números separados por comas.")
            sys.exit(1)
    # Si hay múltiples argumentos numéricos
    elif len(args) > 1:
        try:
            specific_ids = [int(x) for x in args]
        except ValueError:
             print("Error: Los IDs deben ser números.")
             sys.exit(1)
    # Si solo hay un argumento y parece ser grande (ID de pedido) en lugar de días (pequeño)
    elif len(args) == 1:
        try:
            val = int(args[0])
            if val > 1000: # Asumimos que es un ID de pedido
                specific_ids = [val]
            else:
                days = val
        except ValueError:
             print("Error: Argumento inválido.")
             sys.exit(1)
            
    resend_tracking_emails(days, specific_ids)
