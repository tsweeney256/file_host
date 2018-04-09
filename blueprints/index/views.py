from flask import Blueprint, redirect, session, render_template, url_for
from file_host.helpers import login_required

blueprint = Blueprint('index', __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    if 'site_user_id' not in session:
        return redirect(url_for('user.login'))
    return render_template('index/index.html')
