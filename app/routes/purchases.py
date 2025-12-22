# app/routes/purchases.py
"""
Blueprint para el módulo de Compras/Reabastecimiento

Gestiona órdenes de compra para productos sin stock
"""
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from app.routes.auth import admin_required
from app.models import (
    db, Product, ProductMeta, StockHistory,
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderHistory
)
from config import get_local_time
from datetime import datetime, timedelta
from sqlalchemy import text, and_, or_
from decimal import Decimal
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

bp = Blueprint('purchases', __name__, url_prefix='/purchases')


# =====================================================
# VISTAS HTML
# =====================================================

@bp.route('/')
@login_required
def index():
    """
    Vista principal: Lista de productos sin stock

    URL: /purchases
    """
    return render_template('purchases_list.html', title='Productos Sin Stock')


@bp.route('/orders')
@login_required
def orders_list():
    """
    Vista: Lista de órdenes de compra

    URL: /purchases/orders
    """
    return render_template('purchases_orders.html', title='Órdenes de Compra')


@bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    """
    Vista: Detalle de una orden de compra específica

    URL: /purchases/orders/123
    """
    order = PurchaseOrder.query.get_or_404(order_id)
    return render_template('purchases_detail.html', title=f'Orden {order.order_number}', order=order)


# =====================================================
# API ENDPOINTS
# =====================================================

@bp.route('/api/products-out-of-stock')
@login_required
def api_products_out_of_stock():
    """
    API: Obtener lista de productos sin stock

    Criterios:
    - Stock actual = 0
    - Deben existir en wpyz_stock_history con new_stock = 0
    - Solo productos con SKU válido

    Query params:
    - search: Búsqueda por SKU o nombre
    - sort_by: dias_sin_stock, sku, nombre (default: dias_sin_stock)

    Returns:
        JSON con lista de productos
    """
    try:
        search = request.args.get('search', '', type=str)
        sort_by = request.args.get('sort_by', 'dias_sin_stock', type=str)

        # Query complejo: Productos con stock 0 que están en history
        query = text("""
            SELECT DISTINCT
                p.ID as product_id,
                p.post_title as product_name,
                pm_sku.meta_value as sku,
                pm_stock.meta_value as current_stock,
                sh.new_stock as history_stock,
                sh.changed_by as last_updated_by,
                sh.created_at as last_stock_update,
                DATEDIFF(NOW(), sh.created_at) as dias_sin_stock,
                fc.costo as unit_cost_usd
            FROM wpyz_posts p

            -- SKU (requerido)
            INNER JOIN wpyz_postmeta pm_sku
                ON p.ID = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
                AND pm_sku.meta_value IS NOT NULL
                AND pm_sku.meta_value != ''

            -- Stock actual
            LEFT JOIN wpyz_postmeta pm_stock
                ON p.ID = pm_stock.post_id
                AND pm_stock.meta_key = '_stock'

            -- Último cambio en history donde llegó a 0
            INNER JOIN (
                SELECT
                    product_id,
                    new_stock,
                    changed_by,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY created_at DESC) as rn
                FROM wpyz_stock_history
                WHERE new_stock = 0
            ) sh ON p.ID = sh.product_id AND sh.rn = 1

            -- Costo desde Fishbowl Cost
            LEFT JOIN woo_products_fccost fc
                ON pm_sku.meta_value = fc.sku

            WHERE p.post_type IN ('product', 'product_variation')
            AND p.post_status = 'publish'
            AND (
                CAST(pm_stock.meta_value AS DECIMAL) = 0
                OR pm_stock.meta_value IS NULL
            )
            AND (:search = '' OR pm_sku.meta_value LIKE :search_pattern OR p.post_title LIKE :search_pattern)

            ORDER BY
                CASE :sort_by
                    WHEN 'dias_sin_stock' THEN DATEDIFF(NOW(), sh.created_at)
                    WHEN 'sku' THEN 0
                    WHEN 'nombre' THEN 0
                    ELSE DATEDIFF(NOW(), sh.created_at)
                END DESC,
                CASE :sort_by
                    WHEN 'sku' THEN pm_sku.meta_value
                    WHEN 'nombre' THEN p.post_title
                    ELSE NULL
                END
        """)

        search_pattern = f'%{search}%'
        result = db.session.execute(
            query,
            {
                'search': search,
                'search_pattern': search_pattern,
                'sort_by': sort_by
            }
        )

        products = []
        for row in result:
            products.append({
                'product_id': row.product_id,
                'product_name': row.product_name,
                'sku': row.sku,
                'current_stock': int(float(row.current_stock)) if row.current_stock else 0,
                'dias_sin_stock': row.dias_sin_stock,
                'last_updated_by': row.last_updated_by,
                'last_stock_update': row.last_stock_update.strftime('%Y-%m-%d %H:%M:%S') if row.last_stock_update else None,
                'unit_cost_usd': float(row.unit_cost_usd) if row.unit_cost_usd else 0.00
            })

        return jsonify({
            'success': True,
            'products': products,
            'total': len(products)
        })

    except Exception as e:
        current_app.logger.error(f'Error en api_products_out_of_stock: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/orders', methods=['GET'])
@login_required
def api_get_orders():
    """
    API: Obtener lista de órdenes de compra

    Query params:
    - status: Filtrar por estado (pending, ordered, in_transit, received, cancelled)
    - start_date: Fecha inicio
    - end_date: Fecha fin

    Returns:
        JSON con lista de órdenes
    """
    try:
        status = request.args.get('status', type=str)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)

        query = PurchaseOrder.query

        # Filtros
        if status:
            query = query.filter(PurchaseOrder.status == status)

        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(PurchaseOrder.order_date >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            # Incluir todo el día
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(PurchaseOrder.order_date <= end_dt)

        # Ordenar por fecha más reciente primero
        orders = query.order_by(PurchaseOrder.order_date.desc()).all()

        orders_list = []
        for order in orders:
            order_dict = order.to_dict()
            # Agregar items
            items = []
            for item in order.items.all():
                items.append(item.to_dict())
            order_dict['items'] = items
            orders_list.append(order_dict)

        return jsonify({
            'success': True,
            'orders': orders_list,
            'total': len(orders_list)
        })

    except Exception as e:
        current_app.logger.error(f'Error en api_get_orders: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/orders/<int:order_id>', methods=['GET'])
@login_required
def api_get_order_detail(order_id):
    """
    API: Obtener detalle de una orden específica

    Returns:
        JSON con datos completos de la orden
    """
    try:
        order = PurchaseOrder.query.get_or_404(order_id)

        order_dict = order.to_dict()

        # Items
        items = []
        for item in order.items.all():
            items.append(item.to_dict())
        order_dict['items'] = items

        # Historial
        history = []
        for h in order.history.order_by(PurchaseOrderHistory.created_at.desc()).all():
            history.append(h.to_dict())
        order_dict['history'] = history

        return jsonify({
            'success': True,
            'order': order_dict
        })

    except Exception as e:
        current_app.logger.error(f'Error en api_get_order_detail: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/orders', methods=['POST'])
@login_required
@admin_required
def api_create_order():
    """
    API: Crear nueva orden de compra

    JSON Body:
    {
        "supplier_name": "Proveedor ABC",
        "expected_delivery_date": "2024-12-30",
        "notes": "Orden urgente",
        "items": [
            {
                "product_id": 123,
                "sku": "ABC-001",
                "product_title": "Producto XYZ",
                "quantity": 50,
                "unit_cost_usd": 15.00
            }
        ]
    }

    Returns:
        JSON con la orden creada
    """
    try:
        data = request.get_json()

        # Validaciones
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({
                'success': False,
                'error': 'Debe incluir al menos un producto'
            }), 400

        # Obtener tipo de cambio actual
        exchange_rate_query = text("""
            SELECT tasa_cambio
            FROM woo_tipo_cambio
            ORDER BY fecha DESC
            LIMIT 1
        """)
        result = db.session.execute(exchange_rate_query).first()
        exchange_rate = Decimal(str(result[0])) if result else Decimal('3.75')

        # Generar número de orden
        year = datetime.now().year
        last_order = PurchaseOrder.query.filter(
            PurchaseOrder.order_number.like(f'PO-{year}-%')
        ).order_by(PurchaseOrder.order_number.desc()).first()

        if last_order:
            last_num = int(last_order.order_number.split('-')[-1])
            order_number = f'PO-{year}-{last_num + 1:03d}'
        else:
            order_number = f'PO-{year}-001'

        # Calcular totales
        total_cost_usd = Decimal('0')
        for item in data['items']:
            quantity = Decimal(str(item['quantity']))
            unit_cost = Decimal(str(item['unit_cost_usd']))
            total_cost_usd += quantity * unit_cost

        total_cost_pen = total_cost_usd * exchange_rate

        # Parsear fecha estimada
        expected_delivery = None
        if data.get('expected_delivery_date'):
            expected_delivery = datetime.strptime(data['expected_delivery_date'], '%Y-%m-%d').date()

        # Crear orden
        order = PurchaseOrder(
            order_number=order_number,
            supplier_name=data.get('supplier_name', 'Sin especificar'),
            status='pending',
            order_date=get_local_time(),
            expected_delivery_date=expected_delivery,
            total_cost_usd=total_cost_usd,
            exchange_rate=exchange_rate,
            total_cost_pen=total_cost_pen,
            notes=data.get('notes'),
            created_by=current_user.username
        )

        db.session.add(order)
        db.session.flush()  # Para obtener el ID

        # Crear items
        for item_data in data['items']:
            quantity = int(item_data['quantity'])
            unit_cost = Decimal(str(item_data['unit_cost_usd']))

            item = PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=item_data['product_id'],
                product_title=item_data['product_title'],
                sku=item_data['sku'],
                quantity=quantity,
                unit_cost_usd=unit_cost,
                total_cost_usd=quantity * unit_cost,
                notes=item_data.get('notes')
            )
            db.session.add(item)

        # Crear registro en historial
        history = PurchaseOrderHistory(
            purchase_order_id=order.id,
            old_status=None,
            new_status='pending',
            changed_by=current_user.username,
            change_reason='Orden creada'
        )
        db.session.add(history)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Orden {order_number} creada exitosamente',
            'order': order.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error en api_create_order: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@login_required
@admin_required
def api_update_order_status(order_id):
    """
    API: Cambiar estado de una orden

    JSON Body:
    {
        "status": "received",
        "reason": "Mercancía recibida en almacén"
    }

    IMPORTANTE: Si status = 'received', actualiza stock automáticamente

    Returns:
        JSON con resultado
    """
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        data = request.get_json()

        new_status = data.get('status')
        reason = data.get('reason', f'Cambio a {new_status}')

        # Validar estado
        valid_statuses = ['pending', 'ordered', 'in_transit', 'received', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Estado inválido. Debe ser uno de: {", ".join(valid_statuses)}'
            }), 400

        old_status = order.status

        # Si cambia a 'received', actualizar stock automáticamente
        if new_status == 'received' and old_status != 'received':
            # Actualizar stock de cada producto
            for item in order.items.all():
                product = Product.query.get(item.product_id)
                if not product:
                    current_app.logger.warning(f'Producto {item.product_id} no encontrado')
                    continue

                # Obtener stock actual
                current_stock_value = product.get_meta('_stock')
                current_stock = int(float(current_stock_value)) if current_stock_value else 0

                # Nuevo stock = actual + cantidad recibida
                new_stock = current_stock + item.quantity

                # Actualizar metadatos
                product.set_meta('_stock', new_stock)
                product.set_meta('_stock_status', 'instock')
                product.set_meta('_manage_stock', 'yes')

                # Registrar en historial de stock
                stock_history = StockHistory(
                    product_id=product.ID,
                    product_title=product.post_title,
                    sku=item.sku,
                    old_stock=current_stock,
                    new_stock=new_stock,
                    change_amount=item.quantity,
                    changed_by=current_user.username,
                    change_reason=f'Recepción de orden {order.order_number}'
                )
                db.session.add(stock_history)

            # Guardar fecha real de entrega
            order.actual_delivery_date = datetime.now().date()

        # Actualizar estado
        order.status = new_status

        # Registrar en historial de orden
        history = PurchaseOrderHistory(
            purchase_order_id=order.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=current_user.username,
            change_reason=reason
        )
        db.session.add(history)

        db.session.commit()

        message = f'Estado actualizado a {new_status}'
        if new_status == 'received':
            message += f'. Stock actualizado para {order.items.count()} productos.'

        return jsonify({
            'success': True,
            'message': message,
            'order': order.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error en api_update_order_status: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/stats')
@login_required
def api_stats():
    """
    API: Estadísticas generales de compras

    Returns:
        JSON con métricas
    """
    try:
        # Total productos sin stock
        products_count_query = text("""
            SELECT COUNT(DISTINCT p.ID) as total
            FROM wpyz_posts p
            INNER JOIN wpyz_postmeta pm_sku
                ON p.ID = pm_sku.post_id
                AND pm_sku.meta_key = '_sku'
                AND pm_sku.meta_value IS NOT NULL
                AND pm_sku.meta_value != ''
            LEFT JOIN wpyz_postmeta pm_stock
                ON p.ID = pm_stock.post_id
                AND pm_stock.meta_key = '_stock'
            INNER JOIN (
                SELECT product_id, MAX(created_at) as last_update
                FROM wpyz_stock_history
                WHERE new_stock = 0
                GROUP BY product_id
            ) sh ON p.ID = sh.product_id
            WHERE p.post_type IN ('product', 'product_variation')
            AND p.post_status = 'publish'
            AND (CAST(pm_stock.meta_value AS DECIMAL) = 0 OR pm_stock.meta_value IS NULL)
        """)

        result = db.session.execute(products_count_query).first()
        products_out_of_stock = result[0] if result else 0

        # Órdenes por estado
        orders_by_status = db.session.query(
            PurchaseOrder.status,
            db.func.count(PurchaseOrder.id).label('count'),
            db.func.sum(PurchaseOrder.total_cost_usd).label('total_usd')
        ).group_by(PurchaseOrder.status).all()

        status_summary = {}
        for status, count, total in orders_by_status:
            status_summary[status] = {
                'count': count,
                'total_usd': float(total) if total else 0
            }

        return jsonify({
            'success': True,
            'stats': {
                'products_out_of_stock': products_out_of_stock,
                'orders_by_status': status_summary
            }
        })

    except Exception as e:
        current_app.logger.error(f'Error en api_stats: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/orders/<int:order_id>/pdf')
@login_required
def api_generate_pdf(order_id):
    """
    API: Generar y descargar PDF de orden de compra

    Returns:
        PDF file
    """
    try:
        order = PurchaseOrder.query.get_or_404(order_id)

        # Crear buffer en memoria
        buffer = BytesIO()

        # Crear documento PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#212529'),
            spaceAfter=12,
        )

        # Contenido del PDF
        elements = []

        # Título
        title = Paragraph("ORDEN DE COMPRA", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Información de la orden
        order_info_data = [
            ['Número de Orden:', order.order_number],
            ['Fecha:', order.order_date.strftime('%d/%m/%Y %H:%M')],
            ['Proveedor:', order.supplier_name or 'Sin especificar'],
            ['Estado:', order.status.upper()],
        ]

        if order.expected_delivery_date:
            order_info_data.append(['Fecha Estimada Entrega:', order.expected_delivery_date.strftime('%d/%m/%Y')])

        if order.actual_delivery_date:
            order_info_data.append(['Fecha Real Entrega:', order.actual_delivery_date.strftime('%d/%m/%Y')])

        order_info_table = Table(order_info_data, colWidths=[2*inch, 4*inch])
        order_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e9ecef')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(order_info_table)
        elements.append(Spacer(1, 20))

        # Productos
        products_heading = Paragraph("Productos", heading_style)
        elements.append(products_heading)

        # Tabla de productos
        products_data = [['SKU', 'Producto', 'Cantidad', 'Costo Unit.', 'Total']]

        for item in order.items:
            products_data.append([
                str(item.sku),
                str(item.product_title)[:40],  # Limitar longitud
                str(item.quantity),
                f'${float(item.unit_cost_usd):.2f}',
                f'${float(item.total_cost_usd):.2f}'
            ])

        # Fila de totales
        products_data.append(['', '', '', 'Total USD:', f'${float(order.total_cost_usd):.2f}'])
        products_data.append(['', '', '', 'Tipo de Cambio:', f'{float(order.exchange_rate):.4f}'])
        products_data.append(['', '', '', 'Total PEN:', f'S/. {float(order.total_cost_pen):.2f}'])

        products_table = Table(products_data, colWidths=[1.2*inch, 2.5*inch, 0.8*inch, 1.2*inch, 1*inch])
        products_table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Contenido
            ('TEXTCOLOR', (0, 1), (-1, -4), colors.black),
            ('ALIGN', (2, 1), (2, -4), 'CENTER'),  # Cantidad centrada
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Montos alineados a derecha
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),

            # Totales
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -3), (-1, -3), 2, colors.black),

            # Padding general
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(products_table)
        elements.append(Spacer(1, 20))

        # Notas
        if order.notes:
            notes_heading = Paragraph("Notas", heading_style)
            elements.append(notes_heading)
            notes_text = Paragraph(order.notes, styles['Normal'])
            elements.append(notes_text)
            elements.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer = Paragraph(
            f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} por {current_user.username}",
            footer_style
        )
        elements.append(Spacer(1, 12))
        elements.append(footer)

        # Construir PDF
        doc.build(elements)

        # Preparar respuesta
        buffer.seek(0)
        filename = f"orden_compra_{order.order_number}.pdf"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        current_app.logger.error(f'Error en api_generate_pdf: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
