from app import create_app
import os

# Crear la aplicación
app = create_app()

if __name__ == '__main__':
    # Obtener configuración del .env
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"\n{'='*50}")
    print(f"🚀 Iniciando WooCommerce Manager")
    print(f"{'='*50}")
    print(f"🌍 Ambiente: {app.config['ENVIRONMENT'].upper()}")
    print(f"🗄️  Base de datos: {app.config['SQLALCHEMY_DATABASE_URI'].split('/')[-1]}")
    print(f"🔧 Debug: {debug}")
    print(f"{'='*50}\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug
    )