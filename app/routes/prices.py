from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('prices', __name__, url_prefix='/prices')

@bp.route('/')
@login_required
def index():
    """Gestión de precios"""
    return render_template('prices.html', title='Gestión de Precios')