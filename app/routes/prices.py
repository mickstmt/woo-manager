from flask import Blueprint, render_template

bp = Blueprint('prices', __name__, url_prefix='/prices')

@bp.route('/')
def index():
    """Gestión de precios"""
    return render_template('prices.html', title='Gestión de Precios')