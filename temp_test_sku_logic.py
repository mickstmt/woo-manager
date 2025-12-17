from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print('=== Prueba de lógica de SKUs ===')
    print()

    # Casos de prueba
    test_cases = [
        '1006745',           # SKU simple
        '1006745-1006746',   # SKU compuesto (dos SKUs válidos)
        '1006745-CSRMW3ABR', # SKU con sufijo no válido
        '1006745-AB',        # SKU con sufijo corto
    ]

    for sku_test in test_cases:
        print(f'SKU: {sku_test}')

        # Lógica ACTUAL (solo LIKE)
        result_like = db.session.execute(text("""
            SELECT fc.sku, fc.FCLastCost
            FROM woo_products_fccost fc
            WHERE :sku COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                AND LENGTH(fc.sku) = 7
        """), {'sku': sku_test}).fetchall()

        print(f'  LIKE encontró {len(result_like)} matches:')
        total_like = 0
        for match in result_like:
            print(f'    - {match[0]}: ${match[1]}')
            total_like += float(match[1])
        print(f'  Total LIKE: ${total_like}')

        # Verificar si la segunda parte (después del guion) es un SKU válido
        parts = sku_test.split('-')
        if len(parts) == 2:
            segunda_parte = parts[1]
            print(f'  Segunda parte: "{segunda_parte}" (longitud: {len(segunda_parte)})')

            if len(segunda_parte) == 7:
                print(f'    -> Es un SKU compuesto válido')
            else:
                print(f'    -> NO es un SKU válido (sufijo)')

        print()
