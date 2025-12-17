"""
Script para copiar datos de woo_products_fccost desde ambiente de prueba a producción

IMPORTANTE:
- Configurar credenciales de ambas bases de datos
- Ejecutar con precaución, validar antes en un ambiente controlado
"""

import pymysql
from datetime import datetime

# ====================================
# CONFIGURACIÓN - EDITAR ESTOS VALORES
# ====================================

# Base de datos de PRUEBA (origen)
DB_TEST = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tu_password',
    'database': 'nombre_bd_prueba',
    'charset': 'utf8mb4'
}

# Base de datos de PRODUCCIÓN (destino)
DB_PROD = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tu_password',
    'database': 'nombre_bd_produccion',
    'charset': 'utf8mb4'
}

# ====================================
# SCRIPT
# ====================================

def copy_fccost_data():
    conn_test = None
    conn_prod = None

    try:
        # Conectar a base de datos de prueba
        print("Conectando a base de datos de PRUEBA...")
        conn_test = pymysql.connect(**DB_TEST)
        cursor_test = conn_test.cursor()

        # Conectar a base de datos de producción
        print("Conectando a base de datos de PRODUCCIÓN...")
        conn_prod = pymysql.connect(**DB_PROD)
        cursor_prod = conn_prod.cursor()

        # Obtener datos de prueba
        print("\nExtrayendo datos de ambiente de prueba...")
        cursor_test.execute("SELECT * FROM woo_products_fccost")
        rows = cursor_test.fetchall()

        print(f"Se encontraron {len(rows)} registros en prueba")

        if len(rows) == 0:
            print("No hay datos para copiar. Abortando.")
            return

        # Obtener estructura de columnas
        cursor_test.execute("DESCRIBE woo_products_fccost")
        columns = [col[0] for col in cursor_test.fetchall()]
        print(f"Columnas: {', '.join(columns)}")

        # Confirmar acción
        print("\n" + "="*60)
        print("ATENCIÓN: Se van a copiar los datos a PRODUCCIÓN")
        print("="*60)
        respuesta = input("¿Deseas continuar? (SI/no): ")

        if respuesta.upper() != 'SI':
            print("Operación cancelada por el usuario")
            return

        # Limpiar tabla en producción (OPCIONAL - comentar si no quieres borrar)
        print("\n¿Deseas LIMPIAR la tabla en producción antes de copiar?")
        limpiar = input("Esto BORRARÁ todos los datos existentes (SI/no): ")

        if limpiar.upper() == 'SI':
            print("Limpiando tabla en producción...")
            cursor_prod.execute("TRUNCATE TABLE woo_products_fccost")
            conn_prod.commit()
            print("Tabla limpiada")

        # Preparar query de inserción
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)

        insert_query = f"""
            INSERT INTO woo_products_fccost ({columns_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
                FCLastCost = VALUES(FCLastCost),
                FCStock = VALUES(FCStock)
        """

        # Insertar datos
        print(f"\nInsertando {len(rows)} registros en producción...")
        inserted = 0
        updated = 0

        for i, row in enumerate(rows, 1):
            cursor_prod.execute(insert_query, row)

            if cursor_prod.rowcount == 1:
                inserted += 1
            elif cursor_prod.rowcount == 2:
                updated += 1

            if i % 100 == 0:
                print(f"  Procesados: {i}/{len(rows)}")

        # Commit
        conn_prod.commit()

        print("\n" + "="*60)
        print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"  Registros insertados: {inserted}")
        print(f"  Registros actualizados: {updated}")
        print(f"  Total procesado: {len(rows)}")

        # Verificar en producción
        cursor_prod.execute("SELECT COUNT(*) FROM woo_products_fccost")
        total_prod = cursor_prod.fetchone()[0]
        print(f"\nTotal de registros en producción: {total_prod}")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        if conn_prod:
            conn_prod.rollback()
        raise

    finally:
        if conn_test:
            conn_test.close()
        if conn_prod:
            conn_prod.close()


if __name__ == '__main__':
    print("="*60)
    print("COPIAR DATOS DE woo_products_fccost")
    print("DE PRUEBA A PRODUCCIÓN")
    print("="*60)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nIMPORTANTE: Edita las credenciales en el script antes de ejecutar")
    print("="*60)
    print()

    copy_fccost_data()
