# whitelist/__init__.py
# Este archivo hace que config sea un paquete de Python


"""
Módulo de lista blanca de correos autorizados
"""
from .emails import (
    AUTHORIZED_EMAILS,
    is_email_authorized,
    get_authorized_count,
    get_authorized_list
)

__all__ = [
    'AUTHORIZED_EMAILS',
    'is_email_authorized',
    'get_authorized_count',
    'get_authorized_list'
]

