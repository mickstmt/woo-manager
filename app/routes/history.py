# app/routes/history.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models import StockHistory, PriceHistory
from app import db
from datetime import datetime, timedelta

# Crear el blueprint
bp = Blueprint('history', __name__, url_prefix='/history')


@bp.route('/')
@login_required
def index():
    """
    Ruta principal del historial
    Muestra todos los cambios de stock y precios

    URL: http://localhost:5001/history/
    """
    return render_template('history.html', title='Historial de Cambios')


@bp.route('/stock')
@login_required
def stock_history():
    """
    Obtener historial de cambios de stock en formato JSON

    Parámetros GET:
    - page: número de página (default: 1)
    - per_page: registros por página (default: 50)
    - search: búsqueda por SKU, producto, o usuario (opcional)
    - date_from: fecha desde (opcional)
    - date_to: fecha hasta (opcional)
    - product_id: filtrar por producto específico (opcional)

    URL: http://localhost:5001/history/stock?page=1&per_page=50
    """
    try:
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '', type=str).strip()
        date_from_str = request.args.get('date_from', '', type=str)
        date_to_str = request.args.get('date_to', '', type=str)
        product_id = request.args.get('product_id', None, type=int)

        # Limitar per_page
        per_page = min(per_page, 500)

        # Query base
        query = db.session.query(StockHistory)

        # Filtro por producto específico
        if product_id:
            query = query.filter(StockHistory.product_id == product_id)

        # Filtro de búsqueda
        if search:
            query = query.filter(
                db.or_(
                    StockHistory.sku.ilike(f'%{search}%'),
                    StockHistory.product_title.ilike(f'%{search}%'),
                    StockHistory.changed_by.ilike(f'%{search}%')
                )
            )

        # Filtro de fechas
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                query = query.filter(StockHistory.created_at >= date_from)
            except ValueError:
                pass

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                # Agregar 23:59:59 para incluir todo el día
                date_to = date_to.replace(hour=23, minute=59, second=59)
                query = query.filter(StockHistory.created_at <= date_to)
            except ValueError:
                pass

        # Ordenar por fecha descendente (más reciente primero)
        query = query.order_by(StockHistory.created_at.desc())

        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Construir respuesta
        items = []
        for history in pagination.items:
            items.append({
                'id': history.id,
                'product_id': history.product_id,
                'product_title': history.product_title,
                'sku': history.sku,
                'old_stock': history.old_stock,
                'new_stock': history.new_stock,
                'change_amount': history.change_amount,
                'changed_by': history.changed_by,
                'change_reason': history.change_reason,
                'created_at': history.created_at.strftime('%Y-%m-%d %H:%M:%S') if history.created_at else None
            })

        return jsonify({
            'success': True,
            'items': items,
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/prices')
@login_required
def price_history():
    """
    Obtener historial de cambios de precios en formato JSON

    Similar a stock_history pero para precios
    """
    try:
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '', type=str).strip()
        date_from_str = request.args.get('date_from', '', type=str)
        date_to_str = request.args.get('date_to', '', type=str)
        product_id = request.args.get('product_id', None, type=int)

        # Limitar per_page
        per_page = min(per_page, 500)

        # Query base
        query = db.session.query(PriceHistory)

        # Filtro por producto específico
        if product_id:
            query = query.filter(PriceHistory.product_id == product_id)

        # Filtro de búsqueda
        if search:
            query = query.filter(
                db.or_(
                    PriceHistory.sku.ilike(f'%{search}%'),
                    PriceHistory.product_title.ilike(f'%{search}%'),
                    PriceHistory.changed_by.ilike(f'%{search}%')
                )
            )

        # Filtro de fechas
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                query = query.filter(PriceHistory.created_at >= date_from)
            except ValueError:
                pass

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                date_to = date_to.replace(hour=23, minute=59, second=59)
                query = query.filter(PriceHistory.created_at <= date_to)
            except ValueError:
                pass

        # Ordenar por fecha descendente
        query = query.order_by(PriceHistory.created_at.desc())

        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Construir respuesta
        items = []
        for history in pagination.items:
            items.append({
                'id': history.id,
                'product_id': history.product_id,
                'product_title': history.product_title,
                'sku': history.sku,
                'old_regular_price': float(history.old_regular_price) if history.old_regular_price else None,
                'new_regular_price': float(history.new_regular_price) if history.new_regular_price else None,
                'old_sale_price': float(history.old_sale_price) if history.old_sale_price else None,
                'new_sale_price': float(history.new_sale_price) if history.new_sale_price else None,
                'old_active_price': float(history.old_active_price) if history.old_active_price else None,
                'new_active_price': float(history.new_active_price) if history.new_active_price else None,
                'changed_by': history.changed_by,
                'change_reason': history.change_reason,
                'created_at': history.created_at.strftime('%Y-%m-%d %H:%M:%S') if history.created_at else None
            })

        return jsonify({
            'success': True,
            'items': items,
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
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
