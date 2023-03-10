from os import environ, path
from flask import Flask, Blueprint, render_template, request, url_for, redirect, g, send_file
from flask_sqlalchemy import SQLAlchemy
from jinja2 import Environment
from sqlalchemy.sql import func, text
from werkzeug.exceptions import HTTPException, InternalServerError, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
from dateutil import parser
from glob import glob
from hashlib import md5
from csv import writer
from re import sub
import io
import logging
import base64
import time


app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

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

with app.app_context():
    valid_columns = [c[1] for c in db.session.execute(text('pragma table_info(Killmails)'))]
    valid_columns.append('date_start')
    valid_columns.append('date_end')
    valid_columns.append('csv')


def date_to_timestamp(datestring, end=False):
    if not datestring:
        return None
    try:
        date_obj = parser.isoparse(datestring)
    except:
        print(f"[!] bad date: '{datestring}'")
        return None
    if end:
        timestamp = datetime.combine(date_obj, date_obj.max.time(), tzinfo=timezone.utc).timestamp()
    else:
        timestamp = datetime.combine(date_obj, date_obj.min.time(), tzinfo=timezone.utc).timestamp()
    return int(timestamp)


def make_csv(killmails):
    headers = killmails[0]._fields
    csv = io.StringIO()
    w = writer(csv)
    w.writerow(headers)
    w.writerows(killmails)
    file = io.BytesIO()
    file.write(csv.getvalue().encode())
    file.seek(0)
    csv.close()
    return file


def gen_params(request_args):
    report_id = request_args['report_id'] if 'report_id' in request_args and request_args['report_id'] else None
    killer_corp = sub('\*', '%', request_args['killer_corp']) if 'killer_corp' in request_args and request_args['killer_corp'] else None
    killer_name = '%' + sub('\*', '%', request_args['killer_name']) if 'killer_name' in request_args and request_args['killer_name'] else None
    minimum_isk = request_args['isk'] if 'isk' in request_args and request_args['isk'] else None
    victim_ship_type = '%' + sub('\*', '%', request_args['victim_ship_type']) if 'victim_ship_type' in request_args and request_args['victim_ship_type'] else None
    victim_ship_category = sub('\*', '%', request_args['victim_ship_category']) if 'victim_ship_category' in request_args and request_args['victim_ship_category'] else None
    victim_name = '%' + sub('\*', '%', request_args['victim_name']) if 'victim_name' in request_args and request_args['victim_name'] else None
    victim_corp = sub('\*', '%', request_args['victim_corp']) if 'victim_corp' in request_args and request_args['victim_corp'] else None
    system = '%' + sub('\*', '%', request_args['system']) if 'system' in request_args and request_args['system'] else None
    constellation = '%' + sub('\*', '%', request_args['constellation']) if 'constellation' in request_args and request_args['constellation'] else None
    region = '%' + sub('\*', '%', request_args['region']) if 'region' in request_args and request_args['region'] else None
    victim_total_damage_received = request_args['victim_total_damage_received'] if 'victim_total_damage_received' in request_args else None
    max_total_participants = request_args['total_participants'] if 'total_participants' in request_args else None
    killer_ship_type = '%' + sub('\*', '%', request_args['killer_ship_type']) if 'killer_ship_type' in request_args and request_args['killer_ship_type'] else None
    killer_ship_category = sub('\*', '%', request_args['killer_ship_category']) if 'killer_ship_category' in request_args and request_args['killer_ship_category'] else None
    timestamp = request_args['timestamp'] if 'timestamp' in request_args else None
    date_start = request_args['date_start'] if 'date_start' in request_args else None
    date_end = request_args['date_end'] if 'date_end' in request_args else None

    timestamp_start = date_to_timestamp(date_start)
    timestamp_end = date_to_timestamp(date_end, end=True)

    if timestamp_start and timestamp_end and timestamp_start > timestamp_end:
        timestamp_start, timestamp_end = None, None
    
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
              'timestamp': timestamp,
              'timestamp_start': timestamp_start,
              'timestamp_end': timestamp_end
              }

    return params

@app.template_filter('urlify')
def urlify(text):
    return text.replace('+', '%2B') if text else None

app.jinja_env.filters['urlify'] = urlify


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

    killmails = latest.all()
    csv = make_csv(killmails)
    
    return render_template('index.html', kms=killmails, csv=csv, update_age_minutes=update_minutes_old, title="latest")


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
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400
    
    params = gen_params(request.args)

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
                                    (:timestamp_start IS NULL OR timestamp >= :timestamp_start) AND
                                    (:timestamp_end IS NULL OR timestamp <= :timestamp_end)
                                    ORDER BY isk DESC
                                    LIMIT 10000
                                  '''), params=params)

    killmails = kms.all()
    if request.args.get("csv", default=False, type=bool):
        csv = make_csv(killmails)
        datestamp = datetime.now().strftime("%Y-%m-%d")
        filename = '&'.join([f"{key}={val}" for key,val in (request.args.items()) if key != 'csv']) + f'-{datestamp}.csv'
        return send_file(csv, download_name=filename, as_attachment=True)

    isk_total = sum(km._mapping['isk'] for km in killmails)
    return render_template('search.html', title="killmail search", kms=killmails, isk_total=isk_total, timestamp_start=params['timestamp_start'], timestamp_end=params['timestamp_end'])


@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400

    params = gen_params(request.args)

    kms = db.session.execute(text('''
                                    SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails
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
                                    (:timestamp_start IS NULL OR timestamp >= :timestamp_start) AND
                                    (:timestamp_end IS NULL OR timestamp <= :timestamp_end) AND
                                    isk > 0
                                    GROUP BY killer_name
                                    ORDER BY SUM(isk) DESC
                                  '''), params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/leaderboard?', '')
    return render_template('leaderboard.html', title="killmail search", kms=killmails, url_params=url_params)


@app.route('/loserboard', methods=['GET'])
def loserboard():
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400

    params = gen_params(request.args)

    kms = db.session.execute(text('''
                                    SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails
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
                                    (:timestamp_start IS NULL OR timestamp >= :timestamp_start) AND
                                    (:timestamp_end IS NULL OR timestamp <= :timestamp_end) AND
                                    isk > 0
                                    GROUP BY victim_name
                                    ORDER BY SUM(isk) DESC
                                  '''), params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/loserboard?', '')
    return render_template('loserboard.html', title="killmail search", kms=killmails, url_params=url_params)



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