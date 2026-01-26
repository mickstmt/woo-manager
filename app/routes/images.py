from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.models import Product, ProductMeta
from app import db
from sqlalchemy import text, or_
import os

bp = Blueprint('images', __name__, url_prefix='/images')

@bp.route('/')
@login_required
def index():
    """Vista principal de gestión de imágenes"""
    return render_template('images.html', title='Gestión de Imágenes')

@bp.route('/api/list')
@login_required
def list_products():
    """
    Listar productos para gestión de imágenes con búsqueda
    Reutiliza la lógica de búsqueda de products.py
    """
    try:
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 24  # Grid view se ve mejor con múltiplos de 3 o 4

        query = Product.query.filter(Product.post_type == 'product', Product.post_status == 'publish')

        if search:
            # Separar términos de búsqueda
            search_terms = search.split()
            conditions = []
            for term in search_terms:
                conditions.append(or_(
                    Product.post_title.like(f'%{term}%'),
                    Product.ID.like(f'%{term}%'),
                    Product.product_meta.any(db.and_(ProductMeta.meta_key == '_sku', ProductMeta.meta_value.like(f'%{term}%')))
                ))
            query = query.filter(db.and_(*conditions))

        pagination = query.order_by(Product.post_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        products = pagination.items

        # Precargar imágenes para mayor eficiencia
        Product.preload_images_for_products(products)

        products_list = []
        for p in products:
            products_list.append({
                'id': p.ID,
                'title': p.post_title,
                'sku': p.get_meta('_sku') or 'N/A',
                'image_url': p._image_url_cache or '/static/img/no-image.png',
                'is_variable': p.is_variable()
            })

        return jsonify({
            'success': True,
            'products': products_list,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/details/<int:product_id>')
@login_required
def get_details(product_id):
    """Obtener detalles de imagen del producto padre y todas sus variaciones"""
    try:
        parent = Product.query.get(product_id)
        if not parent:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

        # Obtener variaciones
        variations = parent.get_variations()
        
        # Precargar imágenes
        all_items = [parent] + variations
        Product.preload_images_for_products(all_items)

        # Preparar data del padre
        data = {
            'id': parent.ID,
            'title': parent.post_title,
            'sku': parent.get_meta('_sku') or 'N/A',
            'image_url': parent._image_url_cache or '/static/img/no-image.png',
            'variations': []
        }

        # Preparar data de variaciones
        for v in variations:
            # Obtener atributos de la variación
            attributes = []
            for meta in v.product_meta:
                if meta.meta_key.startswith('attribute_pa_'):
                    attr_name = meta.meta_key.replace('attribute_pa_', '').title()
                    attributes.append(f"{attr_name}: {meta.meta_value}")
            
            data['variations'].append({
                'id': v.ID,
                'sku': v.get_meta('_sku') or 'N/A',
                'image_url': v._image_url_cache or '/static/img/no-image.png',
                'label': ', '.join(attributes) if attributes else f"Variación #{v.ID}"
            })

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/upload', methods=['POST'])
@login_required
def upload_image():
    """Subir imagen a la biblioteca de medios y asignarla a un producto/variación"""
    try:
        from woocommerce import API
        import tempfile
        import base64

        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se recibió ninguna imagen'}), 400
        
        file = request.files['image']
        product_id = request.form.get('product_id')
        is_variation = request.form.get('is_variation') == 'true'

        if not product_id:
            return jsonify({'success': False, 'error': 'Falta el ID del producto'}), 400

        # Conectar con API de WooCommerce
        wcapi = API(
            url=current_app.config['WC_API_URL'],
            consumer_key=current_app.config['WC_CONSUMER_KEY'],
            consumer_secret=current_app.config['WC_CONSUMER_SECRET'],
            version="wc/v3",
            timeout=60
        )

        # Leer archivo y codificar en base64 para WooCommerce API
        file_content = file.read()
        encoded_string = base64.b64encode(file_content).decode('utf-8')

        # Preparar objeto de imagen para WC
        image_data = {
            "name": file.filename,
            "type": file.content_type,
            "src": f"data:{file.content_type};base64,{encoded_string}"
        }

        if is_variation:
            # Actualizar variación
            var_obj = Product.query.get(product_id)
            if not var_obj:
                return jsonify({'success': False, 'error': 'Variación no encontrada'}), 404
                
            parent_id = var_obj.post_parent
            resp = wcapi.put(f"products/{parent_id}/variations/{product_id}", {
                "image": image_data
            })
        else:
            # Actualizar producto padre (reemplaza imagen principal)
            resp = wcapi.put(f"products/{product_id}", {
                "images": [image_data]
            })

        if resp.status_code not in [200, 201]:
            error_data = resp.json()
            return jsonify({'success': False, 'error': error_data.get('message', 'Error en API de WooCommerce')}), resp.status_code

        # Obtener la nueva URL para devolverla al frontend
        updated_data = resp.json()
        new_url = ""
        if is_variation:
            new_url = updated_data.get('image', {}).get('src', '')
        else:
            new_url = updated_data.get('images', [{}])[0].get('src', '')

        return jsonify({
            'success': True,
            'message': 'Imagen actualizada correctamente',
            'new_url': new_url
        })

    except Exception as e:
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500