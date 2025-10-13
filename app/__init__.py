from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config
import os

# Inicializar extensiones
db = SQLAlchemy()

def create_app(config_name=None):
    """Factory para crear la aplicación Flask"""
    
    # Si no se especifica, usar variable de entorno o default
    if config_name is None:
        config_name = os.environ.get('ENVIRONMENT', 'testing')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Registrar blueprints
    from app.routes import products, stock, prices, images, categories
    
    app.register_blueprint(products.bp)
    app.register_blueprint(stock.bp)
    app.register_blueprint(prices.bp)
    app.register_blueprint(images.bp)
    app.register_blueprint(categories.bp)
    
    # Contexto global para templates
    @app.context_processor
    def inject_config():
        return {
            'environment': app.config['ENVIRONMENT'],
            'is_production': app.config['ENVIRONMENT'] == 'production',
            'db_prefix': app.config['DB_PREFIX']
        }
    
    # Ruta principal
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('dashboard.html')
    
    return app