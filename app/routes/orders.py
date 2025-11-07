# app/routes/orders.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import Order, OrderAddress, OrderItem, OrderItemMeta, OrderMeta, Product, ProductMeta
from app import db
from datetime import datetime
from decimal import Decimal
from sqlalchemy import or_, desc
import pytz

bp = Blueprint('orders', __name__, url_prefix='/orders')


def get_gmt_time():
    """Obtener la hora actual en GMT/UTC como espera WooCommerce"""
    return datetime.utcnow()


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
    Listar pedidos con paginación y filtros

    Query params:
    - page: número de página
    - per_page: items por página
    - search: búsqueda por ID, email, nombre
    - status: filtrar por estado
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        status_filter = request.args.get('status', '', type=str)

        # Limitar per_page
        per_page = min(per_page, 100)

        # Query base
        query = Order.query

        # Filtro de búsqueda
        if search:
            # Buscar en pedidos o direcciones
            query = query.join(OrderAddress, Order.id == OrderAddress.order_id, isouter=True)
            query = query.filter(
                or_(
                    Order.id.like(f'%{search}%'),
                    Order.billing_email.like(f'%{search}%'),
                    OrderAddress.first_name.like(f'%{search}%'),
                    OrderAddress.last_name.like(f'%{search}%'),
                    OrderAddress.phone.like(f'%{search}%')
                )
            ).distinct()

        # Filtro de estado
        if status_filter:
            query = query.filter(Order.status == status_filter)

        # Ordenar por fecha descendente
        query = query.order_by(desc(Order.date_created_gmt))

        # Paginar
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Preparar datos
        orders_list = []
        for order in pagination.items:
            # Obtener dirección de facturación
            billing_address = order.addresses.filter_by(address_type='billing').first()

            # Contar items
            items_count = order.items.count()

            orders_list.append({
                'id': order.id,
                'status': order.status,
                'total': float(order.total_amount) if order.total_amount else 0,
                'currency': order.currency,
                'billing_email': order.billing_email,
                'customer_name': f"{billing_address.first_name} {billing_address.last_name}" if billing_address else 'N/A',
                'customer_phone': billing_address.phone if billing_address else 'N/A',
                'payment_method': order.payment_method_title or order.payment_method,
                'items_count': items_count,
                'date_created': order.date_created_gmt.strftime('%Y-%m-%d %H:%M:%S') if order.date_created_gmt else ''
            })

        return jsonify({
            'success': True,
            'orders': orders_list,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
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

        # ===== DIRECCIONES =====
        # Crear dirección de facturación
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

        # Usar misma dirección para envío
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
            item_metas = [
                ('_product_id', product_id),
                ('_variation_id', variation_id),
                ('_qty', quantity),
                ('_line_subtotal', str(line_subtotal.quantize(Decimal('0.01')))),
                ('_line_subtotal_tax', str(line_tax.quantize(Decimal('0.01')))),
                ('_line_total', str(line_subtotal.quantize(Decimal('0.01')))),
                ('_line_tax', str(line_tax.quantize(Decimal('0.01')))),
                ('_tax_class', ''),
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

            shipping_item = OrderItem(
                order_item_name='Envío',
                order_item_type='shipping',
                order_id=order.id
            )
            db.session.add(shipping_item)
            db.session.flush()

            shipping_metas = [
                ('method_id', 'flat_rate'),
                ('cost', str(shipping_subtotal.quantize(Decimal('0.01')))),
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

        # ===== METADATOS DEL PEDIDO =====
        # Construir índices de direcciones para búsqueda
        billing_index = f"{customer.get('first_name', '')} {customer.get('last_name', '')} {customer.get('company', '')} {customer.get('address_1', '')} {customer.get('city', '')} {customer.get('state', '')} {customer.get('postcode', '')} {customer.get('country', '')} {customer.get('email', '')} {customer.get('phone', '')}".strip()
        shipping_index = billing_index  # Usamos la misma dirección

        order_metas = [
            # Identificación
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

            # Attribution (rastreo de origen)
            ('_wc_order_attribution_source_type', 'direct'),
            ('_wc_order_attribution_referrer', 'whatsapp'),
            ('_wc_order_attribution_utm_source', 'whatsapp'),
            ('_wc_order_attribution_session_pages', '1'),
            ('_wc_order_attribution_session_count', '1'),
            ('_wc_order_attribution_user_agent', request.headers.get('User-Agent', '')[:200]),
        ]

        for meta_key, meta_value in order_metas:
            order_meta = OrderMeta(
                order_id=order.id,
                meta_key=meta_key,
                meta_value=str(meta_value)
            )
            db.session.add(order_meta)

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

        return jsonify({
            'success': True,
            'message': f'Pedido #{order.id} creado exitosamente',
            'order_id': order.id,
            'total': float(total_with_tax),
            'tax': float(tax_amount),
            'subtotal': float(subtotal)
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# Importar get_local_time
from config import get_local_time
