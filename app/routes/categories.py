from flask import Blueprint, render_template

bp = Blueprint('categories', __name__, url_prefix='/categories')

@bp.route('/')
def index():
    """Gestión de categorías"""
    return render_template('categories.html', title='Gestión de Categorías')