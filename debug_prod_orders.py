# -*- coding: utf-8 -*-
"""
Script para debuggear pedidos sin método de envío en PRODUCCIÓN
Ejecutar en el servidor de producción
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Cargar variables de entorno
load_dotenv()

# Construir DATABASE_URL para PRODUCCIÓN
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME_PRODUCTION')  # PRODUCCIÓN

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# Pedidos problemáticos
problem_orders = [41674, 41684]

print("\n" + "="*100)
print("ANÁLISIS DETALLADO DE PEDIDOS SIN MÉTODO DE ENVÍO - PRODUCCIÓN")
print("="*100 + "\n")

with engine.connect() as conn:
    for order_id in problem_orders:
        print(f"\n{'='*100}")
        print(f"PEDIDO #{order_id}")
        print(f"{'='*100}\n")

        # 1. Ver información básica del pedido
        print("1. INFORMACIÓN BÁSICA:")
        print("-" * 100)
        basic_query = text("""
            SELECT
                id,
                status,
                date_created_gmt,
                total_amount
            FROM wpyz_wc_orders
            WHERE id = :order_id
        """)
        result = conn.execute(basic_query, {"order_id": order_id})
        row = result.fetchone()
        if row:
            print(f"  ID: {row[0]}")
            print(f"  Status: {row[1]}")
            print(f"  Fecha creación: {row[2]}")
            print(f"  Total: S/ {row[3]}")
        else:
            print(f"  ✗ Pedido NO encontrado en wpyz_wc_orders")
            continue

        # 2. Ver todos los order_items
        print("\n2. ORDER ITEMS (wpyz_woocommerce_order_items):")
        print("-" * 100)
        items_query = text("""
            SELECT
                order_item_id,
                order_item_name,
                order_item_type
            FROM wpyz_woocommerce_order_items
            WHERE order_id = :order_id
            ORDER BY order_item_type, order_item_id
        """)
        items_result = conn.execute(items_query, {"order_id": order_id})
        items_rows = list(items_result)

        has_shipping_item = False
        if items_rows:
            for item in items_rows:
                print(f"  ID: {item[0]:<8} Type: {item[1]:<15} Name: {item[2]}")
                if item[1] == 'shipping':
                    has_shipping_item = True
        else:
            print(f"  ✗ NO tiene items en wpyz_woocommerce_order_items")

        if has_shipping_item:
            print(f"\n  ✓ SÍ tiene shipping item")
        else:
            print(f"\n  ✗ NO tiene shipping item en order_items")

        # 3. Ver TODA la metadata del pedido
        print("\n3. METADATA DEL PEDIDO (wpyz_wc_orders_meta):")
        print("-" * 100)
        meta_query = text("""
            SELECT
                meta_key,
                meta_value
            FROM wpyz_wc_orders_meta
            WHERE order_id = :order_id
            ORDER BY meta_key
        """)
        meta_result = conn.execute(meta_query, {"order_id": order_id})
        meta_rows = list(meta_result)

        shipping_meta_found = []
        billing_entrega = None

        if meta_rows:
            for meta in meta_rows:
                key = meta[0]
                value = str(meta[1])[:100] if meta[1] else '[NULL]'

                # Destacar metadata relevante para shipping
                if 'ship' in key.lower() or 'entrega' in key.lower() or 'delivery' in key.lower():
                    print(f"  ► {key:<40} {value}")
                    shipping_meta_found.append(key)
                    if key == '_billing_entrega':
                        billing_entrega = meta[1]
                else:
                    print(f"    {key:<40} {value}")
        else:
            print(f"  ✗ NO tiene metadata")

        # 4. Probar la query ACTUAL (sin fix)
        print("\n4. QUERY ACTUAL (SIN FALLBACK):")
        print("-" * 100)
        current_query = text("""
            SELECT
                (SELECT oi.order_item_name
                 FROM wpyz_woocommerce_order_items oi
                 WHERE oi.order_id = o.id
                   AND oi.order_item_type = 'shipping'
                 LIMIT 1) as shipping_method
            FROM wpyz_wc_orders o
            WHERE o.id = :order_id
        """)
        current_result = conn.execute(current_query, {"order_id": order_id})
        current_row = current_result.fetchone()
        current_method = current_row[0] if current_row and current_row[0] else None

        if current_method:
            print(f"  ✓ Método encontrado: {current_method}")
        else:
            print(f"  ✗ NULL - No se encontró método de envío")

        # 5. Probar la query NUEVA (con fallback)
        print("\n5. QUERY NUEVA (CON FALLBACK):")
        print("-" * 100)
        new_query = text("""
            SELECT
                COALESCE(
                    (SELECT oi.order_item_name
                     FROM wpyz_woocommerce_order_items oi
                     WHERE oi.order_id = o.id
                       AND oi.order_item_type = 'shipping'
                     LIMIT 1),
                    CASE
                        WHEN om_billing_entrega.meta_value = 'billing_recojo' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value LIKE '%recojo%' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value = 'billing_address' THEN 'Envío a domicilio'
                        ELSE NULL
                    END
                ) as shipping_method,
                om_billing_entrega.meta_value as billing_entrega_value
            FROM wpyz_wc_orders o
            LEFT JOIN wpyz_wc_orders_meta om_billing_entrega
                ON o.id = om_billing_entrega.order_id
                AND om_billing_entrega.meta_key = '_billing_entrega'
            WHERE o.id = :order_id
        """)
        new_result = conn.execute(new_query, {"order_id": order_id})
        new_row = new_result.fetchone()
        new_method = new_row[0] if new_row and new_row[0] else None
        billing_entrega_val = new_row[1] if new_row and new_row[1] else None

        print(f"  _billing_entrega: {billing_entrega_val or '[NULL]'}")
        if new_method:
            print(f"  ✓ Método encontrado: {new_method}")
        else:
            print(f"  ✗ NULL - Tampoco se encontró con fallback")

        # 6. DIAGNÓSTICO
        print("\n6. DIAGNÓSTICO:")
        print("-" * 100)

        if current_method:
            print(f"  ✓ El pedido SÍ tiene método de envío normal: '{current_method}'")
            print(f"  → El problema NO debería ocurrir con este pedido")
        elif new_method:
            print(f"  ✓ El pedido NO tiene shipping item, pero SÍ tiene _billing_entrega")
            print(f"  ✓ El FALLBACK funcionaría: '{new_method}'")
            print(f"  → El fix debería resolver el problema")
        else:
            print(f"  ✗ El pedido NO tiene shipping item NI _billing_entrega válido")
            print(f"  ✗ Metadata shipping encontrada: {shipping_meta_found}")
            print(f"  → Necesitamos investigar más este caso")

            # Buscar en otras ubicaciones posibles
            print("\n  BUSCANDO EN OTRAS UBICACIONES:")

            # Verificar si tiene método en _shipping_address_index
            shipping_index_query = text("""
                SELECT meta_value
                FROM wpyz_wc_orders_meta
                WHERE order_id = :order_id
                AND meta_key = '_shipping_address_index'
            """)
            shipping_index_result = conn.execute(shipping_index_query, {"order_id": order_id})
            shipping_index_row = shipping_index_result.fetchone()
            if shipping_index_row and shipping_index_row[0]:
                print(f"  → _shipping_address_index: {shipping_index_row[0][:150]}")

        print("\n" + "="*100)

print("\n" + "="*100)
print("FIN DEL ANÁLISIS")
print("="*100 + "\n")
