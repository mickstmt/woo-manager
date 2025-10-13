import os
from dotenv import load_dotenv
from urllib.parse import quote_plus  # ← Agregar esta línea

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-this'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DB_PREFIX = os.environ.get('DB_PREFIX', 'wpyz_')
    
    # Configuración de sesión
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600

class DevelopmentConfig(Config):
    """Configuración para desarrollo local"""
    DEBUG = True
    ENVIRONMENT = 'development'
    
    # Obtener valores del .env
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME_TESTING')
    
    # Codificar la contraseña para que funcione en la URL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{db_user}:{quote_plus(db_password)}@"
        f"{db_host}/{db_name}"
    )

class TestingConfig(Config):
    """Configuración para base de datos de pruebas"""
    DEBUG = True
    ENVIRONMENT = 'testing'
    
    # Obtener valores del .env
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME_TESTING')
    
    # Codificar la contraseña para que funcione en la URL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{db_user}:{quote_plus(db_password)}@"
        f"{db_host}/{db_name}"
    )

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    ENVIRONMENT = 'production'
    SESSION_COOKIE_SECURE = True
    
    # Obtener valores del .env
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME_PRODUCTION')
    
    # Codificar la contraseña para que funcione en la URL
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{db_user}:{quote_plus(db_password)}@"
        f"{db_host}/{db_name}"
    )

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': TestingConfig
}