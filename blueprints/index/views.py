from flask import Blueprint, redirect, session, render_template, url_for
from file_host.helpers import login_required

blueprint = Blueprint('index', __name__, template_folder='templates')


@blueprint.route('/')
@login_required
def index():
    return render_template('index/index.html')
