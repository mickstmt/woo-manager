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
            return redirect(url_for('index'))
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
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        # Log para debug (ocultando pass)
        current_app.logger.info(f"Procesando backup para URI (ofuscada): {db_uri.split('@')[-1] if '@' in db_uri else 'N/A'}")

        # Usar urlparse para una extracción más robusta
        from urllib.parse import urlparse, unquote
        
        # SQLALCHEMY_DATABASE_URI suele tener el formato mysql+pymysql://...
        # urlparse maneja esto bien si el esquema es reconocido
        try:
            # Eliminamos el prefijo 'mysql+pymysql://' para que urlparse lo trate como una URL estándar
            raw_uri = db_uri.replace('mysql+pymysql://', 'mysql://')
            parsed = urlparse(raw_uri)
            
            db_user = unquote(parsed.username) if parsed.username else ''
            db_password = unquote(parsed.password) if parsed.password else ''
            db_host = parsed.hostname or 'localhost'
            db_port = str(parsed.port or 3306)
            
            # El path suele ser '/dbname', eliminamos la barra inicial
            db_name = parsed.path.lstrip('/')
            
            # CRITICAL: Si el path tiene parámetros (?charset=...), eliminarlos
            if '?' in db_name:
                db_name = db_name.split('?')[0]
                
            if not db_name:
                raise ValueError("No se encontró el nombre de la base de datos en la URI")
                
        except Exception as e:
            current_app.logger.error(f"Error parseando URI: {str(e)}")
            raise ValueError(f"Formato de base de datos no reconocido: {str(e)}")

        # Nombre del archivo de backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_woocommerce_{timestamp}"
        sql_path = os.path.join(tempfile.gettempdir(), f"{filename}.sql")
        gz_path = f"{sql_path}.gz"

        # Intentar encontrar mysqldump
        cmd_path = shutil.which('mysqldump') or shutil.which('mariadb-dump')
        if not cmd_path and os.name == 'nt':
            cmd_path = shutil.which('mysqldump.exe')

        if not cmd_path:
            flash("Error: No se encontró el comando 'mysqldump' en el sistema.", "danger")
            return redirect(url_for('index'))

        # Crear un archivo de opciones temporal para las credenciales
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as f_cnf:
            f_cnf.write("[client]\n")
            f_cnf.write(f"user=\"{db_user}\"\n")
            if db_password:
                f_cnf.write(f"password=\"{db_password}\"\n")
            f_cnf.write(f"host=\"{db_host}\"\n")
            f_cnf.write(f"port={db_port}\n")
            cnf_path = f_cnf.name

        try:
            # Comando final
            cmd = [
                cmd_path, 
                f"--defaults-extra-file={cnf_path}",
                '--column-statistics=0',
                '--no-tablespaces',
                '--result-file=' + sql_path, 
                db_name
            ]
            
            current_app.logger.info(f"Ejecutando backup con: {cmd_path} para la base {db_name} en {db_host}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Si falla por --column-statistics (versiones viejas), reintentar sin eso
            if result.returncode != 0 and "--column-statistics" in (result.stderr or ""):
                current_app.logger.info("Reintentando sin --column-statistics...")
                cmd = [c for c in cmd if c != '--column-statistics=0']
                result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                error_msg = result.stderr or "Error desconocido en mysqldump"
                current_app.logger.error(f"Error en backup: {error_msg}")
                flash(f"Error al generar el backup: {error_msg}", "danger")
                return redirect(url_for('index'))

        finally:
            if os.path.exists(cnf_path):
                os.remove(cnf_path)

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
        return redirect(url_for('index'))

    finally:
        # Nota: La eliminación del archivo .gz no se puede hacer aquí directamente 
        # si se está sirviendo vía send_file, a menos que se use un generador o 
        # cleanup posterior. Sin embargo, en tempdir se limpiará eventualmente.
        pass
