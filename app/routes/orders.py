# app/routes/orders.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import Order, OrderAddress, OrderItem, OrderItemMeta, OrderMeta, Product, ProductMeta
from app import db
from datetime import datetime
from decimal import Decimal
from sqlalchemy import or_, desc
import pytz
import hashlib

bp = Blueprint('orders', __name__, url_prefix='/orders')


def get_gmt_time():
    """Obtener la hora actual en GMT/UTC como espera WooCommerce"""
    return datetime.utcnow()


def get_next_manager_order_number():
    """
    Obtener el siguiente número de pedido para manager (formato W-XXXXX)
    Almacena el contador en wpyz_options con la clave 'woocommerce_manager_order_number'

    Returns:
        str: Número de pedido en formato W-00001
    """
    from sqlalchemy import text

    option_name = 'woocommerce_manager_order_number'

    # Intentar obtener el contador actual
    get_counter = text("""
        SELECT option_value
        FROM wpyz_options
        WHERE option_name = :option_name
    """)
    result = db.session.execute(get_counter, {'option_name': option_name}).fetchone()

    if result:
        # Incrementar contador existente
        current_number = int(result[0])
        next_number = current_number + 1

        update_counter = text("""
            UPDATE wpyz_options
            SET option_value = :next_number
            WHERE option_name = :option_name
        """)
        db.session.execute(update_counter, {
            'next_number': str(next_number),
            'option_name': option_name
        })
    else:
        # Crear contador si no existe (empezar en 1)
        next_number = 1

        insert_counter = text("""
            INSERT INTO wpyz_options (option_name, option_value, autoload)
            VALUES (:option_name, :next_number, 'no')
        """)
        db.session.execute(insert_counter, {
            'option_name': option_name,
            'next_number': str(next_number)
        })

    db.session.commit()

    # Formatear como W-00001
    return f"W-{next_number:05d}"


@bp.route('/')
@login_required
def index():
    """
    Vista principal del módulo de pedidos (listado)

    URL: http://localhost:5000/orders/
    """
    return render_template('orders_list.html', title='Gestión de Pedidos')


@bp.route('/create')
@login_required
def create_page():
    """
    Página para crear nuevo pedido (Wizard de 3 pasos)

    URL: http://localhost:5000/orders/create
    """
    return render_template('orders_create.html', title='Crear Nuevo Pedido')


@bp.route('/list')
@login_required
def list_orders():
    """
    Listar pedidos creados por el manager con paginación y filtros

    Query params:
    - page: número de página
    - per_page: items por página
    - search: búsqueda por ID, email, nombre, W-XXXXX
    - created_by: filtrar por usuario creador
    """
    try:
        from sqlalchemy import text
        from app.models import User

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        created_by_filter = request.args.get('created_by', '', type=str)

        # Limitar per_page
        per_page = min(per_page, 100)

        # Query optimizada con JOIN a postmeta para filtrar solo pedidos del manager
        # IMPORTANTE: Solo mostramos pedidos que tienen _order_number (W-XXXXX)
        query = text("""
            SELECT DISTINCT
                o.id,
                o.status,
                o.total_amount,
                o.currency,
                o.billing_email,
                o.payment_method,
                o.payment_method_title,
                o.date_created_gmt,
                ba.first_name,
                ba.last_name,
                ba.phone,
                om_order_number.meta_value as order_number,
                om_created_by.meta_value as created_by,
                (SELECT COUNT(*) FROM wpyz_woocommerce_order_items WHERE order_id = o.id AND order_item_type = 'line_item') as items_count
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_order_number ON o.id = om_order_number.order_id AND om_order_number.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_orders_meta om_created_by ON o.id = om_created_by.order_id AND om_created_by.meta_key = '_created_by'
            LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id AND ba.address_type = 'billing'
            WHERE 1=1
            {search_filter}
            {created_by_filter}
            ORDER BY o.date_created_gmt DESC
            LIMIT :limit OFFSET :offset
        """)

        # Query para contar total de registros
        count_query = text("""
            SELECT COUNT(DISTINCT o.id)
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_order_number ON o.id = om_order_number.order_id AND om_order_number.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_orders_meta om_created_by ON o.id = om_created_by.order_id AND om_created_by.meta_key = '_created_by'
            LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id AND ba.address_type = 'billing'
            WHERE 1=1
            {search_filter}
            {created_by_filter}
        """)

        # Construir filtros dinámicos
        search_filter = ""
        created_by_filter_clause = ""
        params = {
            'limit': per_page,
            'offset': (page - 1) * per_page
        }

        if search:
            # Buscar por order_number (W-XXXXX), email, nombre, teléfono, ID
            search_filter = """
                AND (
                    om_order_number.meta_value LIKE :search
                    OR o.billing_email LIKE :search
                    OR ba.first_name LIKE :search
                    OR ba.last_name LIKE :search
                    OR ba.phone LIKE :search
                    OR CAST(o.id AS CHAR) LIKE :search
                )
            """
            params['search'] = f'%{search}%'

        if created_by_filter:
            created_by_filter_clause = "AND om_created_by.meta_value = :created_by"
            params['created_by'] = created_by_filter

        # Formatear queries con filtros
        final_query = query.text.format(
            search_filter=search_filter,
            created_by_filter=created_by_filter_clause
        )
        final_count_query = count_query.text.format(
            search_filter=search_filter,
            created_by_filter=created_by_filter_clause
        )

        # Ejecutar queries
        results = db.session.execute(text(final_query), params).fetchall()
        total_count = db.session.execute(text(final_count_query), params).fetchone()[0]

        # Calcular paginación
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None

        # Preparar datos
        orders_list = []
        for row in results:
            orders_list.append({
                'id': row[0],
                'status': row[1],
                'total': float(row[2]) if row[2] else 0,
                'currency': row[3] or 'PEN',
                'billing_email': row[4] or '',
                'payment_method': row[6] or row[5] or '',
                'customer_name': f"{row[8]} {row[9]}" if row[8] and row[9] else 'N/A',
                'customer_phone': row[10] or 'N/A',
                'order_number': row[11] or '',  # W-XXXXX
                'created_by': row[12] or 'N/A',  # Usuario que creó el pedido
                'items_count': row[13] or 0,
                'date_created': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else ''
            })

        return jsonify({
            'success': True,
            'orders': orders_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
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


@bp.route('/get-users')
@login_required
def get_users():
    """
    Obtener lista de usuarios que han creado pedidos en el manager

    Retorna lista de usuarios únicos que aparecen en _created_by
    """
    try:
        from sqlalchemy import text

        # Query para obtener usuarios únicos que han creado pedidos
        query = text("""
            SELECT DISTINCT meta_value as username
            FROM wpyz_wc_orders_meta
            WHERE meta_key = '_created_by'
            AND meta_value IS NOT NULL
            AND meta_value != ''
            ORDER BY meta_value
        """)

        results = db.session.execute(query).fetchall()

        users_list = [{'username': row[0]} for row in results]

        return jsonify({
            'success': True,
            'users': users_list
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/search-products')
@login_required
def search_products():
    """
    Buscar productos para agregar al pedido

    Query params:
    - q: término de búsqueda (SKU o nombre)
    """
    try:
        search_term = request.args.get('q', '', type=str)

        if not search_term or len(search_term) < 2:
            return jsonify({
                'success': True,
                'products': []
            })

        # Buscar productos simples y variaciones
        products_query = Product.query.filter(
            Product.post_status == 'publish',
            or_(
                Product.post_type == 'product',
                Product.post_type == 'product_variation'
            )
        )

        # Buscar por título o SKU
        from sqlalchemy import text
        sku_search = text("""
            SELECT DISTINCT post_id
            FROM wpyz_postmeta
            WHERE meta_key = '_sku'
            AND meta_value LIKE :search
        """)

        result = db.session.execute(sku_search, {'search': f'%{search_term}%'})
        product_ids_by_sku = [row[0] for row in result]

        # Combinar búsqueda por título y SKU
        products_query = products_query.filter(
            or_(
                Product.post_title.like(f'%{search_term}%'),
                Product.ID.in_(product_ids_by_sku)
            )
        )

        products = products_query.limit(10).all()

        # Preparar resultados
        products_list = []
        for product in products:
            sku = product.get_meta('_sku') or 'N/A'
            price = product.get_meta('_price') or '0'
            stock = product.get_meta('_stock') or '0'

            # Si es variación, obtener atributos
            variation_label = ''
            if product.post_type == 'product_variation':
                # Obtener nombre del producto padre
                parent = Product.query.get(product.post_parent)
                parent_name = parent.post_title if parent else ''

                # Obtener atributos de variación
                attributes = []
                for meta in product.product_meta:
                    if meta.meta_key.startswith('attribute_pa_'):
                        attr_name = meta.meta_key.replace('attribute_pa_', '').title()
                        attributes.append(f"{attr_name}: {meta.meta_value}")

                variation_label = f" ({', '.join(attributes)})" if attributes else ''
                product_name = f"{parent_name}{variation_label}"
            else:
                product_name = product.post_title

            products_list.append({
                'id': product.ID,
                'name': product_name,
                'sku': sku,
                'price': float(price),
                'stock': int(float(stock)),
                'type': product.post_type
            })

        return jsonify({
            'success': True,
            'products': products_list
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/get-categories')
@login_required
def get_categories():
    """
    Obtener árbol de categorías de productos

    Retorna categorías principales y subcategorías anidadas
    """
    try:
        from sqlalchemy import text
        from app.models import Term, TermTaxonomy

        # Obtener todas las categorías con productos
        query = text("""
            SELECT
                t.term_id,
                t.name,
                t.slug,
                tt.parent,
                tt.count
            FROM wpyz_terms t
            JOIN wpyz_term_taxonomy tt ON t.term_id = tt.term_id
            WHERE tt.taxonomy = 'product_cat'
            AND tt.count > 0
            ORDER BY tt.parent, t.name
        """)

        result = db.session.execute(query)
        categories = []
        category_dict = {}

        # Primera pasada: crear todas las categorías
        for row in result:
            cat = {
                'id': row[0],
                'name': row[1],
                'slug': row[2],
                'parent_id': row[3] or 0,
                'product_count': row[4],
                'children': []
            }
            category_dict[cat['id']] = cat

            if cat['parent_id'] == 0:
                categories.append(cat)

        # Segunda pasada: anidar subcategorías
        for cat_id, cat in category_dict.items():
            if cat['parent_id'] != 0 and cat['parent_id'] in category_dict:
                category_dict[cat['parent_id']]['children'].append(cat)

        return jsonify({
            'success': True,
            'categories': categories
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/get-products-by-category/<int:category_id>')
@login_required
def get_products_by_category(category_id):
    """
    Obtener productos de una categoría específica
    Solo productos principales (no variaciones)
    Optimizado con una sola query SQL
    """
    try:
        from sqlalchemy import text

        # Query optimizada: obtener productos con todos sus datos en una sola consulta
        query = text("""
            SELECT DISTINCT
                p.ID,
                p.post_title,
                MAX(CASE WHEN pm.meta_key = '_sku' THEN pm.meta_value END) AS sku,
                MAX(CASE WHEN pm.meta_key = '_price' THEN pm.meta_value END) AS price,
                MAX(CASE WHEN pm.meta_key = '_stock_status' THEN pm.meta_value END) AS stock_status,
                MAX(CASE WHEN pm.meta_key = '_thumbnail_id' THEN pm.meta_value END) AS thumbnail_id,
                (
                    SELECT COUNT(*)
                    FROM wpyz_posts pv
                    WHERE pv.post_parent = p.ID
                    AND pv.post_type = 'product_variation'
                    AND pv.post_status = 'publish'
                ) AS has_variations
            FROM wpyz_posts p
            JOIN wpyz_term_relationships tr ON p.ID = tr.object_id
            JOIN wpyz_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id
                AND pm.meta_key IN ('_sku', '_price', '_stock_status', '_thumbnail_id')
            WHERE tt.term_id = :category_id
            AND p.post_type = 'product'
            AND p.post_status = 'publish'
            GROUP BY p.ID, p.post_title
            ORDER BY p.post_title
        """)

        result = db.session.execute(query, {'category_id': category_id}).fetchall()

        if not result:
            return jsonify({
                'success': True,
                'products': []
            })

        # Obtener URLs de imágenes en batch si hay thumbnails
        thumbnail_ids = [row[5] for row in result if row[5]]
        image_urls = {}

        if thumbnail_ids:
            image_query = text("""
                SELECT pm.post_id, pm.meta_value
                FROM wpyz_postmeta pm
                WHERE pm.post_id IN :thumbnail_ids
                AND pm.meta_key = '_wp_attached_file'
            """)

            image_results = db.session.execute(
                image_query,
                {'thumbnail_ids': tuple(thumbnail_ids)}
            ).fetchall()

            # Construir URLs de imágenes
            for img_row in image_results:
                image_urls[str(img_row[0])] = f"https://www.izistoreperu.com/wp-content/uploads/{img_row[1]}"

        # Construir lista de productos
        products_list = []
        for row in result:
            product_id = row[0]
            thumbnail_id = row[5]

            products_list.append({
                'id': product_id,
                'name': row[1],
                'sku': row[2] or 'N/A',
                'price': float(row[3]) if row[3] else 0.0,
                'stock_status': row[4] or 'outofstock',
                'has_variations': row[6] > 0,
                'image_url': image_urls.get(str(thumbnail_id)) if thumbnail_id else None
            })

        return jsonify({
            'success': True,
            'products': products_list
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/get-variations/<int:product_id>')
@login_required
def get_variations(product_id):
    """
    Obtener todas las variaciones de un producto organizadas por atributos
    Optimizado con queries SQL en batch
    """
    try:
        from sqlalchemy import text

        # Query optimizada: obtener producto padre con sus metadatos
        parent_query = text("""
            SELECT
                p.ID,
                p.post_title,
                MAX(CASE WHEN pm.meta_key = '_price' THEN pm.meta_value END) AS price,
                MAX(CASE WHEN pm.meta_key = '_sku' THEN pm.meta_value END) AS sku,
                MAX(CASE WHEN pm.meta_key = '_stock' THEN pm.meta_value END) AS stock,
                MAX(CASE WHEN pm.meta_key = '_thumbnail_id' THEN pm.meta_value END) AS thumbnail_id
            FROM wpyz_posts p
            LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id
                AND pm.meta_key IN ('_price', '_sku', '_stock', '_thumbnail_id')
            WHERE p.ID = :product_id
            GROUP BY p.ID, p.post_title
        """)

        parent_result = db.session.execute(parent_query, {'product_id': product_id}).fetchone()

        if not parent_result:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

        # Query optimizada: obtener todas las variaciones con sus metadatos y atributos
        variations_query = text("""
            SELECT
                p.ID,
                p.post_title,
                MAX(CASE WHEN pm.meta_key = '_sku' THEN pm.meta_value END) AS sku,
                MAX(CASE WHEN pm.meta_key = '_price' THEN pm.meta_value END) AS price,
                MAX(CASE WHEN pm.meta_key = '_stock' THEN pm.meta_value END) AS stock,
                MAX(CASE WHEN pm.meta_key = '_stock_status' THEN pm.meta_value END) AS stock_status,
                MAX(CASE WHEN pm.meta_key = '_thumbnail_id' THEN pm.meta_value END) AS thumbnail_id,
                GROUP_CONCAT(
                    CASE
                        WHEN pm.meta_key LIKE 'attribute_%'
                        THEN CONCAT(pm.meta_key, ':', pm.meta_value)
                    END
                    SEPARATOR '||'
                ) AS attributes_raw
            FROM wpyz_posts p
            LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id
            WHERE p.post_parent = :product_id
            AND p.post_type = 'product_variation'
            AND p.post_status = 'publish'
            GROUP BY p.ID, p.post_title
            ORDER BY p.ID
        """)

        variations_result = db.session.execute(
            variations_query,
            {'product_id': product_id}
        ).fetchall()

        # Obtener todos los slugs únicos de atributos PA para buscar nombres en batch
        all_slugs = set()
        for var in variations_result:
            if var[7]:  # attributes_raw
                attrs = var[7].split('||')
                for attr in attrs:
                    if attr and ':' in attr:
                        key, value = attr.split(':', 1)
                        if key.startswith('attribute_pa_'):
                            all_slugs.add(value)

        # Obtener nombres de términos en batch
        slug_to_name = {}
        if all_slugs:
            terms_query = text("""
                SELECT slug, name
                FROM wpyz_terms
                WHERE slug IN :slugs
            """)
            terms_result = db.session.execute(
                terms_query,
                {'slugs': tuple(all_slugs)}
            ).fetchall()
            slug_to_name = {row[0]: row[1] for row in terms_result}

        # Obtener URLs de imágenes en batch
        thumbnail_ids = [var[6] for var in variations_result if var[6]]
        if parent_result[5]:
            thumbnail_ids.append(parent_result[5])

        image_urls = {}
        if thumbnail_ids:
            image_query = text("""
                SELECT pm.post_id, pm.meta_value
                FROM wpyz_postmeta pm
                WHERE pm.post_id IN :thumbnail_ids
                AND pm.meta_key = '_wp_attached_file'
            """)
            image_results = db.session.execute(
                image_query,
                {'thumbnail_ids': tuple(thumbnail_ids)}
            ).fetchall()

            for img_row in image_results:
                image_urls[str(img_row[0])] = f"https://www.izistoreperu.com/wp-content/uploads/{img_row[1]}"

        # Procesar variaciones
        attributes_map = {}
        variations_list = []

        for var in variations_result:
            # Parsear atributos
            attributes = {}
            if var[7]:  # attributes_raw
                attrs = var[7].split('||')
                for attr in attrs:
                    if attr and ':' in attr:
                        key, value = attr.split(':', 1)

                        if key.startswith('attribute_pa_'):
                            attr_name = key.replace('attribute_pa_', '').replace('_', ' ').title()
                            attr_value = slug_to_name.get(value, value)
                        elif key.startswith('attribute_'):
                            attr_name = key.replace('attribute_', '').replace('_', ' ').title()
                            attr_value = value
                        else:
                            continue

                        attributes[attr_name] = attr_value

                        if attr_name not in attributes_map:
                            attributes_map[attr_name] = set()
                        attributes_map[attr_name].add(attr_value)

            variations_list.append({
                'id': var[0],
                'name': var[1],
                'sku': var[2] or 'N/A',
                'price': float(var[3]) if var[3] else 0.0,
                'stock': int(float(var[4])) if var[4] else 0,
                'stock_status': var[5] or 'outofstock',
                'attributes': attributes,
                'image_url': image_urls.get(str(var[6])) if var[6] else None
            })

        # Convertir sets a listas ordenadas
        available_attributes = {}
        for attr_name, values in attributes_map.items():
            available_attributes[attr_name] = sorted(list(values))

        return jsonify({
            'success': True,
            'parent': {
                'id': parent_result[0],
                'name': parent_result[1],
                'image_url': image_urls.get(str(parent_result[5])) if parent_result[5] else None,
                'price': float(parent_result[2]) if parent_result[2] else 0.0,
                'sku': parent_result[3] or 'N/A',
                'stock': int(float(parent_result[4])) if parent_result[4] else 0
            },
            'available_attributes': available_attributes,
            'variations': variations_list
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/save-order', methods=['POST'])
@login_required
def create_order():
    """
    Crear un nuevo pedido manualmente (ventas por WhatsApp)

    JSON Body:
    {
        "customer": {
            "first_name": "Juan",
            "last_name": "Pérez",
            "email": "juan@example.com",
            "phone": "987654321",
            "company": "12345678",  # DNI/CE
            "billing_ruc": "20123456789",  # Opcional
            "billing_entrega": "billing_domicilio",  # billing_domicilio | billing_agencia | billing_recojo
            "billing_referencia": "Frente al parque",  # Opcional
            "address_1": "Av. Principal 123",
            "city": "Lima",
            "state": "Lima",
            "postcode": "15001",
            "country": "PE"
        },
        "items": [
            {
                "product_id": 123,
                "variation_id": 456,  # opcional
                "quantity": 2,
                "price": 50.00  # Precio CON IGV incluido
            }
        ],
        "shipping_cost": 15.00,  # Costo de envío
        "payment_method": "cod",
        "payment_method_title": "Yape",
        "customer_note": "Cliente contactó por WhatsApp"
    }
    """
    try:
        data = request.get_json()

        # Validar datos
        if not data.get('customer'):
            return jsonify({'success': False, 'error': 'Datos del cliente requeridos'}), 400

        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'success': False, 'error': 'Debe agregar al menos un producto'}), 400

        customer = data['customer']
        items_data = data['items']
        shipping_cost = Decimal(str(data.get('shipping_cost', 0)))

        # DEBUG: Log customer data para verificar qué se está recibiendo
        current_app.logger.info(f"Creating order with customer data: {customer}")

        # ===== CALCULAR TOTALES =====
        # Los precios INCLUYEN IGV (18%)
        # Fórmula: precio_sin_igv = precio_con_igv / 1.18

        total_with_tax = Decimal('0')

        # Sumar productos
        for item_data in items_data:
            item_price_with_tax = Decimal(str(item_data['price'])) * item_data['quantity']
            total_with_tax += item_price_with_tax

        # Sumar envío
        total_with_tax += shipping_cost

        # Calcular subtotal e IGV
        subtotal = total_with_tax / Decimal('1.18')
        tax_amount = total_with_tax - subtotal

        # ===== CREAR PEDIDO =====
        order = Order(
            status='wc-processing',  # Estado inicial
            currency='PEN',
            type='shop_order',
            tax_amount=tax_amount,
            total_amount=total_with_tax,
            customer_id=0,  # Sin cuenta de usuario
            billing_email=customer.get('email'),
            date_created_gmt=get_gmt_time(),
            date_updated_gmt=get_gmt_time(),
            payment_method=data.get('payment_method', 'cod'),
            payment_method_title=data.get('payment_method_title', 'Pago manual'),
            customer_note=data.get('customer_note', ''),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )

        db.session.add(order)
        db.session.flush()  # Para obtener el ID del pedido

        # ===== GENERAR NÚMERO DE PEDIDO W-XXXXX =====
        # Genera un número único de pedido en formato W-00001 para identificar
        # pedidos creados por el manager y evitar conflictos con IDs naturales
        manager_order_number = get_next_manager_order_number()
        current_app.logger.info(f"Generated manager order number: {manager_order_number} for order ID {order.id}")

        # ===== REGISTRO EN WPYZ_POSTS (CRÍTICO para compatibilidad HPOS) =====
        # WooCommerce HPOS requiere sincronización con wpyz_posts para plugins antiguos
        # IMPORTANTE: Verificar si el ID ya existe antes de insertar para evitar
        # duplicados por race conditions con pedidos naturales del sitio
        from sqlalchemy import text

        # Verificar si el ID ya existe en wpyz_posts
        check_post_exists = text("""
            SELECT ID FROM wpyz_posts WHERE ID = :order_id
        """)
        existing_post = db.session.execute(check_post_exists, {'order_id': order.id}).fetchone()

        if not existing_post:
            # El ID no existe, podemos insertar de manera segura
            insert_post = text("""
                INSERT INTO wpyz_posts (
                    ID, post_author, post_date, post_date_gmt, post_content, post_title,
                    post_excerpt, post_status, comment_status, ping_status, post_password,
                    post_name, to_ping, pinged, post_modified, post_modified_gmt,
                    post_content_filtered, post_parent, guid, menu_order, post_type, post_mime_type, comment_count
                ) VALUES (
                    :order_id, 1, :post_date, :post_date_gmt, '', :post_title,
                    '', :post_status, 'open', 'closed', '',
                    :post_name, '', '', :post_modified, :post_modified_gmt,
                    '', 0, '', 0, 'shop_order', '', 0
                )
            """)

            current_time = get_gmt_time()
            # Usar W-XXXXX en lugar del ID para identificar pedidos del manager
            post_title = f"Pedido {manager_order_number} &ndash; {current_time.strftime('%B %d, %Y @ %I:%M %p')}"
            post_name = f"order-{manager_order_number.lower()}-{current_time.strftime('%b-%d-%Y').lower()}"

            db.session.execute(insert_post, {
                'order_id': order.id,
                'post_date': current_time,
                'post_date_gmt': current_time,
                'post_title': post_title,
                'post_status': order.status,  # wc-processing, wc-pending, etc.
                'post_name': post_name,
                'post_modified': current_time,
                'post_modified_gmt': current_time
            })
            current_app.logger.info(f"Inserted order {order.id} into wpyz_posts with title: {post_title}")
        else:
            # El ID ya existe (race condition con pedido natural)
            # No insertamos en wpyz_posts, pero el pedido seguirá funcionando con postmeta
            current_app.logger.warning(f"Order ID {order.id} already exists in wpyz_posts (race condition detected). Skipping wpyz_posts insert. Order will rely on postmeta only.")

        # ===== DIRECCIONES =====
        # IMPORTANTE: WooCommerce NO tiene HPOS habilitado, usa el sistema antiguo (postmeta)
        # Guardamos en ambos sistemas para compatibilidad total

        # 1. Guardar en wpyz_wc_order_addresses (HPOS - para compatibilidad futura)
        billing_address = OrderAddress(
            order_id=order.id,
            address_type='billing',
            first_name=customer.get('first_name'),
            last_name=customer.get('last_name'),
            company=customer.get('company', ''),  # DNI/CE
            address_1=customer.get('address_1'),
            address_2=customer.get('address_2', ''),
            city=customer.get('city'),
            state=customer.get('state'),
            postcode=customer.get('postcode', ''),
            country=customer.get('country', 'PE'),
            email=customer.get('email'),
            phone=customer.get('phone')
        )
        db.session.add(billing_address)

        shipping_address = OrderAddress(
            order_id=order.id,
            address_type='shipping',
            first_name=customer.get('first_name'),
            last_name=customer.get('last_name'),
            company=customer.get('company', ''),
            address_1=customer.get('address_1'),
            address_2=customer.get('address_2', ''),
            city=customer.get('city'),
            state=customer.get('state'),
            postcode=customer.get('postcode', ''),
            country=customer.get('country', 'PE'),
            email=customer.get('email'),
            phone=customer.get('phone')
        )
        db.session.add(shipping_address)

        # 2. Guardar en wpyz_postmeta (Sistema antiguo - lo que WooCommerce está leyendo AHORA)
        address_meta_fields = [
            # Billing
            ('_billing_first_name', customer.get('first_name', '')),
            ('_billing_last_name', customer.get('last_name', '')),
            ('_billing_company', customer.get('company', '')),
            ('_billing_address_1', customer.get('address_1', '')),
            ('_billing_address_2', customer.get('address_2', '')),
            ('_billing_city', customer.get('city', '')),
            ('_billing_state', customer.get('state', '')),
            ('_billing_postcode', customer.get('postcode', '')),
            ('_billing_country', customer.get('country', 'PE')),
            ('_billing_email', customer.get('email', '')),
            ('_billing_phone', customer.get('phone', '')),
            # Shipping (mismos datos)
            ('_shipping_first_name', customer.get('first_name', '')),
            ('_shipping_last_name', customer.get('last_name', '')),
            ('_shipping_company', customer.get('company', '')),
            ('_shipping_address_1', customer.get('address_1', '')),
            ('_shipping_address_2', customer.get('address_2', '')),
            ('_shipping_city', customer.get('city', '')),
            ('_shipping_state', customer.get('state', '')),
            ('_shipping_postcode', customer.get('postcode', '')),
            ('_shipping_country', customer.get('country', 'PE')),
        ]

        for meta_key, meta_value in address_meta_fields:
            insert_address_meta = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:post_id, :meta_key, :meta_value)
            """)
            db.session.execute(insert_address_meta, {
                'post_id': order.id,
                'meta_key': meta_key,
                'meta_value': str(meta_value)
            })

        # ===== ITEMS DEL PEDIDO =====
        items_subtotal = Decimal('0')
        items_tax = Decimal('0')

        for item_data in items_data:
            product_id = item_data['product_id']
            variation_id = item_data.get('variation_id', 0)
            quantity = item_data['quantity']
            price_with_tax = Decimal(str(item_data['price']))

            # Obtener producto
            if variation_id:
                product = Product.query.get(variation_id)
            else:
                product = Product.query.get(product_id)

            if not product:
                raise Exception(f'Producto {product_id} no encontrado')

            # Calcular subtotal e impuestos del item (precio incluye IGV)
            line_total_with_tax = price_with_tax * quantity
            line_subtotal = line_total_with_tax / Decimal('1.18')
            line_tax = line_total_with_tax - line_subtotal

            items_subtotal += line_subtotal
            items_tax += line_tax

            # Crear item
            order_item = OrderItem(
                order_item_name=product.post_title,
                order_item_type='line_item',
                order_id=order.id
            )
            db.session.add(order_item)
            db.session.flush()

            # Agregar metadatos del item
            # Crear estructura de _line_tax_data (serializado PHP)
            line_tax_data = f'a:2:{{s:5:"total";a:1:{{i:1;s:{len(str(line_tax.quantize(Decimal("0.01"))))}:"{line_tax.quantize(Decimal("0.01"))}";}}s:8:"subtotal";a:1:{{i:1;s:{len(str(line_tax.quantize(Decimal("0.01"))))}:"{line_tax.quantize(Decimal("0.01"))}";}}}}'

            item_metas = [
                ('_product_id', product_id),
                ('_variation_id', variation_id),
                ('_qty', quantity),
                ('_line_subtotal', str(line_subtotal.quantize(Decimal('0.01')))),
                ('_line_subtotal_tax', str(line_tax.quantize(Decimal('0.01')))),
                ('_line_total', str(line_subtotal.quantize(Decimal('0.01')))),
                ('_line_tax', str(line_tax.quantize(Decimal('0.01')))),
                ('_line_tax_data', line_tax_data),  # Desglose de impuestos serializado
                ('_tax_class', ''),
                ('_reduced_stock', quantity),  # Cantidad de stock reducida
            ]

            for meta_key, meta_value in item_metas:
                item_meta = OrderItemMeta(
                    order_item_id=order_item.order_item_id,
                    meta_key=meta_key,
                    meta_value=str(meta_value)
                )
                db.session.add(item_meta)

            # Reducir stock del producto correcto
            target_product = Product.query.get(variation_id if variation_id else product_id)
            if target_product:
                stock_meta = target_product.product_meta.filter_by(meta_key='_stock').first()
                if stock_meta:
                    current_stock = int(float(stock_meta.meta_value))
                    new_stock = max(0, current_stock - quantity)
                    stock_meta.meta_value = str(new_stock)

                    # Actualizar estado de stock
                    if new_stock == 0:
                        stock_status_meta = target_product.product_meta.filter_by(meta_key='_stock_status').first()
                        if stock_status_meta:
                            stock_status_meta.meta_value = 'outofstock'

        # ===== ITEM DE ENVÍO =====
        if shipping_cost > 0:
            shipping_subtotal = shipping_cost / Decimal('1.18')
            shipping_tax = shipping_cost - shipping_subtotal

            # Mapear billing_entrega a nombres legibles para WooCommerce
            billing_entrega = customer.get('billing_entrega', 'billing_domicilio')
            shipping_method_names = {
                'billing_agencia': 'En Agencia Shalom/Olva Courier',
                'billing_domicilio': 'Entrega a Domicilio',
                'billing_recojo': 'Recojo en Almacén'
            }
            shipping_method_name = shipping_method_names.get(billing_entrega, 'Envío')

            shipping_item = OrderItem(
                order_item_name=shipping_method_name,  # Usar nombre específico del método
                order_item_type='shipping',
                order_id=order.id
            )
            db.session.add(shipping_item)
            db.session.flush()

            shipping_metas = [
                ('method_id', 'advanced_shipping'),  # Cambiado de 'flat_rate' a 'advanced_shipping'
                ('cost', str(shipping_subtotal.quantize(Decimal('0.01')))),
                ('instance_id', '0'),  # Agregar instance_id
                ('total_tax', str(shipping_tax.quantize(Decimal('0.01')))),
                ('taxes', 'a:1:{s:1:"1";s:4:"' + str(shipping_tax.quantize(Decimal('0.01'))) + '";}'),
            ]

            for meta_key, meta_value in shipping_metas:
                shipping_meta = OrderItemMeta(
                    order_item_id=shipping_item.order_item_id,
                    meta_key=meta_key,
                    meta_value=str(meta_value)
                )
                db.session.add(shipping_meta)
        else:
            shipping_subtotal = Decimal('0')
            shipping_tax = Decimal('0')

        # ===== ITEM DE IMPUESTO (TAX) =====
        # WooCommerce requiere un item separado para los impuestos totales
        total_tax_amount = items_tax + shipping_tax
        if total_tax_amount > 0:
            tax_item = OrderItem(
                order_item_name='PE-IMPUESTO-1',  # Nombre del impuesto en Perú
                order_item_type='tax',
                order_id=order.id
            )
            db.session.add(tax_item)
            db.session.flush()

            # Metadatos del item de impuesto (coinciden con estructura de WooCommerce)
            tax_metas = [
                ('rate_id', '1'),  # ID de la tasa de impuesto (IGV)
                ('label', 'Impuesto'),  # Etiqueta visible
                ('compound', ''),  # No es compuesto
                ('tax_amount', str(items_tax.quantize(Decimal('0.01')))),  # Impuesto de productos
                ('shipping_tax_amount', str(shipping_tax.quantize(Decimal('0.01')))),  # Impuesto de envío
                ('rate_percent', '18'),  # IGV es 18%
                ('_wcpdf_rate_percentage', '18.00'),  # Para plugin PDF
                ('_wcpdf_ubl_tax_category', 'S'),  # Categoría para facturación electrónica
                ('_wcpdf_ubl_tax_reason', ''),
                ('_wcpdf_ubl_tax_scheme', 'VAT'),  # Esquema de impuesto
            ]

            for meta_key, meta_value in tax_metas:
                tax_meta = OrderItemMeta(
                    order_item_id=tax_item.order_item_id,
                    meta_key=meta_key,
                    meta_value=str(meta_value)
                )
                db.session.add(tax_meta)

        # ===== METADATOS DEL PEDIDO =====
        # Construir índices de direcciones para búsqueda
        # DEBUG: Log customer data antes de construir billing_index
        current_app.logger.info(f"Building billing_index with customer: {customer}")

        billing_index = f"{customer.get('first_name', '')} {customer.get('last_name', '')} {customer.get('company', '')} {customer.get('address_1', '')} {customer.get('city', '')} {customer.get('state', '')} {customer.get('postcode', '')} {customer.get('country', '')} {customer.get('email', '')} {customer.get('phone', '')}".strip()
        shipping_index = billing_index  # Usamos la misma dirección

        # DEBUG: Log billing_index generado
        current_app.logger.info(f"Generated billing_index: {billing_index}")

        # Generar external_id (hash único del pedido)
        external_id = hashlib.sha256(f"order_{order.id}_{get_gmt_time().timestamp()}".encode()).hexdigest()

        # Generar edit_lock (timestamp actual + user ID)
        edit_lock = f"{int(get_gmt_time().timestamp())}:{current_user.id}"

        order_metas = [
            # Identificación crítica
            ('external_id', external_id),  # CRÍTICO: Hash único para WooCommerce
            ('_order_number', manager_order_number),  # CRÍTICO: Número de pedido W-XXXXX para manager
            ('_edit_lock', edit_lock),  # Lock de edición
            ('_created_via', 'woocommerce-manager'),
            ('_order_source', 'whatsapp'),
            ('_created_by', current_user.username),
            ('_order_version', '9.0.0'),

            # Configuración de impuestos
            ('_prices_include_tax', 'yes'),  # IMPORTANTE: precios incluyen IGV
            ('is_vat_exempt', 'no'),  # No está exento de impuestos

            # Índices de búsqueda (CRÍTICO para que WooCommerce encuentre el pedido)
            ('_billing_address_index', billing_index),
            ('_shipping_address_index', shipping_index),

            # Totales
            ('_cart_discount', '0'),
            ('_cart_discount_tax', '0'),
            ('_order_shipping', str(shipping_subtotal.quantize(Decimal('0.01')))),
            ('_order_shipping_tax', str(shipping_tax.quantize(Decimal('0.01')))),
            ('_order_tax', str(tax_amount.quantize(Decimal('0.01')))),
            ('_order_total', str(total_with_tax.quantize(Decimal('0.01')))),

            # Campos custom del plugin Checkout Field Editor
            ('_billing_ruc', customer.get('billing_ruc', '')),
            ('_billing_entrega', customer.get('billing_entrega', 'billing_domicilio')),
            ('_billing_referencia', customer.get('billing_referencia', '')),
            ('billing_entrega', customer.get('billing_entrega', 'billing_domicilio')),
            ('billing_referencia', customer.get('billing_referencia', '')),
            ('_thwcfe_ship_to_billing', '1'),  # Copiar billing a shipping

            # Attribution (rastreo de origen) - Compatibilidad con WooCommerce Order Attribution
            ('_wc_order_attribution_source_type', 'admin'),  # Cambiado de 'direct' a 'admin'
            ('_wc_order_attribution_referrer', 'whatsapp'),
            ('_wc_order_attribution_utm_source', 'whatsapp'),
            ('_wc_order_attribution_utm_medium', 'manual_order'),  # Agregar medium
            ('_wc_order_attribution_utm_content', 'woocommerce-manager'),  # Agregar content
            ('_wc_order_attribution_session_entry', 'https://www.izistoreperu.com/orders/create'),  # URL de entrada
            ('_wc_order_attribution_session_start_time', get_gmt_time().strftime('%Y-%m-%d %H:%M:%S')),  # Timestamp
            ('_wc_order_attribution_session_pages', '1'),
            ('_wc_order_attribution_session_count', '1'),
            ('_wc_order_attribution_device_type', 'Desktop'),  # Tipo de dispositivo
            ('_wc_order_attribution_user_agent', request.headers.get('User-Agent', '')[:200]),
        ]

        # Guardar metadatos en AMBOS sistemas
        for meta_key, meta_value in order_metas:
            # 1. Guardar en wpyz_wc_orders_meta (HPOS - compatibilidad futura)
            order_meta = OrderMeta(
                order_id=order.id,
                meta_key=meta_key,
                meta_value=str(meta_value)
            )
            db.session.add(order_meta)

            # 2. Guardar en wpyz_postmeta (Sistema antiguo - lo que WooCommerce lee AHORA)
            insert_postmeta_meta = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:post_id, :meta_key, :meta_value)
            """)
            db.session.execute(insert_postmeta_meta, {
                'post_id': order.id,
                'meta_key': meta_key,
                'meta_value': str(meta_value)
            })

        # ===== GUARDAR EN POSTMETA TAMBIÉN =====
        # WooCommerce guarda algunos metadatos tanto en wc_orders_meta como en postmeta
        from sqlalchemy import text
        postmeta_fields = [
            ('_billing_ruc', customer.get('billing_ruc', '')),
            ('_billing_entrega', customer.get('billing_entrega', 'billing_domicilio')),
            ('_billing_referencia', customer.get('billing_referencia', '')),
            ('_thwcfe_ship_to_billing', '1'),
            ('_billing_company', customer.get('company', '')),  # DNI/CE
        ]

        for meta_key, meta_value in postmeta_fields:
            if meta_value:  # Solo insertar si tiene valor
                insert_postmeta = text("""
                    INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                    VALUES (:post_id, :meta_key, :meta_value)
                """)
                db.session.execute(insert_postmeta, {
                    'post_id': order.id,
                    'meta_key': meta_key,
                    'meta_value': str(meta_value)
                })

        # Guardar todo
        db.session.commit()

        # Verificar que el pedido se guardó correctamente con TODOS sus datos
        verify_query = text('SELECT id, status, total_amount, billing_email FROM wpyz_wc_orders WHERE id = :order_id')
        verification = db.session.execute(verify_query, {'order_id': order.id}).fetchone()

        if not verification:
            current_app.logger.error(f"CRITICAL: Order {order.id} was committed but does not exist in database")
            return jsonify({
                'success': False,
                'error': f'El pedido fue creado con ID {order.id} pero no se pudo verificar en la base de datos.',
                'order_id': order.id
            }), 500

        # Verificar direcciones
        verify_addresses = text('SELECT COUNT(*) FROM wpyz_wc_order_addresses WHERE order_id = :order_id')
        address_count = db.session.execute(verify_addresses, {'order_id': order.id}).fetchone()[0]

        # Verificar metadatos
        verify_metas = text('SELECT COUNT(*) FROM wpyz_wc_orders_meta WHERE order_id = :order_id')
        meta_count = db.session.execute(verify_metas, {'order_id': order.id}).fetchone()[0]

        # Verificar billing_email
        billing_email = verification[3]

        # Si falta algo crítico, retornar error detallado
        errors = []
        if address_count == 0:
            errors.append('direcciones')
        if meta_count == 0:
            errors.append('metadatos')
        if not billing_email:
            errors.append('email')

        if errors:
            error_msg = f"El pedido {order.id} se creó incompleto. Faltan: {', '.join(errors)}"
            current_app.logger.error(f"CRITICAL: Order {order.id} incomplete - Addresses: {address_count}, Metas: {meta_count}, Email: {billing_email}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'order_id': order.id,
                'debug': {
                    'addresses': address_count,
                    'metas': meta_count,
                    'email': billing_email or 'NULL'
                }
            }), 500

        current_app.logger.info(f"Order {order.id} created successfully and fully verified (addresses: {address_count}, metas: {meta_count})")

        # Limpiar cache de WooCommerce y LiteSpeed Cache
        try:
            # Limpiar transients de WooCommerce relacionados con pedidos
            clear_transients = text("""
                DELETE FROM wpyz_options
                WHERE option_name LIKE '%_transient_wc_orders%'
                OR option_name LIKE '%_transient_timeout_wc_orders%'
                OR option_name LIKE '%_transient_wc_order_%'
            """)
            db.session.execute(clear_transients)
            db.session.commit()

            # Forzar actualización del pedido para invalidar cache
            update_order = text("UPDATE wpyz_wc_orders SET date_updated_gmt = :now WHERE id = :order_id")
            db.session.execute(update_order, {'now': get_gmt_time(), 'order_id': order.id})
            db.session.commit()

            current_app.logger.info(f"Cache cleared for order {order.id}")
        except Exception as cache_error:
            current_app.logger.warning(f"Could not clear cache for order {order.id}: {str(cache_error)}")
            # No fallar si la limpieza de cache falla

        return jsonify({
            'success': True,
            'message': f'Pedido {manager_order_number} creado exitosamente',
            'order_id': order.id,
            'order_number': manager_order_number,
            'total': float(total_with_tax),
            'tax': float(tax_amount),
            'subtotal': float(subtotal)
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Error creating order: {str(e)}\n{error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_details
        }), 500


# Importar get_local_time
from config import get_local_time


@bp.route('/debug-last-order')
@login_required
def debug_last_order():
    """
    Endpoint temporal para debugging: muestra información del último pedido creado
    """
    from sqlalchemy import text

    # Obtener el último pedido
    last_order_query = text("""
        SELECT id, billing_email, customer_id, total_amount, date_created_gmt
        FROM wpyz_wc_orders
        ORDER BY id DESC
        LIMIT 1
    """)
    last_order = db.session.execute(last_order_query).fetchone()

    if not last_order:
        return jsonify({'error': 'No hay pedidos en la base de datos'}), 404

    order_id = last_order[0]

    # Obtener direcciones
    addresses_query = text("""
        SELECT address_type, first_name, last_name, email, phone, company, address_1, city, state, country
        FROM wpyz_wc_order_addresses
        WHERE order_id = :order_id
    """)
    addresses = db.session.execute(addresses_query, {'order_id': order_id}).fetchall()

    # Obtener billing_address_index
    billing_index_query = text("""
        SELECT meta_value
        FROM wpyz_wc_orders_meta
        WHERE order_id = :order_id
        AND meta_key = '_billing_address_index'
    """)
    billing_index = db.session.execute(billing_index_query, {'order_id': order_id}).fetchone()

    # Construir respuesta
    result = {
        'order_id': order_id,
        'billing_email': last_order[1],
        'customer_id': last_order[2],
        'total_amount': float(last_order[3]) if last_order[3] else 0,
        'date_created_gmt': str(last_order[4]),
        'addresses': [],
        'billing_address_index': billing_index[0] if billing_index else 'NOT FOUND'
    }

    for addr in addresses:
        result['addresses'].append({
            'type': addr[0],
            'first_name': addr[1],
            'last_name': addr[2],
            'email': addr[3],
            'phone': addr[4],
            'company': addr[5],
            'address_1': addr[6],
            'city': addr[7],
            'state': addr[8],
            'country': addr[9]
        })

    return jsonify(result)
