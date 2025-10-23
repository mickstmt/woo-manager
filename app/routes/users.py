# app/routes/users.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.routes.auth import admin_required
from app.models import User, UserLoginHistory
from app import db
from datetime import datetime, timedelta
from sqlalchemy import or_, func

bp = Blueprint('users', __name__, url_prefix='/users')


@bp.route('/')
@login_required
@admin_required
def index():
    """
    Vista principal de gestión de usuarios
    Solo accesible para administradores
    
    URL: /users/
    """
    return render_template('users/index.html', title='Gestión de Usuarios')


@bp.route('/list')
@login_required
@admin_required
def list_users():
    """
    Obtener lista de usuarios en formato JSON
    
    URL: /users/list
    Parámetros:
        - page: número de página
        - per_page: usuarios por página
        - search: término de búsqueda
        - role: filtro por rol (admin/user)
        - status: filtro por estado (active/inactive)
    """
    try:
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        search = request.args.get('search', '', type=str)
        role_filter = request.args.get('role', '', type=str)
        status_filter = request.args.get('status', '', type=str)
        
        # Limitar per_page
        per_page = min(per_page, 100)
        
        # Consulta base
        query = User.query
        
        # Aplicar búsqueda
        if search and search.strip():
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    User.username.like(search_term),
                    User.email.like(search_term),
                    User.full_name.like(search_term)
                )
            )
        
        # Aplicar filtro de rol
        if role_filter:
            query = query.filter_by(role=role_filter)
        
        # Aplicar filtro de estado
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'inactive':
            query = query.filter_by(is_active=False)
        
        # Ordenar por fecha de creación (más recientes primero)
        query = query.order_by(User.created_at.desc())
        
        # Paginar
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Convertir a JSON
        users_list = []
        for user in pagination.items:
            users_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name or '',
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                'is_current_user': user.id == current_user.id
            })
        
        return jsonify({
            'success': True,
            'users': users_list,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next,
                'prev_num': pagination.prev_num,
                'next_num': pagination.next_num
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/stats')
@login_required
@admin_required
def stats():
    """
    Obtener estadísticas de usuarios
    
    URL: /users/stats
    """
    try:
        total = User.query.count()
        active = User.query.filter_by(is_active=True).count()
        inactive = User.query.filter_by(is_active=False).count()
        admins = User.query.filter_by(role='admin').count()
        regular_users = User.query.filter_by(role='user').count()
        
        # Usuarios que iniciaron sesión en los últimos 7 días
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_last_week = User.query.filter(
            User.last_login >= week_ago
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'active': active,
                'inactive': inactive,
                'admins': admins,
                'regular_users': regular_users,
                'active_last_week': active_last_week
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """
    Crear un nuevo usuario
    
    URL: POST /users/create
    JSON Body:
    {
        "username": "nuevo_usuario",
        "email": "email@izistoreperu.com",
        "full_name": "Nombre Completo",
        "password": "contraseña",
        "role": "user"  // o "admin"
    }
    """
    try:
        data = request.get_json()
        
        # Validaciones
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        full_name = data.get('full_name', '').strip()
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not all([username, email, password]):
            return jsonify({
                'success': False,
                'error': 'Usuario, email y contraseña son obligatorios'
            }), 400
        
        # Validar que el email termine en @izistoreperu.com
        if not email.endswith('@izistoreperu.com'):
            return jsonify({
                'success': False,
                'error': 'Solo se permiten correos corporativos @izistoreperu.com'
            }), 400
        
        # Validar formato de usuario
        import re
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return jsonify({
                'success': False,
                'error': 'El usuario debe tener entre 3 y 20 caracteres (solo letras, números y guiones bajos)'
            }), 400
        
        # Validar longitud de contraseña
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener al menos 6 caracteres'
            }), 400
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            return jsonify({
                'success': False,
                'error': 'El nombre de usuario ya está en uso'
            }), 400
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            return jsonify({
                'success': False,
                'error': 'El email ya está registrado'
            }), 400
        
        # Validar rol
        if role not in ['admin', 'user']:
            role = 'user'
        
        # Crear usuario
        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario {username} creado exitosamente',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'full_name': new_user.full_name,
                'role': new_user.role,
                'is_active': new_user.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/<int:user_id>')
@login_required
@admin_required
def get_user(user_id):
    """
    Obtener información detallada de un usuario
    
    URL: /users/123
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # Obtener historial de accesos (últimos 10)
        login_history = UserLoginHistory.query.filter_by(
            user_id=user_id
        ).order_by(UserLoginHistory.login_at.desc()).limit(10).all()
        
        history_list = []
        for record in login_history:
            history_list.append({
                'login_at': record.login_at.strftime('%Y-%m-%d %H:%M:%S'),
                'ip_address': record.ip_address,
                'user_agent': record.user_agent
            })
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': user.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                'is_current_user': user.id == current_user.id
            },
            'login_history': history_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:user_id>/update', methods=['POST'])
@login_required
@admin_required
def update_user(user_id):
    """
    Actualizar información de un usuario
    
    URL: POST /users/123/update
    JSON Body:
    {
        "email": "nuevo@izistoreperu.com",
        "full_name": "Nuevo Nombre",
        "role": "admin"
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        data = request.get_json()
        
        # Actualizar email si se proporciona
        if 'email' in data:
            new_email = data['email'].strip().lower()
            
            # Validar formato
            if not new_email.endswith('@izistoreperu.com'):
                return jsonify({
                    'success': False,
                    'error': 'Solo se permiten correos corporativos @izistoreperu.com'
                }), 400
            
            # Verificar que no esté en uso por otro usuario
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({
                    'success': False,
                    'error': 'El email ya está en uso por otro usuario'
                }), 400
            
            user.email = new_email
        
        # Actualizar nombre completo
        if 'full_name' in data:
            user.full_name = data['full_name'].strip()
        
        # Actualizar rol
        if 'role' in data:
            new_role = data['role']
            if new_role in ['admin', 'user']:
                # No permitir que el admin se quite sus propios permisos
                if user.id == current_user.id and new_role != 'admin':
                    return jsonify({
                        'success': False,
                        'error': 'No puedes quitarte tus propios permisos de administrador'
                    }), 400
                user.role = new_role
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuario actualizado exitosamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'is_active': user.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """
    Activar/Desactivar un usuario
    
    URL: POST /users/123/toggle-status
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # No permitir desactivar al usuario actual
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'No puedes desactivar tu propia cuenta'
            }), 400
        
        # Cambiar estado
        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'activado' if user.is_active else 'desactivado'
        
        return jsonify({
            'success': True,
            'message': f'Usuario {status} exitosamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_active': user.is_active
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """
    Restablecer contraseña de un usuario
    
    URL: POST /users/123/reset-password
    JSON Body:
    {
        "new_password": "nueva_contraseña"
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        data = request.get_json()
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({
                'success': False,
                'error': 'La nueva contraseña es obligatoria'
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                'success': False,
                'error': 'La contraseña debe tener al menos 6 caracteres'
            }), 400
        
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contraseña restablecida exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Eliminar un usuario
    
    URL: POST /users/123/delete
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
        
        # No permitir eliminar al usuario actual
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'No puedes eliminar tu propia cuenta'
            }), 400
        
        username = user.username
        
        # Eliminar historial de accesos primero
        UserLoginHistory.query.filter_by(user_id=user_id).delete()
        
        # Eliminar usuario
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Usuario {username} eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500