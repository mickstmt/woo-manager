from flask import Blueprint, render_template

bp = Blueprint('images', __name__, url_prefix='/images')

@bp.route('/')
def index():
    """Gestión de imágenes"""
    return render_template('images.html', title='Gestión de Imágenes')