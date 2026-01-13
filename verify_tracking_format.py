# -*- coding: utf-8 -*-
"""
Script para verificar el formato del tracking en los pedidos
y diagnosticar por qué no aparece en la columna de WooCommerce
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import json
import phpserialize

# Cargar variables de entorno
load_dotenv()

# Construir DATABASE_URL para PRODUCCIÓN
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME_PRODUCTION')  # PRODUCCIÓN

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# Pedidos a verificar (de la captura)
test_orders = [41987, 41986, 41985]

print("\n" + "="*100)
print("VERIFICACIÓN DE FORMATO DE TRACKING")
print("="*100 + "\n")

with engine.connect() as conn:
    for order_id in test_orders:
        print(f"\n{'─'*100}")
        print(f"PEDIDO #{order_id}")
        print(f"{'─'*100}\n")

        # Obtener tracking de HPOS
        query = text("""
            SELECT
                meta_key,
                meta_value
            FROM wpyz_wc_orders_meta
            WHERE order_id = :order_id
              AND meta_key = '_wc_shipment_tracking_items'
        """)

        result = conn.execute(query, {"order_id": order_id})
        row = result.fetchone()

        if not row:
            print(f"  ✗ NO tiene tracking guardado en wpyz_wc_orders_meta")
            continue

        meta_value = row[1]
        print(f"  ✓ Tracking encontrado en HPOS")
        print(f"\n  Longitud del valor: {len(meta_value)} caracteres")
        print(f"  Primeros 100 caracteres: {meta_value[:100]}")

        # Determinar formato
        print(f"\n  ANÁLISIS DEL FORMATO:")

        # Intentar como JSON
        is_json = False
        try:
            data_json = json.loads(meta_value)
            print(f"    ✓ Es JSON válido")
            print(f"    Tipo: {type(data_json)}")
            if isinstance(data_json, list):
                print(f"    Elementos en array: {len(data_json)}")
                if len(data_json) > 0:
                    print(f"    Primer elemento: {data_json[0]}")
                    if 'tracking_number' in data_json[0]:
                        print(f"    📦 Tracking Number: {data_json[0]['tracking_number']}")
            is_json = True
        except json.JSONDecodeError:
            print(f"    ✗ NO es JSON válido")

        # Intentar como PHP serializado
        is_php = False
        if not is_json:
            try:
                # Convertir a bytes si es necesario
                if isinstance(meta_value, str):
                    meta_bytes = meta_value.encode('utf-8')
                else:
                    meta_bytes = meta_value

                data_php = phpserialize.loads(meta_bytes)
                print(f"    ✓ Es PHP serializado válido")
                print(f"    Tipo: {type(data_php)}")
                if isinstance(data_php, list) and len(data_php) > 0:
                    print(f"    Elementos en array: {len(data_php)}")
                    print(f"    Primer elemento: {data_php[0]}")
                    if b'tracking_number' in data_php[0]:
                        tracking_num = data_php[0][b'tracking_number'].decode('utf-8')
                        print(f"    📦 Tracking Number: {tracking_num}")
                is_php = True
            except Exception as e:
                print(f"    ✗ NO es PHP serializado válido: {str(e)}")

        # DIAGNÓSTICO
        print(f"\n  DIAGNÓSTICO:")
        if is_json:
            print(f"    ✓ El formato es JSON (CORRECTO para HPOS)")
            print(f"    → El tracking debería aparecer en WooCommerce")
            print(f"    ℹ️  Si no aparece, puede ser un problema de cache")
        elif is_php:
            print(f"    ⚠️  El formato es PHP serializado (INCORRECTO para HPOS)")
            print(f"    → HPOS requiere JSON, no PHP serializado")
            print(f"    → Este es probablemente el problema")
            print(f"    → Solución: Guardar como JSON en lugar de PHP serializado")
        else:
            print(f"    ✗ Formato desconocido o corrupto")

print("\n" + "="*100)
print("CONCLUSIÓN Y RECOMENDACIONES")
print("="*100 + "\n")

print("""
Si el tracking está guardado como PHP serializado:
  → Este es el problema. HPOS requiere JSON.
  → Solución: Modificar dispatch.py para guardar JSON en lugar de PHP serializado.

Si el tracking está guardado como JSON válido:
  → El formato es correcto.
  → Problema puede ser:
    1. Cache de WooCommerce (limpiar cache)
    2. Plugin de tracking desactualizado
    3. Incompatibilidad de versión

Archivos a revisar:
  - app/routes/dispatch.py (líneas 1058-1119)
  - Cambiar phpserialize.dumps() por json.dumps()
""")

print("\n" + "="*100 + "\n")
