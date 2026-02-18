# app/models.py
from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_local_time

class Product(db.Model):
    """
    Modelo para productos de WooCommerce
    
    Representa la tabla wpyz_posts donde WooCommerce guarda los productos
    Los productos son un tipo especial de 'post' con post_type='product'
    """
    __tablename__ = 'wpyz_posts'
    __bind_key__ = None
    
    # Campos de la tabla wpyz_posts
    ID = db.Column(db.Integer, primary_key=True)
    post_author = db.Column(db.Integer, default=0)
    post_date = db.Column(db.DateTime)
    post_date_gmt = db.Column(db.DateTime)
    post_content = db.Column(db.Text)
    post_title = db.Column(db.String(200))
    post_excerpt = db.Column(db.Text)
    post_status = db.Column(db.String(20))
    comment_status = db.Column(db.String(20), default='open')
    ping_status = db.Column(db.String(20), default='open')
    post_password = db.Column(db.String(255), default='')
    post_name = db.Column(db.String(200))
    to_ping = db.Column(db.Text)
    pinged = db.Column(db.Text)
    post_modified = db.Column(db.DateTime)
    post_modified_gmt = db.Column(db.DateTime)
    post_content_filtered = db.Column(db.Text)
    post_parent = db.Column(db.Integer, default=0)  # ← CAMPO CLAVE PARA VARIACIONES
    guid = db.Column(db.String(255))
    menu_order = db.Column(db.Integer, default=0)
    post_type = db.Column(db.String(20))
    post_mime_type = db.Column(db.String(100))
    comment_count = db.Column(db.Integer, default=0)
    
    # Relación con metadatos
    product_meta = db.relationship('ProductMeta', backref='product', lazy='dynamic')
    
    def __init__(self, *args, **kwargs):
        super(Product, self).__init__(*args, **kwargs)
        self._meta_cache = {}

    @db.orm.reconstructor
    def init_on_load(self):
        self._meta_cache = {}
        self._image_url_cache = None

    def get_meta(self, key):
        """
        Método útil para obtener un metadato específico.
        Utiliza una caché interna para evitar consultas N+1.
        """
        if not hasattr(self, '_meta_cache'):
            self._meta_cache = {}
            
        if key in self._meta_cache:
            return self._meta_cache[key]
            
        meta = self.product_meta.filter_by(meta_key=key).first()
        value = meta.meta_value if meta else None
        
        self._meta_cache[key] = value
        return value
    
    def preload_meta(self, meta_keys=None):
        """
        Carga todos los metadatos (o los especificados) en la caché interna
        en una sola consulta.
        """
        if not hasattr(self, '_meta_cache'):
            self._meta_cache = {}
            
        query = ProductMeta.query.filter_by(post_id=self.ID)
        if meta_keys:
            query = query.filter(ProductMeta.meta_key.in_(meta_keys))
            
        metas = query.all()
        for meta in metas:
            self._meta_cache[meta.meta_key] = meta.meta_value
            
        return self._meta_cache

    @staticmethod
    def preload_metadata_for_products(products, meta_keys=None):
        """
        Carga metadatos para una lista de productos en UNA sola consulta.
        """
        if not products:
            return
            
        product_ids = [p.ID for p in products]
        query = ProductMeta.query.filter(ProductMeta.post_id.in_(product_ids))
        
        if meta_keys:
            query = query.filter(ProductMeta.meta_key.in_(meta_keys))
            
        all_meta = query.all()
        
        # Organizar por producto
        meta_map = {}
        for meta in all_meta:
            if meta.post_id not in meta_map:
                meta_map[meta.post_id] = {}
            meta_map[meta.post_id][meta.meta_key] = meta.meta_value
            
        # Asignar a la caché de cada producto
        for product in products:
            if not hasattr(product, '_meta_cache'):
                product._meta_cache = {}
            product._meta_cache.update(meta_map.get(product.ID, {}))

    def set_meta(self, key, value):
        """
        Método útil para establecer o actualizar un metadato
        """
        meta = self.product_meta.filter_by(meta_key=key).first()
        if meta:
            meta.meta_value = str(value)
        else:
            new_meta = ProductMeta(
                post_id=self.ID,
                meta_key=key,
                meta_value=str(value)
            )
            db.session.add(new_meta)
        
        # Actualizar caché si existe
        if hasattr(self, '_meta_cache'):
            self._meta_cache[key] = str(value)

    def get_image_url(self, parent_checked=False):
        """
        Obtiene la URL de la imagen destacada del producto.
        Utiliza caché interna para evitar consultas N+1.
        """
        if hasattr(self, '_image_url_cache') and self._image_url_cache:
            return self._image_url_cache

        try:
            from sqlalchemy import text
            
            # Obtener el ID de la imagen destacada (usa caché de metas)
            thumbnail_id = self.get_meta('_thumbnail_id')
            
            # Si es una variación y no tiene imagen, heredar del producto padre
            if not thumbnail_id and self.post_type == 'product_variation' and self.post_parent and not parent_checked:
                try:
                    parent = Product.query.get(self.post_parent)
                    if parent:
                        url = parent.get_image_url(parent_checked=True)
                        self._image_url_cache = url
                        return url
                except Exception:
                    return None
            
            if not thumbnail_id:
                return None
            
            # Buscar la ruta del archivo
            image_query = text("""
                SELECT meta_value
                FROM wpyz_postmeta
                WHERE post_id = :image_id
                AND meta_key = '_wp_attached_file'
                LIMIT 1
            """)
            
            result = db.session.execute(image_query, {'image_id': int(thumbnail_id)})
            row = result.fetchone()
            
            if row and row[0]:
                base_url = 'https://www.izistoreperu.com/wp-content/uploads/'
                url = base_url + row[0]
                self._image_url_cache = url
                return url
            
            return None
            
        except Exception:
            return None

    @staticmethod
    def preload_images_for_products(products):
        """
        Carga las URLs de imágenes para una lista de productos en UNA sola consulta.
        """
        if not products:
            return
            
        # 1. Identificar thumbnail_ids únicos
        thumbnail_ids = []
        for p in products:
            if not hasattr(p, '_image_url_cache'):
                p._image_url_cache = None
            
            tid = p.get_meta('_thumbnail_id')
            if tid:
                try:
                    thumbnail_ids.append(int(tid))
                except:
                    pass
        
        if not thumbnail_ids:
            return
            
        # 2. Consultar todos los _wp_attached_file en una vez
        from sqlalchemy import text
        image_query = text("""
            SELECT post_id, meta_value
            FROM wpyz_postmeta
            WHERE post_id IN :ids
            AND meta_key = '_wp_attached_file'
        """)
        
        result = db.session.execute(image_query, {'ids': tuple(set(thumbnail_ids))})
        
        # 3. Mapear IDs a URLs
        base_url = 'https://www.izistoreperu.com/wp-content/uploads/'
        image_map = {row[0]: base_url + row[1] for row in result if row[1]}
        
        # 4. Asignar a la caché de cada producto
        for p in products:
            tid = p.get_meta('_thumbnail_id')
            if tid:
                p._image_url_cache = image_map.get(int(tid))
    
    def get_variations(self):
        """
        Obtener todas las variaciones de este producto
        
        Retorna una lista de objetos Product con post_type='product_variation'
        """
        return Product.query.filter_by(
            post_type='product_variation',
            post_parent=self.ID
        ).all()
    
    def is_variable(self):
        """
        Verificar si este producto es variable (tiene variaciones)
        
        Retorna True si tiene variaciones, False si no
        """
        return Product.query.filter_by(
            post_type='product_variation',
            post_parent=self.ID
        ).count() > 0


class ProductMeta(db.Model):
    """
    Modelo para metadatos de productos
    
    Aquí es donde WooCommerce guarda toda la información extra de los productos:
    - Precios (_price, _regular_price, _sale_price)
    - Stock (_stock, _stock_status)
    - SKU (_sku)
    - Dimensiones (_weight, _length, _width, _height)
    - Y mucho más...
    """
    __tablename__ = 'wpyz_postmeta'
    
    meta_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('wpyz_posts.ID'))
    meta_key = db.Column(db.String(255))
    meta_value = db.Column(db.Text)
    
    def __repr__(self):
        """Representación en texto del objeto"""
        return f'<Meta {self.meta_key}: {self.meta_value[:50]}>'


class Term(db.Model):
    """
    Modelo para términos (categorías, etiquetas, atributos)
    
    WooCommerce usa el sistema de taxonomías de WordPress:
    - product_cat = Categorías de productos
    - product_tag = Etiquetas de productos
    - pa_* = Atributos (ejemplo: pa_color, pa_size)
    """
    __tablename__ = 'wpyz_terms'
    
    term_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    
    def __repr__(self):
        """Representación en texto del objeto"""
        return f'<Term {self.name}>'


class TermTaxonomy(db.Model):
    """
    Modelo para taxonomías de términos
    
    Define QUÉ TIPO de término es (categoría, etiqueta, atributo, etc.)
    """
    __tablename__ = 'wpyz_term_taxonomy'
    
    term_taxonomy_id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.Integer, db.ForeignKey('wpyz_terms.term_id'))
    taxonomy = db.Column(db.String(32))
    description = db.Column(db.Text)
    parent = db.Column(db.Integer, default=0)
    count = db.Column(db.Integer, default=0)
    
    # Relación con el término
    term = db.relationship('Term', backref='taxonomies')
    
    def __repr__(self):
        return f'<TermTaxonomy {self.taxonomy}>'


class TermRelationship(db.Model):
    """
    Modelo para relaciones entre productos y términos
    
    Esta tabla conecta productos con sus categorías, etiquetas y atributos
    """
    __tablename__ = 'wpyz_term_relationships'
    
    object_id = db.Column(db.Integer, db.ForeignKey('wpyz_posts.ID'), primary_key=True)
    term_taxonomy_id = db.Column(db.Integer, db.ForeignKey('wpyz_term_taxonomy.term_taxonomy_id'), primary_key=True)
    term_order = db.Column(db.Integer, default=0)
    
    # Relaciones
    product = db.relationship('Product', backref='term_relationships')
    term_taxonomy = db.relationship('TermTaxonomy', backref='relationships')
    
    def __repr__(self):
        return f'<TermRelationship Product:{self.object_id} Term:{self.term_taxonomy_id}>'
    

class StockHistory(db.Model):
    """
    Modelo para historial de cambios de stock

    Registra todos los cambios de inventario para auditoría
    """
    __tablename__ = 'wpyz_stock_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    product_title = db.Column(db.String(200))
    sku = db.Column(db.String(100))
    old_stock = db.Column(db.Integer)
    new_stock = db.Column(db.Integer)
    change_amount = db.Column(db.Integer)
    changed_by = db.Column(db.String(100), default='system')
    change_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_local_time)

    def __repr__(self):
        return f'<StockHistory Product:{self.product_id} {self.old_stock}→{self.new_stock}>'


class PriceHistory(db.Model):
    """
    Modelo para historial de cambios de precios

    Registra todos los cambios de precios para auditoría y análisis
    Prefijo woo_ para distinguir de tablas WooCommerce (wpyz_)
    """
    __tablename__ = 'woo_price_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    product_title = db.Column(db.String(200))
    sku = db.Column(db.String(100))

    # Precios anteriores
    old_regular_price = db.Column(db.Numeric(10, 2))
    old_sale_price = db.Column(db.Numeric(10, 2))
    old_price = db.Column(db.Numeric(10, 2))

    # Precios nuevos
    new_regular_price = db.Column(db.Numeric(10, 2))
    new_sale_price = db.Column(db.Numeric(10, 2))
    new_price = db.Column(db.Numeric(10, 2))

    # Auditoría
    changed_by = db.Column(db.String(100), default='system')
    change_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_local_time)

    def __repr__(self):
        return f'<PriceHistory Product:{self.product_id} {self.old_price}→{self.new_price}>'


class User(UserMixin, db.Model):
    """Modelo de usuario para autenticación"""
    __tablename__ = 'woo_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    avatar_file = db.Column(db.String(255), nullable=True)
    role = db.Column(db.Enum('master', 'admin', 'advisor', 'user'), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)
    last_login = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        """Hashear contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)

    def is_master(self):
        """Verificar si es master (superusuario)"""
        return self.role == 'master'

    def is_admin(self):
        """Verificar si es admin o master"""
        return self.role in ('master', 'admin')

    def is_advisor(self):
        """Verificar si es asesor"""
        return self.role == 'advisor'

    def is_admin_or_advisor(self):
        """Verificar si es admin, master o asesor"""
        return self.role in ('master', 'admin', 'advisor')

    def update_last_login(self):
        """Actualizar último login"""
        self.last_login = get_local_time()
        db.session.commit()

    def generate_reset_token(self):
        """Generar token de reseteo de contraseña"""
        import secrets
        from datetime import datetime, timedelta

        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Expira en 1 hora
        db.session.commit()
        return self.reset_token

    def verify_reset_token(self, token):
        """Verificar si el token es válido y no ha expirado"""
        from datetime import datetime

        if self.reset_token != token:
            return False

        if self.reset_token_expires is None:
            return False

        if datetime.utcnow() > self.reset_token_expires:
            return False

        return True

    def clear_reset_token(self):
        """Limpiar token de reseteo después de usar"""
        self.reset_token = None
        self.reset_token_expires = None
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'


class Order(db.Model):
    """
    Modelo para pedidos de WooCommerce (HPOS - High Performance Order Storage)

    Representa la tabla wpyz_wc_orders donde WooCommerce guarda los pedidos
    con el nuevo sistema de almacenamiento de alto rendimiento
    """
    __tablename__ = 'wpyz_wc_orders'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    status = db.Column(db.String(20))
    currency = db.Column(db.String(10))
    type = db.Column(db.String(20))
    tax_amount = db.Column(db.Numeric(26, 8))
    total_amount = db.Column(db.Numeric(26, 8))
    customer_id = db.Column(db.BigInteger)
    billing_email = db.Column(db.String(320))
    date_created_gmt = db.Column(db.DateTime)
    date_updated_gmt = db.Column(db.DateTime)
    parent_order_id = db.Column(db.BigInteger)
    payment_method = db.Column(db.String(100))
    payment_method_title = db.Column(db.Text)
    transaction_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(100))
    user_agent = db.Column(db.Text)
    customer_note = db.Column(db.Text)

    # Relaciones
    addresses = db.relationship('OrderAddress', backref='order', lazy='dynamic')
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    meta = db.relationship('OrderMeta', backref='order', lazy='dynamic')

    def __repr__(self):
        return f'<Order {self.id}: {self.status} - {self.total_amount}>'

    def get_meta(self, key):
        """Obtener un metadato específico del pedido"""
        meta = self.meta.filter_by(meta_key=key).first()
        return meta.meta_value if meta else None

    def set_meta(self, key, value):
        """Establecer o actualizar un metadato del pedido"""
        meta = self.meta.filter_by(meta_key=key).first()
        if meta:
            meta.meta_value = str(value)
        else:
            new_meta = OrderMeta(
                order_id=self.id,
                meta_key=key,
                meta_value=str(value)
            )
            db.session.add(new_meta)


class OrderAddress(db.Model):
    """
    Modelo para direcciones de pedidos (facturación y envío)
    """
    __tablename__ = 'wpyz_wc_order_addresses'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_wc_orders.id'))
    address_type = db.Column(db.String(20))  # 'billing' o 'shipping'
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    company = db.Column(db.Text)
    address_1 = db.Column(db.Text)
    address_2 = db.Column(db.Text)
    city = db.Column(db.Text)
    state = db.Column(db.Text)
    postcode = db.Column(db.Text)
    country = db.Column(db.Text)
    email = db.Column(db.String(320))
    phone = db.Column(db.String(100))

    def __repr__(self):
        return f'<OrderAddress {self.address_type}: {self.first_name} {self.last_name}>'


class OrderItem(db.Model):
    """
    Modelo para items (productos) de un pedido
    """
    __tablename__ = 'wpyz_woocommerce_order_items'

    order_item_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_item_name = db.Column(db.Text)
    order_item_type = db.Column(db.String(200))
    order_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_wc_orders.id'))

    # Relación con metadatos
    item_meta = db.relationship('OrderItemMeta', backref='order_item', lazy='dynamic')

    def __repr__(self):
        return f'<OrderItem {self.order_item_id}: {self.order_item_name}>'

    def get_meta(self, key):
        """Obtener un metadato específico del item"""
        meta = self.item_meta.filter_by(meta_key=key).first()
        return meta.meta_value if meta else None

    def set_meta(self, key, value):
        """Establecer o actualizar un metadato del item"""
        meta = self.item_meta.filter_by(meta_key=key).first()
        if meta:
            meta.meta_value = str(value)
        else:
            new_meta = OrderItemMeta(
                order_item_id=self.order_item_id,
                meta_key=key,
                meta_value=str(value)
            )
            db.session.add(new_meta)


class OrderItemMeta(db.Model):
    """
    Modelo para metadatos de items de pedido

    Aquí se guardan cantidades, precios, impuestos, IDs de productos, etc.
    """
    __tablename__ = 'wpyz_woocommerce_order_itemmeta'

    meta_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_item_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_woocommerce_order_items.order_item_id'))
    meta_key = db.Column(db.String(255))
    meta_value = db.Column(db.Text)

    def __repr__(self):
        return f'<OrderItemMeta {self.meta_key}: {self.meta_value[:50]}>'


class OrderMeta(db.Model):
    """
    Modelo para metadatos de pedidos
    """
    __tablename__ = 'wpyz_wc_orders_meta'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_wc_orders.id'))
    meta_key = db.Column(db.String(255))
    meta_value = db.Column(db.Text)

    def __repr__(self):
        return f'<OrderMeta {self.meta_key}: {self.meta_value[:50]}>'


class OrderExternal(db.Model):
    """
    Modelo para pedidos externos (no WooCommerce)

    Tabla: woo_orders_ext
    Propósito: Registrar pedidos de fuentes externas para tracking interno
    NO se sincronizan con WooCommerce, solo para reportes consolidados
    """
    __tablename__ = 'woo_orders_ext'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(50), nullable=False, unique=True)

    # Fechas
    date_created_gmt = db.Column(db.DateTime, nullable=False)
    date_updated_gmt = db.Column(db.DateTime, nullable=False)

    # Estado (siempre 'wc-completed' para externos)
    status = db.Column(db.String(50), nullable=False, default='wc-completed')

    # Cliente
    customer_first_name = db.Column(db.String(255), nullable=False)
    customer_last_name = db.Column(db.String(255), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    customer_dni = db.Column(db.String(20))
    customer_ruc = db.Column(db.String(20))

    # Dirección
    shipping_address_1 = db.Column(db.String(255))
    shipping_city = db.Column(db.String(100))
    shipping_state = db.Column(db.String(100))
    shipping_postcode = db.Column(db.String(20))
    shipping_country = db.Column(db.String(2), default='PE')
    shipping_reference = db.Column(db.Text)
    delivery_type = db.Column(db.String(50))

    # Envío
    shipping_method_title = db.Column(db.String(255))
    shipping_cost = db.Column(db.Numeric(10, 2), default=0.00)

    # Pago
    payment_method = db.Column(db.String(100))
    payment_method_title = db.Column(db.String(255))

    # Totales
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    tax_total = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    # Metadatos
    customer_note = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    external_source = db.Column(db.String(100))  # marketplace, tienda física, etc.
    is_cod = db.Column(db.Boolean, default=False, nullable=False)  # Pago contraentrega (Cash On Delivery)

    # Relaciones
    items = db.relationship('OrderExternalItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<OrderExternal {self.order_number}: {self.total_amount}>'


class OrderExternalItem(db.Model):
    """
    Modelo para items de pedidos externos

    Tabla: woo_orders_ext_items
    Representa los productos dentro de un pedido externo
    """
    __tablename__ = 'woo_orders_ext_items'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_ext_id = db.Column(db.BigInteger, db.ForeignKey('woo_orders_ext.id'), nullable=False)

    # Producto
    product_id = db.Column(db.BigInteger, nullable=False)
    variation_id = db.Column(db.BigInteger, default=0)
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(100))

    # Cantidades y precios
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<OrderExternalItem {self.product_name} x{self.quantity}>'


class TipoCambio(db.Model):
    """
    Modelo para tipo de cambio USD/PEN

    Tabla: woo_tipo_cambio
    Propósito: Almacenar histórico de tipo de cambio para calcular ganancias
    """
    __tablename__ = 'woo_tipo_cambio'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.Date, nullable=False)
    tasa_compra = db.Column(db.Numeric(6, 4), nullable=False)
    tasa_venta = db.Column(db.Numeric(6, 4), nullable=False)
    tasa_promedio = db.Column(db.Numeric(6, 4), nullable=False)
    actualizado_por = db.Column(db.String(100), nullable=False)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    notas = db.Column(db.Text)

    def __repr__(self):
        return f'<TipoCambio {self.fecha} - {self.tasa_promedio}>'

    @staticmethod
    def get_tasa_actual():
        """Obtener tasa de cambio actual (más reciente activa)"""
        return TipoCambio.query.filter_by(activo=True).order_by(TipoCambio.fecha.desc()).first()

    @staticmethod
    def get_tasa_por_fecha(fecha):
        """Obtener tasa de cambio para una fecha específica"""
        # Buscar tasa exacta de esa fecha
        tasa = TipoCambio.query.filter(
            TipoCambio.fecha == fecha,
            TipoCambio.activo == True
        ).first()

        if tasa:
            return tasa

        # Si no existe, buscar la más cercana anterior
        tasa = TipoCambio.query.filter(
            TipoCambio.fecha <= fecha,
            TipoCambio.activo == True
        ).order_by(TipoCambio.fecha.desc()).first()

        return tasa


class ExpenseDetail(db.Model):
    """
    Modelo para Gastos Detallados
    Solo accesible para usuarios con rol Master
    """
    __tablename__ = 'expense_details'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)              # Fecha del gasto
    tipo_gasto = db.Column(db.String(100), nullable=False)  # Tipo de gasto
    categoria = db.Column(db.String(100), nullable=False)   # Categoría
    descripcion = db.Column(db.Text, nullable=False)        # Descripción
    monto = db.Column(db.Numeric(10, 2), nullable=False)    # Monto

    # Auditoría
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=get_local_time)

    def __repr__(self):
        return f'<ExpenseDetail {self.id}: {self.tipo_gasto} - {self.categoria}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'fecha': self.fecha.strftime('%Y-%m-%d') if self.fecha else None,
            'tipo_gasto': self.tipo_gasto,
            'categoria': self.categoria,
            'descripcion': self.descripcion,
            'monto': float(self.monto) if self.monto else 0,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class ExpenseType(db.Model):
    """
    Modelo para Tipos de Gasto
    Catálogo maestro de tipos (Operativo, Marketing, etc.)
    """
    __tablename__ = 'woo_expense_types'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)

    # Auditoría
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=get_local_time)

    # Relación con categorías
    categories = db.relationship('ExpenseCategory', backref='expense_type', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ExpenseType {self.id}: {self.nombre}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'activo': self.activo,
            'orden': self.orden,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class ExpenseCategory(db.Model):
    """
    Modelo para Categorías de Gasto
    Cada categoría pertenece a un Tipo de Gasto
    """
    __tablename__ = 'woo_expense_categories'

    id = db.Column(db.Integer, primary_key=True)
    expense_type_id = db.Column(db.Integer, db.ForeignKey('woo_expense_types.id', ondelete='CASCADE'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)

    # Auditoría
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=get_local_time)

    # Relación con descripciones
    descriptions = db.relationship('ExpenseDescription', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ExpenseCategory {self.id}: {self.nombre}>'

    def to_dict(self):
        return {
            'id': self.id,
            'expense_type_id': self.expense_type_id,
            'expense_type_nombre': self.expense_type.nombre if self.expense_type else None,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'activo': self.activo,
            'orden': self.orden,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class ExpenseDescription(db.Model):
    """
    Modelo para Descripciones Predefinidas
    Sugerencias de descripciones para agilizar entrada de datos
    """
    __tablename__ = 'woo_expense_descriptions'

    id = db.Column(db.Integer, primary_key=True)
    expense_category_id = db.Column(db.Integer, db.ForeignKey('woo_expense_categories.id', ondelete='SET NULL'))
    descripcion = db.Column(db.Text, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    uso_count = db.Column(db.Integer, default=0)

    # Auditoría
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_by = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime, onupdate=get_local_time)

    def __repr__(self):
        return f'<ExpenseDescription {self.id}: {self.descripcion[:50]}>'

    def to_dict(self):
        return {
            'id': self.id,
            'expense_category_id': self.expense_category_id,
            'descripcion': self.descripcion,
            'activo': self.activo,
            'uso_count': self.uso_count,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


# =====================================================
# MODELOS DE COMPRAS / REABASTECIMIENTO
# =====================================================

class PurchaseOrder(db.Model):
    """
    Modelo para órdenes de compra / reabastecimiento

    Gestiona las órdenes de compra para reabastecer inventario
    de productos que han llegado a stock 0
    """
    __tablename__ = 'woo_purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_name = db.Column(db.String(200))
    status = db.Column(db.String(20), nullable=False, default='pending')
    order_date = db.Column(db.DateTime, nullable=False)
    expected_delivery_date = db.Column(db.Date)
    actual_delivery_date = db.Column(db.Date)
    total_cost_usd = db.Column(db.Numeric(10, 2))
    exchange_rate = db.Column(db.Numeric(6, 4))
    total_cost_pen = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)

    # Relaciones
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy='dynamic', cascade='all, delete-orphan')
    history = db.relationship('PurchaseOrderHistory', backref='purchase_order', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PurchaseOrder {self.order_number}: {self.status}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        # Intentar obtener el conteo de items de manera eficiente
        try:
            # Si items ya está cargado como lista (joinedload), usar len()
            items_count = len(list(self.items)) if hasattr(self.items, '__iter__') else self.items.count()
        except:
            items_count = 0

        return {
            'id': self.id,
            'order_number': self.order_number,
            'supplier_name': self.supplier_name,
            'status': self.status,
            'order_date': self.order_date.strftime('%Y-%m-%d %H:%M:%S') if self.order_date else None,
            'expected_delivery_date': self.expected_delivery_date.strftime('%Y-%m-%d') if self.expected_delivery_date else None,
            'actual_delivery_date': self.actual_delivery_date.strftime('%Y-%m-%d') if self.actual_delivery_date else None,
            'total_cost_usd': float(self.total_cost_usd) if self.total_cost_usd else 0,
            'exchange_rate': float(self.exchange_rate) if self.exchange_rate else 0,
            'total_cost_pen': float(self.total_cost_pen) if self.total_cost_pen else 0,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'items_count': items_count
        }


class PurchaseOrderItem(db.Model):
    """
    Modelo para items/productos en una orden de compra

    Cada fila representa un producto específico dentro de una orden
    """
    __tablename__ = 'woo_purchase_order_items'

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('woo_purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_title = db.Column(db.String(200))
    sku = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost_usd = db.Column(db.Numeric(10, 2))
    total_cost_usd = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<PurchaseOrderItem {self.sku}: {self.quantity} units>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'product_id': self.product_id,
            'product_title': self.product_title,
            'sku': self.sku,
            'quantity': self.quantity,
            'unit_cost_usd': float(self.unit_cost_usd) if self.unit_cost_usd else 0,
            'total_cost_usd': float(self.total_cost_usd) if self.total_cost_usd else 0,
            'notes': self.notes
        }


class PurchaseOrderHistory(db.Model):
    """
    Modelo para historial de cambios de estado de órdenes de compra

    Auditoría de todos los cambios de estado de las órdenes
    """
    __tablename__ = 'woo_purchase_order_history'

    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('woo_purchase_orders.id'), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    changed_by = db.Column(db.String(100))
    change_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_local_time)

    def __repr__(self):
        return f'<PurchaseOrderHistory Order:{self.purchase_order_id} {self.old_status}→{self.new_status}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'purchase_order_id': self.purchase_order_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'change_reason': self.change_reason,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


# ============================================
# MODELOS PARA MÓDULO DE DESPACHO KANBAN
# ============================================

class DispatchHistory(db.Model):
    """
    Modelo para historial de cambios de método de envío

    Tabla: woo_dispatch_history
    Propósito: Registrar todos los movimientos de pedidos en el tablero Kanban
    con trazabilidad completa (usuario, timestamp, método anterior/nuevo)
    """
    __tablename__ = 'woo_dispatch_history'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_wc_orders.id'), nullable=False)
    order_number = db.Column(db.String(50), nullable=False)

    # Cambio de método de envío
    previous_shipping_method = db.Column(db.String(100))  # Puede ser NULL si es el primer registro
    new_shipping_method = db.Column(db.String(100), nullable=False)

    # Trazabilidad
    changed_by = db.Column(db.String(100), nullable=False)  # Username del usuario
    changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Notas opcionales
    dispatch_note = db.Column(db.Text)

    # Relación con Order
    order = db.relationship('Order', backref=db.backref('dispatch_history', lazy='dynamic'))

    def __repr__(self):
        return f'<DispatchHistory Order:{self.order_number} {self.previous_shipping_method}→{self.new_shipping_method}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'previous_shipping_method': self.previous_shipping_method,
            'new_shipping_method': self.new_shipping_method,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.strftime('%Y-%m-%d %H:%M:%S') if self.changed_at else None,
            'dispatch_note': self.dispatch_note
        }


class DispatchPriority(db.Model):
    """
    Modelo para gestión de prioridades de pedidos

    Tabla: woo_dispatch_priorities
    Propósito: Marcar pedidos como prioritarios/urgentes en el tablero de despacho
    con información sobre quién lo marcó y por qué
    """
    __tablename__ = 'woo_dispatch_priorities'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('wpyz_wc_orders.id'), nullable=False, unique=True)
    order_number = db.Column(db.String(50), nullable=False)

    # Configuración de prioridad
    is_priority = db.Column(db.Boolean, default=False, nullable=False)
    priority_level = db.Column(db.Enum('normal', 'high', 'urgent', name='priority_level_enum'), default='normal')

    # Configuración de atención/empaquetado (Ready/Packed)
    is_atendido = db.Column(db.Boolean, default=False, nullable=False)
    atendido_by = db.Column(db.String(100))
    atendido_at = db.Column(db.DateTime)

    # Metadata
    marked_by = db.Column(db.String(100))
    marked_at = db.Column(db.DateTime)
    priority_note = db.Column(db.Text)

    # Relación con Order
    order = db.relationship('Order', backref=db.backref('dispatch_priority', uselist=False))

    def __repr__(self):
        return f'<DispatchPriority Order:{self.order_number} Level:{self.priority_level}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'is_priority': self.is_priority,
            'priority_level': self.priority_level,
            'is_atendido': self.is_atendido,
            'atendido_by': self.atendido_by,
            'atendido_at': self.atendido_at.strftime('%Y-%m-%d %H:%M:%S') if self.atendido_at else None,
            'marked_by': self.marked_by,
            'marked_at': self.marked_at.strftime('%Y-%m-%d %H:%M:%S') if self.marked_at else None,
            'priority_note': self.priority_note
        }


# =====================================================================
# MODELO PARA REGISTRO DE ENVÍOS CHAMO
# =====================================================================

class ChamoShipment(db.Model):
    """
    Registro de envíos realizados por CHAMO courier

    Tabla: woo_chamo_shipments
    Propósito: Registrar todos los envíos realizados por CHAMO para control y facturación
    Solo se registran envíos cuando el tracking es enviado desde la columna CHAMO
    """
    __tablename__ = 'woo_chamo_shipments'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, nullable=False)
    order_number = db.Column(db.String(50), nullable=False)

    # Shipment details
    tracking_number = db.Column(db.Text, nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    shipping_provider = db.Column(db.String(100), default='Motorizado Izi')

    # Customer info
    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(50))
    customer_email = db.Column(db.String(320))
    customer_address = db.Column(db.Text)
    customer_district = db.Column(db.String(100))

    # Financial
    order_total = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    cod_amount = db.Column(db.Numeric(10, 2), default=0)
    is_cod = db.Column(db.Boolean, default=False)

    # Metadata
    sent_by = db.Column(db.String(100), nullable=False)
    sent_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sent_via = db.Column(db.Enum('individual', 'bulk', name='sent_via_enum'), default='individual')
    column_at_send = db.Column(db.String(100), default='Motorizado (CHAMO)')
    notes = db.Column(db.Text)

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'tracking_number': self.tracking_number,
            'delivery_date': self.delivery_date.strftime('%Y-%m-%d') if self.delivery_date else None,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'order_total': float(self.order_total) if self.order_total else 0,
            'cod_amount': float(self.cod_amount) if self.cod_amount else 0,
            'is_cod': self.is_cod,
            'sent_by': self.sent_by,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S') if self.sent_at else None,
            'sent_via': self.sent_via
        }

    def __repr__(self):
        return f'<ChamoShipment Order:{self.order_number} Delivery:{self.delivery_date}>'


# =====================================================================
# MODELOS PARA COTIZACIONES (QUOTATIONS)
# =====================================================================

class Quotation(db.Model):
    """
    Modelo para cotizaciones

    Tabla: woo_quotations
    Propósito: Gestionar cotizaciones de productos para clientes con posibilidad
    de conversión a órdenes WooCommerce
    """
    __tablename__ = 'woo_quotations'

    id = db.Column(db.Integer, primary_key=True)

    # Identificación
    quote_number = db.Column(db.String(50), unique=True, nullable=False)
    version = db.Column(db.Integer, default=1)

    # Información del Cliente
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(50))
    customer_dni = db.Column(db.String(20))
    customer_ruc = db.Column(db.String(20))
    customer_address = db.Column(db.Text)
    customer_city = db.Column(db.String(100))
    customer_state = db.Column(db.String(100))

    # Estado y Fechas
    status = db.Column(db.String(20), nullable=False, default='draft')
    quote_date = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)

    # Precios
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount_type = db.Column(db.String(20), default='percentage')
    discount_value = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=18.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Términos
    payment_terms = db.Column(db.Text)
    delivery_time = db.Column(db.String(100))
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)

    # Auditoría
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)
    sent_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    converted_order_id = db.Column(db.BigInteger)

    # Relaciones
    items = db.relationship('QuotationItem', backref='quotation', lazy='dynamic', cascade='all, delete-orphan')
    history = db.relationship('QuotationHistory', backref='quotation', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quotation {self.quote_number} - {self.customer_name}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'quote_number': self.quote_number,
            'version': self.version,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_dni': self.customer_dni,
            'customer_ruc': self.customer_ruc,
            'customer_address': self.customer_address,
            'customer_city': self.customer_city,
            'customer_state': self.customer_state,
            'status': self.status,
            'quote_date': self.quote_date.strftime('%Y-%m-%d %H:%M:%S') if self.quote_date else None,
            'valid_until': self.valid_until.strftime('%Y-%m-%d') if self.valid_until else None,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value) if self.discount_value else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'shipping_cost': float(self.shipping_cost) if self.shipping_cost else 0,
            'total': float(self.total) if self.total else 0,
            'payment_terms': self.payment_terms,
            'delivery_time': self.delivery_time,
            'notes': self.notes,
            'terms_conditions': self.terms_conditions,
            'created_by': self.created_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S') if self.sent_at else None,
            'accepted_at': self.accepted_at.strftime('%Y-%m-%d %H:%M:%S') if self.accepted_at else None,
            'converted_order_id': self.converted_order_id,
            'is_expired': self.is_expired(),
            'items_count': self.items.count()
        }

    def is_expired(self):
        """Verificar si la cotización ha expirado"""
        if self.status in ['accepted', 'rejected', 'converted']:
            return False
        from datetime import datetime
        return datetime.now().date() > self.valid_until

    def calculate_totals(self):
        """Recalcular todos los totales desde los items"""
        from decimal import Decimal

        # Sumar subtotales de items
        self.subtotal = sum(Decimal(str(item.subtotal)) for item in self.items)

        # Aplicar descuento
        if self.discount_type == 'percentage':
            self.discount_amount = self.subtotal * (Decimal(str(self.discount_value)) / Decimal('100'))
        else:
            self.discount_amount = Decimal(str(self.discount_value))

        # Calcular base imponible
        subtotal_after_discount = self.subtotal - self.discount_amount

        # Calcular IGV
        self.tax_amount = subtotal_after_discount * (Decimal(str(self.tax_rate)) / Decimal('100'))

        # Calcular total
        self.total = subtotal_after_discount + self.tax_amount + Decimal(str(self.shipping_cost))


class QuotationItem(db.Model):
    """
    Modelo para items de cotización

    Tabla: woo_quotation_items
    Propósito: Almacenar los productos incluidos en cada cotización
    """
    __tablename__ = 'woo_quotation_items'

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('woo_quotations.id'), nullable=False)

    # Referencia al Producto
    product_id = db.Column(db.BigInteger, nullable=False)
    variation_id = db.Column(db.BigInteger, default=0)
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(100))

    # Precios (personalizables por cotización)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2))
    discount_percentage = db.Column(db.Numeric(5, 2), default=0)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    # Metadata
    notes = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<QuotationItem {self.product_name} x{self.quantity}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'quotation_id': self.quotation_id,
            'product_id': self.product_id,
            'variation_id': self.variation_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'original_price': float(self.original_price) if self.original_price else 0,
            'discount_percentage': float(self.discount_percentage) if self.discount_percentage else 0,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax': float(self.tax) if self.tax else 0,
            'total': float(self.total) if self.total else 0,
            'notes': self.notes,
            'display_order': self.display_order
        }


class QuotationHistory(db.Model):
    """
    Modelo para historial de cambios en cotizaciones

    Tabla: woo_quotation_history
    Propósito: Auditoría de todos los cambios de estado en las cotizaciones
    """
    __tablename__ = 'woo_quotation_history'

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('woo_quotations.id'), nullable=False)

    # Rastreo de Cambios
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.String(100), nullable=False)
    change_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_local_time)

    def __repr__(self):
        return f'<QuotationHistory {self.old_status} → {self.new_status}>'

    def to_dict(self):
        """Convertir a diccionario para JSON"""
        return {
            'id': self.id,
            'quotation_id': self.quotation_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'change_reason': self.change_reason,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }