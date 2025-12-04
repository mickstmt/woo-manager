# app/routes/prices.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.routes.auth import admin_required, advisor_or_admin_required
from app.models import Product, ProductMeta, PriceHistory
from app import db, cache
from datetime import datetime
from sqlalchemy import or_, func, text
from decimal import Decimal, InvalidOperation

bp = Blueprint('prices', __name__, url_prefix='/prices')


@bp.route('/')
@login_required
def index():
    """
    Vista principal de gestión de precios

    URL: http://localhost:5000/prices/
    """
    return render_template('prices.html', title='Gestión de Precios')


@bp.route('/list')
@login_required
@cache.cached(timeout=300, query_string=True)  # Cache 5 min basado en búsqueda
def list_prices():
    """
    Obtener lista de productos con información de precios

    Comportamiento:
    - Sin búsqueda: No muestra nada (lista vacía)
    - Con búsqueda: Detecta si es SKU o nombre y busca en ambos (productos + variaciones)
    """
    try:
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '', type=str)

        # Limitar per_page
        per_page = min(per_page, 500)

        # Inicializar lista de productos
        products_list = []
        all_items = []

        # ========================================
        # CASO 1: Sin búsqueda - No mostrar nada
        # ========================================
        if not search or search.strip() == '':
            return jsonify({
                'success': True,
                'products': [],
                'search_term': '',
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'pages': 1,
                    'has_prev': False,
                    'has_next': False,
                    'prev_num': None,
                    'next_num': None
                }
            })

        # ========================================
        # CASO 2: Con búsqueda
        # ========================================

        # Buscar en productos simples (con SKU)
        simple_products_query = text("""
            SELECT DISTINCT p.ID
            FROM wpyz_posts p
            LEFT JOIN wpyz_postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sku'
            WHERE p.post_type = 'product'
            AND p.post_status = 'publish'
            AND (
                p.post_title LIKE :search
                OR p.ID LIKE :search
                OR pm.meta_value LIKE :search
            )
        """)

        result = db.session.execute(simple_products_query, {'search': f'%{search}%'})
        simple_ids = [row[0] for row in result]

        # Buscar en variaciones (por título, ID, SKU O por ID del producto padre)
        variations_query = text("""
            SELECT DISTINCT v.ID
            FROM wpyz_posts v
            LEFT JOIN wpyz_postmeta vm ON v.ID = vm.post_id AND vm.meta_key = '_sku'
            WHERE v.post_type = 'product_variation'
            AND v.post_status = 'publish'
            AND (
                v.post_title LIKE :search
                OR v.ID LIKE :search
                OR vm.meta_value LIKE :search
                OR v.post_parent LIKE :search
            )
        """)

        result = db.session.execute(variations_query, {'search': f'%{search}%'})
        variation_ids = [row[0] for row in result]

        # Obtener productos simples
        if simple_ids:
            simple_products = Product.query.filter(Product.ID.in_(simple_ids)).all()
            for product in simple_products:
                all_items.append({
                    'product': product,
                    'is_variation': False
                })

        # Obtener variaciones
        if variation_ids:
            variations = Product.query.filter(Product.ID.in_(variation_ids)).all()
            for variation in variations:
                all_items.append({
                    'product': variation,
                    'is_variation': True
                })

        # ========================================
        # OPTIMIZACIÓN: Eager load de metadatos - 1 query
        # ========================================
        all_product_ids = [item['product'].ID for item in all_items]

        # Obtener TODOS los metadatos en UNA sola consulta
        meta_keys = ['_sku', '_regular_price', '_sale_price', '_price']

        all_meta = db.session.query(
            ProductMeta.post_id,
            ProductMeta.meta_key,
            ProductMeta.meta_value
        ).filter(
            ProductMeta.post_id.in_(all_product_ids),
            ProductMeta.meta_key.in_(meta_keys)
        ).all()

        # Crear diccionario: {product_id: {meta_key: meta_value}}
        meta_dict = {}
        for post_id, meta_key, meta_value in all_meta:
            if post_id not in meta_dict:
                meta_dict[post_id] = {}
            meta_dict[post_id][meta_key] = meta_value

        # ========================================
        # OPTIMIZACIÓN: Cargar productos padre en 1 query
        # ========================================
        parent_ids = list(set([item['product'].post_parent for item in all_items
                              if item['is_variation'] and item['product'].post_parent]))

        parents_dict = {}
        if parent_ids:
            parents = Product.query.filter(Product.ID.in_(parent_ids)).all()
            parents_dict = {p.ID: p for p in parents}

        # ========================================
        # Procesar todos los items - SIN QUERIES ADICIONALES
        # ========================================
        for item in all_items:
            product = item['product']
            is_variation = item['is_variation']

            # Obtener metadatos del diccionario (sin queries)
            product_meta = meta_dict.get(product.ID, {})
            sku = product_meta.get('_sku', 'N/A')
            regular_price = product_meta.get('_regular_price', '0')
            sale_price = product_meta.get('_sale_price', '')
            price = product_meta.get('_price', '0')

            # Convertir a float para JSON
            try:
                regular_price_num = float(regular_price) if regular_price else 0.0
            except:
                regular_price_num = 0.0

            try:
                sale_price_num = float(sale_price) if sale_price else None
            except:
                sale_price_num = None

            try:
                price_num = float(price) if price else 0.0
            except:
                price_num = 0.0

            # Determinar si está en oferta
            on_sale = sale_price_num is not None and sale_price_num > 0

            # Obtener padre del diccionario (sin query)
            parent_id = None
            parent_title = None
            if is_variation and product.post_parent:
                parent = parents_dict.get(product.post_parent)
                if parent:
                    parent_id = parent.ID
                    parent_title = parent.post_title

            product_data = {
                'id': product.ID,
                'parent_id': parent_id,
                'parent_title': parent_title,
                'title': product.post_title,
                'type': 'variation' if is_variation else 'simple',
                'sku': sku,
                'regular_price': regular_price_num,
                'sale_price': sale_price_num,
                'price': price_num,
                'on_sale': on_sale
            }

            products_list.append(product_data)

        # ========================================
        # Paginación
        # ========================================
        total_items = len(products_list)

        # Aplicar paginación manualmente
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_products = products_list[start_idx:end_idx]

        # Calcular páginas
        import math
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

        return jsonify({
            'success': True,
            'products': paginated_products,
            'search_term': search,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_items,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < total_pages else None
            }
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/update/<int:product_id>', methods=['POST'])
@login_required
@advisor_or_admin_required
def update_price(product_id):
    """
    Actualizar precios de un producto individual

    URL: POST http://localhost:5000/prices/update/123

    JSON Body:
    {
        "regular_price": 100.00,
        "sale_price": 80.00,  # opcional, null para eliminar
        "reason": "Ajuste de mercado"
    }
    """
    try:
        # Invalidar caché al actualizar precios
        cache.clear()

        # Obtener datos del request
        data = request.get_json()
        new_regular_price = data.get('regular_price')
        new_sale_price = data.get('sale_price')  # Puede ser None
        reason = data.get('reason', 'Actualización manual')

        # Validar precio regular
        if new_regular_price is None:
            return jsonify({
                'success': False,
                'error': 'El campo regular_price es requerido'
            }), 400

        try:
            new_regular_price = Decimal(str(new_regular_price))
            if new_regular_price <= 0:
                return jsonify({
                    'success': False,
                    'error': 'El precio regular debe ser mayor que 0'
                }), 400
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'El precio regular debe ser un número válido'
            }), 400

        # Validar precio de oferta si existe
        if new_sale_price is not None and new_sale_price != '':
            try:
                new_sale_price = Decimal(str(new_sale_price))
                if new_sale_price < 0:
                    return jsonify({
                        'success': False,
                        'error': 'El precio de oferta no puede ser negativo'
                    }), 400
                if new_sale_price >= new_regular_price:
                    return jsonify({
                        'success': False,
                        'error': 'El precio de oferta debe ser menor que el precio regular'
                    }), 400
            except (InvalidOperation, ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'El precio de oferta debe ser un número válido'
                }), 400
        else:
            new_sale_price = None

        # Buscar el producto
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'error': 'Producto no encontrado'
            }), 404

        # Obtener precios actuales
        old_regular_price_value = product.get_meta('_regular_price')
        old_sale_price_value = product.get_meta('_sale_price')
        old_price_value = product.get_meta('_price')

        old_regular_price = Decimal(old_regular_price_value) if old_regular_price_value else Decimal('0')
        old_sale_price = Decimal(old_sale_price_value) if old_sale_price_value else None
        old_price = Decimal(old_price_value) if old_price_value else Decimal('0')

        # Determinar precio activo nuevo
        new_price = new_sale_price if new_sale_price else new_regular_price

        # Si no cambió nada, no hacer nada
        if (old_regular_price == new_regular_price and
            old_sale_price == new_sale_price and
            old_price == new_price):
            return jsonify({
                'success': True,
                'message': 'No hubo cambios en los precios',
                'old_regular_price': float(old_regular_price),
                'new_regular_price': float(new_regular_price)
            })

        # Actualizar los precios
        product.set_meta('_regular_price', str(new_regular_price))

        if new_sale_price:
            product.set_meta('_sale_price', str(new_sale_price))
        else:
            # Eliminar precio de oferta si es None
            sale_meta = product.product_meta.filter_by(meta_key='_sale_price').first()
            if sale_meta:
                db.session.delete(sale_meta)

        product.set_meta('_price', str(new_price))

        # Guardar en la base de datos
        db.session.commit()

        # Registrar en el historial (transacción separada)
        try:
            history = PriceHistory(
                product_id=product.ID,
                product_title=product.post_title,
                sku=product.get_meta('_sku') or 'N/A',
                old_regular_price=old_regular_price,
                old_sale_price=old_sale_price,
                old_price=old_price,
                new_regular_price=new_regular_price,
                new_sale_price=new_sale_price,
                new_price=new_price,
                changed_by=current_user.username,
                change_reason=reason
            )
            db.session.add(history)
            db.session.commit()
        except Exception as hist_error:
            # Si falla el historial, no fallar la actualización de precios
            db.session.rollback()
            import logging
            logging.error(f"Error al guardar historial de precios para producto {product.ID}: {str(hist_error)}")
            import traceback
            logging.error(traceback.format_exc())

        return jsonify({
            'success': True,
            'message': f'Precios actualizados correctamente',
            'product_id': product.ID,
            'product_title': product.post_title,
            'old_regular_price': float(old_regular_price),
            'new_regular_price': float(new_regular_price),
            'old_sale_price': float(old_sale_price) if old_sale_price else None,
            'new_sale_price': float(new_sale_price) if new_sale_price else None,
            'old_price': float(old_price),
            'new_price': float(new_price)
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/update-multiple', methods=['POST'])
@advisor_or_admin_required
def update_multiple_prices():
    """
    Actualizar precios de múltiples productos a la vez
    ADMINS Y ASESORES

    Modos soportados:
    1. "percentage": Aplicar incremento/descuento porcentual
    2. "fixed": Establecer precios fijos
    3. "remove_sale": Eliminar precios de oferta
    """
    try:
        # Invalidar caché al actualizar precios masivos
        cache.clear()

        # Obtener datos
        data = request.get_json()
        mode = data.get('mode', 'fixed')
        reason = data.get('reason', 'Actualización masiva')

        updated = []
        errors = []

        # ========================================
        # MODO 1: Incremento/Descuento Porcentual
        # ========================================
        if mode == 'percentage':
            product_ids = data.get('products', [])
            percentage = data.get('percentage', 0)
            apply_to = data.get('apply_to', 'regular')  # 'regular', 'sale', 'both'

            if not product_ids:
                return jsonify({
                    'success': False,
                    'error': 'No se enviaron productos para actualizar'
                }), 400

            try:
                percentage = Decimal(str(percentage))
            except:
                return jsonify({
                    'success': False,
                    'error': 'Porcentaje inválido'
                }), 400

            # Procesar cada producto
            for product_id in product_ids:
                try:
                    product = db.session.query(Product).filter_by(ID=product_id).first()

                    if not product:
                        errors.append({'id': product_id, 'error': 'Producto no encontrado'})
                        continue

                    # Obtener precios actuales
                    regular_meta = db.session.query(ProductMeta).filter_by(
                        post_id=product_id, meta_key='_regular_price'
                    ).first()
                    sale_meta = db.session.query(ProductMeta).filter_by(
                        post_id=product_id, meta_key='_sale_price'
                    ).first()

                    old_regular = Decimal(regular_meta.meta_value) if regular_meta else Decimal('0')
                    old_sale = Decimal(sale_meta.meta_value) if sale_meta and sale_meta.meta_value else None

                    # Calcular nuevos precios
                    multiplier = Decimal('1') + (percentage / Decimal('100'))

                    new_regular = old_regular
                    new_sale = old_sale

                    if apply_to in ['regular', 'both']:
                        new_regular = (old_regular * multiplier).quantize(Decimal('0.01'))

                    if apply_to in ['sale', 'both'] and old_sale:
                        new_sale = (old_sale * multiplier).quantize(Decimal('0.01'))

                    # Validar
                    if new_regular <= 0:
                        errors.append({'id': product_id, 'error': 'Precio resultante inválido'})
                        continue

                    if new_sale and new_sale >= new_regular:
                        errors.append({'id': product_id, 'error': 'Precio de oferta >= precio regular'})
                        continue

                    # Actualizar
                    if regular_meta:
                        regular_meta.meta_value = str(new_regular)
                    else:
                        db.session.add(ProductMeta(post_id=product_id, meta_key='_regular_price',
                                                   meta_value=str(new_regular)))

                    if new_sale:
                        if sale_meta:
                            sale_meta.meta_value = str(new_sale)
                        else:
                            db.session.add(ProductMeta(post_id=product_id, meta_key='_sale_price',
                                                       meta_value=str(new_sale)))

                    # Actualizar precio activo
                    new_price = new_sale if new_sale else new_regular
                    price_meta = db.session.query(ProductMeta).filter_by(
                        post_id=product_id, meta_key='_price'
                    ).first()
                    if price_meta:
                        price_meta.meta_value = str(new_price)
                    else:
                        db.session.add(ProductMeta(post_id=product_id, meta_key='_price',
                                                   meta_value=str(new_price)))

                    db.session.commit()

                    # Historial
                    try:
                        history = PriceHistory(
                            product_id=product_id,
                            product_title=product.post_title,
                            sku=product.get_meta('_sku') or 'N/A',
                            old_regular_price=old_regular,
                            old_sale_price=old_sale,
                            old_price=old_sale if old_sale else old_regular,
                            new_regular_price=new_regular,
                            new_sale_price=new_sale,
                            new_price=new_price,
                            changed_by=current_user.username,
                            change_reason=reason
                        )
                        db.session.add(history)
                        db.session.commit()
                    except:
                        pass

                    updated.append({
                        'id': product_id,
                        'title': product.post_title,
                        'old_regular': float(old_regular),
                        'new_regular': float(new_regular),
                        'old_sale': float(old_sale) if old_sale else None,
                        'new_sale': float(new_sale) if new_sale else None
                    })

                except Exception as prod_error:
                    db.session.rollback()
                    errors.append({'id': product_id, 'error': str(prod_error)})

        # ========================================
        # MODO 2: Precios Fijos
        # ========================================
        elif mode == 'fixed':
            products_data = data.get('products', [])

            if not products_data:
                return jsonify({
                    'success': False,
                    'error': 'No se enviaron productos para actualizar'
                }), 400

            for item in products_data:
                product_id = item.get('id')
                new_regular = item.get('regular_price')
                new_sale = item.get('sale_price')

                # Validaciones
                if not product_id or new_regular is None:
                    errors.append({'id': product_id, 'error': 'ID o precio regular faltante'})
                    continue

                try:
                    new_regular = Decimal(str(new_regular))
                    if new_regular <= 0:
                        errors.append({'id': product_id, 'error': 'Precio regular debe ser > 0'})
                        continue
                except:
                    errors.append({'id': product_id, 'error': 'Precio regular inválido'})
                    continue

                if new_sale is not None and new_sale != '':
                    try:
                        new_sale = Decimal(str(new_sale))
                        if new_sale >= new_regular:
                            errors.append({'id': product_id, 'error': 'Precio oferta >= regular'})
                            continue
                    except:
                        errors.append({'id': product_id, 'error': 'Precio de oferta inválido'})
                        continue
                else:
                    new_sale = None

                # Procesar
                try:
                    product = db.session.query(Product).filter_by(ID=product_id).first()
                    if not product:
                        errors.append({'id': product_id, 'error': 'Producto no encontrado'})
                        continue

                    # Obtener precios actuales
                    old_regular = Decimal(product.get_meta('_regular_price') or '0')
                    old_sale_val = product.get_meta('_sale_price')
                    old_sale = Decimal(old_sale_val) if old_sale_val else None

                    # Actualizar
                    product.set_meta('_regular_price', str(new_regular))

                    if new_sale:
                        product.set_meta('_sale_price', str(new_sale))
                    else:
                        sale_meta = product.product_meta.filter_by(meta_key='_sale_price').first()
                        if sale_meta:
                            db.session.delete(sale_meta)

                    new_price = new_sale if new_sale else new_regular
                    product.set_meta('_price', str(new_price))

                    db.session.commit()

                    # Historial
                    try:
                        history = PriceHistory(
                            product_id=product_id,
                            product_title=product.post_title,
                            sku=product.get_meta('_sku') or 'N/A',
                            old_regular_price=old_regular,
                            old_sale_price=old_sale,
                            old_price=old_sale if old_sale else old_regular,
                            new_regular_price=new_regular,
                            new_sale_price=new_sale,
                            new_price=new_price,
                            changed_by=current_user.username,
                            change_reason=reason
                        )
                        db.session.add(history)
                        db.session.commit()
                    except:
                        pass

                    updated.append({
                        'id': product_id,
                        'title': product.post_title,
                        'old_regular': float(old_regular),
                        'new_regular': float(new_regular)
                    })

                except Exception as prod_error:
                    db.session.rollback()
                    errors.append({'id': product_id, 'error': str(prod_error)})

        # ========================================
        # MODO 3: Eliminar Ofertas
        # ========================================
        elif mode == 'remove_sale':
            product_ids = data.get('products', [])

            if not product_ids:
                return jsonify({
                    'success': False,
                    'error': 'No se enviaron productos para actualizar'
                }), 400

            for product_id in product_ids:
                try:
                    product = db.session.query(Product).filter_by(ID=product_id).first()
                    if not product:
                        errors.append({'id': product_id, 'error': 'Producto no encontrado'})
                        continue

                    # Obtener precios actuales
                    old_regular = Decimal(product.get_meta('_regular_price') or '0')
                    old_sale_val = product.get_meta('_sale_price')
                    old_sale = Decimal(old_sale_val) if old_sale_val else None

                    # Eliminar precio de oferta
                    sale_meta = product.product_meta.filter_by(meta_key='_sale_price').first()
                    if sale_meta:
                        db.session.delete(sale_meta)

                    # Precio activo = regular
                    product.set_meta('_price', str(old_regular))

                    db.session.commit()

                    # Historial
                    try:
                        history = PriceHistory(
                            product_id=product_id,
                            product_title=product.post_title,
                            sku=product.get_meta('_sku') or 'N/A',
                            old_regular_price=old_regular,
                            old_sale_price=old_sale,
                            old_price=old_sale if old_sale else old_regular,
                            new_regular_price=old_regular,
                            new_sale_price=None,
                            new_price=old_regular,
                            changed_by=current_user.username,
                            change_reason=reason
                        )
                        db.session.add(history)
                        db.session.commit()
                    except:
                        pass

                    updated.append({
                        'id': product_id,
                        'title': product.post_title,
                        'removed_sale': True
                    })

                except Exception as prod_error:
                    db.session.rollback()
                    errors.append({'id': product_id, 'error': str(prod_error)})

        else:
            return jsonify({
                'success': False,
                'error': f'Modo "{mode}" no soportado'
            }), 400

        # Respuesta final
        if updated:
            return jsonify({
                'success': True,
                'message': f'{len(updated)} productos actualizados',
                'updated': updated,
                'errors': errors,
                'total_updated': len(updated),
                'total_errors': len(errors)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo actualizar ningún producto',
                'errors': errors
            }), 400

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/history/<int:product_id>')
@login_required
def product_history(product_id):
    """
    Obtener historial de cambios de precios de un producto

    URL: http://localhost:5000/prices/history/123
    """
    try:
        # Obtener historial ordenado por fecha (más reciente primero)
        history = PriceHistory.query.filter_by(
            product_id=product_id
        ).order_by(PriceHistory.created_at.desc()).limit(50).all()

        history_list = []
        for record in history:
            history_list.append({
                'id': record.id,
                'old_regular_price': float(record.old_regular_price) if record.old_regular_price else None,
                'new_regular_price': float(record.new_regular_price) if record.new_regular_price else None,
                'old_sale_price': float(record.old_sale_price) if record.old_sale_price else None,
                'new_sale_price': float(record.new_sale_price) if record.new_sale_price else None,
                'old_price': float(record.old_price) if record.old_price else None,
                'new_price': float(record.new_price) if record.new_price else None,
                'changed_by': record.changed_by,
                'reason': record.change_reason,
                'date': record.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({
            'success': True,
            'product_id': product_id,
            'history': history_list,
            'total': len(history_list)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/stats')
@login_required
def price_stats():
    """
    Obtener estadísticas generales de precios

    URL: http://localhost:5000/prices/stats
    """
    try:
        # Contar productos totales
        total_products = Product.query.filter_by(
            post_type='product',
            post_status='publish'
        ).count()

        # Estas estadísticas las calcularemos en el cliente
        # porque dependen de los metadatos

        return jsonify({
            'success': True,
            'stats': {
                'total': total_products
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
