# app/routes/reports.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.routes.auth import admin_required
from app import db
from datetime import datetime, timedelta
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
