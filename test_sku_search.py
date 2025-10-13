# test_sku_search.py
from app import create_app, db
from app.models import Product, ProductMeta
from sqlalchemy import text, and_, or_

app = create_app('testing')

with app.app_context():
    search_term = '1007510'  # ← Cambia esto por el SKU que quieres buscar
    
    print("=" * 80)
    print(f"🔍 Buscando productos con SKU que contenga: {search_term}")
    print("=" * 80)
    
    # Método 1: Buscar directamente en postmeta
    print("\n1️⃣ Búsqueda directa en wpyz_postmeta:")
    result = db.session.execute(text("""
        SELECT post_id, meta_value 
        FROM wpyz_postmeta 
        WHERE meta_key = '_sku' 
        AND meta_value LIKE :search
        LIMIT 10
    """), {'search': f'%{search_term}%'})
    
    found = False
    for row in result:
        found = True
        print(f"   ✓ Product ID: {row[0]} | SKU: {row[1]}")
    
    if not found:
        print(f"   ❌ No se encontraron SKUs que contengan '{search_term}'")
    
    # Método 2: Obtener información completa del producto
    print("\n2️⃣ Información completa de productos encontrados:")
    result = db.session.execute(text("""
        SELECT 
            p.ID,
            p.post_title,
            p.post_status,
            p.post_type,
            pm.meta_value as sku
        FROM wpyz_posts p
        INNER JOIN wpyz_postmeta pm ON p.ID = pm.post_id
        WHERE pm.meta_key = '_sku'
        AND pm.meta_value LIKE :search
        AND p.post_type = 'product'
        LIMIT 10
    """), {'search': f'%{search_term}%'})
    
    found_products = 0
    for row in result:
        found_products += 1
        print(f"\n   Producto #{found_products}:")
        print(f"   ID: {row[0]}")
        print(f"   Título: {row[1]}")
        print(f"   Estado: {row[2]}")
        print(f"   Tipo: {row[3]}")
        print(f"   SKU: {row[4]}")
    
    if found_products == 0:
        print("   ⚠️  PROBLEMA: La consulta SQL con JOIN no devolvió resultados")
        print("   Esto puede significar que:")
        print("   - Los productos tienen post_type diferente a 'product'")
        print("   - Los productos están en otro estado")
        
        # Verificar qué post_type tienen estos productos
        print("\n   🔍 Verificando post_type de los productos encontrados:")
        check_query = text("""
            SELECT p.ID, p.post_type, p.post_status
            FROM wpyz_posts p
            WHERE p.ID IN (28807, 28812, 28822, 28832, 28842)
        """)
        check_result = db.session.execute(check_query)
        for row in check_result:
            print(f"      ID {row[0]}: post_type='{row[1]}' | post_status='{row[2]}'")
    
    # Método 3: Probar con SQLAlchemy ORM
    print("\n3️⃣ Prueba con SQLAlchemy ORM (método actual):")
    sku_subquery = db.session.query(ProductMeta.post_id).filter(
        and_(
            ProductMeta.meta_key == '_sku',
            ProductMeta.meta_value.like(f'%{search_term}%')
        )
    ).subquery()
    
    products = Product.query.filter(
        and_(
            Product.post_type == 'product',
            Product.ID.in_(sku_subquery)
        )
    ).limit(10).all()
    
    if products:
        print(f"   ✓ Encontrados {len(products)} productos:")
        for p in products:
            sku = p.get_meta('_sku')
            print(f"      - ID: {p.ID} | Título: {p.post_title} | SKU: {sku}")
    else:
        print(f"   ❌ SQLAlchemy no encontró productos")
    
    print("\n" + "=" * 80)