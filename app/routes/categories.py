from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('categories', __name__, url_prefix='/categories')

@bp.route('/')
@login_required
def index():
    """Gestión de categorías"""
    return render_template('categories.html', title='Gestión de Categorías')