# app/__init__.py
from flask import Flask, redirect, render_template, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import config
import os

# Inicializar extensiones
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    
    if config_name is None:
        config_name = os.environ.get('ENVIRONMENT', 'testing')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    
    # ========================================
    # MANEJAR RECONEXIÓN DE BD
    # ========================================
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Cerrar sesión de BD al final de cada request"""
        db.session.remove()
    
    # Configurar Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    # User loader callback
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            # Si falla la conexión, invalidar sesión
            import logging
            logging.error(f"Error al cargar usuario {user_id}: {str(e)}")
            return None
    
    # ========================================
    # PROTECCIÓN GLOBAL
    # ========================================
    @app.before_request
    def require_login():
        """Middleware que requiere autenticación"""
        
        public_endpoints = [
            'auth.login',
            'auth.register',
            'static'
        ]
        
        if request.endpoint and request.endpoint not in public_endpoints:
            try:
                if not current_user.is_authenticated:
                    return redirect(url_for('auth.login', next=request.url))
            except Exception as e:
                # Si hay error de BD, redirigir a login
                import logging
                logging.error(f"Error en require_login: {str(e)}")
                return redirect(url_for('auth.login'))
    
    # Registrar blueprints
    from app.routes import products, stock, prices, images, categories, auth
    
    app.register_blueprint(products.bp)
    app.register_blueprint(stock.bp)
    app.register_blueprint(prices.bp)
    app.register_blueprint(images.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(auth.bp)
    
    # Contexto global para templates
    @app.context_processor
    def inject_config():
        return {
            'environment': app.config['ENVIRONMENT'],
            'is_production': app.config['ENVIRONMENT'] == 'production',
            'db_prefix': app.config['DB_PREFIX'],
            'current_user': current_user
        }
    
    # Ruta principal
    @app.route('/')
    def index():
        """Dashboard principal"""
        return render_template('dashboard.html')
    
    return app