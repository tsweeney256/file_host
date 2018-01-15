import os
from file_host.helpers import app_name
from flask import Flask


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
