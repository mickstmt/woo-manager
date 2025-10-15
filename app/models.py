# app/models.py
from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<StockHistory Product:{self.product_id} {self.old_stock}→{self.new_stock}>'
    

class User(UserMixin, db.Model):
    """Modelo de usuario para autenticación"""
    __tablename__ = 'woo_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.Enum('admin', 'user'), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hashear contraseña"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Verificar si es admin"""
        return self.role == 'admin'
    
    def update_last_login(self):
        """Actualizar último login"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'