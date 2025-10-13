# debug_product_type.py
from app import create_app, db
from app.models import Product, ProductMeta
from sqlalchemy import text

app = create_app('testing')

with app.app_context():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: Detectando productos variables")
    print("=" * 80)
    
    # Seleccionar un producto al azar para analizar
    print("\n1️⃣ Buscando productos para analizar...")
    
    # Tomar los primeros 10 productos
    products = Product.query.filter_by(post_type='product').limit(10).all()
    
    print(f"✅ Encontrados {len(products)} productos para analizar\n")
    
    for product in products:
        print("-" * 80)
        print(f"📦 Producto ID: {product.ID}")
        print(f"   Título: {product.post_title}")
        
        # Obtener TODOS los metadatos de este producto
        print(f"\n   📋 Metadatos relevantes:")
        
        meta_keys_to_check = [
            '_product_type',
            'product_type',
            '_product_attributes',
            '_default_attributes'
        ]
        
        for meta_key in meta_keys_to_check:
            meta = product.get_meta(meta_key)
            if meta:
                print(f"      ✓ {meta_key}: {meta}")
        
        # Contar si tiene variaciones (hijos)
        variations_count = Product.query.filter_by(
            post_type='product_variation',
            post_parent=product.ID
        ).count()
        
        if variations_count > 0:
            print(f"\n   🔢 TIENE {variations_count} VARIACIONES")
            
            # Mostrar las primeras 3 variaciones
            variations = Product.query.filter_by(
                post_type='product_variation',
                post_parent=product.ID
            ).limit(3).all()
            
            for var in variations:
                print(f"      - Variación ID: {var.ID} | Título: {var.post_title}")
        else:
            print(f"\n   ℹ️  No tiene variaciones (producto simple)")
        
        print()
    
    # Consulta directa para verificar
    print("=" * 80)
    print("2️⃣ Consulta directa a la base de datos")
    print("=" * 80)
    
    # Buscar todos los meta_keys que contengan 'type' o 'variable'
    result = db.session.execute(text("""
        SELECT DISTINCT meta_key 
        FROM wpyz_postmeta 
        WHERE meta_key LIKE '%type%' 
        OR meta_key LIKE '%variable%'
        OR meta_key LIKE '%attribute%'
        ORDER BY meta_key
        LIMIT 20
    """))
    
    print("\n📝 Meta keys relacionados con 'type', 'variable' o 'attribute':")
    for row in result:
        print(f"   - {row[0]}")
    
    # Contar productos con variaciones
    print("\n" + "=" * 80)
    print("3️⃣ Estadísticas de productos variables")
    print("=" * 80)
    
    # Productos que tienen hijos
    result = db.session.execute(text("""
        SELECT 
            p.ID,
            p.post_title,
            COUNT(v.ID) as variations_count
        FROM wpyz_posts p
        LEFT JOIN wpyz_posts v ON v.post_parent = p.ID AND v.post_type = 'product_variation'
        WHERE p.post_type = 'product'
        GROUP BY p.ID, p.post_title
        HAVING COUNT(v.ID) > 0
        LIMIT 10
    """))
    
    print("\n📊 Productos con variaciones encontrados:")
    count = 0
    for row in result:
        count += 1
        print(f"   {count}. ID: {row[0]} | {row[1]} | Variaciones: {row[2]}")
    
    if count == 0:
        print("   ⚠️  No se encontraron productos con variaciones")
        print("   💡 Esto podría significar que tu tienda solo tiene productos simples")
    
    print("\n" + "=" * 80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("=" * 80)