from os import environ, path
from flask import Flask, Blueprint, render_template, request, url_for, redirect, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, text
from werkzeug.exceptions import HTTPException, InternalServerError, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
from dateutil import parser
from glob import glob
from hashlib import md5
from re import sub
from datetime import datetime, timezone
import logging
import base64
import time


app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
# register(app.jinja_env)

db_name = '../km.db'
basedir = path.abspath(path.dirname(__file__))
db_path = 'sqlite:///' + path.join(basedir, db_name)

app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Killmails(db.Model):
    id = db.Column(db.String, primary_key=True, nullable=False, unique=True)
    report_id = db.Column(db.String, nullable=False)
    killer_corp = db.Column(db.String)
    killer_name = db.Column(db.String, nullable=False)
    isk = db.Column(db.Integer, nullable=False)
    date_killed = db.Column(db.String, nullable=False)
    image_url = db.Column(db.String, nullable=False)
    victim_ship_type = db.Column(db.String)
    victim_ship_category = db.Column(db.String)
    external_provider = db.Column(db.String)
    victim_name = db.Column(db.String)
    victim_corp = db.Column(db.String)
    system = db.Column(db.String)
    constellation = db.Column(db.String)
    region = db.Column(db.String)
    victim_total_damage_received = db.Column(db.Integer)
    total_participants = db.Column(db.Integer)
    killer_ship_type = db.Column(db.String)
    killer_ship_category =db.Column(db.String)
    timestamp = db.Column(db.Integer)

    def __repr__(self):
        return f'<Killmail {self.report_id}>'


# @app.errorhandler(BadRequest)
# def handle_bad_request(e):
#     return 'bad request!', 400

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

routes = Blueprint('views', __name__)

@routes.route('/')
def index():
    latest = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    ORDER BY timestamp DESC
                                    LIMIT 50
                                  '''))

    update_time = db.session.execute(text('''SELECT last_refreshed 
                                                  FROM Months
                                                  ORDER BY month DESC
                                                  LIMIT 1''')).all()[0][0]

    update_seconds_old = (datetime.now(timezone.utc) - parser.isoparse(update_time)).total_seconds()
    update_minutes_old = int(divmod(update_seconds_old , 60)[0])
    
    return render_template('index.html', kms=latest.all(), update_age_minutes=update_minutes_old)


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


@app.route('/positivity')
def positivity():
    corps_poz = db.session.execute(text('''
                                        SELECT killer_corp, sum(isk)
                                        FROM Killmails
                                        GROUP BY killer_corp
                                        ORDER BY sum(isk)
    '''))

    corps_neg = db.session.execute(text('''
                                        SELECT victim_corp, sum(isk)
                                        FROM Killmails
                                        GROUP BY victim_corp
                                        ORDER BY sum(isk)
    '''))

    score = {}

    for corp in corps_poz:
        score[corp[0]] = corp[1]
    for corp in corps_neg:
        if not corp[0] in score:
            score[corp[0]] = corp[1] * -1
        else:
            score[corp[0]] = score[corp[0]] - corp[1]

    sorted_score = dict(sorted(score.items(), key=lambda item: item[1], reverse=True))

    return render_template('positivity.html', title="positivity", score=sorted_score)



@app.route('/bullying')
def bullying():
    bullies = db.session.execute(text('''
                                        SELECT killer_corp, victim_corp, sum(isk)
                                        FROM Killmails
                                        WHERE killer_corp not null AND victim_corp not null
                                        GROUP BY killer_corp, victim_corp
                                        ORDER BY sum(isk) desc
                                        LIMIT 500
    '''))

    return render_template('bullying.html', title="bullying olympics", bullies=bullies)

@app.route('/search', methods=['GET'])
def search():
    valid_columns = [c[1] for c in db.session.execute(text('pragma table_info(Killmails)'))]
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400
    order = 'isk'
    direction = 'desc'
    report_id = request.args['report_id'] if 'report_id' in request.args and request.args['report_id'] else None
    killer_corp = sub('\*', '%', request.args['killer_corp']) if 'killer_corp' in request.args and request.args['killer_corp'] else None
    killer_name = '%' + sub('\*', '%', request.args['killer_name']) if 'killer_name' in request.args and request.args['killer_name'] else None
    minimum_isk = request.args['isk'] if 'isk' in request.args and request.args['isk'] else None
    victim_ship_type = '%' + sub('\*', '%', request.args['victim_ship_type']) if 'victim_ship_type' in request.args and request.args['victim_ship_type'] else None
    victim_ship_category = '%' + sub('\*', '%', request.args['victim_ship_category']) if 'victim_ship_category' in request.args and request.args['victim_ship_category'] else None
    victim_name = '%' + sub('\*', '%', request.args['victim_name']) if 'victim_name' in request.args and request.args['victim_name'] else None
    victim_corp = sub('\*', '%', request.args['victim_corp']) if 'victim_corp' in request.args and request.args['victim_corp'] else None
    system = '%' + sub('\*', '%', request.args['system']) if 'system' in request.args and request.args['system'] else None
    constellation = '%' + sub('\*', '%', request.args['constellation']) if 'constellation' in request.args and request.args['constellation'] else None
    region = '%' + sub('\*', '%', request.args['region']) if 'region' in request.args and request.args['region'] else None
    victim_total_damage_received = request.args['victim_total_damage_received'] if 'victim_total_damage_received' in request.args else None
    max_total_participants = request.args['total_participants'] if 'total_participants' in request.args else None
    killer_ship_type = '%' + sub('\*', '%', request.args['killer_ship_type']) if 'killer_ship_type' in request.args and request.args['killer_ship_type'] else None
    killer_ship_category = '%' + sub('\*', '%', request.args['killer_ship_category']) if 'killer_ship_category' in request.args and request.args['killer_ship_category'] else None
    timestamp = request.args['timestamp'] if 'timestamp' in request.args else None
    
    params = {
              'report_id': report_id,
              'killer_corp': killer_corp,
              'killer_name': killer_name,
              'minimum_isk': minimum_isk,
              'victim_ship_type': victim_ship_type,
              'victim_ship_category': victim_ship_category,
              'victim_name': victim_name,
              'victim_corp': victim_corp,
              'system': system,
              'constellation': constellation,
              'region': region,
              'victim_total_damage_received': victim_total_damage_received,
              'max_total_participants': max_total_participants,
              'killer_ship_type': killer_ship_type,
              'killer_ship_category': killer_ship_category,
              'timestamp': timestamp
              }

    kms = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    WHERE
                                    (:report_id IS NULL OR report_id = :report_id) AND
                                    (:killer_corp IS NULL OR killer_corp LIKE :killer_corp) AND
                                    (:killer_name IS NULL OR killer_name LIKE :killer_name) AND
                                    (:minimum_isk IS NULL OR isk >= :minimum_isk) AND
                                    (:victim_ship_type IS NULL OR victim_ship_type LIKE :victim_ship_type) AND
                                    (:victim_ship_category IS NULL OR victim_ship_category LIKE :victim_ship_category) AND
                                    (:victim_name IS NULL OR victim_name LIKE :victim_name) AND
                                    (:victim_corp IS NULL OR victim_corp LIKE :victim_corp) AND
                                    (:system IS NULL OR system LIKE :system) AND
                                    (:constellation IS NULL OR constellation LIKE :constellation) AND
                                    (:region IS NULL OR region LIKE :region) AND
                                    (:victim_total_damage_received IS NULL OR victim_total_damage_received LIKE :victim_total_damage_received) AND
                                    (:max_total_participants IS NULL OR total_participants <= :max_total_participants) AND
                                    (:killer_ship_type IS NULL OR killer_ship_type LIKE :killer_ship_type) AND
                                    (:killer_ship_category IS NULL OR killer_ship_category LIKE :killer_ship_category) AND
                                    (:timestamp IS NULL OR timestamp LIKE :timestamp)
                                    ORDER BY isk DESC
                                    LIMIT 5000
                                  '''), params=params)

    return render_template('search.html', title="killmail search", kms=kms.all())
    
@app.before_first_request
def database_tweak():
    print("increasing cache size")
    db.session.execute(text('PRAGMA cache_size=-200000'))


app.register_blueprint(routes)

if __name__ == "__main__":
    app.run()

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)