from flask import Blueprint, render_template
from app.utils.auth import get_current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)