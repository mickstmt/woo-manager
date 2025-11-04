# config.py
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import datetime
from zoneinfo import ZoneInfo

# Cargar variables de entorno
load_dotenv()

def get_local_time():
    """
    Obtener la hora actual en la zona horaria de Perú (America/Lima, UTC-5)

    Retorna:
        datetime: Hora actual con timezone America/Lima
    """
    return datetime.now(ZoneInfo('America/Lima'))

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-this'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DB_PREFIX = os.environ.get('DB_PREFIX', 'wpyz_')

    # Configuración de zona horaria
    TIMEZONE = 'America/Lima'  # UTC-5 (Perú)

    # Configuración de sesión
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600
    
    # ========================================
    # CONFIGURACIÓN DEL POOL DE CONEXIONES
    # ========================================
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,              # Número de conexiones en el pool
        'pool_recycle': 3600,         # Reciclar conexiones cada hora
        'pool_pre_ping': True,        # Verificar conexión antes de usar
        'max_overflow': 20,           # Conexiones adicionales si se necesitan
        'pool_timeout': 30,           # Timeout para obtener conexión del pool
        'connect_args': {
            'connect_timeout': 10,    # Timeout de conexión inicial
            'read_timeout': 30,       # Timeout de lectura
            'write_timeout': 30       # Timeout de escritura
        }
    }

class DevelopmentConfig(Config):
    """Configuración para desarrollo local"""
    DEBUG = True
    ENVIRONMENT = 'development'
    
    # Obtener valores del .env con valores por defecto
    db_user = os.environ.get('DB_USER') or 'root'
    db_password = os.environ.get('DB_PASSWORD') or ''
    db_host = os.environ.get('DB_HOST') or 'localhost'
    db_name = os.environ.get('DB_NAME_TESTING') or 'woocommerce_test'
    
    # Codificar la contraseña solo si existe
    encoded_password = quote_plus(db_password) if db_password else ''
    
    # Construir URL de conexión
    if encoded_password:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"

class TestingConfig(Config):
    """Configuración para base de datos de pruebas"""
    DEBUG = True
    ENVIRONMENT = 'testing'
    
    # Obtener valores del .env con valores por defecto
    db_user = os.environ.get('DB_USER') or 'root'
    db_password = os.environ.get('DB_PASSWORD') or ''
    db_host = os.environ.get('DB_HOST') or 'localhost'
    db_name = os.environ.get('DB_NAME_TESTING') or 'woocommerce_test'
    
    # Codificar la contraseña solo si existe
    encoded_password = quote_plus(db_password) if db_password else ''
    
    # Construir URL de conexión
    if encoded_password:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}@{db_host}/{db_name}"

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    ENVIRONMENT = 'production'
    SESSION_COOKIE_SECURE = True
    
    # Obtener valores del .env (obligatorios en producción)
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME_PRODUCTION')
    
    # Validar que las variables críticas existan
    if not all([db_user, db_password, db_host, db_name]):
        missing = []
        if not db_user: missing.append('DB_USER')
        if not db_password: missing.append('DB_PASSWORD')
        if not db_host: missing.append('DB_HOST')
        if not db_name: missing.append('DB_NAME_PRODUCTION')
        raise ValueError(f"Faltan variables de entorno requeridas: {', '.join(missing)}")
    
    # Codificar la contraseña
    encoded_password = quote_plus(db_password)
    
    # Construir URL de conexión
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}"
    
    # En producción, pool más conservador para evitar sobrecargar Hostinger
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,               # Menos conexiones simultáneas
        'pool_recycle': 1800,         # Reciclar cada 30 minutos
        'pool_pre_ping': True,        # Verificar antes de usar (CRÍTICO)
        'max_overflow': 10,
        'pool_timeout': 30,
        'connect_args': {
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
    }

# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': TestingConfig
}