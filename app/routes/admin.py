# app/routes/admin.py
from flask import Blueprint, send_file, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
import subprocess
import os
import tempfile
from datetime import datetime
import gzip
import shutil

bp = Blueprint('admin', __name__, url_prefix='/admin')

def backup_required(f):
    """Decorador para restringir el acceso solo al usuario mickstmt"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.username != 'mickstmt':
            flash('No tienes permisos para acceder a esta funcionalidad del sistema.', 'danger')
            return redirect(url_for('products.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/backup/db')
@login_required
@backup_required
def backup_db():
    """
    Genera un backup de la base de datos usando mysqldump y lo sirve como descarga comprimida.
    """
    try:
        # Obtener configuración de la base de datos
        db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
        
        # SQLALCHEMY_DATABASE_URI format: mysql+pymysql://user:password@host/dbname
        # Necesitamos extraer los componentes para mysqldump
        import re
        match = re.search(r'mysql\+pymysql://([^:]+):?([^@]*)@([^/]+)/(.+)', db_uri)
        
        if not match:
            # Reintentar sin contraseña
            match = re.search(r'mysql\+pymysql://([^@]+)@([^/]+)/(.+)', db_uri)
            if match:
                db_user = match.group(1)
                db_password = None
                db_host = match.group(2)
                db_name = match.group(3)
            else:
                raise ValueError("No se pudo parsear la URL de la base de datos")
        else:
            db_user = match.group(1)
            db_password = match.group(2)
            db_host = match.group(3)
            db_name = match.group(4)

        # Nombre del archivo de backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_woocommerce_{timestamp}"
        sql_path = os.path.join(tempfile.gettempdir(), f"{filename}.sql")
        gz_path = f"{sql_path}.gz"

        # Comando mysqldump
        dump_cmd = 'mysqldump'
        if os.name == 'nt': # Windows check
            dump_cmd = 'mysqldump.exe'

        cmd = [dump_cmd, '--host', db_host, '--user', db_user]
        if db_password:
            cmd.append(f'--password={db_password}')
        cmd.extend([db_name, '--result-file=' + sql_path])

        # Ejecutar backup
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            flash("Error: El comando 'mysqldump' no está instalado o no se encuentra en el PATH del sistema. Si estás en Windows, asegúrate de tener MySQL instalado y su carpeta 'bin' añadida a las variables de entorno.", "danger")
            return redirect(url_for('products.index'))
        
        if result.returncode != 0:
            current_app.logger.error(f"Error en mysqldump: {result.stderr}")
            flash(f"Error al generar el backup: {result.stderr}", "danger")
            return redirect(url_for('products.index'))

        # Comprimir el archivo
        with open(sql_path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Eliminar el SQL sin comprimir
        os.remove(sql_path)

        # Servir el archivo comprimido
        return send_file(
            gz_path,
            as_attachment=True,
            download_name=f"{filename}.sql.gz",
            mimetype='application/gzip'
        )

    except Exception as e:
        current_app.logger.error(f"Error sistemático en backup: {str(e)}")
        flash(f"Error del sistema: {str(e)}", "danger")
        return redirect(url_for('products.index'))

    finally:
        # Nota: La eliminación del archivo .gz no se puede hacer aquí directamente 
        # si se está sirviendo vía send_file, a menos que se use un generador o 
        # cleanup posterior. Sin embargo, en tempdir se limpiará eventualmente.
        pass
