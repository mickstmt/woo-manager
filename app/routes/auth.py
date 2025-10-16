# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User  # ← Import desde models.py
from functools import wraps
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')

def admin_required(f):
    """
    Decorador para rutas que requieren permisos de administrador.
    Uso: @admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            flash('Necesitas permisos de administrador para acceder a esta página.', 'danger')
            return redirect(url_for('products.index'))
        
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('products.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=remember)
            user.update_last_login()
            
            flash(f'¡Bienvenido {user.full_name or user.username}!', 'success')
            
            # Redirigir a la página que intentaba acceder o al dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                # Redirigir al dashboard principal
                return redirect('/')
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro - Solo correos autorizados en lista blanca"""
    if current_user.is_authenticated:
        return redirect(url_for('products.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        full_name = request.form.get('full_name')
        
        # Validación de campos vacíos
        if not all([username, email, password, password_confirm]):
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Limpiar email
        email = email.lower().strip()
        
        # ========================================
        # VALIDACIÓN 1: Dominio corporativo
        # ========================================
        if not email.endswith('@izistoreperu.com'):
            flash('❌ Solo se permiten correos corporativos @izistoreperu.com', 'danger')
            return redirect(url_for('auth.register'))
        
        # ========================================
        # VALIDACIÓN 2: Email en lista blanca
        # ========================================
        from whitelist import is_email_authorized
        
        if not is_email_authorized(email):
            flash('❌ Este correo no está autorizado para registro. Contacta al administrador del sistema.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validar que las contraseñas coincidan
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validar longitud de contraseña
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validar formato de usuario
        import re
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            flash('El usuario debe tener entre 3 y 20 caracteres (solo letras, números y guiones bajos).', 'danger')
            return redirect(url_for('auth.register'))
        
        # Verificar si el usuario ya existe
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Verificar si el email ya existe
        if User.query.filter_by(email=email).first():
            flash('Este correo ya tiene una cuenta registrada.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Crear nuevo usuario
        try:
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                role='user'
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('✅ ¡Cuenta creada exitosamente! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la cuenta: {str(e)}', 'danger')
            return redirect(url_for('auth.register'))
    
    # GET: Mostrar formulario
    from whitelist import get_authorized_count
    authorized_count = get_authorized_count()
    
    return render_template('auth/register.html', authorized_count=authorized_count)

@bp.route('/profile')
@login_required
def profile():
    """Perfil de usuario"""
    return render_template('auth/profile.html')

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambiar contraseña"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('auth.change_password'))
        
        if new_password != confirm_password:
            flash('Las contraseñas nuevas no coinciden.', 'danger')
            return redirect(url_for('auth.change_password'))
        
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Contraseña actualizada correctamente.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')