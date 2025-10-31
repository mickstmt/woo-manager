# app/routes/products.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required
from app.models import Product, ProductMeta
from app import db, cache
from sqlalchemy import or_

# Crear el blueprint
bp = Blueprint('products', __name__, url_prefix='/products')


@bp.route('/')
@login_required
def index():
    """
    Ruta principal de productos
    Muestra la lista de todos los productos con paginación
    
    URL: http://localhost:5000/products/
    """
    return render_template('products.html', title='Gestión de Productos')


@bp.route('/list')
@login_required
@cache.cached(timeout=180, query_string=True)  # Cache 3 min basado en parámetros URL
def list_products():
    """
    Ruta para obtener lista de productos en formato JSON con paginación
    
    Comportamiento simple:
    - Sin búsqueda: Muestra últimos productos padre creados
    - Con búsqueda: Busca en productos padre Y variaciones (muestra padre si encuentra variación)
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
        
        # ========================================
        # CASO 1: Con búsqueda
        # ========================================
        if search and search.strip() != '':
            status_filter = f"AND p.post_status = '{status}'" if status else "AND p.post_status = 'publish'"
            
            # Buscar en productos padre por título, ID o SKU
            parent_query = text(f"""
                SELECT DISTINCT p.ID
                FROM wpyz_posts p
                LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sku'
                WHERE p.post_type = 'product'
                {status_filter}
                AND (
                    p.post_title LIKE :search
                    OR p.ID LIKE :search
                    OR pm.meta_value LIKE :search
                )
            """)
            
            parent_result = db.session.execute(parent_query, {'search': f'%{search}%'})
            parent_ids = [row[0] for row in parent_result]
            
            # Buscar en variaciones por SKU, título o ID del padre
            variation_query = text(f"""
                SELECT DISTINCT v.post_parent
                FROM wpyz_posts v
                LEFT JOIN wpyz_postmeta vm ON v.ID = vm.post_id AND vm.meta_key = '_sku'
                WHERE v.post_type = 'product_variation'
                AND v.post_parent != 0
                AND (
                    v.post_title LIKE :search
                    OR v.ID LIKE :search
                    OR vm.meta_value LIKE :search
                    OR v.post_parent LIKE :search
                )
            """)
            
            variation_result = db.session.execute(variation_query, {'search': f'%{search}%'})
            parent_ids_from_variations = [row[0] for row in variation_result if row[0]]
            
            # Combinar todos los IDs de productos padre (sin duplicados)
            all_parent_ids = list(set(parent_ids + parent_ids_from_variations))
            
            if not all_parent_ids:
                # No se encontró nada
                return jsonify({
                    'success': True,
                    'products': [],
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
            
            # Obtener productos padre
            total_products = len(all_parent_ids)
            
            # Aplicar paginación manualmente
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_ids = all_parent_ids[start_idx:end_idx]
            
            products_items = Product.query.filter(Product.ID.in_(paginated_ids)).order_by(Product.ID.desc()).all()
            
            # Calcular páginas
            import math
            total_pages = math.ceil(total_products / per_page) if total_products > 0 else 1
            has_prev = page > 1
            has_next = page < total_pages
            prev_num = page - 1 if has_prev else None
            next_num = page + 1 if has_next else None
            
        # ========================================
        # CASO 2: Sin búsqueda (mostrar últimos productos padre)
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
            has_prev = products.has_prev
            has_next = products.has_next
            prev_num = products.prev_num
            next_num = products.next_num
        
        # ========================================
        # Procesar productos padre - OPTIMIZADO
        # ========================================
        product_ids = [p.ID for p in products_items]

        # Contar variaciones de todos los productos en UNA SOLA consulta
        from sqlalchemy import func
        variations_query = db.session.query(
            Product.post_parent,
            func.count(Product.ID).label('count')
        ).filter(
            Product.post_type == 'product_variation',
            Product.post_parent.in_(product_ids)
        ).group_by(Product.post_parent).all()

        # Crear diccionario para búsqueda rápida
        variations_dict = {row[0]: row[1] for row in variations_query}

        # ========================================
        # OPTIMIZACIÓN: Eager load de metadatos en 1 query
        # ========================================
        # Obtener TODOS los metadatos necesarios de todos los productos en UNA sola consulta
        meta_keys = ['_sku', '_price', '_stock', '_stock_status', '_thumbnail_id']

        all_meta = db.session.query(
            ProductMeta.post_id,
            ProductMeta.meta_key,
            ProductMeta.meta_value
        ).filter(
            ProductMeta.post_id.in_(product_ids),
            ProductMeta.meta_key.in_(meta_keys)
        ).all()

        # Crear diccionario anidado: {product_id: {meta_key: meta_value}}
        meta_dict = {}
        for post_id, meta_key, meta_value in all_meta:
            if post_id not in meta_dict:
                meta_dict[post_id] = {}
            meta_dict[post_id][meta_key] = meta_value

        # Convertir a formato JSON
        products_list = []
        for product in products_items:
            # Obtener metadatos del diccionario (sin queries adicionales)
            product_meta = meta_dict.get(product.ID, {})
            sku = product_meta.get('_sku', 'N/A')
            price = product_meta.get('_price', '0')
            stock = product_meta.get('_stock', 'N/A')
            stock_status = product_meta.get('_stock_status', 'instock')
            thumbnail_id = product_meta.get('_thumbnail_id')

            # Obtener cantidad de variaciones del diccionario
            variations_count = variations_dict.get(product.ID, 0)

            # Determinar tipo de producto
            is_variable = variations_count > 0
            product_type = 'variable' if is_variable else 'simple'

            # Obtener URL de imagen (usando thumbnail_id del diccionario para evitar query)
            image_url = None
            if thumbnail_id:
                try:
                    image_query = text("""
                        SELECT meta_value
                        FROM wpyz_postmeta
                        WHERE post_id = :image_id
                        AND meta_key = '_wp_attached_file'
                        LIMIT 1
                    """)
                    result = db.session.execute(image_query, {'image_id': int(thumbnail_id)})
                    row = result.fetchone()
                    if row and row[0]:
                        base_url = 'https://www.izistoreperu.com/wp-content/uploads/'
                        image_url = base_url + row[0]
                except:
                    image_url = None

            products_list.append({
                'id': product.ID,
                'title': product.post_title,
                'status': product.post_status,
                'type': product_type,
                'sku': sku,
                'price': price,
                'stock': stock,
                'stock_status': stock_status,
                'is_variable': is_variable,
                'variations_count': variations_count,
                'image_url': image_url,
                'date': product.post_date.strftime('%Y-%m-%d %H:%M:%S') if product.post_date else None
            })
        
        return jsonify({
            'success': True,
            'products': products_list,
            'search_term': search if search else '',
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_products,
                'pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_num': prev_num,
                'next_num': next_num
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
@login_required
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
@login_required
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
@login_required
def view_product(product_id):
    """
    Ver detalles completos de un producto
    
    URL: /products/123
    """
    try:
        # Obtener el producto
        product = Product.query.get(product_id)
        
        if not product:
            flash('Producto no encontrado.', 'danger')
            return redirect(url_for('products.index'))
        
        # Obtener metadatos importantes
        product_data = {
            'id': product.ID,
            'title': product.post_title,
            'status': product.post_status,
            'type': product.post_type,
            'description': product.post_content,
            'short_description': product.post_excerpt,
            'created_at': product.post_date,
            'modified_at': product.post_modified,
            
            # Metadatos
            'sku': product.get_meta('_sku') or 'N/A',
            'regular_price': product.get_meta('_regular_price') or '0',
            'sale_price': product.get_meta('_sale_price') or '',
            'price': product.get_meta('_price') or '0',
            'stock': product.get_meta('_stock') or '0',
            'stock_status': product.get_meta('_stock_status') or 'outofstock',
            'manage_stock': product.get_meta('_manage_stock') or 'no',
            'backorders': product.get_meta('_backorders') or 'no',
            'sold_individually': product.get_meta('_sold_individually') or 'no',
            
            # Dimensiones
            'weight': product.get_meta('_weight') or '',
            'length': product.get_meta('_length') or '',
            'width': product.get_meta('_width') or '',
            'height': product.get_meta('_height') or '',
            
            # Imagen
            'image_url': product.get_image_url(),
            
            # Producto padre (si es variación)
            'parent_id': product.post_parent
        }
        
        # Si es variación, obtener el producto padre
        parent_product = None
        if product.post_type == 'product_variation' and product.post_parent:
            parent_product = Product.query.get(product.post_parent)
        
        # Si es producto variable, obtener variaciones
        variations = []
        if product.post_type == 'product':
            variations_query = Product.query.filter_by(
                post_type='product_variation',
                post_parent=product.ID
            ).all()
            
            for var in variations_query:
                variations.append({
                    'id': var.ID,
                    'title': var.post_title,
                    'sku': var.get_meta('_sku') or 'N/A',
                    'price': var.get_meta('_price') or '0',
                    'stock': var.get_meta('_stock') or '0',
                    'stock_status': var.get_meta('_stock_status') or 'outofstock',
                    'image_url': var.get_image_url()
                })
        
        # Obtener categorías
        from sqlalchemy import text
        categories_query = text("""
            SELECT t.name, t.slug
            FROM wpyz_term_relationships tr
            JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            JOIN wpyz_terms t ON tt.term_id = t.term_id
            WHERE tr.object_id = :product_id
            AND tt.taxonomy = 'product_cat'
        """)
        
        categories_result = db.session.execute(categories_query, {'product_id': product_id})
        categories = [{'name': row[0], 'slug': row[1]} for row in categories_result]
        
        # Obtener historial de stock
        from app.models import StockHistory
        stock_history = StockHistory.query.filter_by(
            product_id=product_id
        ).order_by(StockHistory.created_at.desc()).limit(10).all()
        
        return render_template(
            'products/view.html',
            product=product_data,
            parent_product=parent_product,
            variations=variations,
            categories=categories,
            stock_history=stock_history
        )
        
    except Exception as e:
        import traceback
        print("Error al ver producto:")
        print(traceback.format_exc())
        flash(f'Error al cargar el producto: {str(e)}', 'danger')
        return redirect(url_for('products.index'))


@bp.route('/export-excel')
@login_required
def export_excel():
    """
    Exportar productos a Excel con filtros de fecha y título

    Parámetros GET:
    - date_from: Fecha desde (YYYY-MM-DD) - obligatorio
    - date_to: Fecha hasta (YYYY-MM-DD) - obligatorio
    - title: Filtro de título (opcional)

    Columnas del Excel:
    ID | Título | SKU | [Atributos dinámicos] | ID Padre | Descripción Corta |
    Descripción Larga | Precio Regular | Precio Oferta | URL Imagen | Stock
    """
    try:
        from datetime import datetime, timedelta
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        from flask import make_response
        from io import BytesIO

        # Obtener parámetros
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        title_filter = request.args.get('title', '').strip()

        # Validar parámetros obligatorios
        if not date_from_str or not date_to_str:
            return jsonify({
                'success': False,
                'error': 'Los parámetros date_from y date_to son obligatorios'
            }), 400

        # Convertir fechas
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            # Agregar 23:59:59 a date_to para incluir todo el día
            date_to = date_to.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de fecha inválido. Usa YYYY-MM-DD'
            }), 400

        # PASO 1: Consultar productos del rango de fechas
        query = db.session.query(Product).filter(
            Product.post_type.in_(['product', 'product_variation']),
            Product.post_date >= date_from,
            Product.post_date <= date_to
        )

        # Filtrar por título si se especificó
        if title_filter:
            query = query.filter(Product.post_title.ilike(f'%{title_filter}%'))

        products = query.order_by(Product.post_date.desc()).all()

        if not products:
            return jsonify({
                'success': False,
                'error': f'No se encontraron productos entre {date_from_str} y {date_to_str}'
            }), 404

        # PASO 2: Obtener todos los IDs de productos
        product_ids = [p.ID for p in products]

        # PASO 2.5: Obtener IDs de productos padre para variantes
        parent_ids = set()
        for p in products:
            if p.post_type == 'product_variation' and p.post_parent > 0:
                parent_ids.add(p.post_parent)

        # Cargar productos padre que no están en la lista
        parent_products = {}
        if parent_ids:
            missing_parent_ids = parent_ids - set(product_ids)
            if missing_parent_ids:
                parents = db.session.query(Product).filter(
                    Product.ID.in_(list(missing_parent_ids))
                ).all()
                for parent in parents:
                    parent_products[parent.ID] = parent

        # PASO 3: Eager load de todos los metadatos
        meta_keys_base = ['_sku', '_price', '_regular_price', '_sale_price', '_stock',
                         '_stock_status', '_thumbnail_id', '_product_image_gallery']

        all_meta = db.session.query(
            ProductMeta.post_id,
            ProductMeta.meta_key,
            ProductMeta.meta_value
        ).filter(
            ProductMeta.post_id.in_(product_ids)
        ).all()

        # Crear diccionario de metadatos
        meta_dict = {}
        for post_id, meta_key, meta_value in all_meta:
            if post_id not in meta_dict:
                meta_dict[post_id] = {}
            meta_dict[post_id][meta_key] = meta_value

        # PASO 4: Detectar todos los atributos únicos (para columnas dinámicas)
        # Atributos específicos que queremos detectar
        known_attributes = ['color', 'conector', 'talla', 'medidas', 'medida']
        all_attributes = set()

        for post_id in product_ids:
            product_meta = meta_dict.get(post_id, {})
            for key in product_meta.keys():
                if key.startswith('attribute_pa_'):
                    # Extraer nombre del atributo (ej: attribute_pa_color -> color)
                    attr_slug = key.replace('attribute_pa_', '')
                    all_attributes.add(attr_slug)

        # Ordenar atributos alfabéticamente y capitalizar
        sorted_attributes = sorted(list(all_attributes))

        # PASO 4.5: Crear diccionario de términos (slug -> nombre legible)
        # Obtener todos los slugs de atributos únicos
        all_slugs = set()
        for post_id in product_ids:
            product_meta = meta_dict.get(post_id, {})
            for key, value in product_meta.items():
                if key.startswith('attribute_pa_') and value:
                    all_slugs.add(value)

        # Consultar nombres legibles desde wpyz_terms
        from sqlalchemy import text
        term_names = {}
        if all_slugs:
            # Convertir set a lista y crear placeholders
            slug_list = list(all_slugs)
            placeholders = ','.join([':slug' + str(i) for i in range(len(slug_list))])

            query = text(f"""
                SELECT slug, name
                FROM wpyz_terms
                WHERE slug IN ({placeholders})
            """)

            # Crear diccionario de parámetros
            params = {f'slug{i}': slug for i, slug in enumerate(slug_list)}

            result = db.session.execute(query, params)
            for row in result:
                term_names[row.slug] = row.name

        # PASO 5: Crear archivo Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Productos"

        # PASO 6: Crear encabezados
        headers = ['ID', 'Título', 'SKU']
        # Capitalizar nombres de atributos para headers
        headers.extend([attr.replace('_', ' ').title() for attr in sorted_attributes])
        headers.extend(['ID Padre', 'Descripción Corta', 'Descripción Larga',
                       'Precio Regular', 'Precio Oferta', 'URL Imagen', 'Stock'])

        # Escribir encabezados con estilo
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # PASO 7: Escribir datos de productos
        for row_num, product in enumerate(products, 2):
            product_meta = meta_dict.get(product.ID, {})

            col_num = 1

            # ID
            ws.cell(row=row_num, column=col_num, value=product.ID)
            col_num += 1

            # Título
            ws.cell(row=row_num, column=col_num, value=product.post_title)
            col_num += 1

            # SKU
            sku = product_meta.get('_sku', '')
            ws.cell(row=row_num, column=col_num, value=sku)
            col_num += 1

            # Atributos dinámicos
            for attr_slug in sorted_attributes:
                attr_key = 'attribute_pa_' + attr_slug
                attr_value_slug = product_meta.get(attr_key, '')

                # Convertir slug a nombre legible
                if attr_value_slug and attr_value_slug in term_names:
                    attr_value = term_names[attr_value_slug]
                else:
                    attr_value = attr_value_slug

                ws.cell(row=row_num, column=col_num, value=attr_value)
                col_num += 1

            # ID Padre
            parent_id = product.post_parent if product.post_parent > 0 else ''
            ws.cell(row=row_num, column=col_num, value=parent_id)
            col_num += 1

            # Descripción Corta y Larga
            # Para variantes, obtener del producto padre si está vacío
            desc_corta = product.post_excerpt or ''
            desc_larga = product.post_content or ''

            # Si es variante y no tiene descripciones, intentar obtener del padre
            if product.post_type == 'product_variation' and product.post_parent > 0:
                if not desc_corta or not desc_larga:
                    # Buscar padre en la lista de productos o en parent_products
                    padre = next((p for p in products if p.ID == product.post_parent), None)
                    if not padre and product.post_parent in parent_products:
                        padre = parent_products[product.post_parent]

                    if padre:
                        desc_corta = desc_corta or padre.post_excerpt or ''
                        desc_larga = desc_larga or padre.post_content or ''

            ws.cell(row=row_num, column=col_num, value=desc_corta)
            col_num += 1

            ws.cell(row=row_num, column=col_num, value=desc_larga)
            col_num += 1

            # Precio Regular
            regular_price = product_meta.get('_regular_price', '')
            ws.cell(row=row_num, column=col_num, value=regular_price)
            col_num += 1

            # Precio Oferta
            sale_price = product_meta.get('_sale_price', '')
            ws.cell(row=row_num, column=col_num, value=sale_price)
            col_num += 1

            # URL Imagen
            thumbnail_id = product_meta.get('_thumbnail_id', '')
            # TODO: Convertir ID de imagen a URL (requiere consulta adicional)
            ws.cell(row=row_num, column=col_num, value=thumbnail_id)
            col_num += 1

            # Stock
            stock = product_meta.get('_stock', '')
            ws.cell(row=row_num, column=col_num, value=stock)

        # PASO 8: Ajustar anchos de columnas
        for col_num in range(1, len(headers) + 1):
            column_letter = get_column_letter(col_num)
            max_length = len(str(headers[col_num - 1]))

            for row in ws.iter_rows(min_row=2, max_row=ws.max_row,
                                   min_col=col_num, max_col=col_num):
                for cell in row:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))

            # Limitar ancho máximo
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # PASO 9: Generar archivo en memoria
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # PASO 10: Crear respuesta HTTP
        filename = f'productos_{date_from_str}_{date_to_str}.xlsx'
        response = make_response(output.read())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500