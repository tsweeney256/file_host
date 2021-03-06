import psycopg2
from functools import wraps
from flask import current_app, g, redirect, request, session, url_for


def get_db_connection():
    if not g.get('db', None):
        db_connection_string = ''
        config = current_app.config
        if 'DBNAME' in config:
            db_connection_string += 'dbname={} '.format(config['DBNAME'])
        if 'DBUSER' in config:
            db_connection_string += 'user={} '.format(config['DBUSER'])
        if 'DBPASS' in config:
            db_connection_string += 'password={} '.format(config['DBPASS'])
        if 'DBPORT' in config:
            db_connection_string += 'port={} '.format(config['DBPORT'])
        if 'DBHOST' in config:
            db_connection_string += 'host={} '.format(config['DBHOST'])
        g.db = psycopg2.connect(db_connection_string)
    return g.db


def get_index_str():
    return current_app.config['INDEX']


def login_required(f):
    @wraps(f)
    def handle_login_requirement(*args, **kwargs):
        if 'site_user_id' not in session:
            return redirect(url_for('user.login', next=request.url))
        return f(*args, **kwargs)
    return handle_login_requirement
