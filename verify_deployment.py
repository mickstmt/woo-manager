# -*- coding: utf-8 -*-
"""
Script para verificar que el código nuevo esté desplegado en producción
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*100)
print("VERIFICACIÓN DE DESPLIEGUE DEL FIX")
print("="*100 + "\n")

# Verificar si el código tiene el fallback
import os

# Buscar el archivo dispatch.py
dispatch_file = None
possible_paths = [
    'app/routes/dispatch.py',
    '/var/www/woocommerce-manager/app/routes/dispatch.py',
    './app/routes/dispatch.py'
]

for path in possible_paths:
    if os.path.exists(path):
        dispatch_file = path
        break

if not dispatch_file:
    print("✗ NO se pudo encontrar app/routes/dispatch.py")
    print("\nRutas buscadas:")
    for path in possible_paths:
        print(f"  - {path}")
    print("\nPor favor indica la ruta correcta del archivo.")
    sys.exit(1)

print(f"✓ Archivo encontrado: {dispatch_file}\n")

# Leer el archivo
with open(dispatch_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar si tiene el COALESCE (código nuevo)
has_coalesce = 'COALESCE' in content and 'om_billing_entrega' in content
has_fallback = 'billing_recojo' in content and 'Recojo en Almacén' in content

# Verificar que AMBAS funciones tengan el fix
get_orders_has_fix = content.count('COALESCE') >= 1 and content.count('om_billing_entrega') >= 2
get_column_has_fix = 'get_column_from_shipping_method' in content and content.count('COALESCE') >= 2

print("VERIFICACIÓN DEL CÓDIGO:")
print("-" * 100)

if has_coalesce and has_fallback and get_orders_has_fix and get_column_has_fix:
    print("✓✓✓ EL FIX ESTÁ COMPLETAMENTE DESPLEGADO ✓✓✓")
    print("\nDetalles encontrados:")
    print("  ✓ COALESCE encontrado en la query SQL")
    print("  ✓ om_billing_entrega JOIN presente (2 veces)")
    print("  ✓ Lógica de fallback 'billing_recojo' → 'Recojo en Almacén'")
    print("  ✓ get_orders() tiene el fix")
    print("  ✓ get_column_from_shipping_method() tiene el fix")

    # Buscar la línea exacta
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'COALESCE' in line:
            print(f"\n  Encontrado en línea {i}:")
            # Mostrar contexto (5 líneas antes y después)
            start = max(0, i-3)
            end = min(len(lines), i+10)
            for j in range(start, end):
                if j == i-1:
                    print(f"  ► {j+1:4d}: {lines[j]}")
                else:
                    print(f"    {j+1:4d}: {lines[j]}")
            break
else:
    print("✗✗✗ EL FIX NO ESTÁ COMPLETAMENTE DESPLEGADO ✗✗✗")
    print("\nVerificación:")
    print(f"  COALESCE presente: {'✓' if 'COALESCE' in content else '✗'}")
    print(f"  om_billing_entrega JOIN: {'✓' if 'om_billing_entrega' in content else '✗'}")
    print(f"  Lógica fallback: {'✓' if has_fallback else '✗'}")
    print(f"  get_orders() tiene fix: {'✓' if get_orders_has_fix else '✗'}")
    print(f"  get_column_from_shipping_method() tiene fix: {'✓' if get_column_has_fix else '✗'}")
    print(f"\n  Conteo COALESCE: {content.count('COALESCE')} (debe ser >= 2)")
    print(f"  Conteo om_billing_entrega: {content.count('om_billing_entrega')} (debe ser >= 2)")
    print("\n⚠️  NECESITAS HACER REDEPLOY del código actualizado")
    print("   Los commits están en GitHub pero no en el servidor de producción")

print("\n" + "="*100)

# Verificar también el archivo orders.py para el fix de reintentos
print("\nVERIFICACIÓN DEL FIX DE REINTENTOS (orders.py):")
print("-" * 100)

orders_file = None
possible_paths_orders = [
    'app/routes/orders.py',
    '/var/www/woocommerce-manager/app/routes/orders.py',
    './app/routes/orders.py'
]

for path in possible_paths_orders:
    if os.path.exists(path):
        orders_file = path
        break

if orders_file:
    with open(orders_file, 'r', encoding='utf-8') as f:
        orders_content = f.read()

    has_retry = 'from urllib3.util.retry import Retry' in orders_content
    has_adapter = 'HTTPAdapter' in orders_content
    has_timeout_30 = 'timeout=30' in orders_content

    if has_retry and has_adapter and has_timeout_30:
        print("✓✓✓ FIX DE REINTENTOS DESPLEGADO ✓✓✓")
        print("\n  ✓ urllib3.Retry importado")
        print("  ✓ HTTPAdapter configurado")
        print("  ✓ Timeout aumentado a 30 segundos")
    else:
        print("✗✗✗ FIX DE REINTENTOS NO DESPLEGADO ✗✗✗")
        print(f"\n  urllib3.Retry: {'✓' if has_retry else '✗'}")
        print(f"  HTTPAdapter: {'✓' if has_adapter else '✗'}")
        print(f"  timeout=30: {'✓' if has_timeout_30 else '✗'}")
else:
    print("✗ No se pudo verificar orders.py")

print("\n" + "="*100 + "\n")
