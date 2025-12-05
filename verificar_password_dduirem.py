#!/usr/bin/env python3
"""
Script para verificar y resetear la contraseña del usuario dduirem

Este script:
1. Verifica el hash actual en la base de datos
2. Intenta verificar si la contraseña 'dduirem123' funciona
3. Si no funciona, resetea la contraseña a 'dduirem123'
4. Muestra información del usuario
"""

from app import create_app, db
from app.models import User
from werkzeug.security import check_password_hash

app = create_app()

with app.app_context():
    # Buscar usuario
    user = User.query.filter_by(username='dduirem').first()

    if not user:
        print("❌ ERROR: Usuario 'dduirem' no encontrado en la base de datos")
        exit(1)

    print("=" * 60)
    print("INFORMACIÓN DEL USUARIO")
    print("=" * 60)
    print(f"ID: {user.id}")
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Full Name: {user.full_name}")
    print(f"Role: {user.role}")
    print(f"Is Active: {user.is_active}")
    print(f"Created At: {user.created_at}")
    print(f"Last Login: {user.last_login}")
    print(f"Updated At: {user.updated_at}")
    print(f"Password Hash (primeros 50 caracteres): {user.password_hash[:50]}...")
    print()

    print("=" * 60)
    print("VERIFICACIÓN DE CONTRASEÑA")
    print("=" * 60)

    # Verificar contraseña actual
    password_to_check = 'dduirem123'
    is_correct = user.check_password(password_to_check)

    print(f"Contraseña a verificar: '{password_to_check}'")
    print(f"¿Es correcta?: {is_correct}")
    print()

    if is_correct:
        print("✅ La contraseña 'dduirem123' ES VÁLIDA")
        print("   El usuario debería poder iniciar sesión con esta contraseña")
    else:
        print("❌ La contraseña 'dduirem123' NO es válida")
        print("   Esto confirma que algo cambió la contraseña")
        print()

        # Preguntar si quiere resetear
        respuesta = input("¿Deseas resetear la contraseña a 'dduirem123'? (s/n): ")

        if respuesta.lower() == 's':
            user.set_password('dduirem123')
            db.session.commit()

            # Verificar que funcionó
            is_correct_now = user.check_password('dduirem123')

            if is_correct_now:
                print("✅ CONTRASEÑA RESETEADA EXITOSAMENTE")
                print(f"   Nuevo hash: {user.password_hash[:50]}...")
                print()
                print("   El usuario ahora puede iniciar sesión con: dduirem123")
            else:
                print("❌ ERROR: Hubo un problema al resetear la contraseña")
        else:
            print("Operación cancelada")

    print()
    print("=" * 60)
    print("ANÁLISIS DE SEGURIDAD")
    print("=" * 60)
    print("Posibles causas si la contraseña cambió sola:")
    print("1. Otro administrador cambió la contraseña desde el panel de admin")
    print("2. El usuario usó 'Olvidé mi contraseña' y recibió un email")
    print("3. Existe un script o proceso automático (revisar cron jobs)")
    print("4. Alguien con acceso a la base de datos modificó el hash directamente")
    print("5. Error en el proceso de cambio de contraseña (poco probable)")
    print()
