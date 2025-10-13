# test_db.py
from app import create_app, db
from app.models import Product, ProductMeta

# Crear la aplicación
app = create_app('testing')

with app.app_context():
    print("=" * 60)
    print("🔍 Probando conexión a la base de datos...")
    print("=" * 60)
    
    try:
        # Probar conexión básica
        print("\n1️⃣ Probando conexión básica...")
        result = db.session.execute(db.text("SELECT 1"))
        print("✅ Conexión establecida correctamente")
        
        # Probar consulta a la tabla de posts
        print("\n2️⃣ Probando consulta a wpyz_posts...")
        result = db.session.execute(db.text("SELECT COUNT(*) as total FROM wpyz_posts"))
        total = result.fetchone()[0]
        print(f"✅ Total de registros en wpyz_posts: {total}")
        
        # Probar consulta a productos
        print("\n3️⃣ Probando consulta a productos...")
        result = db.session.execute(db.text("""
            SELECT COUNT(*) as total 
            FROM wpyz_posts 
            WHERE post_type = 'product'
        """))
        total_products = result.fetchone()[0]
        print(f"✅ Total de productos: {total_products}")
        
        # Probar modelo Product
        print("\n4️⃣ Probando modelo Product de SQLAlchemy...")
        products = Product.query.filter_by(post_type='product').limit(5).all()
        print(f"✅ Productos encontrados: {len(products)}")
        
        if products:
            print("\n📦 Primeros 5 productos:")
            for p in products:
                print(f"   - ID: {p.ID}, Título: {p.post_title}, Estado: {p.post_status}")
        
        # Probar metadatos
        print("\n5️⃣ Probando metadatos del primer producto...")
        if products:
            first_product = products[0]
            print(f"   Producto: {first_product.post_title}")
            
            # Obtener SKU
            sku = first_product.get_meta('_sku')
            print(f"   SKU: {sku}")
            
            # Obtener precio
            price = first_product.get_meta('_price')
            print(f"   Precio: {price}")
            
            # Obtener stock
            stock = first_product.get_meta('_stock')
            print(f"   Stock: {stock}")
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR ENCONTRADO:")
        print("=" * 60)
        print(f"\nTipo de error: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print("\nTraceback completo:")
        import traceback
        traceback.print_exc()
        print("=" * 60)