# app/routes/quotations.py
"""
Blueprint para el módulo de Cotizaciones (Quotations)

Permite crear y gestionar cotizaciones para clientes con posibilidad
de conversión a órdenes WooCommerce
"""
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.routes.auth import admin_required
from app.models import (
    db, Product, ProductMeta,
    Quotation, QuotationItem, QuotationHistory,
    Order, OrderItem, OrderAddress, OrderMeta
)
from config import get_local_time
from datetime import datetime, timedelta, date
from sqlalchemy import text, and_, or_, func
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocDocument, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os

bp = Blueprint('quotations', __name__, url_prefix='/quotations')


# =====================================================
# VISTAS HTML
# =====================================================

@bp.route('/')
@login_required
def index():
    """
    Vista principal: Lista de cotizaciones

    URL: /quotations
    """
    return render_template('quotations_list.html', title='Cotizaciones')


@bp.route('/create')
@login_required
def create():
    """
    Vista: Crear nueva cotización

    URL: /quotations/create
    """
    return render_template('quotations_create.html', title='Nueva Cotización')


@bp.route('/<int:quotation_id>')
@login_required
def detail(quotation_id):
    """
    Vista: Detalle de cotización

    URL: /quotations/123
    """
    quotation = Quotation.query.get_or_404(quotation_id)
    # Obtener historial ordenado por fecha descendente
    history = quotation.history.order_by(QuotationHistory.created_at.desc()).all()
    # Obtener items ordenados por display_order
    items = quotation.items.order_by(QuotationItem.display_order.asc()).all()

    return render_template('quotations_detail.html',
                         title=f'Cotización {quotation.quote_number}',
                         quotation=quotation,
                         items=items,
                         history=history)


@bp.route('/<int:quotation_id>/edit')
@login_required
def edit(quotation_id):
    """
    Vista: Editar cotización (solo draft)

    URL: /quotations/123/edit
    """
    quotation = Quotation.query.get_or_404(quotation_id)

    # Solo se pueden editar borradores
    if quotation.status != 'draft':
        return jsonify({
            'success': False,
            'error': 'Solo se pueden editar cotizaciones en estado borrador'
        }), 400

    # Obtener items
    items = quotation.items.order_by(QuotationItem.display_order.asc()).all()

    return render_template('quotations_edit.html',
                         title=f'Editar {quotation.quote_number}',
                         quotation=quotation,
                         items=items)


# =====================================================
# API ENDPOINTS
# =====================================================

@bp.route('/api/quotations', methods=['GET'])
@login_required
def api_get_quotations():
    """
    API: Listar cotizaciones con filtros y paginación

    Query params:
    - page (int): Número de página (default: 1)
    - per_page (int): Items por página (default: 20)
    - status (str): Filtrar por estado
    - customer (str): Buscar por nombre o email de cliente
    - date_from (str): Fecha desde (YYYY-MM-DD)
    - date_to (str): Fecha hasta (YYYY-MM-DD)
    - show_expired (bool): Incluir vencidas (default: true)
    """
    try:
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Filtros
        status_filter = request.args.get('status', '')
        customer_filter = request.args.get('customer', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        show_expired = request.args.get('show_expired', 'true').lower() == 'true'

        # Query base
        query = Quotation.query

        # Aplicar filtros
        if status_filter:
            query = query.filter(Quotation.status == status_filter)

        if customer_filter:
            query = query.filter(
                or_(
                    Quotation.customer_name.ilike(f'%{customer_filter}%'),
                    Quotation.customer_email.ilike(f'%{customer_filter}%')
                )
            )

        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Quotation.quote_date >= date_from_obj)

        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Quotation.quote_date <= date_to_obj)

        if not show_expired:
            query = query.filter(Quotation.status != 'expired')

        # Ordenar por fecha de creación descendente
        query = query.order_by(Quotation.created_at.desc())

        # Paginar
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Convertir a dict
        quotations = [q.to_dict() for q in pagination.items]

        return jsonify({
            'success': True,
            'quotations': quotations,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error al listar cotizaciones: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/quotations/<int:quotation_id>', methods=['GET'])
@login_required
def api_get_quotation(quotation_id):
    """
    API: Obtener detalle de cotización
    """
    try:
        quotation = Quotation.query.get_or_404(quotation_id)
        items = quotation.items.order_by(QuotationItem.display_order.asc()).all()

        data = quotation.to_dict()
        data['items'] = [item.to_dict() for item in items]

        return jsonify({
            'success': True,
            'quotation': data
        })

    except Exception as e:
        current_app.logger.error(f"Error al obtener cotización: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/quotations', methods=['POST'])
@login_required
def api_create_quotation():
    """
    API: Crear nueva cotización

    Body (JSON):
    {
        "customer_name": "...",
        "customer_email": "...",
        "customer_phone": "...",
        "customer_dni": "...",
        "customer_ruc": "...",
        "customer_address": "...",
        "customer_city": "...",
        "customer_state": "...",
        "valid_days": 15,
        "payment_terms": "...",
        "delivery_time": "...",
        "discount_type": "percentage",
        "discount_value": 0,
        "shipping_cost": 0,
        "tax_rate": 18,
        "notes": "...",
        "terms_conditions": "...",
        "items": [
            {
                "product_id": 123,
                "variation_id": 0,
                "product_name": "...",
                "product_sku": "...",
                "quantity": 1,
                "unit_price": 50.00,
                "original_price": 60.00,
                "notes": "..."
            }
        ]
    }
    """
    try:
        data = request.get_json()

        # Validaciones básicas
        if not data.get('customer_name'):
            return jsonify({'success': False, 'error': 'Nombre de cliente requerido'}), 400

        if not data.get('customer_email'):
            return jsonify({'success': False, 'error': 'Email de cliente requerido'}), 400

        if not data.get('items') or len(data.get('items')) == 0:
            return jsonify({'success': False, 'error': 'Debe agregar al menos un producto'}), 400

        # Generar número de cotización
        quote_number = generate_quote_number()

        # Calcular fecha de validez
        valid_days = data.get('valid_days', 15)
        valid_until = (datetime.now() + timedelta(days=valid_days)).date()

        # Crear cotización
        quotation = Quotation(
            quote_number=quote_number,
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email'),
            customer_phone=data.get('customer_phone'),
            customer_dni=data.get('customer_dni'),
            customer_ruc=data.get('customer_ruc'),
            customer_address=data.get('customer_address'),
            customer_city=data.get('customer_city'),
            customer_state=data.get('customer_state'),
            status='draft',
            quote_date=get_local_time(),
            valid_until=valid_until,
            discount_type=data.get('discount_type', 'percentage'),
            discount_value=Decimal(str(data.get('discount_value', 0))),
            shipping_cost=Decimal(str(data.get('shipping_cost', 0))),
            tax_rate=Decimal(str(data.get('tax_rate', 18))),
            payment_terms=data.get('payment_terms'),
            delivery_time=data.get('delivery_time'),
            notes=data.get('notes'),
            terms_conditions=data.get('terms_conditions'),
            created_by=current_user.username
        )

        db.session.add(quotation)
        db.session.flush()  # Para obtener el ID

        # Crear items
        for idx, item_data in enumerate(data.get('items', [])):
            quantity = int(item_data.get('quantity', 1))
            unit_price = Decimal(str(item_data.get('unit_price', 0)))
            original_price = Decimal(str(item_data.get('original_price', 0)))

            # Calcular descuento por línea
            discount_pct = ((original_price - unit_price) / original_price * 100) if original_price > 0 else 0

            # Calcular subtotal y total
            subtotal = unit_price * quantity
            tax = subtotal * (quotation.tax_rate / 100)
            total = subtotal + tax

            item = QuotationItem(
                quotation_id=quotation.id,
                product_id=item_data.get('product_id'),
                variation_id=item_data.get('variation_id', 0),
                product_name=item_data.get('product_name'),
                product_sku=item_data.get('product_sku'),
                quantity=quantity,
                unit_price=unit_price,
                original_price=original_price,
                discount_percentage=discount_pct,
                subtotal=subtotal,
                tax=tax,
                total=total,
                notes=item_data.get('notes'),
                display_order=idx
            )

            db.session.add(item)

        # Recalcular totales
        db.session.flush()
        quotation.calculate_totals()

        # Crear entrada en historial
        history = QuotationHistory(
            quotation_id=quotation.id,
            old_status=None,
            new_status='draft',
            changed_by=current_user.username,
            change_reason='Cotización creada'
        )
        db.session.add(history)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Cotización {quote_number} creada exitosamente',
            'quotation': quotation.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al crear cotización: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/quotations/<int:quotation_id>', methods=['PUT'])
@login_required
def api_update_quotation(quotation_id):
    """
    API: Actualizar cotización (solo draft)
    """
    try:
        quotation = Quotation.query.get_or_404(quotation_id)

        # Solo se pueden editar borradores
        if quotation.status != 'draft':
            return jsonify({
                'success': False,
                'error': 'Solo se pueden editar cotizaciones en estado borrador'
            }), 400

        data = request.get_json()

        # Actualizar campos básicos
        if 'customer_name' in data:
            quotation.customer_name = data['customer_name']
        if 'customer_email' in data:
            quotation.customer_email = data['customer_email']
        if 'customer_phone' in data:
            quotation.customer_phone = data['customer_phone']
        if 'customer_dni' in data:
            quotation.customer_dni = data['customer_dni']
        if 'customer_ruc' in data:
            quotation.customer_ruc = data['customer_ruc']
        if 'customer_address' in data:
            quotation.customer_address = data['customer_address']
        if 'customer_city' in data:
            quotation.customer_city = data['customer_city']
        if 'customer_state' in data:
            quotation.customer_state = data['customer_state']

        if 'valid_days' in data:
            quotation.valid_until = (datetime.now() + timedelta(days=data['valid_days'])).date()

        if 'discount_type' in data:
            quotation.discount_type = data['discount_type']
        if 'discount_value' in data:
            quotation.discount_value = Decimal(str(data['discount_value']))
        if 'shipping_cost' in data:
            quotation.shipping_cost = Decimal(str(data['shipping_cost']))
        if 'tax_rate' in data:
            quotation.tax_rate = Decimal(str(data['tax_rate']))

        if 'payment_terms' in data:
            quotation.payment_terms = data['payment_terms']
        if 'delivery_time' in data:
            quotation.delivery_time = data['delivery_time']
        if 'notes' in data:
            quotation.notes = data['notes']
        if 'terms_conditions' in data:
            quotation.terms_conditions = data['terms_conditions']

        # Si hay items, actualizar
        if 'items' in data:
            # Eliminar items existentes
            QuotationItem.query.filter_by(quotation_id=quotation_id).delete()

            # Crear nuevos items
            for idx, item_data in enumerate(data.get('items', [])):
                quantity = int(item_data.get('quantity', 1))
                unit_price = Decimal(str(item_data.get('unit_price', 0)))
                original_price = Decimal(str(item_data.get('original_price', 0)))

                discount_pct = ((original_price - unit_price) / original_price * 100) if original_price > 0 else 0

                subtotal = unit_price * quantity
                tax = subtotal * (quotation.tax_rate / 100)
                total = subtotal + tax

                item = QuotationItem(
                    quotation_id=quotation.id,
                    product_id=item_data.get('product_id'),
                    variation_id=item_data.get('variation_id', 0),
                    product_name=item_data.get('product_name'),
                    product_sku=item_data.get('product_sku'),
                    quantity=quantity,
                    unit_price=unit_price,
                    original_price=original_price,
                    discount_percentage=discount_pct,
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                    notes=item_data.get('notes'),
                    display_order=idx
                )

                db.session.add(item)

        # Recalcular totales
        db.session.flush()
        quotation.calculate_totals()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cotización actualizada exitosamente',
            'quotation': quotation.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar cotización: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/quotations/<int:quotation_id>', methods=['DELETE'])
@login_required
def api_delete_quotation(quotation_id):
    """
    API: Eliminar cotización (solo draft)
    """
    try:
        quotation = Quotation.query.get_or_404(quotation_id)

        # Solo se pueden eliminar borradores
        if quotation.status != 'draft':
            return jsonify({
                'success': False,
                'error': 'Solo se pueden eliminar cotizaciones en estado borrador'
            }), 400

        # Eliminar (cascade eliminará items e historial)
        db.session.delete(quotation)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cotización eliminada exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar cotización: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def generate_quote_number():
    """
    Generar número de cotización en formato COT-YYYY-NNN

    Ejemplos:
    - COT-2026-001
    - COT-2026-002
    """
    current_year = datetime.now().year

    # Buscar el último número de cotización del año actual
    last_quote = Quotation.query.filter(
        Quotation.quote_number.like(f'COT-{current_year}-%')
    ).order_by(Quotation.id.desc()).first()

    if last_quote:
        # Extraer el número secuencial
        last_number = int(last_quote.quote_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f'COT-{current_year}-{new_number:03d}'


@bp.route('/api/quotations/<int:quotation_id>/status', methods=['PUT'])
@login_required
def api_update_status(quotation_id):
    """
    API: Cambiar estado de cotización

    Body (JSON):
    {
        "status": "sent|accepted|rejected",
        "reason": "Razón del cambio (opcional)"
    }
    """
    try:
        quotation = Quotation.query.get_or_404(quotation_id)
        data = request.get_json()

        new_status = data.get('status')
        reason = data.get('reason', '')

        # Validar estados permitidos
        valid_statuses = ['draft', 'sent', 'accepted', 'rejected', 'expired']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'error': 'Estado inválido'}), 400

        # Validar transiciones de estado
        if quotation.status == 'converted':
            return jsonify({'success': False, 'error': 'No se puede cambiar el estado de una cotización convertida'}), 400

        old_status = quotation.status

        # Actualizar estado
        quotation.status = new_status

        # Actualizar timestamps según el estado
        if new_status == 'sent' and not quotation.sent_at:
            quotation.sent_at = get_local_time()
        elif new_status == 'accepted' and not quotation.accepted_at:
            quotation.accepted_at = get_local_time()

        # Crear entrada en historial
        history = QuotationHistory(
            quotation_id=quotation.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=current_user.username,
            change_reason=reason
        )
        db.session.add(history)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Estado actualizado a: {new_status}',
            'quotation': quotation.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cambiar estado: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/quotations/<int:quotation_id>/duplicate', methods=['POST'])
@login_required
def api_duplicate_quotation(quotation_id):
    """
    API: Duplicar cotización (crear nueva basada en existente)
    """
    try:
        original = Quotation.query.get_or_404(quotation_id)

        # Generar nuevo número
        new_quote_number = generate_quote_number()

        # Nueva fecha de validez (15 días desde hoy)
        new_valid_until = (datetime.now() + timedelta(days=15)).date()

        # Crear nueva cotización
        new_quotation = Quotation(
            quote_number=new_quote_number,
            customer_name=original.customer_name,
            customer_email=original.customer_email,
            customer_phone=original.customer_phone,
            customer_dni=original.customer_dni,
            customer_ruc=original.customer_ruc,
            customer_address=original.customer_address,
            customer_city=original.customer_city,
            customer_state=original.customer_state,
            status='draft',
            quote_date=get_local_time(),
            valid_until=new_valid_until,
            discount_type=original.discount_type,
            discount_value=original.discount_value,
            shipping_cost=original.shipping_cost,
            tax_rate=original.tax_rate,
            payment_terms=original.payment_terms,
            delivery_time=original.delivery_time,
            notes=original.notes,
            terms_conditions=original.terms_conditions,
            created_by=current_user.username
        )

        db.session.add(new_quotation)
        db.session.flush()

        # Copiar items
        for orig_item in original.items:
            new_item = QuotationItem(
                quotation_id=new_quotation.id,
                product_id=orig_item.product_id,
                variation_id=orig_item.variation_id,
                product_name=orig_item.product_name,
                product_sku=orig_item.product_sku,
                quantity=orig_item.quantity,
                unit_price=orig_item.unit_price,
                original_price=orig_item.original_price,
                discount_percentage=orig_item.discount_percentage,
                subtotal=orig_item.subtotal,
                tax=orig_item.tax,
                total=orig_item.total,
                notes=orig_item.notes,
                display_order=orig_item.display_order
            )
            db.session.add(new_item)

        # Recalcular totales
        db.session.flush()
        new_quotation.calculate_totals()

        # Crear entrada en historial
        history = QuotationHistory(
            quotation_id=new_quotation.id,
            old_status=None,
            new_status='draft',
            changed_by=current_user.username,
            change_reason=f'Duplicada desde {original.quote_number}'
        )
        db.session.add(history)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Cotización duplicada como {new_quote_number}',
            'quotation': new_quotation.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al duplicar cotización: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/check-expired', methods=['GET'])
@login_required
def api_check_expired():
    """
    API: Marcar cotizaciones vencidas automáticamente

    Marca como 'expired' todas las cotizaciones en estado 'draft' o 'sent'
    cuya fecha valid_until haya pasado
    """
    try:
        today = date.today()

        # Buscar cotizaciones vencidas
        expired_quotes = Quotation.query.filter(
            Quotation.status.in_(['draft', 'sent']),
            Quotation.valid_until < today
        ).all()

        count = 0
        for quote in expired_quotes:
            old_status = quote.status
            quote.status = 'expired'

            # Crear entrada en historial
            history = QuotationHistory(
                quotation_id=quote.id,
                old_status=old_status,
                new_status='expired',
                changed_by='system',
                change_reason='Fecha de validez expirada'
            )
            db.session.add(history)
            count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{count} cotización(es) marcada(s) como vencidas',
            'count': count
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al verificar cotizaciones vencidas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    """
    API: Estadísticas de cotizaciones
    """
    try:
        # Totales por estado
        stats = {}

        stats['total'] = Quotation.query.count()
        stats['draft'] = Quotation.query.filter_by(status='draft').count()
        stats['sent'] = Quotation.query.filter_by(status='sent').count()
        stats['accepted'] = Quotation.query.filter_by(status='accepted').count()
        stats['rejected'] = Quotation.query.filter_by(status='rejected').count()
        stats['expired'] = Quotation.query.filter_by(status='expired').count()
        stats['converted'] = Quotation.query.filter_by(status='converted').count()

        # Valor total de cotizaciones aceptadas
        accepted_total = db.session.query(func.sum(Quotation.total)).filter_by(status='accepted').scalar()
        stats['accepted_total_value'] = float(accepted_total) if accepted_total else 0

        # Valor total de cotizaciones convertidas
        converted_total = db.session.query(func.sum(Quotation.total)).filter_by(status='converted').scalar()
        stats['converted_total_value'] = float(converted_total) if converted_total else 0

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        current_app.logger.error(f"Error al obtener estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
