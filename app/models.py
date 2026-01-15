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
    
    def __repr__(self):
        """Representación en texto del objeto"""
        return f'<Product {self.ID}: {self.post_title}>'
    
    def get_meta(self, key):
        """
        Método útil para obtener un metadato específico
        
        Ejemplo de uso:
            product = Product.query.first()
            sku = product.get_meta('_sku')
            price = product.get_meta('_price')
        """
        meta = self.product_meta.filter_by(meta_key=key).first()
        return meta.meta_value if meta else None
    
    def set_meta(self, key, value):
        """
        Método útil para establecer o actualizar un metadato
        
        Ejemplo de uso:
            product.set_meta('_price', '99.99')
            db.session.commit()
        """
        meta = self.product_meta.filter_by(meta_key=key).first()
        if meta:
            # Si ya existe, actualizar
            meta.meta_value = str(value)
        else:
            # Si no existe, crear nuevo
            new_meta = ProductMeta(
                post_id=self.ID,
                meta_key=key,
                meta_value=str(value)
            )
            db.session.add(new_meta)
    
    def get_image_url(self, parent_checked=False):
        """
        Obtiene la URL de la imagen destacada del producto
        
        WooCommerce guarda el ID de la imagen en _thumbnail_id
        y luego busca la URL en los postmeta del attachment
        
        Para variaciones: si no tiene imagen propia, hereda la del producto padre
        
        Parámetros:
            parent_checked (bool): Interno, previene recursión infinita
        
        Retorna:
            str: URL de la imagen o None si no existe
        
        Ejemplo de uso:
            product = Product.query.first()
            image_url = product.get_image_url()
        """
        try:
            from sqlalchemy import text
            import os
            
            # Obtener el ID de la imagen destacada
            thumbnail_id = self.get_meta('_thumbnail_id')
            
            # Si es una variación y no tiene imagen, heredar del producto padre
            if not thumbnail_id and self.post_type == 'product_variation' and self.post_parent and not parent_checked:
                try:
                    parent = Product.query.get(self.post_parent)
                    if parent:
                        return parent.get_image_url(parent_checked=True)
                except Exception as e:
                    # Solo log de errores importantes
                    import logging
                    logging.error(f"Error al obtener imagen del padre para variación {self.ID}: {str(e)}")
                    return None
            
            if not thumbnail_id:
                return None
            
            # Buscar la ruta del archivo en los metadatos del attachment
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
                # Construir URL completa de la imagen
                base_url = 'https://www.izistoreperu.com/wp-content/uploads/'
                image_path = row[0]
                full_url = base_url + image_path
                
                return full_url
            
            return None
            
        except Exception as e:
            # Solo log de errores críticos
            import logging
            logging.error(f"Error al obtener imagen para producto {self.ID}: {str(e)}")
            return None
    
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
            'marked_by': self.marked_by,
            'marked_at': self.marked_at.strftime('%Y-%m-%d %H:%M:%S') if self.marked_at else None,
            'priority_note': self.priority_note
        }