# app/routes/dispatch.py
"""
Módulo de Despacho Kanban

Blueprint para gestión visual de despachos organizados por método de envío.
TODOS los pedidos en estado wc-processing inician en la columna "Por Asignar".
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
import unicodedata

# Crear blueprint
bp = Blueprint('dispatch', __name__, url_prefix='/dispatch')


# ============================================
# MAPEO DE MÉTODOS DE ENVÍO A COLUMNAS
# ============================================

# Mapeo de shipping_method_id (post_id de wpyz_posts) a columnas del Kanban
SHIPPING_METHOD_TO_COLUMN = {
    # SHALOM
    '29884': 'SHALOM',  # Envio Shalom 10
    '15347': 'SHALOM',  # Envio Shalom 12
    '16017': 'SHALOM',  # Zona Maynas Iquitos

    # OLVA COURIER
    '15305': 'Olva Courier',  # Zona Envio Provincia 12.7
    '15369': 'Olva Courier',  # Zona Olva Ica Pisco y Zonas de Lima
    '15310': 'Olva Courier',  # Zona Olva Lima Provincia S/31.90
    '15306': 'Olva Courier',  # Zona Olva Provincia 13.79 13.80
    '15307': 'Olva Courier',  # Zona Olva Provincia 20.7
    '15308': 'Olva Courier',  # Zona Olva Provincia 24.8
    '15311': 'Olva Courier',  # Zona Olva Provincia 32.7 33.70
    '15312': 'Olva Courier',  # Zona Olva Provincia 39.97
    '15304': 'Olva Courier',  # Zona Olva Provincia 9.1
    '15355': 'Olva Courier',  # Zona Olva S/6.90 Lima

    # DINSIDES
    '40672': 'DINSIDES',  # Lima Sur Envio Rapido
    '15302': 'DINSIDES',  # Zona Envio Rapido A
    '15303': 'DINSIDES',  # Zona Envio Rapido B
    '21722': 'DINSIDES',  # Zona Envio Rapido C
    '15300': 'DINSIDES',  # Zona Envio Rapido D
    '15352': 'DINSIDES',  # Zona Rapido L-M-V (1)
    '15354': 'DINSIDES',  # Zona Rapido L-M-V (3)

    # RECOJO EN ALMACÉN
    '15360': 'Recojo en Almacén',  # Zona Recojo
}


def normalize_text(text):
    """
    Normaliza texto removiendo acentos y convirtiéndolo a minúsculas.

    Args:
        text: String a normalizar

    Returns:
        str: Texto normalizado sin acentos en minúsculas
    """
    # Normalizar a NFD (Canonical Decomposition) y remover marcas de acento
    nfd = unicodedata.normalize('NFD', text)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower()


def get_column_from_shipping_method(order_id):
    """
    Determina la columna del Kanban basándose en el método de envío del pedido.

    Args:
        order_id: ID del pedido

    Returns:
        str: Nombre de la columna ('SHALOM', 'Olva Courier', 'DINSIDES', 'Recojo en Almacén',
             'Motorizado (CHAMO)', o 'Por Asignar')
    """
    try:
        # Obtener el nombre del método de envío (con fallback para pedidos sin shipping item)
        query = text("""
            SELECT
                COALESCE(
                    (SELECT oi.order_item_name
                     FROM wpyz_woocommerce_order_items oi
                     WHERE oi.order_id = o.id
                       AND oi.order_item_type = 'shipping'
                     LIMIT 1),
                    -- Fallback: extraer desde _billing_entrega metadata
                    CASE
                        WHEN om_billing_entrega.meta_value = 'billing_recojo' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value LIKE '%recojo%' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value = 'billing_address' THEN 'Envío a domicilio'
                        ELSE NULL
                    END
                ) as shipping_method
            FROM wpyz_wc_orders o
            LEFT JOIN wpyz_wc_orders_meta om_billing_entrega
                ON o.id = om_billing_entrega.order_id
                AND om_billing_entrega.meta_key = '_billing_entrega'
            WHERE o.id = :order_id
        """)

        result = db.session.execute(query, {'order_id': order_id}).fetchone()

        if result and result[0]:
            # Normalizar el nombre del método de envío (quitar acentos y minúsculas)
            shipping_method_name = normalize_text(result[0])

            # Mapeo por palabras clave en el nombre del método (sin acentos)
            # SHALOM
            if 'shalom' in shipping_method_name or 'maynas' in shipping_method_name or 'iquitos' in shipping_method_name:
                return 'SHALOM'

            # OLVA COURIER
            elif 'olva' in shipping_method_name:
                return 'Olva Courier'

            # RECOJO EN ALMACÉN
            elif 'recojo' in shipping_method_name:
                return 'Recojo en Almacén'

            # DINSIDES (Envío rápido, Lima Sur, 1 día hábil, etc.)
            # Búsqueda sin acentos: "envio 1 dia habil" coincide con "Envío 1 día hábil"
            elif any(keyword in shipping_method_name for keyword in ['rapido', 'lima sur', 'envio rapido', '1 dia', 'dia habil']):
                return 'DINSIDES'

            else:
                current_app.logger.warning(f"[DISPATCH] Order {order_id}: Nombre '{result[0]}' NO coincide con ningún patrón (normalizado: '{shipping_method_name}')")

        else:
            current_app.logger.warning(f"[DISPATCH] Order {order_id}: NO tiene método de envío")

        # Si no se encuentra mapeo, va a "Por Asignar"
        current_app.logger.info(f"[DISPATCH] Order {order_id}: Asignado a 'Por Asignar' (sin mapeo)")
        return 'Por Asignar'

    except Exception as e:
        current_app.logger.error(f"[DISPATCH] Error obteniendo columna para pedido {order_id}: {str(e)}")
        return 'Por Asignar'


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
    - Por Asignar (TODOS los pedidos wc-processing inician aquí)
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

@bp.route('/api/debug', methods=['GET'])
@login_required
@master_required
def debug_params():
    """
    Endpoint temporal de debug para ver qué parámetros llegan
    """
    return jsonify({
        'success': True,
        'debug': {
            'all_args': dict(request.args),
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
            'priority_only': request.args.get('priority_only'),
            'raw_query_string': request.query_string.decode('utf-8')
        }
    })


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

        # Convertir formato de fecha si viene en formato dd/mm/yyyy a yyyy-mm-dd
        if date_from and '/' in date_from:
            # Formato dd/mm/yyyy -> yyyy-mm-dd
            parts = date_from.split('/')
            if len(parts) == 3:
                date_from = f"{parts[2]}-{parts[1]}-{parts[0]}"

        if date_to and '/' in date_to:
            # Formato dd/mm/yyyy -> yyyy-mm-dd
            parts = date_to.split('/')
            if len(parts) == 3:
                date_to = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Query base: TODOS los pedidos wc-processing (WooCommerce nativos + WhatsApp)
        query = text("""
            SELECT DISTINCT
                o.id,
                COALESCE(om_number.meta_value, CONCAT('#', o.id)) as order_number,
                om_number.meta_value as whatsapp_number,  -- Número W-XXXXX si existe
                DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR) as date_created_local,
                o.total_amount,
                o.status,
                o.billing_email,

                -- Datos de cliente
                ba.first_name,
                ba.last_name,
                ba.phone,

                -- Método de envío (con fallback para pedidos sin shipping item)
                COALESCE(
                    (SELECT oi.order_item_name
                     FROM wpyz_woocommerce_order_items oi
                     WHERE oi.order_id = o.id
                       AND oi.order_item_type = 'shipping'
                     LIMIT 1),
                    -- Fallback: extraer desde _billing_entrega metadata
                    CASE
                        WHEN om_billing_entrega.meta_value = 'billing_recojo' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value LIKE '%recojo%' THEN 'Recojo en Almacén'
                        WHEN om_billing_entrega.meta_value = 'billing_address' THEN 'Envío a domicilio'
                        ELSE NULL
                    END
                ) as shipping_method,

                -- Prioridad (si existe)
                dp.is_priority,
                dp.priority_level,

                -- Tiempo sin mover (horas desde última actualización)
                TIMESTAMPDIFF(HOUR, o.date_updated_gmt, UTC_TIMESTAMP()) as hours_since_update,

                -- Usuario que creó el pedido
                om_created.meta_value as created_by,

                -- Distrito de envío (para pedidos 1 día hábil)
                sa.city as shipping_district

            FROM wpyz_wc_orders o

            -- Número de pedido (opcional - puede no tener W-XXXXX si es WooCommerce nativo)
            LEFT JOIN wpyz_wc_orders_meta om_number
                ON o.id = om_number.order_id
                AND om_number.meta_key = '_order_number'

            -- Dirección de facturación (datos de cliente)
            LEFT JOIN wpyz_wc_order_addresses ba
                ON o.id = ba.order_id
                AND ba.address_type = 'billing'

            -- Dirección de envío (para obtener distrito)
            LEFT JOIN wpyz_wc_order_addresses sa
                ON o.id = sa.order_id
                AND sa.address_type = 'shipping'

            -- Prioridades
            LEFT JOIN woo_dispatch_priorities dp
                ON o.id = dp.order_id

            -- Usuario que creó
            LEFT JOIN wpyz_wc_orders_meta om_created
                ON o.id = om_created.order_id
                AND om_created.meta_key = '_created_by'

            -- Metadata de tipo de entrega (fallback para shipping_method)
            LEFT JOIN wpyz_wc_orders_meta om_billing_entrega
                ON o.id = om_billing_entrega.order_id
                AND om_billing_entrega.meta_key = '_billing_entrega'

            WHERE o.status = 'wc-processing'

            -- Filtro por fecha
            {date_filter}

            -- Filtro por prioridad
            {priority_filter}

            ORDER BY
                dp.is_priority DESC,
                dp.priority_level DESC,
                hours_since_update DESC  -- Pedidos con más retraso primero
        """)

        # Construir filtros dinámicos
        date_filter = ""
        priority_filter = ""
        params = {}

        # NOTA: El filtro de fechas es OPCIONAL
        # Por defecto, muestra TODOS los pedidos en estado wc-processing
        # Solo filtra por fecha si el usuario aplica el filtro manualmente
        # IMPORTANTE: Usar DATE_SUB para convertir GMT a hora de Perú (UTC-5)
        if date_from and date_to:
            date_filter = "AND DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :date_from AND :date_to"
            params['date_from'] = date_from
            params['date_to'] = date_to

        if priority_only:
            priority_filter = "AND dp.is_priority = TRUE"

        # Reemplazar placeholders
        query_str = str(query).format(
            date_filter=date_filter,
            priority_filter=priority_filter
        )

        # Log para debug
        current_app.logger.info("="*80)
        current_app.logger.info(f"DISPATCH API - GET ORDERS REQUEST")
        current_app.logger.info(f"date_from (convertido): {date_from}")
        current_app.logger.info(f"date_to (convertido): {date_to}")
        current_app.logger.info(f"priority_only: {priority_only}")
        current_app.logger.info(f"Query params: {params}")
        current_app.logger.info(f"Date filter SQL: {date_filter}")
        current_app.logger.info("="*80)

        # Ejecutar query
        results = db.session.execute(text(query_str), params).fetchall()

        current_app.logger.info(f"✓ Pedidos encontrados: {len(results)}")
        if len(results) > 0:
            current_app.logger.info(f"  Primer pedido: ID={results[0][0]}, Numero={results[0][1]}, Fecha={results[0][2]}")
        current_app.logger.info("="*80)

        # Agrupar por método de envío
        orders_by_method = {
            'Por Asignar': [],
            'Olva Courier': [],
            'Recojo en Almacén': [],
            'Motorizado (CHAMO)': [],
            'SHALOM': [],
            'DINSIDES': []
        }

        # Obtener última ubicación de cada pedido desde el historial
        order_ids = [row[0] for row in results]
        last_positions = {}

        if order_ids:
            # Query para obtener el último movimiento de cada pedido
            positions_query = text("""
                SELECT
                    dh.order_id,
                    dh.new_shipping_method
                FROM woo_dispatch_history dh
                INNER JOIN (
                    SELECT order_id, MAX(changed_at) as last_changed
                    FROM woo_dispatch_history
                    WHERE order_id IN :order_ids
                    GROUP BY order_id
                ) latest ON dh.order_id = latest.order_id
                    AND dh.changed_at = latest.last_changed
            """)

            positions_result = db.session.execute(
                positions_query,
                {'order_ids': tuple(order_ids)}
            ).fetchall()

            # Mapear order_id -> última columna
            for pos_row in positions_result:
                last_positions[pos_row[0]] = pos_row[1]

        for row in results:
            order_id = row[0]

            # Verificar si el pedido tiene un movimiento previo en el historial
            if order_id in last_positions:
                # Si tiene historial, usar la última posición guardada
                column = last_positions[order_id]
            else:
                # Si no hay historial, determinar columna automáticamente según método de envío
                column = get_column_from_shipping_method(order_id)

            # Aplicar filtro de métodos si existe
            if shipping_methods_filter and column not in shipping_methods_filter:
                continue

            # Construir objeto de pedido
            whatsapp_number = row[2]  # W-XXXXX si existe, None si no
            display_number = row[1]   # Ya viene como COALESCE(W-XXXXX, #ID)

            # Si es pedido WhatsApp, mostrar #ID principal y W-XXXXX secundario
            if whatsapp_number and whatsapp_number.startswith('W-'):
                display_number = f"#{row[0]}"  # ID original
                whatsapp_label = whatsapp_number  # W-XXXXX
            else:
                whatsapp_label = None

            order_data = {
                'id': row[0],
                'number': display_number,
                'whatsapp_number': whatsapp_label,  # W-XXXXX para mostrar en gris
                'date_created': row[3].strftime('%Y-%m-%d %H:%M') if row[3] else None,
                'total': float(row[4]) if row[4] else 0,
                'status': row[5],
                'email': row[6],
                'customer_name': f"{row[7]} {row[8]}" if row[7] and row[8] else 'N/A',
                'customer_phone': row[9] or 'N/A',
                'shipping_method': row[10] or 'Sin método',
                'is_priority': bool(row[11]) if row[11] is not None else False,
                'priority_level': row[12] or 'normal',
                'hours_since_update': row[13] or 0,
                'is_stale': (row[13] or 0) > 24,  # Más de 24h sin mover
                'created_by': row[14] or 'Desconocido',
                'shipping_district': row[15] or None  # Distrito de envío
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

        # Obtener número de pedido (puede ser None para pedidos WooCommerce nativos)
        order_number = order.get_meta('_order_number')
        if not order_number:
            order_number = f"#{order_id}"

        # Obtener método de envío actual (ORIGINAL del pedido)
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

        # NO actualizar el método de envío en la base de datos
        # Solo registrar el movimiento en el historial de despacho
        # Esto permite mantener el método de envío original del pedido

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


@bp.route('/api/add-tracking', methods=['POST'])
@login_required
@master_required
def add_tracking():
    """
    Agregar información de tracking a un pedido.

    Request Body:
        {
            "order_id": 41608,
            "tracking_number": "IZI26010841608660",
            "shipping_provider": "Motorizado Izi",
            "date_shipped": "2026-01-08",  // Opcional, por defecto fecha actual
            "mark_as_shipped": true  // Opcional, si cambiar a wc-completed
        }

    Returns:
        JSON con confirmación del cambio
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        tracking_number = data.get('tracking_number')
        shipping_provider = data.get('shipping_provider')
        date_shipped = data.get('date_shipped')
        mark_as_shipped = data.get('mark_as_shipped', False)

        # Validar parámetros requeridos
        if not all([order_id, tracking_number, shipping_provider]):
            return jsonify({
                'success': False,
                'error': 'Parámetros faltantes: order_id, tracking_number y shipping_provider son requeridos'
            }), 400

        # Validar que el pedido existe
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'error': f'Pedido {order_id} no encontrado'
            }), 404

        # Fecha de envío (por defecto hoy)
        if not date_shipped:
            from datetime import date
            date_shipped = date.today().strftime('%Y-%m-%d')

        # Timestamp actual
        timestamp = int(datetime.utcnow().timestamp())

        # Crear el array de tracking items en formato PHP serializado
        # Estructura: array con un item que contiene tracking_number, tracking_provider, date_shipped
        tracking_items = [{
            'tracking_number': tracking_number,
            'tracking_provider': shipping_provider,
            'custom_tracking_provider': '',
            'custom_tracking_link': '',
            'date_shipped': date_shipped,
            'tracking_id': str(timestamp)  # ID único basado en timestamp
        }]

        # Serializar a formato PHP
        import phpserialize
        serialized_items = phpserialize.dumps(tracking_items).decode('utf-8')

        current_app.logger.info(f"[TRACKING] Order {order_id}: Agregando tracking {tracking_number} con provider '{shipping_provider}'")
        current_app.logger.info(f"[TRACKING] Serialized data: {serialized_items}")

        # Guardar metadatos en wpyz_postmeta (para compatibilidad con el plugin)
        # 1. _tracking_number
        query_tracking_number = text("""
            INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
            VALUES (:order_id, '_tracking_number', :tracking_number)
            ON DUPLICATE KEY UPDATE meta_value = :tracking_number
        """)
        db.session.execute(query_tracking_number, {
            'order_id': order_id,
            'tracking_number': tracking_number
        })

        # 2. _tracking_provider
        query_tracking_provider = text("""
            INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
            VALUES (:order_id, '_tracking_provider', :shipping_provider)
            ON DUPLICATE KEY UPDATE meta_value = :shipping_provider
        """)
        db.session.execute(query_tracking_provider, {
            'order_id': order_id,
            'shipping_provider': shipping_provider
        })

        # 3. _wc_shipment_tracking_items (PHP serialized array)
        query_tracking_items = text("""
            INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
            VALUES (:order_id, '_wc_shipment_tracking_items', :serialized_items)
            ON DUPLICATE KEY UPDATE meta_value = :serialized_items
        """)
        db.session.execute(query_tracking_items, {
            'order_id': order_id,
            'serialized_items': serialized_items
        })

        # Guardar también en wpyz_wc_orders_meta (HPOS)
        query_hpos_tracking = text("""
            INSERT INTO wpyz_wc_orders_meta (order_id, meta_key, meta_value)
            VALUES (:order_id, '_wc_shipment_tracking_items', :serialized_items)
            ON DUPLICATE KEY UPDATE meta_value = :serialized_items
        """)
        db.session.execute(query_hpos_tracking, {
            'order_id': order_id,
            'serialized_items': serialized_items
        })

        # Si se marca como enviado, cambiar el estado a wc-completed
        if mark_as_shipped:
            current_app.logger.info(f"[TRACKING] Order {order_id}: Cambiando estado a wc-completed")
            order.status = 'wc-completed'
            order.date_updated_gmt = datetime.utcnow()

        # COMMIT INMEDIATO: Guardar cambios en BD antes de llamar a API externa
        # Esto permite responder rápido al usuario sin esperar WooCommerce
        db.session.commit()

        # Triggerar email usando WooCommerce API (después del commit)
        if mark_as_shipped:
            try:
                from woocommerce import API
                wc_api = API(
                    url=current_app.config['WC_API_URL'],
                    consumer_key=current_app.config['WC_CONSUMER_KEY'],
                    consumer_secret=current_app.config['WC_CONSUMER_SECRET'],
                    version="wc/v3",
                    timeout=10  # Reducir timeout de 30s a 10s
                )

                # Actualizar pedido via API para triggerar emails
                # Preservar payment_method del pedido
                payment_method = order.get_meta('_payment_method') or order.payment_method

                wc_api.put(f"orders/{order_id}", {
                    "status": "completed",
                    "payment_method": payment_method,
                    "meta_data": [
                        {"key": "_tracking_number", "value": tracking_number},
                        {"key": "_tracking_provider", "value": shipping_provider},
                        {"key": "_wc_shipment_tracking_items", "value": serialized_items}
                    ]
                })

                current_app.logger.info(f"[TRACKING] Order {order_id}: Email de tracking enviado via WooCommerce API")

            except Exception as email_error:
                current_app.logger.error(f"[TRACKING] Error al enviar email via API: {str(email_error)}")
                # No fallar la operación si el email falla - tracking ya está guardado

        # Obtener número de pedido
        order_number = order.get_meta('_order_number')
        if not order_number:
            order_number = f"#{order_id}"

        current_app.logger.info(
            f"Tracking agregado a pedido {order_number}: {tracking_number} ({shipping_provider}) "
            f"por {current_user.username}"
        )

        return jsonify({
            'success': True,
            'message': f'Tracking agregado exitosamente al pedido {order_number}',
            'order_id': order_id,
            'order_number': order_number,
            'tracking_number': tracking_number,
            'shipping_provider': shipping_provider,
            'date_shipped': date_shipped,
            'status_changed': mark_as_shipped
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error agregando tracking: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
