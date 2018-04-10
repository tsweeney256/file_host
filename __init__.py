import os
from flask import Flask
from flask_mail import Mail
from file_host.helpers import get_db_connection


def create_app(settings_file):
    app = Flask(__name__)
    app.config.from_pyfile(settings_file)
    site_user_statuses = {}
    with app.app_context():
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute('select status_id, status from site_user_status;')
            for id, name in cursor:
                site_user_statuses[name] = id
    app.config['site_user_statuses'] = site_user_statuses
    app.config['mail'] = Mail(app)
    if 'INDEX' not in app.config:
        app.config['INDEX'] = 'index.index'
    import file_host.blueprints.index.views as index_views
    app.register_blueprint(index_views.blueprint)
    import file_host.blueprints.user.views as user_views
    app.register_blueprint(user_views.blueprint, url_prefix='/user')
    return app


if __name__ == '__main__':
    settings = os.path.dirname(os.path.realpath(__file__)) + '/settings.py'
    if 'FILE_HOST_SETTINGS' in os.environ:
        settings = os.environ['FILE_HOST_SETTINGS']
    app = create_app(settings)
    app.run()
