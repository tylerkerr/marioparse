from os import environ, path
from flask import Flask, redirect, g
from sqlalchemy.sql import text
from werkzeug.middleware.proxy_fix import ProxyFix
from glob import glob
from hashlib import md5
from db import db
from views import routes
from api import apiroutes
from filters import register
import util
import logging
import base64
import time


app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

db_name = '../km.db'

db_path = 'sqlite:///' + path.join(util.basedir, db_name)

app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@app.errorhandler(405)
def method_not_allowed(error):
    return redirect("/", code=302)


if environ.get('MARIOVIEW_ENVIRONMENT') == "production":
    app.secret_key = environ.get('MARIOVIEW_FLASK_KEY')
    app.config.update(SESSION_COOKIE_SECURE=True,
                      SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Strict')
else:
    app.secret_key = 'debug'

mutable_static = glob(path.join(app.root_path, 'static/style', '*.css')) + \
    glob(path.join(app.root_path, 'static/script', '*.js'))

hash_obj = md5(open(mutable_static[0], 'rb').read())

for static_file in mutable_static[1:]:
    hash_obj.update(open(static_file, 'rb').read())
app.config['STATIC_HASH'] = base64.urlsafe_b64encode(
    hash_obj.digest()).decode('ascii')[:-2]

app.config.from_pyfile(path.join(app.root_path, 'app.cfg'))

with app.app_context():
    db.init_app(app)

register(app.jinja_env)


@app.before_first_request
def app_setup():
    print("increasing cache size")
    db.session.execute(text('PRAGMA cache_size=-200000'))


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


# routes

app.register_blueprint(routes)
app.register_blueprint(apiroutes)

if __name__ == "__main__":
    app.run()

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
