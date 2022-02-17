import os, logging

from flask import Flask

# Copied from flask tutorial
def create_app(test_config=None):
    # # Start logging
    # log = init_logging()

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    database = os.path.join(app.instance_path, 'badstats.sqlite')
    app.config.from_mapping(
        SECRET_KEY=os.environ["FLASK_SECRET"],
        DATABASE=database,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='Strict'
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    if not os.path.exists(database):
        with app.app_context():
            db.init_db()
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import stats
    app.register_blueprint(stats.bp)
    app.add_url_rule('/', endpoint='index')

    @app.after_request
    def setSecureHeaders(response):
        headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self';\
                img-src 'self' https://*.scdn.co data: ;",
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',


        }

        response.headers.update(headers)

        return response

    return app

def getHostname():
    if "REDIRECT_HOSTNAME" not in os.environ:
        host = "http://127.0.0.1:5000"
    else:
        host = os.environ['REDIRECT_HOSTNAME']
    return host