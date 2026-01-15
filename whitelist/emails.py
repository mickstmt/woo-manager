# whitelist/emails.py
"""
Lista de correos autorizados para registro en WooCommerce Manager

IMPORTANTE: Solo los correos listados aquí pueden crear cuentas.
Para agregar un nuevo empleado, simplemente añade su correo a la lista.
"""

AUTHORIZED_EMAILS = [
    # Administradores
    'admin@izistoreperu.com',
    'mickstmt@izistoreperu.com',
    'franksmaza@izistoreperu.com',
    'jleon@izistoreperu.com'
    
    # Diseno y redes
    'jsanmartin@izistoreperu.com',

    # Equipo de almacén
    'almacen@izistoreperu.com',
    'inventario@izistoreperu.com',
    
    # Equipo de ventas
    'aherrera@izistoreperu.com',
    'dduire@izistoreperu.com',
    'ventasizistoreperu@izistoreperu.com',

    # Soporte
    'msanmartin@izistoreperu.com'
    
    # Otros empleados (agregar según necesites)
    # 'nombre.apellido@izistoreperu.com',
]


def is_email_authorized(email):
    """
    Verifica si un email está autorizado para registro
    
    Args:
        email (str): Email a verificar
    
    Returns:
        bool: True si está autorizado, False si no
    """
    if not email:
        return False
    
    email_lower = email.lower().strip()
    authorized_lower = [e.lower().strip() for e in AUTHORIZED_EMAILS]
    
    return email_lower in authorized_lower


def get_authorized_count():
    """Retorna el número de emails autorizados"""
    return len(AUTHORIZED_EMAILS)


def get_authorized_list():
    """Retorna la lista completa de correos autorizados"""
    return AUTHORIZED_EMAILS.copy()