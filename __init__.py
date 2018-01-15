import os
from flask import Flask


def create_app(settings_file):
    app = Flask(__name__)
    app.config.from_pyfile(settings_file)
    import file_host.blueprints.index.views as index_views
    app.register_blueprint(index_views.blueprint)
    import file_host.blueprints.user.views as user_views
    app.register_blueprint(user_views.blueprint)
    return app


if __name__ == '__main__':
    settings = os.path.dirname(os.path.realpath(__file__)) + '/settings.py'
    if 'FILE_HOST_SETTINGS' in os.environ:
        settings = os.environ['FILE_HOST_SETTINGS']
    app = create_app(settings)
    app.run()
