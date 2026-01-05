# app/routes/dispatch.py
"""
Módulo de Despacho Kanban

Blueprint para gestión visual de despachos organizados por método de envío.
Permite drag & drop de pedidos entre columnas, marcado de prioridades,
y trazabilidad completa de cambios.

Acceso exclusivo para usuario master (Jleon).
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Order, OrderMeta, DispatchHistory, DispatchPriority
from sqlalchemy import text, or_
from datetime import datetime, timedelta
from functools import wraps

# Crear blueprint
bp = Blueprint('dispatch', __name__, url_prefix='/dispatch')


# ============================================
# MIDDLEWARE DE AUTORIZACIÓN
# ============================================

def master_required(f):
    """
    Decorador para restringir acceso solo a usuarios con role 'master'

    Uso:
        @bp.route('/ruta')
        @login_required
        @master_required
        def mi_funcion():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'No autenticado'
            }), 401

        if current_user.role != 'master':
            current_app.logger.warning(
                f"Usuario {current_user.username} (role: {current_user.role}) "
                f"intentó acceder a módulo de despacho sin permisos"
            )
            return jsonify({
                'success': False,
                'error': 'Acceso denegado. Este módulo es exclusivo para usuarios master.'
            }), 403

        return f(*args, **kwargs)

    return decorated_function


# ============================================
# RUTAS PRINCIPALES
# ============================================

@bp.route('/')
@login_required
@master_required
def index():
    """
    Vista principal del tablero Kanban de despacho

    Muestra pedidos organizados por método de envío en columnas:
    - Olva Courier
    - Recojo en Almacén
    - Motorizado (CHAMO)
    - SHALOM
    - DINSIDES
    """
    current_app.logger.info(f"Usuario {current_user.username} accedió al módulo de despacho")

    return render_template(
        'dispatch_board.html',
        page_title='Módulo de Despacho',
        user=current_user
    )


# ============================================
# API ENDPOINTS
# ============================================

@bp.route('/api/orders', methods=['GET'])
@login_required
@master_required
def get_orders():
    """
    Obtener pedidos agrupados por método de envío

    Query Parameters:
        - date_from: Fecha inicio (YYYY-MM-DD)
        - date_to: Fecha fin (YYYY-MM-DD)
        - priority_only: Si es 'true', solo pedidos prioritarios
        - shipping_methods: Métodos de envío separados por coma

    Returns:
        JSON con pedidos agrupados por método de envío
    """
    try:
        # Parámetros de filtro
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        priority_only = request.args.get('priority_only', 'false').lower() == 'true'
        shipping_methods_filter = request.args.get('shipping_methods', '').split(',') if request.args.get('shipping_methods') else None

        # Query base: TODOS los pedidos wc-processing (WooCommerce nativos + WhatsApp)
        query = text("""
            SELECT DISTINCT
                o.id,
                COALESCE(om_number.meta_value, CONCAT('#', o.id)) as order_number,
                o.date_created_gmt,
                o.total_amount,
                o.status,
                o.billing_email,

                -- Datos de cliente
                ba.first_name,
                ba.last_name,
                ba.phone,

                -- Método de envío actual
                (SELECT oi.order_item_name
                 FROM wpyz_woocommerce_order_items oi
                 WHERE oi.order_id = o.id
                   AND oi.order_item_type = 'shipping'
                 LIMIT 1) as shipping_method,

                -- Prioridad (si existe)
                dp.is_priority,
                dp.priority_level,

                -- Tiempo sin mover (horas desde última actualización)
                TIMESTAMPDIFF(HOUR, o.date_updated_gmt, UTC_TIMESTAMP()) as hours_since_update,

                -- Usuario que creó el pedido
                om_created.meta_value as created_by

            FROM wpyz_wc_orders o

            -- Número de pedido (opcional - puede no tener W-XXXXX si es WooCommerce nativo)
            LEFT JOIN wpyz_wc_orders_meta om_number
                ON o.id = om_number.order_id
                AND om_number.meta_key = '_order_number'

            -- Dirección de facturación (datos de cliente)
            LEFT JOIN wpyz_wc_order_addresses ba
                ON o.id = ba.order_id
                AND ba.address_type = 'billing'

            -- Prioridades
            LEFT JOIN woo_dispatch_priorities dp
                ON o.id = dp.order_id

            -- Usuario que creó
            LEFT JOIN wpyz_wc_orders_meta om_created
                ON o.id = om_created.order_id
                AND om_created.meta_key = '_created_by'

            WHERE o.status = 'wc-processing'

            -- Filtro por fecha
            {date_filter}

            -- Filtro por prioridad
            {priority_filter}

            ORDER BY
                dp.is_priority DESC,
                dp.priority_level DESC,
                o.date_created_gmt DESC
        """)

        # Construir filtros dinámicos
        date_filter = ""
        priority_filter = ""
        params = {}

        if date_from and date_to:
            date_filter = "AND DATE(o.date_created_gmt) BETWEEN :date_from AND :date_to"
            params['date_from'] = date_from
            params['date_to'] = date_to

        if priority_only:
            priority_filter = "AND dp.is_priority = TRUE"

        # Reemplazar placeholders
        query_str = str(query).format(
            date_filter=date_filter,
            priority_filter=priority_filter
        )

        # Ejecutar query
        results = db.session.execute(text(query_str), params).fetchall()

        # Agrupar por método de envío
        orders_by_method = {
            'Olva Courier': [],
            'Recojo en Almacén': [],
            'Motorizado (CHAMO)': [],
            'SHALOM': [],
            'DINSIDES': []
        }

        for row in results:
            # Determinar método de envío
            shipping_method = row[9] or 'Sin método'

            # Mapear a columnas del tablero
            if 'Olva' in shipping_method:
                column = 'Olva Courier'
            elif 'Recojo' in shipping_method:
                column = 'Recojo en Almacén'
            elif 'CHAMO' in shipping_method or 'Motorizado' in shipping_method:
                column = 'Motorizado (CHAMO)'
            elif 'SHALOM' in shipping_method:
                column = 'SHALOM'
            elif 'DINSIDES' in shipping_method:
                column = 'DINSIDES'
            else:
                # Si no coincide con ninguno, asignar a columna por defecto
                column = 'Olva Courier'

            # Aplicar filtro de métodos si existe
            if shipping_methods_filter and column not in shipping_methods_filter:
                continue

            # Construir objeto de pedido
            order_data = {
                'id': row[0],
                'number': row[1],
                'date_created': row[2].strftime('%Y-%m-%d %H:%M') if row[2] else None,
                'total': float(row[3]) if row[3] else 0,
                'status': row[4],
                'email': row[5],
                'customer_name': f"{row[6]} {row[7]}" if row[6] and row[7] else 'N/A',
                'customer_phone': row[8] or 'N/A',
                'shipping_method': row[9] or 'Sin método',
                'is_priority': bool(row[10]) if row[10] is not None else False,
                'priority_level': row[11] or 'normal',
                'hours_since_update': row[12] or 0,
                'is_stale': (row[12] or 0) > 24,  # Más de 24h sin mover
                'created_by': row[13] or 'Desconocido'
            }

            orders_by_method[column].append(order_data)

        # Calcular estadísticas
        total_orders = sum(len(orders) for orders in orders_by_method.values())
        priority_orders = sum(
            1 for orders in orders_by_method.values()
            for order in orders
            if order['is_priority']
        )
        stale_orders = sum(
            1 for orders in orders_by_method.values()
            for order in orders
            if order['is_stale']
        )

        return jsonify({
            'success': True,
            'orders': orders_by_method,
            'stats': {
                'total': total_orders,
                'priority': priority_orders,
                'stale': stale_orders
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error obteniendo pedidos para despacho: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/move', methods=['POST'])
@login_required
@master_required
def move_order():
    """
    Mover pedido a otra columna (cambiar método de envío)

    Request Body:
        {
            "order_id": 123,
            "new_shipping_method": "Olva Courier"
        }

    Returns:
        JSON con confirmación del cambio
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        new_shipping_method = data.get('new_shipping_method')

        if not order_id or not new_shipping_method:
            return jsonify({
                'success': False,
                'error': 'Parámetros faltantes: order_id y new_shipping_method son requeridos'
            }), 400

        # Obtener pedido
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': f'Pedido {order_id} no encontrado'
            }), 404

        # Obtener número de pedido
        order_number = order.get_meta('_order_number')

        # Obtener método de envío actual
        current_shipping = db.session.execute(
            text("""
                SELECT order_item_name
                FROM wpyz_woocommerce_order_items
                WHERE order_id = :order_id
                  AND order_item_type = 'shipping'
                LIMIT 1
            """),
            {'order_id': order_id}
        ).scalar()

        # Actualizar método de envío en la base de datos
        db.session.execute(
            text("""
                UPDATE wpyz_woocommerce_order_items
                SET order_item_name = :new_method
                WHERE order_id = :order_id
                  AND order_item_type = 'shipping'
            """),
            {
                'order_id': order_id,
                'new_method': new_shipping_method
            }
        )

        # Registrar en historial
        history_entry = DispatchHistory(
            order_id=order_id,
            order_number=order_number,
            previous_shipping_method=current_shipping,
            new_shipping_method=new_shipping_method,
            changed_by=current_user.username,
            changed_at=datetime.utcnow()
        )
        db.session.add(history_entry)

        # Actualizar date_updated_gmt del pedido
        order.date_updated_gmt = datetime.utcnow()

        db.session.commit()

        current_app.logger.info(
            f"Pedido {order_number} movido de '{current_shipping}' a '{new_shipping_method}' "
            f"por {current_user.username}"
        )

        return jsonify({
            'success': True,
            'message': f'Pedido {order_number} movido exitosamente',
            'order_id': order_id,
            'order_number': order_number,
            'previous_method': current_shipping,
            'new_method': new_shipping_method
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error moviendo pedido: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/priority', methods=['POST'])
@login_required
@master_required
def set_priority():
    """
    Marcar/desmarcar pedido como prioritario

    Request Body:
        {
            "order_id": 123,
            "is_priority": true,
            "priority_level": "urgent",  // 'normal', 'high', 'urgent'
            "note": "Cliente requiere envío urgente"
        }

    Returns:
        JSON con confirmación
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        is_priority = data.get('is_priority', False)
        priority_level = data.get('priority_level', 'normal')
        note = data.get('note', '')

        if not order_id:
            return jsonify({
                'success': False,
                'error': 'order_id es requerido'
            }), 400

        # Obtener pedido
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': f'Pedido {order_id} no encontrado'
            }), 404

        order_number = order.get_meta('_order_number')

        # Buscar o crear registro de prioridad
        priority = DispatchPriority.query.filter_by(order_id=order_id).first()

        if not priority:
            priority = DispatchPriority(
                order_id=order_id,
                order_number=order_number
            )
            db.session.add(priority)

        # Actualizar valores
        priority.is_priority = is_priority
        priority.priority_level = priority_level if is_priority else 'normal'
        priority.marked_by = current_user.username if is_priority else None
        priority.marked_at = datetime.utcnow() if is_priority else None
        priority.priority_note = note if is_priority else None

        db.session.commit()

        action = "marcado como prioritario" if is_priority else "desmarcado como prioritario"
        current_app.logger.info(
            f"Pedido {order_number} {action} (nivel: {priority_level}) "
            f"por {current_user.username}"
        )

        return jsonify({
            'success': True,
            'message': f'Pedido {order_number} {action}',
            'order_id': order_id,
            'order_number': order_number,
            'is_priority': is_priority,
            'priority_level': priority_level
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error configurando prioridad: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/note', methods=['POST'])
@login_required
@master_required
def add_note():
    """
    Agregar nota de despacho a un pedido

    Request Body:
        {
            "order_id": 123,
            "note": "Empacar con cuidado - producto frágil"
        }

    Returns:
        JSON con confirmación
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        note = data.get('note', '').strip()

        if not order_id or not note:
            return jsonify({
                'success': False,
                'error': 'order_id y note son requeridos'
            }), 400

        # Obtener pedido
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': f'Pedido {order_id} no encontrado'
            }), 404

        order_number = order.get_meta('_order_number')

        # Obtener método de envío actual
        current_shipping = db.session.execute(
            text("""
                SELECT order_item_name
                FROM wpyz_woocommerce_order_items
                WHERE order_id = :order_id
                  AND order_item_type = 'shipping'
                LIMIT 1
            """),
            {'order_id': order_id}
        ).scalar()

        # Crear entrada en historial con solo nota (sin cambio de método)
        history_entry = DispatchHistory(
            order_id=order_id,
            order_number=order_number,
            previous_shipping_method=None,
            new_shipping_method=current_shipping or 'Sin método',
            changed_by=current_user.username,
            changed_at=datetime.utcnow(),
            dispatch_note=note
        )
        db.session.add(history_entry)
        db.session.commit()

        current_app.logger.info(
            f"Nota agregada al pedido {order_number} por {current_user.username}: {note[:50]}..."
        )

        return jsonify({
            'success': True,
            'message': 'Nota agregada exitosamente',
            'order_id': order_id,
            'order_number': order_number,
            'note': note
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error agregando nota: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/history/<int:order_id>', methods=['GET'])
@login_required
@master_required
def get_history(order_id):
    """
    Obtener historial completo de cambios de un pedido

    Returns:
        JSON con lista de cambios ordenados cronológicamente
    """
    try:
        history = DispatchHistory.query.filter_by(order_id=order_id)\
            .order_by(DispatchHistory.changed_at.desc())\
            .all()

        return jsonify({
            'success': True,
            'order_id': order_id,
            'history': [entry.to_dict() for entry in history]
        })

    except Exception as e:
        current_app.logger.error(f"Error obteniendo historial: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/order/<int:order_id>', methods=['GET'])
@login_required
@master_required
def get_order_detail(order_id):
    """
    Obtener detalles completos de un pedido incluyendo productos

    Returns:
        JSON con información completa del pedido y lista de productos
    """
    try:
        # Query para obtener detalles del pedido
        order_query = text("""
            SELECT
                o.id,
                COALESCE(om_number.meta_value, CONCAT('#', o.id)) as order_number,
                o.date_created_gmt,
                o.total_amount,
                o.status,
                o.billing_email,
                ba.first_name,
                ba.last_name,
                ba.phone,
                (SELECT oi.order_item_name
                 FROM wpyz_woocommerce_order_items oi
                 WHERE oi.order_id = o.id
                   AND oi.order_item_type = 'shipping'
                 LIMIT 1) as shipping_method,
                om_created.meta_value as created_by
            FROM wpyz_wc_orders o
            LEFT JOIN wpyz_wc_orders_meta om_number
                ON o.id = om_number.order_id
                AND om_number.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_order_addresses ba
                ON o.id = ba.order_id
                AND ba.address_type = 'billing'
            LEFT JOIN wpyz_wc_orders_meta om_created
                ON o.id = om_created.order_id
                AND om_created.meta_key = '_created_by'
            WHERE o.id = :order_id
        """)

        order_result = db.session.execute(order_query, {'order_id': order_id}).fetchone()

        if not order_result:
            return jsonify({
                'success': False,
                'error': f'Pedido {order_id} no encontrado'
            }), 404

        # Query para obtener productos del pedido con SKU
        # NOTA: Los atributos los extraemos del order_item_name directamente
        products_query = text("""
            SELECT
                oi.order_item_name as product_name,
                oim_qty.meta_value as quantity,
                COALESCE(oim_variation_id.meta_value, oim_product_id.meta_value) as product_id,
                (SELECT pm.meta_value
                 FROM wpyz_postmeta pm
                 WHERE pm.post_id = COALESCE(oim_variation_id.meta_value, oim_product_id.meta_value)
                   AND pm.meta_key = '_sku'
                 LIMIT 1) as sku
            FROM wpyz_woocommerce_order_items oi
            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_qty
                ON oi.order_item_id = oim_qty.order_item_id
                AND oim_qty.meta_key = '_qty'
            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_product_id
                ON oi.order_item_id = oim_product_id.order_item_id
                AND oim_product_id.meta_key = '_product_id'
            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_variation_id
                ON oi.order_item_id = oim_variation_id.order_item_id
                AND oim_variation_id.meta_key = '_variation_id'
                AND oim_variation_id.meta_value != '0'
            WHERE oi.order_id = :order_id
              AND oi.order_item_type = 'line_item'
            ORDER BY oi.order_item_id
        """)

        products_result = db.session.execute(products_query, {'order_id': order_id}).fetchall()

        # Construir lista de productos con imágenes
        products_list = []
        for row in products_result:
            product_id = row[2]
            product_name_raw = row[0]

            # DEBUG: Log para ver qué está trayendo la BD
            current_app.logger.info(f"DEBUG - Product name raw from DB: {product_name_raw}")

            # Limpiar el nombre del producto - eliminar basura técnica de WooCommerce
            # Formato sucio: "Nombre - Atributos | line_subtotal_tax: ... | reduced_stock: ..."
            # Queremos solo: "Nombre - Atributos"
            product_name_clean = product_name_raw
            if ' | line' in product_name_raw or ' | reduced' in product_name_raw or ' | tax' in product_name_raw:
                # Eliminar todo después del primer " | " que contiene datos técnicos
                product_name_clean = product_name_raw.split(' | line')[0].split(' | reduced')[0].split(' | tax')[0].strip()

            # Extraer atributos del nombre limpio del producto
            # Formato: "Nombre - Atributo1, Atributo2"
            # Los atributos están después del último " - " o después de la primera coma
            attributes_from_name = None
            clean_product_name = product_name_clean

            if ' - ' in product_name_clean:
                # Dividir por el último " - "
                parts = product_name_clean.rsplit(' - ', 1)
                if len(parts) == 2:
                    clean_product_name = parts[0].strip()
                    # La segunda parte contiene los atributos
                    attributes_from_name = parts[1].strip()
            elif ',' in product_name_clean and ' | ' not in product_name_clean:
                # Si no hay " - " pero hay coma (y no es basura técnica), todo después de la coma son atributos
                parts = product_name_clean.split(',', 1)
                if len(parts) == 2:
                    clean_product_name = parts[0].strip()
                    attributes_from_name = parts[1].strip()

            # Los atributos solo vienen del nombre (row[4] ya no existe - eliminamos el GROUP_CONCAT)
            final_attributes = attributes_from_name

            # Obtener imagen del producto
            image_url = None
            if product_id:
                image_query = text("""
                    SELECT pm.meta_value as image_id
                    FROM wpyz_postmeta pm
                    WHERE pm.post_id = :product_id
                      AND pm.meta_key = '_thumbnail_id'
                    LIMIT 1
                """)
                image_result = db.session.execute(image_query, {'product_id': product_id}).fetchone()

                if image_result and image_result[0]:
                    image_id = image_result[0]
                    # Obtener URL de la imagen
                    image_url_query = text("""
                        SELECT guid
                        FROM wpyz_posts
                        WHERE ID = :image_id
                    """)
                    image_url_result = db.session.execute(image_url_query, {'image_id': image_id}).fetchone()
                    if image_url_result:
                        image_url = image_url_result[0]

            products_list.append({
                'name': clean_product_name,
                'quantity': int(row[1]) if row[1] else 1,
                'sku': row[3] if row[3] else None,
                'attributes': final_attributes,
                'image': image_url
            })

        # Construir respuesta
        order_data = {
            'id': order_result[0],
            'number': order_result[1],
            'date_created': order_result[2].strftime('%Y-%m-%d %H:%M') if order_result[2] else None,
            'total': float(order_result[3]) if order_result[3] else 0,
            'status': order_result[4],
            'email': order_result[5],
            'customer_name': f"{order_result[6]} {order_result[7]}" if order_result[6] and order_result[7] else 'N/A',
            'customer_phone': order_result[8] or 'N/A',
            'shipping_method': order_result[9] or 'Sin método',
            'created_by': order_result[10] or 'Desconocido',
            'products': products_list
        }

        return jsonify({
            'success': True,
            'order': order_data
        })

    except Exception as e:
        current_app.logger.error(f"Error obteniendo detalle de pedido: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
