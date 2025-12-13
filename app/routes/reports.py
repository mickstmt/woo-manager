# app/routes/reports.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.routes.auth import admin_required
from app import db
from app.models import TipoCambio
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy import text, func

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('/')
@login_required
def index():
    """
    Página principal de reportes con dashboard
    """
    return render_template('reports.html', title='Reportes')


@bp.route('/api/summary')
@login_required
def api_summary():
    """
    Obtener resumen general de métricas clave

    Query params:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    try:
        # Obtener fechas de filtro
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        # Si no se especifican, usar hoy
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        # Query para métricas generales
        # IMPORTANTE: Convertir UTC a hora Perú (UTC-5) antes de comparar fechas
        query = text("""
            SELECT
                COUNT(DISTINCT o.id) as total_orders,
                COALESCE(SUM(o.total_amount), 0) as total_sales,
                COALESCE(AVG(o.total_amount), 0) as avg_order_value,
                COUNT(DISTINCT CASE WHEN o.status = 'wc-completed' THEN o.id END) as completed_orders,
                COUNT(DISTINCT CASE WHEN o.status = 'wc-cancelled' THEN o.id END) as cancelled_orders,
                COUNT(DISTINCT CASE WHEN o.status = 'wc-processing' THEN o.id END) as processing_orders
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id AND om.meta_key = '_order_number'
            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
        """)

        result = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchone()

        # Query para total de descuentos
        discount_query = text("""
            SELECT COALESCE(SUM(CAST(meta_value AS DECIMAL(10,2))), 0) as total_discounts
            FROM wpyz_wc_orders_meta om
            INNER JOIN wpyz_wc_orders o ON om.order_id = o.id
            WHERE om.meta_key = '_wc_discount_amount'
                AND DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
        """)

        discount_result = db.session.execute(discount_query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchone()

        return jsonify({
            'success': True,
            'data': {
                'total_orders': result[0] or 0,
                'total_sales': float(result[1] or 0),
                'avg_order_value': float(result[2] or 0),
                'completed_orders': result[3] or 0,
                'cancelled_orders': result[4] or 0,
                'processing_orders': result[5] or 0,
                'total_discounts': float(discount_result[0] or 0),
                'period': {
                    'start': start_date,
                    'end': end_date
                }
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/sales-by-day')
@login_required
def api_sales_by_day():
    """
    Ventas agrupadas por día para gráfico de tendencia
    """
    try:
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        query = text("""
            SELECT
                DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as date,
                COUNT(o.id) as orders,
                COALESCE(SUM(o.total_amount), 0) as total
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id AND om.meta_key = '_order_number'
            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
            GROUP BY DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
            ORDER BY date ASC
        """)

        results = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        data = [{
            'date': str(row[0]),
            'orders': row[1],
            'total': float(row[2])
        } for row in results]

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/top-products')
@login_required
def api_top_products():
    """
    Productos más vendidos en el período
    """
    try:
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        limit = request.args.get('limit', 10, type=int)

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        query = text("""
            SELECT
                p.post_title as product_name,
                SUM(CAST(oim.meta_value AS SIGNED)) as quantity_sold,
                COUNT(DISTINCT oi.order_id) as times_ordered
            FROM wpyz_woocommerce_order_items oi
            INNER JOIN wpyz_wc_orders o ON oi.order_id = o.id
            INNER JOIN wpyz_woocommerce_order_itemmeta oim ON oi.order_item_id = oim.order_item_id AND oim.meta_key = '_qty'
            INNER JOIN wpyz_woocommerce_order_itemmeta oim_product ON oi.order_item_id = oim_product.order_item_id AND oim_product.meta_key = '_product_id'
            INNER JOIN wpyz_posts p ON CAST(oim_product.meta_value AS SIGNED) = p.ID
            WHERE oi.order_item_type = 'line_item'
                AND DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
            GROUP BY p.ID, p.post_title
            ORDER BY quantity_sold DESC
            LIMIT :limit
        """)

        results = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit
        }).fetchall()

        data = [{
            'product_name': row[0],
            'quantity_sold': row[1],
            'times_ordered': row[2]
        } for row in results]

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/sales-by-user')
@login_required
def api_sales_by_user():
    """
    Ventas por usuario creador
    """
    try:
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        query = text("""
            SELECT
                om_created.meta_value as username,
                COUNT(o.id) as total_orders,
                COALESCE(SUM(o.total_amount), 0) as total_sales
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_number ON o.id = om_number.order_id AND om_number.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_orders_meta om_created ON o.id = om_created.order_id AND om_created.meta_key = '_created_by'
            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
            GROUP BY om_created.meta_value
            ORDER BY total_sales DESC
        """)

        results = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        # Obtener nombres completos de usuarios
        from app.models import User
        data = []
        for row in results:
            username = row[0] or 'Desconocido'
            user = User.query.filter_by(username=username).first() if username != 'Desconocido' else None

            data.append({
                'username': username,
                'full_name': user.full_name if user and user.full_name else username,
                'total_orders': row[1],
                'total_sales': float(row[2])
            })

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/status-distribution')
@login_required
def api_status_distribution():
    """
    Distribución de pedidos por estado
    """
    try:
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        query = text("""
            SELECT
                o.status,
                COUNT(o.id) as count
            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om ON o.id = om.order_id AND om.meta_key = '_order_number'
            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
            GROUP BY o.status
            ORDER BY count DESC
        """)

        results = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        data = [{
            'status': row[0],
            'count': row[1]
        } for row in results]

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/profits')
@login_required
def profits_report():
    """
    Página de reporte de ganancias
    """
    return render_template('reports_profits.html', title='Reporte de Ganancias')


@bp.route('/api/profits')
@login_required
def api_profits():
    """
    Obtener reporte de ganancias por pedidos

    Query params:
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    """
    try:
        # Obtener fechas de filtro
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        # Si no se especifican, usar últimos 30 días
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Query principal: ganancias por pedido
        orders_query = text("""
            SELECT
                o.id as pedido_id,
                om_numero.meta_value as numero_pedido,
                DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) as fecha_pedido,
                o.status as estado,
                o.total_amount as total_venta_pen,

                -- Tipo de cambio usado (del día del pedido)
                (
                    SELECT tasa_promedio
                    FROM woo_tipo_cambio tc
                    WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                        AND tc.activo = TRUE
                    ORDER BY tc.fecha DESC
                    LIMIT 1
                ) as tipo_cambio,

                -- Costo total en USD
                (
                    SELECT SUM(
                        (
                            SELECT SUM(fc.FCLastCost)
                            FROM woo_products_fccost fc
                            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                AND LENGTH(fc.sku) = 7
                        ) * oim_qty.meta_value
                    )
                    FROM wpyz_woocommerce_order_items oi
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                        AND oim_pid.meta_key = '_product_id'
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                        AND oim_qty.meta_key = '_qty'
                    LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                        AND oim_vid.meta_key = '_variation_id'
                    INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                        AND pm_sku.meta_key = '_sku'
                    WHERE oi.order_id = o.id
                        AND oi.order_item_type = 'line_item'
                ) as costo_total_usd,

                -- Costo total en PEN
                (
                    SELECT SUM(
                        (
                            SELECT SUM(fc.FCLastCost)
                            FROM woo_products_fccost fc
                            WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                AND LENGTH(fc.sku) = 7
                        ) * oim_qty.meta_value
                    )
                    FROM wpyz_woocommerce_order_items oi
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                        AND oim_pid.meta_key = '_product_id'
                    INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                        AND oim_qty.meta_key = '_qty'
                    LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                        AND oim_vid.meta_key = '_variation_id'
                    INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                        AND pm_sku.meta_key = '_sku'
                    WHERE oi.order_id = o.id
                        AND oi.order_item_type = 'line_item'
                ) * (
                    SELECT tasa_promedio
                    FROM woo_tipo_cambio tc
                    WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                        AND tc.activo = TRUE
                    ORDER BY tc.fecha DESC
                    LIMIT 1
                ) as costo_total_pen,

                -- Ganancia
                o.total_amount - (
                    (
                        SELECT SUM(
                            (
                                SELECT SUM(fc.FCLastCost)
                                FROM woo_products_fccost fc
                                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                    AND LENGTH(fc.sku) = 7
                            ) * oim_qty.meta_value
                        )
                        FROM wpyz_woocommerce_order_items oi
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                            AND oim_pid.meta_key = '_product_id'
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                            AND oim_qty.meta_key = '_qty'
                        LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                            AND oim_vid.meta_key = '_variation_id'
                        INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                            AND pm_sku.meta_key = '_sku'
                        WHERE oi.order_id = o.id
                            AND oi.order_item_type = 'line_item'
                    ) * (
                        SELECT tasa_promedio
                        FROM woo_tipo_cambio tc
                        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                            AND tc.activo = TRUE
                        ORDER BY tc.fecha DESC
                        LIMIT 1
                    )
                ) as ganancia_pen,

                -- Margen porcentual
                ROUND(
                    (
                        (o.total_amount - (
                            (
                                SELECT SUM(
                                    (
                                        SELECT SUM(fc.FCLastCost)
                                        FROM woo_products_fccost fc
                                        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                            AND LENGTH(fc.sku) = 7
                                    ) * oim_qty.meta_value
                                )
                                FROM wpyz_woocommerce_order_items oi
                                INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                                    AND oim_pid.meta_key = '_product_id'
                                INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                                    AND oim_qty.meta_key = '_qty'
                                LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                                    AND oim_vid.meta_key = '_variation_id'
                                INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                                    AND pm_sku.meta_key = '_sku'
                                WHERE oi.order_id = o.id
                                    AND oi.order_item_type = 'line_item'
                            ) * (
                                SELECT tasa_promedio
                                FROM woo_tipo_cambio tc
                                WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                                    AND tc.activo = TRUE
                                ORDER BY tc.fecha DESC
                                LIMIT 1
                            )
                        )) / NULLIF(o.total_amount, 0)
                    ) * 100
                , 2) as margen_porcentaje,

                -- Cliente
                ba.first_name as cliente_nombre,
                ba.last_name as cliente_apellido

            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
                AND om_numero.meta_key = '_order_number'
            LEFT JOIN wpyz_wc_order_addresses ba ON o.id = ba.order_id
                AND ba.address_type = 'billing'

            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
                AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')

            HAVING costo_total_usd IS NOT NULL

            ORDER BY fecha_pedido DESC, o.id DESC
        """)

        orders = db.session.execute(orders_query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()

        # Query resumen del período
        summary_query = text("""
            SELECT
                COUNT(DISTINCT o.id) as total_pedidos,
                ROUND(SUM(o.total_amount), 2) as ventas_totales_pen,
                ROUND(SUM(
                    (
                        SELECT SUM(
                            (
                                SELECT SUM(fc.FCLastCost)
                                FROM woo_products_fccost fc
                                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                    AND LENGTH(fc.sku) = 7
                            ) * oim_qty.meta_value
                        )
                        FROM wpyz_woocommerce_order_items oi
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                            AND oim_pid.meta_key = '_product_id'
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                            AND oim_qty.meta_key = '_qty'
                        LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                            AND oim_vid.meta_key = '_variation_id'
                        INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                            AND pm_sku.meta_key = '_sku'
                        WHERE oi.order_id = o.id
                            AND oi.order_item_type = 'line_item'
                    )
                ), 2) as costos_totales_usd,
                ROUND(SUM(
                    (
                        SELECT SUM(
                            (
                                SELECT SUM(fc.FCLastCost)
                                FROM woo_products_fccost fc
                                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                    AND LENGTH(fc.sku) = 7
                            ) * oim_qty.meta_value
                        )
                        FROM wpyz_woocommerce_order_items oi
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                            AND oim_pid.meta_key = '_product_id'
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                            AND oim_qty.meta_key = '_qty'
                        LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                            AND oim_vid.meta_key = '_variation_id'
                        INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                            AND pm_sku.meta_key = '_sku'
                        WHERE oi.order_id = o.id
                            AND oi.order_item_type = 'line_item'
                    ) * (
                        SELECT tasa_promedio
                        FROM woo_tipo_cambio tc
                        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                            AND tc.activo = TRUE
                        ORDER BY tc.fecha DESC
                        LIMIT 1
                    )
                ), 2) as costos_totales_pen,
                ROUND(SUM(o.total_amount) - SUM(
                    (
                        SELECT SUM(
                            (
                                SELECT SUM(fc.FCLastCost)
                                FROM woo_products_fccost fc
                                WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                    AND LENGTH(fc.sku) = 7
                            ) * oim_qty.meta_value
                        )
                        FROM wpyz_woocommerce_order_items oi
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                            AND oim_pid.meta_key = '_product_id'
                        INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                            AND oim_qty.meta_key = '_qty'
                        LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                            AND oim_vid.meta_key = '_variation_id'
                        INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                            AND pm_sku.meta_key = '_sku'
                        WHERE oi.order_id = o.id
                            AND oi.order_item_type = 'line_item'
                    ) * (
                        SELECT tasa_promedio
                        FROM woo_tipo_cambio tc
                        WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                            AND tc.activo = TRUE
                        ORDER BY tc.fecha DESC
                        LIMIT 1
                    )
                ), 2) as ganancias_totales_pen,
                ROUND(
                    (SUM(o.total_amount) - SUM(
                        (
                            SELECT SUM(
                                (
                                    SELECT SUM(fc.FCLastCost)
                                    FROM woo_products_fccost fc
                                    WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                                        AND LENGTH(fc.sku) = 7
                                ) * oim_qty.meta_value
                            )
                            FROM wpyz_woocommerce_order_items oi
                            INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid ON oi.order_item_id = oim_pid.order_item_id
                                AND oim_pid.meta_key = '_product_id'
                            INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty ON oi.order_item_id = oim_qty.order_item_id
                                AND oim_qty.meta_key = '_qty'
                            LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid ON oi.order_item_id = oim_vid.order_item_id
                                AND oim_vid.meta_key = '_variation_id'
                            INNER JOIN wpyz_postmeta pm_sku ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                                AND pm_sku.meta_key = '_sku'
                            WHERE oi.order_id = o.id
                                AND oi.order_item_type = 'line_item'
                        ) * (
                            SELECT tasa_promedio
                            FROM woo_tipo_cambio tc
                            WHERE tc.fecha <= DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR))
                                AND tc.activo = TRUE
                            ORDER BY tc.fecha DESC
                            LIMIT 1
                        )
                    )) / NULLIF(SUM(o.total_amount), 0) * 100
                , 2) as margen_promedio_porcentaje

            FROM wpyz_wc_orders o
            INNER JOIN wpyz_wc_orders_meta om_numero ON o.id = om_numero.order_id
                AND om_numero.meta_key = '_order_number'

            WHERE DATE(DATE_SUB(o.date_created_gmt, INTERVAL 5 HOUR)) BETWEEN :start_date AND :end_date
                AND o.status != 'trash'
                AND o.status NOT IN ('wc-cancelled', 'wc-refunded', 'wc-failed')
        """)

        summary = db.session.execute(summary_query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchone()

        # Convertir resultados a formato JSON
        orders_data = []
        for order in orders:
            # Obtener items del pedido
            items_query = text("""
                SELECT
                    oi.order_item_name as producto,
                    oim_qty.meta_value as cantidad,
                    pm_sku.meta_value as sku,
                    (
                        SELECT SUM(fc.FCLastCost)
                        FROM woo_products_fccost fc
                        WHERE pm_sku.meta_value COLLATE utf8mb4_unicode_520_ci LIKE CONCAT('%', fc.sku COLLATE utf8mb4_unicode_520_ci, '%')
                            AND LENGTH(fc.sku) = 7
                    ) as costo_unitario_usd
                FROM wpyz_woocommerce_order_items oi
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_pid
                    ON oi.order_item_id = oim_pid.order_item_id
                    AND oim_pid.meta_key = '_product_id'
                INNER JOIN wpyz_woocommerce_order_itemmeta oim_qty
                    ON oi.order_item_id = oim_qty.order_item_id
                    AND oim_qty.meta_key = '_qty'
                LEFT JOIN wpyz_woocommerce_order_itemmeta oim_vid
                    ON oi.order_item_id = oim_vid.order_item_id
                    AND oim_vid.meta_key = '_variation_id'
                LEFT JOIN wpyz_postmeta pm_sku
                    ON CAST(COALESCE(NULLIF(oim_vid.meta_value, '0'), oim_pid.meta_value) AS UNSIGNED) = pm_sku.post_id
                    AND pm_sku.meta_key = '_sku'
                WHERE oi.order_id = :order_id
                    AND oi.order_item_type = 'line_item'
            """)

            items_result = db.session.execute(items_query, {'order_id': order[0]}).fetchall()

            items_data = []
            for item in items_result:
                costo_unit = float(item[3] or 0)
                cantidad = int(item[1] or 0)
                costo_total_item = costo_unit * cantidad

                items_data.append({
                    'producto': item[0],
                    'cantidad': cantidad,
                    'sku': item[2] or 'Sin SKU',
                    'tiene_sku': bool(item[2]),
                    'costo_unitario_usd': costo_unit,
                    'costo_total_usd': costo_total_item,
                    'tiene_costo': costo_unit > 0
                })

            orders_data.append({
                'pedido_id': order[0],
                'numero_pedido': order[1],
                'fecha_pedido': str(order[2]),
                'estado': order[3],
                'total_venta_pen': float(order[4] or 0),
                'tipo_cambio': float(order[5] or 0),
                'costo_total_usd': float(order[6] or 0),
                'costo_total_pen': float(order[7] or 0),
                'ganancia_pen': float(order[8] or 0),
                'margen_porcentaje': float(order[9] or 0),
                'cliente_nombre': order[10] or '',
                'cliente_apellido': order[11] or '',
                'items': items_data,
                'total_items': len(items_data)
            })

        return jsonify({
            'success': True,
            'data': {
                'orders': orders_data,
                'summary': {
                    'total_pedidos': summary[0] or 0,
                    'ventas_totales_pen': float(summary[1] or 0),
                    'costos_totales_usd': float(summary[2] or 0),
                    'costos_totales_pen': float(summary[3] or 0),
                    'ganancias_totales_pen': float(summary[4] or 0),
                    'margen_promedio_porcentaje': float(summary[5] or 0)
                },
                'period': {
                    'start': start_date,
                    'end': end_date
                }
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/exchange-rate')
@login_required
def exchange_rate():
    """
    Página de gestión de tipo de cambio
    """
    return render_template('exchange_rate.html', title='Tipo de Cambio USD/PEN')


@bp.route('/api/exchange-rate', methods=['GET'])
@login_required
def api_get_exchange_rate():
    """
    Obtener tipo de cambio actual o histórico

    Query params:
    - fecha: fecha específica (YYYY-MM-DD) - opcional
    - limit: cantidad de registros históricos (default: 30)
    """
    try:
        fecha_param = request.args.get('fecha', type=str)
        limit = request.args.get('limit', type=int, default=30)

        if fecha_param:
            # Obtener tipo de cambio para fecha específica
            fecha = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            tipo_cambio = TipoCambio.get_tasa_por_fecha(fecha)

            if tipo_cambio:
                return jsonify({
                    'success': True,
                    'data': {
                        'id': tipo_cambio.id,
                        'fecha': tipo_cambio.fecha.isoformat(),
                        'tasa_compra': float(tipo_cambio.tasa_compra),
                        'tasa_venta': float(tipo_cambio.tasa_venta),
                        'tasa_promedio': float(tipo_cambio.tasa_promedio),
                        'actualizado_por': tipo_cambio.actualizado_por,
                        'notas': tipo_cambio.notas
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'No se encontró tipo de cambio para esa fecha'
                }), 404
        else:
            # Obtener histórico
            tipos_cambio = TipoCambio.query.filter_by(activo=True)\
                .order_by(TipoCambio.fecha.desc())\
                .limit(limit)\
                .all()

            data = [{
                'id': tc.id,
                'fecha': tc.fecha.isoformat(),
                'tasa_compra': float(tc.tasa_compra),
                'tasa_venta': float(tc.tasa_venta),
                'tasa_promedio': float(tc.tasa_promedio),
                'actualizado_por': tc.actualizado_por,
                'notas': tc.notas or ''
            } for tc in tipos_cambio]

            return jsonify({
                'success': True,
                'data': data
            })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/exchange-rate', methods=['POST'])
@login_required
def api_create_exchange_rate():
    """
    Crear o actualizar tipo de cambio

    Body JSON:
    {
        "fecha": "YYYY-MM-DD",
        "tasa_compra": 3.75,
        "tasa_venta": 3.78,
        "notas": "opcional"
    }
    """
    try:
        data = request.get_json()

        # Validar datos requeridos
        if not data.get('fecha') or not data.get('tasa_compra') or not data.get('tasa_venta'):
            return jsonify({
                'success': False,
                'error': 'Faltan campos requeridos: fecha, tasa_compra, tasa_venta'
            }), 400

        fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        tasa_compra = Decimal(str(data['tasa_compra']))
        tasa_venta = Decimal(str(data['tasa_venta']))
        tasa_promedio = (tasa_compra + tasa_venta) / 2
        notas = data.get('notas', '')

        # Verificar si ya existe un tipo de cambio para esa fecha
        existing = TipoCambio.query.filter_by(fecha=fecha, activo=True).first()

        if existing:
            # Actualizar existente
            existing.tasa_compra = tasa_compra
            existing.tasa_venta = tasa_venta
            existing.tasa_promedio = tasa_promedio
            existing.actualizado_por = current_user.username
            existing.fecha_actualizacion = datetime.now()
            existing.notas = notas
            tipo_cambio = existing
        else:
            # Crear nuevo
            tipo_cambio = TipoCambio(
                fecha=fecha,
                tasa_compra=tasa_compra,
                tasa_venta=tasa_venta,
                tasa_promedio=tasa_promedio,
                actualizado_por=current_user.username,
                activo=True,
                notas=notas
            )
            db.session.add(tipo_cambio)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Tipo de cambio guardado exitosamente',
            'data': {
                'id': tipo_cambio.id,
                'fecha': tipo_cambio.fecha.isoformat(),
                'tasa_compra': float(tipo_cambio.tasa_compra),
                'tasa_venta': float(tipo_cambio.tasa_venta),
                'tasa_promedio': float(tipo_cambio.tasa_promedio)
            }
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Formato de datos inválido: ' + str(e)
        }), 400
    except Exception as e:
        import traceback
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
