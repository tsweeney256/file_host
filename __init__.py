import os
import psycopg2
from flask import current_app, Flask, g

app_name = 'file_host'


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


def create_app(settings_file):
    app = Flask(app_name)
    app.config.from_pyfile(settings_file)
    import file_host.views
    app.register_blueprint(file_host.views.user)
    return app


if __name__ == '__main__':
    settings = os.path.dirname(os.path.realpath(__file__)) + '/settings.py'
    if 'FILE_HOST_SETTINGS' in os.environ:
        settings = os.environ['FILE_HOST_SETTINGS']
    app = create_app(settings)
    app.run()
