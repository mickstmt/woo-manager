# -*- coding: utf-8 -*-
"""
Script para verificar por qué la columna de tracking muestra guión (-)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME_PRODUCTION')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

print("\n" + "="*100)
print("VERIFICAR COLUMNA DE TRACKING EN WOOCOMMERCE")
print("="*100 + "\n")

with engine.connect() as conn:
    # Query para verificar todos los lugares donde se guarda tracking
    query = text("""
        SELECT
            o.id,
            o.status,

            -- HPOS metadata
            om_hpos.meta_value AS hpos_tracking,

            -- Post meta (legacy)
            pm.meta_value AS postmeta_tracking,

            -- Verificar si son iguales
            CASE
                WHEN om_hpos.meta_value = pm.meta_value THEN '✓ Iguales'
                WHEN om_hpos.meta_value IS NULL AND pm.meta_value IS NOT NULL THEN '⚠️  Solo en postmeta'
                WHEN om_hpos.meta_value IS NOT NULL AND pm.meta_value IS NULL THEN '⚠️  Solo en HPOS'
                WHEN om_hpos.meta_value != pm.meta_value THEN '✗ DIFERENTES'
                ELSE 'Ambos NULL'
            END AS comparacion

        FROM wpyz_wc_orders o

        LEFT JOIN wpyz_wc_orders_meta om_hpos
            ON o.id = om_hpos.order_id
            AND om_hpos.meta_key = '_wc_shipment_tracking_items'

        LEFT JOIN wpyz_postmeta pm
            ON o.id = pm.post_id
            AND pm.meta_key = '_wc_shipment_tracking_items'

        WHERE o.id IN (41987, 41986, 41985, 41984)
        ORDER BY o.id DESC
    """)

    result = conn.execute(query)
    rows = list(result)

    print("PEDIDOS DE LA CAPTURA:")
    print("-" * 100)

    for row in rows:
        order_id = row[0]
        status = row[1]
        hpos = row[2]
        postmeta = row[3]
        comparacion = row[4]

        print(f"\nPedido #{order_id} ({status}):")
        print(f"  Comparación: {comparacion}")
        print(f"  HPOS tracking: {hpos[:80] if hpos else 'NULL'}...")
        print(f"  Postmeta tracking: {postmeta[:80] if postmeta else 'NULL'}...")

    # Verificar configuración del plugin
    print("\n" + "="*100)
    print("CONFIGURACIÓN DEL PLUGIN DE TRACKING")
    print("="*100 + "\n")

    plugin_query = text("""
        SELECT
            option_name,
            option_value
        FROM wpyz_options
        WHERE option_name LIKE '%wc%shipment%'
           OR option_name LIKE '%tracking%'
        ORDER BY option_name
        LIMIT 10
    """)

    plugin_result = conn.execute(plugin_query)
    plugin_rows = list(plugin_result)

    if plugin_rows:
        print("Opciones encontradas:")
        for row in plugin_rows:
            print(f"  {row[0]}: {str(row[1])[:100]}")
    else:
        print("  ⚠️  No se encontraron opciones del plugin")
        print("  → El plugin WooCommerce Shipment Tracking puede no estar activo")

print("\n" + "="*100)
print("DIAGNÓSTICO")
print("="*100 + "\n")

print("""
POSIBLES CAUSAS DEL GUIÓN (-):

1. Plugin no activo o desactualizado
   → Verificar en WordPress > Plugins que "WooCommerce Shipment Tracking" esté activo
   → Actualizar a la última versión

2. Cache de WooCommerce
   → Ir a WooCommerce > Status > Tools
   → Limpiar todos los caches

3. Columna personalizada no configurada
   → El plugin puede necesitar configuración adicional para mostrar en listado
   → Verificar Settings del plugin

4. HPOS vs Postmeta
   → Si HPOS está activo, debe leer de wpyz_wc_orders_meta
   → Si HPOS no está activo, debe leer de wpyz_postmeta
   → Verificar que ambos tengan los datos

5. Formato incompatible
   → Algunas versiones del plugin esperan JSON en lugar de PHP serializado
   → Verificar versión del plugin
""")

print("\n" + "="*100 + "\n")
