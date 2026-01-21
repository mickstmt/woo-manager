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

        # Comando de backup: Intentar mysqldump y mariadb-dump
        dump_commands = ['mysqldump', 'mariadb-dump']
        if os.name == 'nt':
            dump_commands = ['mysqldump.exe']

        result = None
        last_error = ""

        # Preparar entorno para pasar el password de forma segura
        env = os.environ.copy()
        if db_password:
            env['MYSQL_PWD'] = db_password

        for dump_cmd in dump_commands:
            # Agregamos flags de compatibilidad comunes:
            # --column-statistics=0: Evita errores en servidores que no soportan esta opción (MySQL 8 vs 5.7)
            # --no-tablespaces: Evita errores de permisos en entornos restringidos como Hostinger
            cmd = [
                dump_cmd, 
                '--host', db_host, 
                '--port', db_port, 
                '--user', db_user,
                '--column-statistics=0',
                '--no-tablespaces',
                '--result-file=' + sql_path, 
                db_name
            ]
            
            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    break
            except FileNotFoundError:
                last_error = f"Comando '{dump_cmd}' no encontrado."
                continue
            except Exception as e:
                last_error = f"Error ejecutando {dump_cmd}: {str(e)}"
                continue

        if not result or result.returncode != 0:
            error_msg = result.stderr if result else last_error
            # Si el error es específicamente por --column-statistics (versiones viejas de mysqldump)
            if result and "unknown option '--column-statistics=0'" in result.stderr:
                # Reintentar sin esa opción
                cmd.remove('--column-statistics=0')
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode != 0:
                    error_msg = result.stderr
            
            if not result or result.returncode != 0:
                current_app.logger.error(f"Error final en backup: {error_msg}")
                flash(f"Error al generar el backup: {error_msg}", "danger")
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
