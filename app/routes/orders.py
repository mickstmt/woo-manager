# app/routes/orders.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import Order, OrderAddress, OrderItem, OrderItemMeta, OrderMeta, Product, ProductMeta
from app import db
from datetime import datetime
from decimal import Decimal
from sqlalchemy import or_, desc

bp = Blueprint('orders', __name__, url_prefix='/orders')


@bp.route('/')
@login_required
def index():
    """
    Vista principal del módulo de pedidos

    URL: http://localhost:5000/orders/
    """
    return render_template('orders.html', title='Gestión de Pedidos')


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


@bp.route('/create', methods=['POST'])
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
                "price": 50.00
            }
        ],
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

        # Calcular totales
        subtotal = Decimal('0')
        tax_rate = Decimal('0.18')  # IGV 18%

        for item_data in items_data:
            item_subtotal = Decimal(str(item_data['price'])) * item_data['quantity']
            subtotal += item_subtotal

        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        # Crear pedido
        order = Order(
            status='wc-processing',  # Estado inicial
            currency='PEN',
            type='shop_order',
            tax_amount=tax_amount,
            total_amount=total_amount,
            customer_id=0,  # Sin cuenta de usuario
            billing_email=customer.get('email'),
            date_created_gmt=get_local_time(),
            date_updated_gmt=get_local_time(),
            payment_method=data.get('payment_method', 'cod'),
            payment_method_title=data.get('payment_method_title', 'Pago manual'),
            customer_note=data.get('customer_note', ''),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )

        db.session.add(order)
        db.session.flush()  # Para obtener el ID del pedido

        # Crear dirección de facturación
        billing_address = OrderAddress(
            order_id=order.id,
            address_type='billing',
            first_name=customer.get('first_name'),
            last_name=customer.get('last_name'),
            company=customer.get('company', ''),
            address_1=customer.get('address_1'),
            address_2=customer.get('address_2', ''),
            city=customer.get('city'),
            state=customer.get('state'),
            postcode=customer.get('postcode'),
            country=customer.get('country', 'PE'),
            email=customer.get('email'),
            phone=customer.get('phone')
        )
        db.session.add(billing_address)

        # Usar misma dirección para envío (por defecto)
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
            postcode=customer.get('postcode'),
            country=customer.get('country', 'PE'),
            email=customer.get('email'),
            phone=customer.get('phone')
        )
        db.session.add(shipping_address)

        # Agregar items al pedido
        for item_data in items_data:
            product_id = item_data['product_id']
            variation_id = item_data.get('variation_id', 0)
            quantity = item_data['quantity']
            price = Decimal(str(item_data['price']))

            # Obtener producto
            product = Product.query.get(product_id)
            if not product:
                raise Exception(f'Producto {product_id} no encontrado')

            # Calcular subtotal e impuestos del item
            line_subtotal = price * quantity
            line_tax = line_subtotal * tax_rate
            line_total = line_subtotal

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
                ('_line_subtotal', str(line_subtotal)),
                ('_line_subtotal_tax', str(line_tax)),
                ('_line_total', str(line_total)),
                ('_line_tax', str(line_tax)),
                ('_tax_class', ''),
            ]

            for meta_key, meta_value in item_metas:
                item_meta = OrderItemMeta(
                    order_item_id=order_item.order_item_id,
                    meta_key=meta_key,
                    meta_value=str(meta_value)
                )
                db.session.add(item_meta)

            # Reducir stock
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

        # Agregar metadatos del pedido
        order_metas = [
            ('_created_via', 'woocommerce-manager'),
            ('_order_source', 'whatsapp'),
            ('_created_by', current_user.username),
            ('_prices_include_tax', 'no'),
            ('_cart_discount', '0'),
            ('_cart_discount_tax', '0'),
            ('_order_shipping', '0'),
            ('_order_shipping_tax', '0'),
            ('_order_tax', str(tax_amount)),
            ('_order_total', str(total_amount)),
            ('_order_version', '9.0.0'),
        ]

        for meta_key, meta_value in order_metas:
            order_meta = OrderMeta(
                order_id=order.id,
                meta_key=meta_key,
                meta_value=str(meta_value)
            )
            db.session.add(order_meta)

        # Guardar todo
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Pedido #{order.id} creado exitosamente',
            'order_id': order.id,
            'total': float(total_amount)
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
