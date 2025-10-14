from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('images', __name__, url_prefix='/images')

@bp.route('/')
@login_required
def index():
    """Gestión de imágenes"""
    return render_template('images.html', title='Gestión de Imágenes')