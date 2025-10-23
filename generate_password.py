#!/usr/bin/env python3
"""
Script para generar hash de contraseña
Uso: python generate_password.py
"""
from werkzeug.security import generate_password_hash
import sys

def main():
    print("=" * 50)
    print("Generador de Hash de Contraseña")
    print("=" * 50)
    print()
    
    # Solicitar contraseña
    password = input("Ingresa la contraseña: ")
    
    if len(password) < 6:
        print("\n❌ Error: La contraseña debe tener al menos 6 caracteres")
        return
    
    # Confirmar contraseña
    password_confirm = input("Confirma la contraseña: ")
    
    if password != password_confirm:
        print("\n❌ Error: Las contraseñas no coinciden")
        return
    
    # Generar hash
    password_hash = generate_password_hash(password)
    
    print("\n" + "=" * 50)
    print("✅ Hash generado exitosamente")
    print("=" * 50)
    print(f"\nContraseña: {password}")
    print(f"\nHash:\n{password_hash}")
    print("\n" + "=" * 50)
    print("Copia el hash de arriba y úsalo en tu script SQL")
    print("=" * 50)
    
    # Generar SQL de ejemplo
    print("\n📝 Ejemplo de SQL:")
    print(f"""
INSERT INTO `woo_users` (`username`, `email`, `password_hash`, `full_name`, `role`, `is_active`)
VALUES ('admin', 'admin@izistoreperu.com', '{password_hash}', 'Administrador', 'admin', 1);
""")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)