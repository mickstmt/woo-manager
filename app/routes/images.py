from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.models import Product, ProductMeta, Term
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
                'image_url': p._image_url_cache or 'https://placehold.co/600x600?text=Sin+Imagen',
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
            'image_url': parent._image_url_cache or 'https://placehold.co/600x600?text=Sin+Imagen',
            'variations': []
        }

        # 1. Recolectar todos los slugs de atributos globales para buscar sus nombres reales
        term_slugs = set()
        for v in variations:
            for meta in v.product_meta:
                if meta.meta_key.startswith('attribute_pa_') and meta.meta_value:
                    term_slugs.add(meta.meta_value)
        
        term_map = {}
        if term_slugs:
            terms = Term.query.filter(Term.slug.in_(term_slugs)).all()
            term_map = {t.slug: t.name for t in terms}

        # 2. Preparar data de variaciones
        for v in variations:
            # Obtener atributos de la variación
            attr_list = []
            for meta in v.product_meta:
                if meta.meta_key.startswith('attribute_'):
                    attr_slug = meta.meta_value
                    is_global = meta.meta_key.startswith('attribute_pa_')
                    
                    # Valor por defecto (slug original o Cualquiera)
                    display_value = attr_slug if attr_slug else "Cualquiera"
                    
                    # Si es global, buscar en el mapa de términos
                    if is_global and attr_slug in term_map:
                        display_value = term_map[attr_slug]
                    
                    # Limpiar prefijo del nombre del atributo (Color, Talla, etc)
                    attr_name = meta.meta_key.replace('attribute_pa_', '').replace('attribute_', '').replace('_', ' ').replace('-', ' ').title()
                    
                    # Normalizar capitalización del valor: Si ya tiene mezcla de números y letras (como 42mm), 
                    # tratamos de no romperlo con title() si el usuario prefiere mm en minúscula.
                    # Por defecto solo capitalizamos la primera letra si no es un técnico.
                    if display_value and not any(char.isdigit() for char in display_value):
                        display_value = display_value.title()
                    
                    attr_list.append({
                        'name': attr_name,
                        'value': display_value
                    })
            
            data['variations'].append({
                'id': v.ID,
                'sku': v.get_meta('_sku') or 'N/A',
                'image_url': v._image_url_cache or 'https://placehold.co/600x600?text=Sin+Imagen',
                'label': ', '.join([f"{a['name']}: {a['value']}" for a in attr_list]) if attr_list else f"Variación #{v.ID}",
                'attributes': attr_list
            })

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/upload', methods=['POST'])
@login_required
def upload_image():
    """
    Subir imagen a la biblioteca de medios via WP REST API (binario)
    y luego asignarla al producto via WC REST API (ID).
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        from woocommerce import API
        
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se recibió ninguna imagen'}), 400
        
        file = request.files['image']
        product_id = request.form.get('product_id')
        is_variation = request.form.get('is_variation') == 'true'

        if not product_id:
            return jsonify({'success': False, 'error': 'Falta el ID del producto'}), 400

        wc_url = current_app.config['WC_API_URL'].rstrip('/')
        ck = current_app.config['WC_CONSUMER_KEY']
        cs = current_app.config['WC_CONSUMER_SECRET']

        current_app.logger.info(f"[IMAGES] Refactor: Subiendo binario a WP Media API para product_id={product_id}")

        # 1. SUBIR A LA BIBLIOTECA DE MEDIOS (WP API)
        wp_media_url = f"{wc_url}/wp-json/wp/v2/media"
        
        file_content = file.read()
        headers = {
            'Content-Type': file.content_type,
            'Content-Disposition': f'attachment; filename={file.filename}'
        }

        # Obtener credenciales (verificando tanto config como os.environ por si acaso)
        wp_user = current_app.config.get('WP_USER') or os.environ.get('WP_USER')
        wp_pass = current_app.config.get('WP_APP_PASSWORD') or os.environ.get('WP_APP_PASSWORD')

        current_app.logger.info(f"[IMAGES] Intento de subida para ID={product_id}. Detectado WP_USER: {'SÍ' if wp_user else 'NO'}")

        if wp_user and wp_pass:
            current_app.logger.info(f"[IMAGES] Usando credenciales de usuario WP: {wp_user}")
            wp_resp = requests.post(
                wp_media_url,
                data=file_content,
                headers=headers,
                auth=HTTPBasicAuth(wp_user, wp_pass),
                timeout=60
            )
        else:
            # Fallback a llaves de WC (menos probable de funcionar para Medios core)
            current_app.logger.warning("[IMAGES] No hay credenciales de WP configuradas, probando con llaves de WC")
            params = {
                'consumer_key': ck,
                'consumer_secret': cs
            }
            wp_resp = requests.post(
                wp_media_url,
                data=file_content,
                headers=headers,
                params=params,
                timeout=60
            )

        current_app.logger.info(f"[IMAGES] Respuesta WP Media API: status={wp_resp.status_code}")

        if wp_resp.status_code not in [200, 201]:
            try:
                error_data = wp_resp.json()
                error_msg = error_data.get('message', 'Error desconocido')
                error_code = error_data.get('code', 'unknown_error')
                current_app.logger.error(f"[IMAGES] Error WP Media API (status={wp_resp.status_code}): Code={error_code}, Message={error_msg}")
                
                if wp_resp.status_code == 401:
                    error_msg = f"Error de Autenticación (401): Verifique que el usuario '{wp_user}' sea el USERNAME (no el correo) y que la Application Password sea válida."
            except:
                error_msg = wp_resp.text[:200]
                current_app.logger.error(f"[IMAGES] Error WP Media (no JSON): {error_msg}")
            
            return jsonify({'success': False, 'error': error_msg}), wp_resp.status_code

        media_id = wp_resp.json().get('id')
        media_url = wp_resp.json().get('source_url')
        
        current_app.logger.info(f"[IMAGES] Imagen subida exitosamente. Media ID: {media_id}")

        # 2. ASIGNAR ID AL PRODUCTO (WC API)
        wcapi = API(
            url=wc_url,
            consumer_key=ck,
            consumer_secret=cs,
            version="wc/v3",
            timeout=60
        )

        if is_variation:
            # Para variaciones, WC requiere el parent_id
            var_obj = Product.query.get(product_id)
            if not var_obj:
                return jsonify({'success': False, 'error': 'Variación no encontrada'}), 404
            
            parent_id = var_obj.post_parent
            resp = wcapi.put(f"products/{parent_id}/variations/{product_id}", {
                "image": {"id": media_id}
            })
        else:
            # Para productos simple/padre, asignamos a la lista de imágenes (la primera es destacada)
            resp = wcapi.put(f"products/{product_id}", {
                "images": [{"id": media_id}]
            })

        if resp.status_code not in [200, 201]:
            error_data = resp.json()
            current_app.logger.error(f"[IMAGES] Error vinculando imagen: {error_data}")
            return jsonify({'success': False, 'error': f'Error vinculando imagen: {error_data.get("message")}'}), resp.status_code

        current_app.logger.info(f"[IMAGES] Proceso completado exitosamente para ID={product_id}")

        # 3. FORCE SYNC: Actualizar localmente la DB para asegurar persistencia inmediata
        # A veces la API REST tarda un poco en reflejarse en consultas SQL directas
        try:
            update_meta_query = text("""
                INSERT INTO wpyz_postmeta (post_id, meta_key, meta_value)
                VALUES (:pid, '_thumbnail_id', :mid)
                ON DUPLICATE KEY UPDATE meta_value = :mid
            """)
            db.session.execute(update_meta_query, {'pid': product_id, 'mid': media_id})
            db.session.commit()
            current_app.logger.info(f"[IMAGES] Sync local exitoso: _thumbnail_id={media_id} para post_id={product_id}")
            
            # Limpiar caché para que el cambio sea visible en todo el sitio
            from app import cache
            cache.clear()
            current_app.logger.info(f"[IMAGES] Caché del sistema limpiada")
        except Exception as sync_err:
            current_app.logger.warning(f"[IMAGES] Error en sync local (no crítico): {str(sync_err)}")

        return jsonify({
            'success': True,
            'message': 'Imagen actualizada correctamente',
            'new_url': media_url
        })

    except Exception as e:
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
