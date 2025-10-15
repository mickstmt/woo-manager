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
    
    # Configurar Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'info'
    
    # User loader callback
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # ========================================
    # PROTECCIÓN GLOBAL - Requiere login en TODAS las rutas
    # ========================================
    @app.before_request
    def require_login():
        """Middleware que requiere autenticación en todas las rutas excepto las públicas"""
        
        # Lista de rutas públicas (que NO requieren login)
        public_endpoints = [
            'auth.login',
            'auth.register',
            'static'
        ]
        
        # Verificar si la ruta actual es pública
        if request.endpoint and request.endpoint not in public_endpoints:
            if not current_user.is_authenticated:
                # Guardar la URL a la que intentaba acceder
                return redirect(url_for('auth.login', next=request.url))
    
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
    
    # Ruta principal - Mostrar dashboard
    @app.route('/')
    def index():
        """Dashboard principal"""
        return render_template('dashboard.html')
    
    return app