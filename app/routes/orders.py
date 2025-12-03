# app/routes/orders.py
from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models import Order, OrderAddress, OrderItem, OrderItemMeta, OrderMeta, Product, ProductMeta, OrderExternal, OrderExternalItem
from app import db
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import or_, desc
import pytz
import hashlib
import json
import os

bp = Blueprint('orders', __name__, url_prefix='/orders')


def get_gmt_time():
    """
    Obtener la hora actual de Perú (America/Lima, UTC-5) convertida a GMT/UTC

    WooCommerce guarda las fechas en UTC en la base de datos.
    Esta función toma la hora actual de Perú y la convierte a UTC.

    Ejemplo:
    - Hora Perú: 2025-12-01 18:30:00 (UTC-5)
    - Hora UTC: 2025-12-01 23:30:00

    Returns:
        datetime: Hora actual en UTC (sin timezone info)
    """
    from config import get_local_time

    # Obtener hora actual de Perú con timezone
    peru_time = get_local_time()

    # Convertir a UTC
    utc_time = peru_time.astimezone(pytz.UTC)

    # Retornar sin timezone info (naive datetime) como espera WooCommerce
    return utc_time.replace(tzinfo=None)


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


def trigger_woocommerce_email(order_id):
    """
    Dispara el envío de correo de WooCommerce usando la API REST

    ESTRATEGIA: Para forzar el envío de correo, cambiamos el estado del pedido
    de 'pending' a 'processing'. Esta transición de estado dispara el hook
    de email de WooCommerce automáticamente.

    Args:
        order_id (int): ID del pedido

    Returns:
        bool: True si se disparó correctamente, False si hubo error
    """
    import requests
    from requests.auth import HTTPBasicAuth
    import time

    try:
        # Obtener credenciales de WooCommerce API
        wc_url = current_app.config.get('WC_API_URL')
        consumer_key = current_app.config.get('WC_CONSUMER_KEY')
        consumer_secret = current_app.config.get('WC_CONSUMER_SECRET')

        if not all([wc_url, consumer_key, consumer_secret]):
            current_app.logger.error("WooCommerce API credentials not configured")
            return False

        # Endpoint de la API REST de WooCommerce
        api_url = f"{wc_url}/wp-json/wc/v3/orders/{order_id}"
        auth = HTTPBasicAuth(consumer_key, consumer_secret)

        # PASO 1: Cambiar a 'pending' (estado intermedio)
        # Esto asegura que luego podamos hacer una transición real
        payload_pending = {
            'status': 'pending'
        }

        response_pending = requests.put(
            api_url,
            json=payload_pending,
            auth=auth,
            timeout=10
        )

        if response_pending.status_code != 200:
            current_app.logger.error(f"Failed to set order {order_id} to pending: {response_pending.status_code}")
            return False

        current_app.logger.info(f"Order {order_id} set to pending")

        # Pequeña pausa para asegurar que WooCommerce procese el cambio
        time.sleep(0.5)

        # PASO 2: Cambiar a 'processing' + set_paid
        # Esta transición de estado dispara el correo de "Processing order"
        payload_processing = {
            'status': 'processing',
            'set_paid': True
        }

        response_processing = requests.put(
            api_url,
            json=payload_processing,
            auth=auth,
            timeout=10
        )

        if response_processing.status_code == 200:
            current_app.logger.info(f"Successfully triggered email for order {order_id} via status transition")
            return True
        else:
            current_app.logger.error(f"Failed to trigger email for order {order_id}: {response_processing.status_code} - {response_processing.text}")
            return False

    except Exception as e:
        current_app.logger.error(f"Exception triggering email for order {order_id}: {str(e)}")
        return False


@bp.route('/')
@login_required
def index():
    """
    Vista principal del módulo de pedidos (listado)

    URL: http://localhost:5000/orders/
    """
    return render_template('orders_list.html', title='Gestión de Pedidos')


@bp.route('/api/departamentos')
@login_required
def get_departamentos():
    """
    Endpoint API para obtener lista de departamentos de Perú

    Returns:
        JSON con lista de departamentos [{code, name}, ...]
    """
    try:
        # Leer archivo JSON estático
        ubigeo_path = os.path.join(current_app.root_path, 'static', 'data', 'ubigeo.json')

        with open(ubigeo_path, 'r', encoding='utf-8') as f:
            ubigeo_data = json.load(f)

        return jsonify({
            'success': True,
            'departamentos': ubigeo_data['departamentos']
        })

    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Archivo de ubigeo no encontrado'
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/distritos/<departamento_code>')
@login_required
def get_distritos(departamento_code):
    """
    Endpoint API para obtener distritos de un departamento específico

    Args:
        departamento_code: Código del departamento (ej: LIMA, CALL, AREQ)

    Returns:
        JSON con lista de distritos del departamento
    """
    try:
        # Leer archivo JSON estático
        ubigeo_path = os.path.join(current_app.root_path, 'static', 'data', 'ubigeo.json')

        with open(ubigeo_path, 'r', encoding='utf-8') as f:
            ubigeo_data = json.load(f)

        # Validar que el departamento existe
        departamento_code = departamento_code.upper()
        if departamento_code not in ubigeo_data['distritos']:
            return jsonify({
                'success': False,
                'error': f'Departamento {departamento_code} no encontrado'
            }), 404

        return jsonify({
            'success': True,
            'distritos': ubigeo_data['distritos'][departamento_code]
        })

    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Archivo de ubigeo no encontrado'
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/metodos-envio/<distrito>')
@login_required
def get_metodos_envio(distrito):
    """
    Endpoint API para obtener métodos de envío disponibles para un distrito

    Args:
        distrito: Nombre del distrito (ej: "Miraflores", "Ate")

    Returns:
        JSON con lista de métodos de envío disponibles con sus tarifas
    """
    try:
        import phpserialize
        from sqlalchemy import text

        # Obtener todos los métodos de envío activos (post_type = 'was')
        query = text("""
            SELECT p.ID, p.post_title
            FROM wpyz_posts p
            WHERE p.post_type = 'was'
            AND p.post_status = 'publish'
            ORDER BY p.ID
        """)

        shipping_methods = db.session.execute(query).fetchall()
        available_methods = []

        for method in shipping_methods:
            method_id = method[0]
            method_title = method[1]

            # Obtener metadatos del método
            meta_query = text("""
                SELECT meta_key, meta_value
                FROM wpyz_postmeta
                WHERE post_id = :method_id
                AND meta_key IN ('_was_shipping_method', '_was_shipping_method_conditions')
            """)

            meta_result = db.session.execute(meta_query, {'method_id': method_id}).fetchall()

            shipping_data = {}
            conditions_data = {}

            for meta in meta_result:
                meta_key = meta[0]
                meta_value = meta[1]

                if meta_key == '_was_shipping_method':
                    # Deserializar datos PHP del método
                    try:
                        shipping_data = phpserialize.loads(meta_value.encode('utf-8'), decode_strings=True)
                    except:
                        continue

                elif meta_key == '_was_shipping_method_conditions':
                    # Deserializar condiciones (distritos)
                    try:
                        conditions_data = phpserialize.loads(meta_value.encode('utf-8'), decode_strings=True)
                    except:
                        continue

            # Verificar si el distrito está en las condiciones
            distrito_match = False

            if conditions_data and isinstance(conditions_data, dict):
                for group in conditions_data.values():
                    if isinstance(group, dict):
                        for condition in group.values():
                            if isinstance(condition, dict):
                                # Verificar condición de ciudad
                                if condition.get('condition') == 'city':
                                    cities_str = condition.get('value', '')
                                    # Los distritos están separados por comas
                                    cities_list = [city.strip() for city in cities_str.split(',')]

                                    # Comparación case-insensitive
                                    if any(distrito.lower() == city.lower() for city in cities_list):
                                        distrito_match = True
                                        break

                    if distrito_match:
                        break

            # Si el distrito coincide, agregar método a la lista
            if distrito_match and shipping_data:
                method_info = {
                    'id': method_id,
                    'title': shipping_data.get('shipping_title', method_title),
                    'cost': float(shipping_data.get('shipping_cost', 0)),
                    'tax': shipping_data.get('tax', 'taxable')
                }
                available_methods.append(method_info)

        # Ordenar por precio (menor a mayor)
        available_methods.sort(key=lambda x: x['cost'])

        return jsonify({
            'success': True,
            'distrito': distrito,
            'metodos': available_methods,
            'count': len(available_methods)
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


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
    - status: filtrar por estado del pedido
    """
    try:
        from sqlalchemy import text
        from app.models import User

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        created_by_filter = request.args.get('created_by', '', type=str)
        status_filter = request.args.get('status', '', type=str)

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
                (SELECT COUNT(*) FROM wpyz_woocommerce_order_items WHERE order_id = o.id AND order_item_type = 'line_item') as items_count,
                (SELECT oi.order_item_name
                 FROM wpyz_woocommerce_order_items oi
                 WHERE oi.order_id = o.id AND oi.order_item_type = 'shipping'
                 LIMIT 1) as shipping_method
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_order_number ON o.id = om_order_number.order_id AND om_order_number.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_orders_meta om_created_by ON o.id = om_created_by.order_id AND om_created_by.meta_key = '_created_by'
            LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id AND ba.address_type = 'billing'
            WHERE o.status != 'trash'
            {search_filter}
            {created_by_filter}
            {status_filter}
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
            WHERE o.status != 'trash'
            {search_filter}
            {created_by_filter}
            {status_filter}
        """)

        # Construir filtros dinámicos
        search_filter = ""
        created_by_filter_clause = ""
        status_filter_clause = ""
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

        if status_filter:
            status_filter_clause = "AND o.status = :status"
            params['status'] = status_filter

        # Formatear queries con filtros
        final_query = query.text.format(
            search_filter=search_filter,
            created_by_filter=created_by_filter_clause,
            status_filter=status_filter_clause
        )
        final_count_query = count_query.text.format(
            search_filter=search_filter,
            created_by_filter=created_by_filter_clause,
            status_filter=status_filter_clause
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
                'shipping_method': row[14] or 'N/A',  # Método de envío
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
    Obtener lista de usuarios ACTIVOS del sistema para filtrar pedidos

    Retorna lista de usuarios activos con username y nombre completo
    """
    try:
        from app.models import User

        # Obtener solo usuarios ACTIVOS
        users = User.query.filter_by(is_active=True).order_by(User.full_name, User.username).all()

        users_list = [{
            'username': user.username,
            'full_name': user.full_name or user.username  # Usar username si no tiene nombre completo
        } for user in users]

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
        "shipping_method_title": "Envío Olva Courier 3 a 4 días",  # Opcional: nombre del método
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
        discount_percentage = Decimal(str(data.get('discount_percentage', 0)))
        shipping_method_title = data.get('shipping_method_title', '')  # Título del método de envío

        # DEBUG: Log customer data para verificar qué se está recibiendo
        current_app.logger.info(f"Creating order with customer data: {customer}")
        current_app.logger.info(f"Discount percentage: {discount_percentage}%")

        # ===== CALCULAR TOTALES =====
        # Los precios INCLUYEN IGV (18%)
        # Fórmula: precio_sin_igv = precio_con_igv / 1.18

        products_total_with_tax = Decimal('0')

        # Sumar productos
        for item_data in items_data:
            item_price_with_tax = Decimal(str(item_data['price'])) * item_data['quantity']
            products_total_with_tax += item_price_with_tax

        # Aplicar descuento a los productos (NO al envío)
        # Truncar en lugar de redondear usando ROUND_DOWN
        discount_amount = Decimal('0')
        if discount_percentage > 0:
            discount_amount = (products_total_with_tax * discount_percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            current_app.logger.info(f"Discount amount: S/ {discount_amount}")

        products_after_discount = products_total_with_tax - discount_amount

        # Total final = productos con descuento + envío
        total_with_tax = products_after_discount + shipping_cost

        # Calcular subtotal e IGV del total final
        subtotal = total_with_tax / Decimal('1.18')
        tax_amount = total_with_tax - subtotal

        # ===== CREAR PEDIDO CON PROTECCIÓN CONTRA RACE CONDITIONS =====
        # Intentar crear pedido hasta 3 veces en caso de colisión de ID
        from sqlalchemy import text
        max_retries = 3
        order = None

        for attempt in range(max_retries):
            # Crear pedido
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

            # Verificar si el ID ya existe en wpyz_posts (race condition)
            check_post_exists = text("""
                SELECT ID FROM wpyz_posts WHERE ID = :order_id
            """)
            existing_post = db.session.execute(check_post_exists, {'order_id': order.id}).fetchone()

            if not existing_post:
                # ID disponible, continuar con la creación
                current_app.logger.info(f"Order ID {order.id} is available, proceeding with creation")
                break
            else:
                # ID ya existe, hacer rollback y reintentar
                current_app.logger.warning(f"Order ID {order.id} already exists in wpyz_posts (attempt {attempt + 1}/{max_retries}). Rolling back and retrying...")
                db.session.rollback()

                if attempt == max_retries - 1:
                    # Último intento falló
                    raise Exception(f"Failed to create order after {max_retries} attempts due to ID collisions")

                # Forzar nuevo ID incrementando el autoincrement
                # Esto asegura que el próximo ID sea diferente
                continue

        # ===== GENERAR NÚMERO DE PEDIDO W-XXXXX =====
        # Genera un número único de pedido en formato W-00001 para identificar
        # pedidos creados por el manager y evitar conflictos con IDs naturales
        manager_order_number = get_next_manager_order_number()
        current_app.logger.info(f"Generated manager order number: {manager_order_number} for order ID {order.id}")

        # ===== REGISTRO EN WPYZ_POSTS (CRÍTICO para compatibilidad HPOS) =====
        # WooCommerce HPOS requiere sincronización con wpyz_posts para plugins antiguos
        # En este punto sabemos que el ID no existe (verificado arriba)
        if True:  # Siempre ejecutar porque ya verificamos
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

        # OPTIMIZACIÓN: Cargar todos los productos en una sola query (batch loading)
        # Esto evita el problema N+1 de hacer una query por cada item
        product_ids = [item.get('variation_id') or item['product_id'] for item in items_data]
        products_list = Product.query.filter(Product.ID.in_(product_ids)).all()
        products_dict = {p.ID: p for p in products_list}

        for item_data in items_data:
            product_id = item_data['product_id']
            variation_id = item_data.get('variation_id', 0)
            quantity = item_data['quantity']
            price_with_tax = Decimal(str(item_data['price']))

            # Obtener producto del diccionario (ya cargado en memoria)
            target_product_id = variation_id if variation_id else product_id
            product = products_dict.get(target_product_id)

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
            # IMPORTANTE: flush() necesario para obtener order_item_id antes de crear metadatos
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
            # OPTIMIZACIÓN: Reutilizar el producto ya cargado en lugar de hacer otra query
            if product:
                stock_meta = product.product_meta.filter_by(meta_key='_stock').first()
                if stock_meta:
                    current_stock = int(float(stock_meta.meta_value))
                    new_stock = max(0, current_stock - quantity)
                    stock_meta.meta_value = str(new_stock)

                    # Actualizar estado de stock
                    if new_stock == 0:
                        stock_status_meta = product.product_meta.filter_by(meta_key='_stock_status').first()
                        if stock_status_meta:
                            stock_status_meta.meta_value = 'outofstock'

        # ===== ITEM DE ENVÍO =====
        # SIEMPRE crear item de envío, incluso si el costo es 0 (como en "Recojo en Almacén")
        # El costo de envío NO incluye IGV (viene como precio final)
        shipping_subtotal = shipping_cost
        shipping_tax = Decimal('0')

        # Usar shipping_method_title si viene en el request, sino mapear desde billing_entrega
        if shipping_method_title:
            shipping_method_name = shipping_method_title
        else:
            # Fallback: mapear billing_entrega a nombres legibles
            billing_entrega = customer.get('billing_entrega', 'billing_domicilio')
            shipping_method_names = {
                'billing_agencia': 'En Agencia Shalom/Olva Courier',
                'billing_domicilio': 'Entrega a Domicilio',
                'billing_recojo': 'Recojo en Almacén'
            }
            shipping_method_name = shipping_method_names.get(billing_entrega, 'Envío')

        shipping_item = OrderItem(
            order_item_name=shipping_method_name,  # Usar nombre del método de envío
            order_item_type='shipping',
            order_id=order.id
        )
        db.session.add(shipping_item)
        db.session.flush()

        shipping_cost_str = str(shipping_cost.quantize(Decimal('0.01')))
        shipping_metas = [
            ('method_id', 'advanced_shipping'),
            ('instance_id', '0'),
            ('cost', shipping_cost_str),
            ('total_tax', '0'),
            ('taxes', 'a:0:{}'),  # Array vacío en PHP serializado - sin impuestos
            # Agregar metadatos adicionales para que WooCommerce no calcule impuestos
            ('_line_total', shipping_cost_str),
            ('_line_tax', '0'),
            ('_line_subtotal', shipping_cost_str),
            ('_line_subtotal_tax', '0'),
        ]

        for meta_key, meta_value in shipping_metas:
            shipping_meta = OrderItemMeta(
                order_item_id=shipping_item.order_item_id,
                meta_key=meta_key,
                meta_value=str(meta_value)
            )
            db.session.add(shipping_meta)

        # ===== ITEM DE DESCUENTO (FEE) =====
        # Si hay descuento, crear un line item de tipo 'fee' con valor negativo
        if discount_amount > 0:
            # Formatear el porcentaje correctamente
            discount_percentage_str = str(discount_percentage.quantize(Decimal('0.01')))

            discount_item = OrderItem(
                order_item_name=f'Descuento ({discount_percentage_str}%)',
                order_item_type='fee',
                order_id=order.id
            )
            db.session.add(discount_item)
            db.session.flush()

            # Metadatos del descuento (valor negativo)
            # WooCommerce usa _line_total para mostrar el monto en el resumen
            discount_amount_str = str(discount_amount.quantize(Decimal('0.01')))
            discount_metas = [
                ('_fee_amount', f'-{discount_amount_str}'),
                ('_line_total', f'-{discount_amount_str}'),
                ('_line_tax', '0'),
                ('_line_subtotal', f'-{discount_amount_str}'),
                ('_line_subtotal_tax', '0'),
                ('_tax_class', ''),
                ('_line_tax_data', 'a:0:{}'),  # Array vacío de impuestos
            ]

            for meta_key, meta_value in discount_metas:
                discount_meta = OrderItemMeta(
                    order_item_id=discount_item.order_item_id,
                    meta_key=meta_key,
                    meta_value=str(meta_value)
                )
                db.session.add(discount_meta)

            current_app.logger.info(f"Added discount line item: -{discount_amount_str} ({discount_percentage_str}%)")

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

            # Descuento personalizado (metadata para referencia)
            ('_wc_discount_percentage', str(discount_percentage)),
            ('_wc_discount_amount', str(discount_amount.quantize(Decimal('0.01')))),

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

        # OPTIMIZACIÓN: Incluir limpieza de cache ANTES del commit para tener solo 1 commit
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
            current_app.logger.info(f"Cache clear queued for order {order.id}")
        except Exception as cache_error:
            current_app.logger.warning(f"Could not queue cache clear for order {order.id}: {str(cache_error)}")
            # No fallar si la limpieza de cache falla

        # Guardar todo en UN SOLO COMMIT (antes eran 3 commits separados)
        db.session.commit()

        # OPTIMIZACIÓN: Queries de verificación removidas - confiar en SQLAlchemy
        # Antes hacíamos 3 SELECTs adicionales que agregaban ~1 segundo
        current_app.logger.info(f"Order {order.id} created successfully")

        # ===== DISPARAR ENVÍO DE CORREO DE WOOCOMMERCE =====
        # Enviar email en background para no bloquear la respuesta al usuario
        import threading

        def send_email_async(order_id, app):
            """Enviar email en thread separado con contexto de Flask"""
            with app.app_context():
                try:
                    email_sent = trigger_woocommerce_email(order_id)
                    if email_sent:
                        current_app.logger.info(f"Email notification triggered successfully for order {order_id}")
                    else:
                        current_app.logger.warning(f"Could not trigger email notification for order {order_id}")
                except Exception as email_error:
                    current_app.logger.error(f"Exception triggering email for order {order_id}: {str(email_error)}")

        # Iniciar thread en background (no bloqueante)
        email_thread = threading.Thread(
            target=send_email_async,
            args=(order.id, current_app._get_current_object())
        )
        email_thread.daemon = True  # Thread se cierra cuando la app se cierra
        email_thread.start()

        current_app.logger.info(f"Order {order.id} created successfully - Email being sent in background")

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


@bp.route('/get-woo-orders-url')
@login_required
def get_woo_orders_url():
    """
    Devuelve la URL de WooCommerce para ver el listado general de pedidos
    """
    try:
        woo_url = current_app.config.get('WC_API_URL', '')

        if not woo_url:
            return jsonify({
                'success': False,
                'error': 'URL de WooCommerce no configurada'
            }), 500

        # Construir URL completa del listado de pedidos
        full_url = f"{woo_url}/wp-admin/edit.php?post_type=shop_order"

        return jsonify({
            'success': True,
            'url': full_url
        })
    except Exception as e:
        current_app.logger.error(f"Error getting WooCommerce URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/debug-woocommerce-api')
@login_required
def debug_woocommerce_api():
    """
    Endpoint temporal para verificar configuración de WooCommerce API
    """
    wc_url = current_app.config.get('WC_API_URL')
    consumer_key = current_app.config.get('WC_CONSUMER_KEY')
    consumer_secret = current_app.config.get('WC_CONSUMER_SECRET')

    return jsonify({
        'wc_url': wc_url,
        'consumer_key_configured': bool(consumer_key),
        'consumer_secret_configured': bool(consumer_secret),
        'consumer_key_preview': consumer_key[:10] + '...' if consumer_key else None
    })


@bp.route('/test-email-trigger/<int:order_id>')
@login_required
def test_email_trigger(order_id):
    """
    Endpoint de prueba para disparar el correo de un pedido específico
    Muestra el resultado completo de la petición a WooCommerce API

    Uso: /orders/test-email-trigger/12345
    """
    import requests
    from requests.auth import HTTPBasicAuth

    result = {
        'order_id': order_id,
        'timestamp': get_gmt_time().isoformat(),
        'config_check': {},
        'api_request': {},
        'result': 'unknown'
    }

    try:
        # Verificar que el pedido existe
        order = Order.query.get(order_id)
        if not order:
            result['result'] = 'error'
            result['error'] = f'Order {order_id} not found in database'
            return jsonify(result), 404

        result['order_found'] = True
        result['order_number'] = order.id

        # Verificar configuración
        wc_url = current_app.config.get('WC_API_URL')
        consumer_key = current_app.config.get('WC_CONSUMER_KEY')
        consumer_secret = current_app.config.get('WC_CONSUMER_SECRET')

        result['config_check'] = {
            'wc_url': wc_url,
            'consumer_key_configured': bool(consumer_key),
            'consumer_secret_configured': bool(consumer_secret),
            'consumer_key_preview': consumer_key[:10] + '...' if consumer_key else None
        }

        if not all([wc_url, consumer_key, consumer_secret]):
            result['result'] = 'error'
            result['error'] = 'WooCommerce API credentials not configured'
            return jsonify(result), 500

        # Construir URL de API
        api_url = f"{wc_url}/wp-json/wc/v3/orders/{order_id}"
        result['api_request']['url'] = api_url

        # Payload
        payload = {
            'status': 'processing',
            'set_paid': True
        }
        result['api_request']['payload'] = payload

        # Hacer petición a WooCommerce API
        current_app.logger.info(f"TEST: Making API request to {api_url}")

        response = requests.put(
            api_url,
            json=payload,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=10
        )

        result['api_request']['status_code'] = response.status_code
        result['api_request']['response_text'] = response.text[:500]  # Limitar a 500 chars

        if response.status_code == 200:
            result['result'] = 'success'
            result['message'] = 'Email trigger successful'
            current_app.logger.info(f"TEST: Successfully triggered email for order {order_id}")
        else:
            result['result'] = 'api_error'
            result['message'] = f'API returned status {response.status_code}'
            current_app.logger.error(f"TEST: API error for order {order_id}: {response.status_code}")

        return jsonify(result), response.status_code

    except requests.exceptions.RequestException as e:
        result['result'] = 'network_error'
        result['error'] = str(e)
        current_app.logger.error(f"TEST: Network error for order {order_id}: {str(e)}")
        return jsonify(result), 500

    except Exception as e:
        result['result'] = 'exception'
        result['error'] = str(e)
        result['error_type'] = type(e).__name__
        current_app.logger.error(f"TEST: Exception for order {order_id}: {str(e)}")
        return jsonify(result), 500


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


@bp.route('/enable-stock/<int:product_id>', methods=['POST'])
@login_required
def enable_stock(product_id):
    """
    Habilitar stock de un producto/variación específico
    Actualiza el stock_status a 'instock' y opcionalmente establece una cantidad mínima
    """
    try:
        data = request.json or {}
        variation_id = data.get('variation_id', 0)
        min_stock = data.get('min_stock', 1)  # Stock mínimo por defecto: 1 unidad

        # Determinar si es variación o producto simple
        target_id = variation_id if variation_id > 0 else product_id

        # Actualizar stock_status en wpyz_postmeta
        from sqlalchemy import text

        # Verificar si existe el meta_key _stock_status
        check_query = text("""
            SELECT meta_id FROM wpyz_postmeta
            WHERE post_id = :target_id AND meta_key = '_stock_status'
        """)
        existing = db.session.execute(check_query, {'target_id': target_id}).fetchone()

        if existing:
            # Actualizar existente
            update_query = text("""
                UPDATE wpyz_postmeta
                SET meta_value = 'instock'
                WHERE post_id = :target_id AND meta_key = '_stock_status'
            """)
            db.session.execute(update_query, {'target_id': target_id})
        else:
            # Insertar nuevo
            insert_query = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:target_id, '_stock_status', 'instock')
            """)
            db.session.execute(insert_query, {'target_id': target_id})

        # Actualizar stock quantity
        check_stock_query = text("""
            SELECT meta_id FROM wpyz_postmeta
            WHERE post_id = :target_id AND meta_key = '_stock'
        """)
        existing_stock = db.session.execute(check_stock_query, {'target_id': target_id}).fetchone()

        if existing_stock:
            update_stock_query = text("""
                UPDATE wpyz_postmeta
                SET meta_value = :min_stock
                WHERE post_id = :target_id AND meta_key = '_stock'
            """)
            db.session.execute(update_stock_query, {'target_id': target_id, 'min_stock': str(min_stock)})
        else:
            insert_stock_query = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:target_id, '_stock', :min_stock)
            """)
            db.session.execute(insert_stock_query, {'target_id': target_id, 'min_stock': str(min_stock)})

        # Establecer manage_stock en 'yes'
        check_manage_query = text("""
            SELECT meta_id FROM wpyz_postmeta
            WHERE post_id = :target_id AND meta_key = '_manage_stock'
        """)
        existing_manage = db.session.execute(check_manage_query, {'target_id': target_id}).fetchone()

        if existing_manage:
            update_manage_query = text("""
                UPDATE wpyz_postmeta
                SET meta_value = 'yes'
                WHERE post_id = :target_id AND meta_key = '_manage_stock'
            """)
            db.session.execute(update_manage_query, {'target_id': target_id})
        else:
            insert_manage_query = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:target_id, '_manage_stock', 'yes')
            """)
            db.session.execute(insert_manage_query, {'target_id': target_id})

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Stock habilitado: {min_stock} unidades disponibles',
            'product_id': product_id,
            'variation_id': variation_id,
            'stock': min_stock
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error enabling stock: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== ENDPOINTS PARA PEDIDOS EXTERNOS ====================

@bp.route('/list-external')
@login_required
def list_external():
    """
    Listar pedidos externos con paginación y filtros

    Query params:
    - page: número de página (default: 1)
    - per_page: registros por página (default: 20)
    - search: búsqueda por ID, email, nombre o teléfono
    - source: filtrar por fuente (marketplace, tienda_fisica, otro)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str).strip()
        source = request.args.get('source', '', type=str).strip()

        # Query base
        query = OrderExternal.query

        # Filtro de búsqueda
        if search:
            query = query.filter(
                or_(
                    OrderExternal.order_number.ilike(f'%{search}%'),
                    OrderExternal.customer_email.ilike(f'%{search}%'),
                    OrderExternal.customer_first_name.ilike(f'%{search}%'),
                    OrderExternal.customer_last_name.ilike(f'%{search}%'),
                    OrderExternal.customer_phone.ilike(f'%{search}%')
                )
            )

        # Filtro por fuente
        if source:
            query = query.filter(OrderExternal.external_source == source)

        # Ordenar por fecha descendente
        query = query.order_by(desc(OrderExternal.date_created_gmt))

        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Construir respuesta
        peru_tz = pytz.timezone('America/Lima')
        orders = []
        for order in pagination.items:
            # Convertir fecha UTC a hora de Perú para mostrar
            date_created_utc = pytz.UTC.localize(order.date_created_gmt)
            date_created_peru = date_created_utc.astimezone(peru_tz)

            orders.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_first_name': order.customer_first_name,
                'customer_last_name': order.customer_last_name,
                'customer_email': order.customer_email,
                'customer_phone': order.customer_phone,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'external_source': order.external_source,
                'created_by': order.created_by,
                'date_created': date_created_peru.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({
            'success': True,
            'orders': orders,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        })

    except Exception as e:
        current_app.logger.error(f'Error listing external orders: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/count')
@login_required
def count_orders():
    """
    Contar pedidos por canal (whatsapp o external)

    Query params:
    - channel: 'whatsapp' o 'external'
    """
    try:
        from sqlalchemy import text
        channel = request.args.get('channel', 'whatsapp', type=str)

        if channel == 'external':
            count = OrderExternal.query.count()
        else:
            # Contar pedidos de WhatsApp (creados por el manager)
            # Los pedidos del manager tienen meta_key '_created_by' con el username
            # y meta_key '_order_number' (sin formato W-, ese es solo visual en frontend)
            count_query = text("""
                SELECT COUNT(DISTINCT o.id)
                FROM wpyz_wc_orders o
                INNER JOIN wpyz_wc_orders_meta om_number ON o.id = om_number.order_id
                    AND om_number.meta_key = '_order_number'
                INNER JOIN wpyz_wc_orders_meta om_created ON o.id = om_created.order_id
                    AND om_created.meta_key = '_created_by'
                WHERE o.status != 'trash'
            """)

            result = db.session.execute(count_query).fetchone()
            count = result[0] if result else 0

        return jsonify({
            'success': True,
            'count': count,
            'channel': channel
        })

    except Exception as e:
        current_app.logger.error(f'Error counting orders: {str(e)}')
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def get_next_external_order_number():
    """
    Obtener el siguiente número de pedido externo (formato EXT-XXXXX)

    Returns:
        str: Número de pedido en formato EXT-00001
    """
    from sqlalchemy import text

    try:
        # Buscar el último número de pedido externo
        last_order = OrderExternal.query.order_by(desc(OrderExternal.id)).first()

        if last_order and last_order.order_number.startswith('EXT-'):
            # Extraer el número del último pedido
            last_num = int(last_order.order_number.split('-')[1])
            next_num = last_num + 1
        else:
            # Primer pedido externo
            next_num = 1

        return f'EXT-{next_num:05d}'

    except Exception as e:
        current_app.logger.error(f'Error getting next external order number: {str(e)}')
        # Fallback: usar timestamp
        import time
        return f'EXT-{int(time.time())}'


@bp.route('/save-order-external', methods=['POST'])
@login_required
def save_order_external():
    """
    Crear un nuevo pedido externo

    Este endpoint guarda pedidos de fuentes externas (no WooCommerce)
    para tracking interno. Los pedidos externos:
    - Se guardan en woo_orders_ext (NO en tablas de WooCommerce)
    - Estado siempre 'wc-completed'
    - SÍ afectan el stock de productos
    - NO tienen integración con WooCommerce
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos'
            }), 400

        # Validar datos requeridos
        customer = data.get('customer', {})
        items = data.get('items', [])

        if not customer.get('first_name') or not customer.get('email'):
            return jsonify({
                'success': False,
                'error': 'Nombre y email son requeridos'
            }), 400

        if not items or len(items) == 0:
            return jsonify({
                'success': False,
                'error': 'Debe agregar al menos un producto'
            }), 400

        # Obtener número de pedido
        order_number = get_next_external_order_number()

        # Calcular totales
        subtotal = Decimal('0.00')
        for item in items:
            item_subtotal = Decimal(str(item.get('price', 0))) * int(item.get('quantity', 1))
            subtotal += item_subtotal

        # Descuentos
        discount_percentage = Decimal(str(data.get('discount_percentage', 0)))
        discount_amount = Decimal('0.00')
        if discount_percentage > 0:
            discount_amount = (subtotal * discount_percentage / 100).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        # Envío
        shipping_cost = Decimal(str(data.get('shipping_cost', 0)))

        # Total
        total_amount = subtotal - discount_amount + shipping_cost

        # Crear pedido externo
        current_time_utc = get_gmt_time()

        order_ext = OrderExternal(
            order_number=order_number,
            date_created_gmt=current_time_utc,
            date_updated_gmt=current_time_utc,
            status='wc-completed',  # Siempre completed para externos
            customer_first_name=customer.get('first_name', ''),
            customer_last_name=customer.get('last_name', ''),
            customer_email=customer.get('email', ''),
            customer_phone=customer.get('phone', ''),
            customer_dni=customer.get('dni', ''),
            customer_ruc=customer.get('ruc', ''),
            shipping_address_1=customer.get('address_1', ''),
            shipping_city=customer.get('city', ''),
            shipping_state=customer.get('state', ''),
            shipping_postcode=customer.get('postcode', ''),
            shipping_country=customer.get('country', 'PE'),
            shipping_reference=customer.get('reference', ''),
            delivery_type=customer.get('delivery_type', ''),
            shipping_method_title=data.get('shipping_method', ''),
            shipping_cost=shipping_cost,
            payment_method=data.get('payment_method', ''),
            payment_method_title=data.get('payment_method_title', ''),
            subtotal=subtotal,
            tax_total=Decimal('0.00'),
            discount_amount=discount_amount,
            discount_percentage=discount_percentage,
            total_amount=total_amount,
            customer_note=data.get('customer_note', ''),
            created_by=current_user.username,
            external_source=data.get('external_source', 'otro')  # marketplace, tienda_fisica, otro
        )

        db.session.add(order_ext)
        db.session.flush()  # Para obtener el ID

        # Crear items del pedido
        for item_data in items:
            product_id = item_data.get('product_id')
            variation_id = item_data.get('variation_id', 0)
            quantity = int(item_data.get('quantity', 1))
            price = Decimal(str(item_data.get('price', 0)))

            # Obtener info del producto
            product = Product.query.get(product_id)
            if not product:
                raise Exception(f'Producto {product_id} no encontrado')

            product_name = product.post_title
            product_sku = product.get_meta('_sku') or ''

            # Si es variación, obtener nombre y SKU de la variación
            if variation_id:
                variation = Product.query.get(variation_id)
                if variation:
                    product_name = variation.post_title
                    # IMPORTANTE: Obtener SKU de la variación, no del producto padre
                    product_sku = variation.get_meta('_sku') or product_sku

            item_subtotal = price * quantity
            item_total = item_subtotal

            # Crear item
            order_item = OrderExternalItem(
                order_ext_id=order_ext.id,
                product_id=product_id,
                variation_id=variation_id,
                product_name=product_name,
                product_sku=product_sku,
                quantity=quantity,
                unit_price=price,
                subtotal=item_subtotal,
                tax=Decimal('0.00'),
                total=item_total
            )

            db.session.add(order_item)

            # **IMPORTANTE: RESTAR STOCK DEL INVENTARIO**
            target_product_id = variation_id if variation_id else product_id
            target_product = Product.query.get(target_product_id)

            if target_product:
                current_stock_str = target_product.get_meta('_stock')
                if current_stock_str:
                    current_stock = int(float(current_stock_str))
                    new_stock = current_stock - quantity

                    # Actualizar stock
                    target_product.set_meta('_stock', str(new_stock))

                    # Registrar en historial de stock
                    from app.models import StockHistory
                    from config import get_local_time

                    stock_history = StockHistory(
                        product_id=target_product_id,
                        product_title=target_product.post_title,
                        sku=product_sku,
                        old_stock=current_stock,
                        new_stock=new_stock,
                        change_amount=-quantity,
                        changed_by=current_user.username,
                        change_reason=f'Pedido externo {order_number}',
                        created_at=get_local_time()
                    )
                    db.session.add(stock_history)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pedido externo creado exitosamente',
            'order_id': order_ext.id,
            'order_number': order_number,
            'total': float(total_amount)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating external order: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
