# app/routes/expenses.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.routes.auth import master_required
from app.models import ExpenseDetail
from app import db
from config import get_local_time
from datetime import datetime
from decimal import Decimal, InvalidOperation

bp = Blueprint('expenses', __name__, url_prefix='/expenses')


@bp.route('/')
@login_required
@master_required
def index():
    """
    Vista principal de Gastos Detallados
    Solo accesible para usuarios Master

    URL: http://localhost:5000/expenses/
    """
    return render_template('expenses.html', title='Gastos Detallados')


@bp.route('/list', methods=['GET'])
@login_required
@master_required
def list_expenses():
    """
    Obtener lista de todos los gastos

    Responde con JSON para cargar en la tabla editable
    """
    try:
        # Obtener parámetros de paginación y ordenamiento
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        search = request.args.get('search', '', type=str)

        # Construir query base
        query = ExpenseDetail.query

        # Aplicar filtro de búsqueda si existe
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                db.or_(
                    ExpenseDetail.tipo_gasto.like(search_filter),
                    ExpenseDetail.categoria.like(search_filter),
                    ExpenseDetail.descripcion.like(search_filter)
                )
            )

        # Ordenar por fecha descendente y luego por ID
        query = query.order_by(ExpenseDetail.fecha.desc(), ExpenseDetail.id.desc())

        # Paginar resultados
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        expenses = pagination.items

        # Convertir a diccionario
        expenses_list = [expense.to_dict() for expense in expenses]

        return jsonify({
            'success': True,
            'expenses': expenses_list,
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


@bp.route('/create', methods=['POST'])
@login_required
@master_required
def create_expense():
    """
    Crear un nuevo gasto

    JSON Body:
    {
        "fecha": "2025-12-10",
        "tipo_gasto": "Operativo",
        "categoria": "Servicios",
        "descripcion": "Pago de internet",
        "monto": 150.00
    }
    """
    try:
        data = request.get_json()

        # Validaciones
        required_fields = ['fecha', 'tipo_gasto', 'categoria', 'descripcion', 'monto']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'El campo {field} es requerido'
                }), 400

        # Validar y convertir fecha
        try:
            fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Formato de fecha inválido. Usar YYYY-MM-DD'
            }), 400

        # Validar y convertir monto
        try:
            monto = Decimal(str(data['monto']))
            if monto <= 0:
                return jsonify({
                    'success': False,
                    'error': 'El monto debe ser mayor que 0'
                }), 400
        except (InvalidOperation, ValueError):
            return jsonify({
                'success': False,
                'error': 'Monto inválido'
            }), 400

        # Crear nuevo gasto
        expense = ExpenseDetail(
            fecha=fecha,
            tipo_gasto=data['tipo_gasto'].strip(),
            categoria=data['categoria'].strip(),
            descripcion=data['descripcion'].strip(),
            monto=monto,
            created_by=current_user.username
        )

        db.session.add(expense)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Gasto creado correctamente',
            'expense': expense.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/update/<int:expense_id>', methods=['PUT'])
@login_required
@master_required
def update_expense(expense_id):
    """
    Actualizar un gasto existente

    URL: PUT /expenses/update/123

    JSON Body:
    {
        "fecha": "2025-12-10",
        "tipo_gasto": "Operativo",
        "categoria": "Servicios",
        "descripcion": "Pago de internet actualizado",
        "monto": 180.00
    }
    """
    try:
        expense = ExpenseDetail.query.get(expense_id)
        if not expense:
            return jsonify({
                'success': False,
                'error': 'Gasto no encontrado'
            }), 404

        data = request.get_json()

        # Actualizar fecha si se proporciona
        if 'fecha' in data and data['fecha']:
            try:
                expense.fecha = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de fecha inválido'
                }), 400

        # Actualizar tipo_gasto
        if 'tipo_gasto' in data and data['tipo_gasto']:
            expense.tipo_gasto = data['tipo_gasto'].strip()

        # Actualizar categoria
        if 'categoria' in data and data['categoria']:
            expense.categoria = data['categoria'].strip()

        # Actualizar descripcion
        if 'descripcion' in data and data['descripcion']:
            expense.descripcion = data['descripcion'].strip()

        # Actualizar monto
        if 'monto' in data and data['monto'] is not None:
            try:
                monto = Decimal(str(data['monto']))
                if monto <= 0:
                    return jsonify({
                        'success': False,
                        'error': 'El monto debe ser mayor que 0'
                    }), 400
                expense.monto = monto
            except (InvalidOperation, ValueError):
                return jsonify({
                    'success': False,
                    'error': 'Monto inválido'
                }), 400

        # Actualizar auditoría
        expense.updated_by = current_user.username
        expense.updated_at = get_local_time()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Gasto actualizado correctamente',
            'expense': expense.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/delete/<int:expense_id>', methods=['DELETE'])
@login_required
@master_required
def delete_expense(expense_id):
    """
    Eliminar un gasto

    URL: DELETE /expenses/delete/123
    """
    try:
        expense = ExpenseDetail.query.get(expense_id)
        if not expense:
            return jsonify({
                'success': False,
                'error': 'Gasto no encontrado'
            }), 404

        # Guardar info para respuesta
        expense_dict = expense.to_dict()

        db.session.delete(expense)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Gasto eliminado correctamente',
            'expense': expense_dict
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/stats', methods=['GET'])
@login_required
@master_required
def get_stats():
    """
    Obtener estadísticas de gastos

    - Total general
    - Total por tipo de gasto
    - Total por categoría
    - Total por mes
    """
    try:
        from sqlalchemy import func, extract

        # Total general
        total_general = db.session.query(func.sum(ExpenseDetail.monto)).scalar() or 0

        # Total por tipo de gasto
        por_tipo = db.session.query(
            ExpenseDetail.tipo_gasto,
            func.sum(ExpenseDetail.monto).label('total')
        ).group_by(ExpenseDetail.tipo_gasto).all()

        # Total por categoría
        por_categoria = db.session.query(
            ExpenseDetail.categoria,
            func.sum(ExpenseDetail.monto).label('total')
        ).group_by(ExpenseDetail.categoria).all()

        # Total por mes (últimos 12 meses)
        año_col = extract('year', ExpenseDetail.fecha).label('año')
        mes_col = extract('month', ExpenseDetail.fecha).label('mes')
        total_col = func.sum(ExpenseDetail.monto).label('total')

        por_mes = db.session.query(año_col, mes_col, total_col)\
            .group_by(año_col, mes_col)\
            .order_by(año_col.desc(), mes_col.desc())\
            .limit(12).all()

        return jsonify({
            'success': True,
            'stats': {
                'total_general': float(total_general),
                'por_tipo': [{'tipo': t, 'total': float(total)} for t, total in por_tipo],
                'por_categoria': [{'categoria': c, 'total': float(total)} for c, total in por_categoria],
                'por_mes': [{'año': int(y), 'mes': int(m), 'total': float(total)} for y, m, total in por_mes]
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
