from flask import Blueprint, redirect, session, render_template, url_for

blueprint = Blueprint('index', __name__, template_folder='templates')


@blueprint.route('/')
def index():
    if 'site_user_id' not in session:
        return redirect(url_for('user.login'))
    return render_template('index/index.html')
