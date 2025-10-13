# app/routes/stock.py
from flask import Blueprint, render_template, request, jsonify
from app.models import Product, ProductMeta
from app import db
from sqlalchemy import or_, func

bp = Blueprint('stock', __name__, url_prefix='/stock')


@bp.route('/')
def index():
    """
    Vista principal de gestión de stock
    
    URL: http://localhost:5000/stock/
    """
    return render_template('stock.html', title='Gestión de Stock')


@bp.route('/list')
def list_stock():
    """
    Obtener lista de productos con información de stock
    
    Comportamiento:
    - Sin búsqueda: No muestra nada (lista vacía)
    - Con búsqueda: Detecta si es SKU o nombre y busca en ambos (productos + variaciones)
    """
    try:
        from sqlalchemy import text
        
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '', type=str)
        stock_filter = request.args.get('stock_filter', 'all', type=str)
        low_threshold = request.args.get('low_threshold', 10, type=int)
        
        # Limitar per_page
        per_page = min(per_page, 500)
        
        # Inicializar lista de productos
        products_list = []
        all_items = []
        
        # ========================================
        # CASO 1: Sin búsqueda - No mostrar nada
        # ========================================
        if not search or search.strip() == '':
            return jsonify({
                'success': True,
                'products': [],
                'search_term': '',
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 1,
                    'has_prev': False,
                    'has_next': False,
                    'prev_num': None,
                    'next_num': None
                }
            })
        
        # ========================================
        # CASO 2: Con búsqueda
        # ========================================
        
        # Buscar en productos simples (con SKU)
        simple_products_query = text("""
            SELECT DISTINCT p.ID
            FROM wpyz_posts p
            LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sku'
            WHERE p.post_type = 'product'
            AND p.post_status = 'publish'
            AND (
                p.post_title LIKE :search
                OR p.ID LIKE :search
                OR pm.meta_value LIKE :search
            )
        """)
        
        result = db.session.execute(simple_products_query, {'search': f'%{search}%'})
        simple_ids = [row[0] for row in result]
        
        # Buscar en variaciones (por título, ID, SKU O por ID del producto padre)
        variations_query = text("""
            SELECT DISTINCT v.ID
            FROM wpyz_posts v
            LEFT JOIN wpyz_postmeta vm ON v.ID = vm.post_id AND vm.meta_key = '_sku'
            WHERE v.post_type = 'product_variation'
            AND v.post_status = 'publish'
            AND (
                v.post_title LIKE :search
                OR v.ID LIKE :search
                OR vm.meta_value LIKE :search
                OR v.post_parent LIKE :search
            )
        """)
        
        result = db.session.execute(variations_query, {'search': f'%{search}%'})
        variation_ids = [row[0] for row in result]
        
        # Obtener productos simples
        if simple_ids:
            simple_products = Product.query.filter(Product.ID.in_(simple_ids)).all()
            for product in simple_products:
                all_items.append({
                    'product': product,
                    'is_variation': False
                })
        
        # Obtener variaciones
        if variation_ids:
            variations = Product.query.filter(Product.ID.in_(variation_ids)).all()
            for variation in variations:
                all_items.append({
                    'product': variation,
                    'is_variation': True
                })
        
        # ========================================
        # Procesar todos los items
        # ========================================
        for item in all_items:
            product = item['product']
            is_variation = item['is_variation']
            
            # Obtener metadatos
            sku = product.get_meta('_sku') or 'N/A'
            price = product.get_meta('_price') or '0'
            stock = product.get_meta('_stock')
            stock_status = product.get_meta('_stock_status') or 'instock'
            manage_stock = product.get_meta('_manage_stock') or 'no'
            
            # Convertir stock a número
            try:
                stock_quantity = int(stock) if stock else 0
            except:
                stock_quantity = 0
            
            # Determinar si tiene stock bajo
            is_low_stock = stock_quantity > 0 and stock_quantity <= low_threshold
            
            # Aplicar filtro de stock
            if stock_filter == 'instock' and stock_status != 'instock':
                continue
            elif stock_filter == 'outofstock' and stock_status != 'outofstock':
                continue
            elif stock_filter == 'low' and not is_low_stock:
                continue
            
            # Obtener padre si es variación
            parent_id = None
            parent_title = None
            if is_variation and product.post_parent:
                parent = Product.query.get(product.post_parent)
                if parent:
                    parent_id = parent.ID
                    parent_title = parent.post_title
            
            product_data = {
                'id': product.ID,
                'parent_id': parent_id,
                'parent_title': parent_title,
                'title': product.post_title,
                'type': 'variation' if is_variation else 'simple',
                'sku': sku,
                'price': price,
                'stock': stock_quantity,
                'stock_status': stock_status,
                'manage_stock': manage_stock,
                'is_low_stock': is_low_stock
            }
            
            products_list.append(product_data)
        
        # ========================================
        # Paginación
        # ========================================
        total_items = len(products_list)
        
        # Aplicar paginación manualmente
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_products = products_list[start_idx:end_idx]
        
        # Calcular páginas
        import math
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
        
        return jsonify({
            'success': True,
            'products': paginated_products,
            'search_term': search,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_items,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < total_pages else None
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/stats')
def stock_stats():
    """
    Obtener estadísticas generales de stock
    
    URL: http://localhost:5000/stock/stats
    """
    try:
        # Contar productos por estado de stock
        total_products = Product.query.filter_by(
            post_type='product',
            post_status='publish'
        ).count()
        
        # Estas estadísticas las calcularemos en el cliente
        # porque dependen de los metadatos
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total_products
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    

@bp.route('/update/<int:product_id>', methods=['POST'])
def update_stock(product_id):
    """
    Actualizar stock de un producto individual
    
    URL: POST http://localhost:5000/stock/update/123
    
    JSON Body:
    {
        "stock": 50,
        "reason": "Ajuste de inventario"
    }
    """
    try:
        from app.models import StockHistory
        
        # Obtener datos del request
        data = request.get_json()
        new_stock = data.get('stock')
        reason = data.get('reason', 'Actualización manual')
        
        # Validar
        if new_stock is None:
            return jsonify({
                'success': False,
                'error': 'El campo stock es requerido'
            }), 400
        
        try:
            new_stock = int(new_stock)
            if new_stock < 0:
                return jsonify({
                    'success': False,
                    'error': 'El stock no puede ser negativo'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'El stock debe ser un número entero'
            }), 400
        
        # Buscar el producto
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Producto no encontrado'
            }), 404
        
        # Obtener stock actual
        old_stock_value = product.get_meta('_stock')
        old_stock = int(old_stock_value) if old_stock_value else 0
        
        # Si no cambió nada, no hacer nada
        if old_stock == new_stock:
            return jsonify({
                'success': True,
                'message': 'No hubo cambios en el stock',
                'old_stock': old_stock,
                'new_stock': new_stock
            })
        
        # Actualizar el stock
        product.set_meta('_stock', new_stock)
        
        # Actualizar el estado de stock
        if new_stock > 0:
            product.set_meta('_stock_status', 'instock')
        else:
            product.set_meta('_stock_status', 'outofstock')
        
        # Asegurarse de que manage_stock esté activado
        product.set_meta('_manage_stock', 'yes')
        
        # Guardar en la base de datos
        db.session.commit()
        
        # Registrar en el historial
        change_amount = new_stock - old_stock
        history = StockHistory(
            product_id=product.ID,
            product_title=product.post_title,
            sku=product.get_meta('_sku') or 'N/A',
            old_stock=old_stock,
            new_stock=new_stock,
            change_amount=change_amount,
            changed_by='admin',  # Por ahora, luego lo haremos dinámico
            change_reason=reason
        )
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Stock actualizado de {old_stock} a {new_stock}',
            'product_id': product.ID,
            'product_title': product.post_title,
            'old_stock': old_stock,
            'new_stock': new_stock,
            'change_amount': change_amount
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/update-multiple', methods=['POST'])
def update_multiple_stock():
    """
    Actualizar stock de múltiples productos a la vez
    
    URL: POST http://localhost:5000/stock/update-multiple
    
    JSON Body:
    {
        "products": [
            {"id": 123, "stock": 50},
            {"id": 124, "stock": 30}
        ],
        "reason": "Recepción de mercancía"
    }
    """
    try:
        from app.models import StockHistory
        
        # Obtener datos
        data = request.get_json()
        products_data = data.get('products', [])
        reason = data.get('reason', 'Actualización masiva')
        
        if not products_data:
            return jsonify({
                'success': False,
                'error': 'No se enviaron productos para actualizar'
            }), 400
        
        updated = []
        errors = []
        
        # Procesar cada producto
        for item in products_data:
            product_id = item.get('id')
            new_stock = item.get('stock')
            
            try:
                # Validar
                if not product_id or new_stock is None:
                    errors.append({
                        'id': product_id,
                        'error': 'ID o stock faltante'
                    })
                    continue
                
                new_stock = int(new_stock)
                if new_stock < 0:
                    errors.append({
                        'id': product_id,
                        'error': 'Stock no puede ser negativo'
                    })
                    continue
                
                # Buscar producto
                product = Product.query.get(product_id)
                if not product:
                    errors.append({
                        'id': product_id,
                        'error': 'Producto no encontrado'
                    })
                    continue
                
                # Obtener stock actual
                old_stock_value = product.get_meta('_stock')
                old_stock = int(old_stock_value) if old_stock_value else 0
                
                # Actualizar
                product.set_meta('_stock', new_stock)
                
                if new_stock > 0:
                    product.set_meta('_stock_status', 'instock')
                else:
                    product.set_meta('_stock_status', 'outofstock')
                
                product.set_meta('_manage_stock', 'yes')
                
                # Registrar en historial
                change_amount = new_stock - old_stock
                history = StockHistory(
                    product_id=product.ID,
                    product_title=product.post_title,
                    sku=product.get_meta('_sku') or 'N/A',
                    old_stock=old_stock,
                    new_stock=new_stock,
                    change_amount=change_amount,
                    changed_by='admin',
                    change_reason=reason
                )
                db.session.add(history)
                
                updated.append({
                    'id': product.ID,
                    'title': product.post_title,
                    'old_stock': old_stock,
                    'new_stock': new_stock
                })
                
            except Exception as e:
                errors.append({
                    'id': product_id,
                    'error': str(e)
                })
        
        # Guardar todos los cambios
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(updated)} productos actualizados',
            'updated': updated,
            'errors': errors,
            'total_updated': len(updated),
            'total_errors': len(errors)
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/history/<int:product_id>')
def product_history(product_id):
    """
    Obtener historial de cambios de un producto
    
    URL: http://localhost:5000/stock/history/123
    """
    try:
        from app.models import StockHistory
        
        # Obtener historial ordenado por fecha (más reciente primero)
        history = StockHistory.query.filter_by(
            product_id=product_id
        ).order_by(StockHistory.created_at.desc()).limit(50).all()
        
        history_list = []
        for record in history:
            history_list.append({
                'id': record.id,
                'old_stock': record.old_stock,
                'new_stock': record.new_stock,
                'change_amount': record.change_amount,
                'changed_by': record.changed_by,
                'reason': record.change_reason,
                'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'history': history_list,
            'total': len(history_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500