# app/routes/products.py
from flask import Blueprint, render_template, request, jsonify
from app.models import Product, ProductMeta
from app import db
from sqlalchemy import or_

# Crear el blueprint
bp = Blueprint('products', __name__, url_prefix='/products')


@bp.route('/')
def index():
    """
    Ruta principal de productos
    Muestra la lista de todos los productos con paginación
    
    URL: http://localhost:5000/products/
    """
    return render_template('products.html', title='Gestión de Productos')


@bp.route('/list')
def list_products():
    """
    Ruta para obtener lista de productos en formato JSON con paginación
    
    Comportamiento inteligente:
    - Sin búsqueda: Muestra últimos productos padre creados
    - Con búsqueda numérica (SKU): Muestra variaciones que coincidan
    - Con búsqueda texto: Muestra productos padre que coincidan
    """
    try:
        from sqlalchemy import text
        
        # Obtener parámetros de la URL
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        
        # Limitar per_page
        per_page = min(per_page, 500)
        
        # Determinar modo de búsqueda
        search_mode = None  # 'sku', 'name', o None
        show_variations = False
        
        if search:
            # Detectar si es búsqueda por SKU (contiene números) o por nombre
            if any(char.isdigit() for char in search):
                search_mode = 'sku'
                show_variations = True
            else:
                search_mode = 'name'
        
        # ========================================
        # CASO 1: Búsqueda por SKU (mostrar variaciones)
        # ========================================
        if search_mode == 'sku':
            # Buscar variaciones que coincidan con el SKU, ID o ID del padre
            variations_query = text("""
                SELECT DISTINCT v.ID
                FROM wpyz_posts v
                LEFT JOIN wpyz_postmeta vm ON v.ID = vm.post_id AND vm.meta_key = '_sku'
                WHERE v.post_type = 'product_variation'
                AND (
                    vm.meta_value LIKE :search
                    OR v.ID LIKE :search
                    OR v.post_parent LIKE :search
                )
                ORDER BY v.ID DESC
            """)
            
            result = db.session.execute(variations_query, {'search': f'%{search}%'})
            variation_ids = [row[0] for row in result]
            
            if not variation_ids:
                return jsonify({
                    'success': True,
                    'products': [],
                    'search_mode': 'sku',
                    'search_term': search,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 1,
                        'has_prev': False,
                        'has_next': False,
                        'prev_num': None,
                        'next_num': None
                    }
                })
            
            # Paginación manual
            total_variations = len(variation_ids)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_ids = variation_ids[start_idx:end_idx]
            
            # Obtener variaciones
            variations = Product.query.filter(Product.ID.in_(paginated_ids)).all()
            
            # Convertir a JSON
            products_list = []
            for variation in variations:
                # Obtener producto padre
                parent = Product.query.get(variation.post_parent) if variation.post_parent else None
                
                products_list.append({
                    'id': variation.ID,
                    'parent_id': variation.post_parent,
                    'parent_title': parent.post_title if parent else 'N/A',
                    'title': variation.post_title,
                    'status': variation.post_status,
                    'type': 'variation',
                    'sku': variation.get_meta('_sku') or 'N/A',
                    'price': variation.get_meta('_price') or '0',
                    'stock': variation.get_meta('_stock') or 'N/A',
                    'stock_status': variation.get_meta('_stock_status') or 'instock',
                    'image_url': variation.get_image_url(),
                    'date': variation.post_date.strftime('%Y-%m-%d %H:%M:%S') if variation.post_date else None
                })
            
            # Calcular paginación
            import math
            total_pages = math.ceil(total_variations / per_page)
            
            return jsonify({
                'success': True,
                'products': products_list,
                'search_mode': 'sku',
                'search_term': search,
                'show_variations': True,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_variations,
                    'pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages,
                    'prev_num': page - 1 if page > 1 else None,
                    'next_num': page + 1 if page < total_pages else None
                }
            })
        
        # ========================================
        # CASO 2: Búsqueda por nombre (mostrar productos padre)
        # ========================================
        elif search_mode == 'name':
            status_filter = f"AND p.post_status = '{status}'" if status else "AND p.post_status = 'publish'"
            
            # Contar total
            count_query = text(f"""
                SELECT COUNT(DISTINCT p.ID)
                FROM wpyz_posts p
                WHERE p.post_type = 'product'
                {status_filter}
                AND p.post_title LIKE :search
            """)
            
            total_result = db.session.execute(count_query, {'search': f'%{search}%'})
            total_products = total_result.scalar()
            
            # Obtener productos
            offset = (page - 1) * per_page
            
            products_query = text(f"""
                SELECT p.ID, p.post_date
                FROM wpyz_posts p
                WHERE p.post_type = 'product'
                {status_filter}
                AND p.post_title LIKE :search
                GROUP BY p.ID, p.post_date
                ORDER BY p.post_date DESC
                LIMIT :limit OFFSET :offset
            """)
            
            result = db.session.execute(
                products_query,
                {'search': f'%{search}%', 'limit': per_page, 'offset': offset}
            )
            
            product_ids = [row[0] for row in result]
            products_items = Product.query.filter(Product.ID.in_(product_ids)).all() if product_ids else []
            
            # Calcular páginas
            import math
            total_pages = math.ceil(total_products / per_page) if total_products > 0 else 1
            
        # ========================================
        # CASO 3: Sin búsqueda (mostrar últimos productos padre)
        # ========================================
        else:
            query = Product.query.filter_by(post_type='product')
            
            if status:
                query = query.filter_by(post_status=status)
            else:
                query = query.filter_by(post_status='publish')
            
            total_products = query.count()
            
            # Ordenar por fecha de creación (más recientes primero)
            products = query.order_by(Product.post_date.desc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            products_items = products.items
            total_pages = products.pages
        
        # ========================================
        # Procesar productos padre (CASO 2 y 3)
        # ========================================
        if search_mode != 'sku':
            product_ids = [p.ID for p in products_items]
            
            # Contar variaciones
            from sqlalchemy import func
            variations_query = db.session.query(
                Product.post_parent,
                func.count(Product.ID).label('count')
            ).filter(
                Product.post_type == 'product_variation',
                Product.post_parent.in_(product_ids)
            ).group_by(Product.post_parent).all()
            
            variations_dict = {row[0]: row[1] for row in variations_query}
            
            # Convertir a JSON
            products_list = []
            for product in products_items:
                variations_count = variations_dict.get(product.ID, 0)
                is_variable = variations_count > 0
                
                products_list.append({
                    'id': product.ID,
                    'parent_id': None,
                    'parent_title': None,
                    'title': product.post_title,
                    'status': product.post_status,
                    'type': 'variable' if is_variable else 'simple',
                    'sku': product.get_meta('_sku') or 'N/A',
                    'price': product.get_meta('_price') or '0',
                    'stock': product.get_meta('_stock') or 'N/A',
                    'stock_status': product.get_meta('_stock_status') or 'instock',
                    'is_variable': is_variable,
                    'variations_count': variations_count,
                    'image_url': product.get_image_url(),
                    'date': product.post_date.strftime('%Y-%m-%d %H:%M:%S') if product.post_date else None
                })
        
        # Respuesta final
        pagination_data = {
            'page': page,
            'per_page': per_page,
            'total': total_products if search_mode != 'sku' else 0,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
        }
        
        return jsonify({
            'success': True,
            'products': products_list,
            'search_mode': search_mode or 'default',
            'search_term': search if search else '',
            'show_variations': show_variations,
            'pagination': pagination_data
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/stats')
def stats():
    """
    Obtener estadísticas generales de productos
    
    URL: http://localhost:5000/products/stats
    """
    try:
        # Total de productos
        total = Product.query.filter_by(post_type='product').count()
        
        # Productos publicados
        published = Product.query.filter_by(
            post_type='product',
            post_status='publish'
        ).count()
        
        # Productos en borrador
        draft = Product.query.filter_by(
            post_type='product',
            post_status='draft'
        ).count()
        
        # Productos pendientes
        pending = Product.query.filter_by(
            post_type='product',
            post_status='pending'
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'published': published,
                'draft': draft,
                'pending': pending
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:product_id>/variations')
def get_variations(product_id):
    """
    Obtener todas las variaciones de un producto variable
    
    URL: http://localhost:5000/products/123/variations
    """
    try:
        # Buscar variaciones (productos hijos)
        variations = Product.query.filter_by(
            post_type='product_variation',
            post_parent=product_id
        ).order_by(Product.ID.asc()).all()
        
        variations_list = []
        for variation in variations:
            # Obtener atributos de la variación
            # Las variaciones tienen metadatos especiales con los atributos
            attributes = {}
            for meta in variation.product_meta:
                if meta.meta_key.startswith('attribute_'):
                    # Limpiar el nombre del atributo
                    attr_name = meta.meta_key.replace('attribute_pa_', '').replace('attribute_', '')
                    attributes[attr_name] = meta.meta_value
            
            # Obtener datos importantes
            sku = variation.get_meta('_sku') or 'N/A'
            price = variation.get_meta('_price') or '0'
            regular_price = variation.get_meta('_regular_price') or '0'
            sale_price = variation.get_meta('_sale_price') or ''
            stock = variation.get_meta('_stock') or 'N/A'
            stock_status = variation.get_meta('_stock_status') or 'instock'
            
            variations_list.append({
                'id': variation.ID,
                'title': variation.post_title,
                'attributes': attributes,
                'sku': sku,
                'price': price,
                'regular_price': regular_price,
                'sale_price': sale_price,
                'stock': stock,
                'stock_status': stock_status
            })
        
        return jsonify({
            'success': True,
            'variations': variations_list,
            'total': len(variations_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:product_id>')
def view_product(product_id):
    """
    Ver detalles de un producto específico
    
    URL: http://localhost:5000/products/123
    """
    product = Product.query.get_or_404(product_id)
    
    # Obtener todos los metadatos del producto
    metadata = {}
    for meta in product.product_meta:
        metadata[meta.meta_key] = meta.meta_value
    
    return render_template('product_detail.html', 
                         product=product,
                         metadata=metadata)