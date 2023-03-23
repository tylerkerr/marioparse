from os import environ, path
from flask import Flask, Blueprint, render_template, request, url_for, redirect, g, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from jinja2 import Environment
from sqlalchemy.sql import text, bindparam
from werkzeug.exceptions import HTTPException, InternalServerError, BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
from dateutil import parser
from glob import glob
from hashlib import md5
from csv import writer, reader
from re import sub
from math import copysign
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


### utilities


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


def parse_truesec_csv():
    stars_truesec = {}
    with open(path.join(basedir, '../truesec.csv')) as trueseccsv:
        csvreader = reader(trueseccsv)
        next(csvreader)     # skip header row
        for row in csvreader:
            stars_truesec[row[0]] = row[1]
    return stars_truesec


def get_sign(x):
    return copysign(1, x)


def get_rounded_sec(system):
    if system in invalid_systems:
        return None
    if system not in truesec:
        invalid_systems.append(system)
        return None
    truncated = str(truesec[system])[0:5]
    rounded = round(float(truncated), 1)
    return rounded


def get_sec_status(rounded_sec):
    if rounded_sec == None:
        return 'invalid'
    if get_sign(rounded_sec) == -1:
        return 'nullsec'
    elif rounded_sec >= 0.5:
        return 'hisec'
    else:
        return 'lowsec'


def parse_isk_total(text):
    if not text:
        return '0'
    text = text.replace(',', '')
    if text.isdigit():
        return text
    if text[-1] in ['k', 'kk', 'kkk', 'm', 'b', 't']:
        if '.' in text:
            try:
                num = float(text[:-1])
            except:
                return '0'
        else:
            try:
                num = int(text[:-1])
            except:
                return '0'
        mult = text[-1]
        if mult == 'k':
            return num * 1000
        if mult == 'kk' or mult == 'm':
            return num * 1000 * 1000
        if mult == 'kkk' or mult == 'b':
            return num * 1000 * 1000 * 1000
        if mult == 't':
            return num * 1000 * 1000 * 1000 * 1000
    else:
        if '.' in text:
            try:
                return float(text)
            except:
                return '0'
        return '0'


def prep_param(param, fuzzy=False):
    if not param:
        return None
    if ',' in param:
        param_list = [item.lower().strip(' ') for item in param.split(',')]
        return tuple(param_list)
    if fuzzy:
        param = '%' + param.strip(' ')
    return sub('\*', '%', param)


def gen_params(request_args):
    timestamp_start = date_to_timestamp(request_args.get('date_start'))
    timestamp_end = date_to_timestamp(request_args.get('date_end'), end=True)

    if timestamp_start and timestamp_end and timestamp_start > timestamp_end:
        timestamp_start, timestamp_end = None, None
    
    params = {
              'report_id': request_args.get('report_id'),
              'killer_corp': prep_param(request_args.get('killer_corp')),
              'killer_name': prep_param(request_args.get('killer_name'), fuzzy=True),
              'minimum_isk': parse_isk_total(request_args.get('isk')),
              'victim_ship_type': prep_param(request_args.get('victim_ship_type'), fuzzy=True),
              'victim_ship_category': prep_param(request_args.get('victim_ship_category')),
              'victim_name': prep_param(request_args.get('victim_name'), fuzzy=True),
              'victim_corp': prep_param(request_args.get('victim_corp')),
              'system': prep_param(request_args.get('system'), fuzzy=True),
              'constellation': prep_param(request_args.get('constellation'), fuzzy=True),
              'region': prep_param(request_args.get('region'), fuzzy=True),
              'victim_total_damage_received': request_args.get('victim_total_damage_received'),
              'max_total_participants': request_args.get('total_participants'),
              'killer_ship_type': prep_param(request_args.get('killer_ship_type'), fuzzy=True),
              'killer_ship_category': prep_param(request_args.get('killer_ship_category')),
              'timestamp': request_args.get('timestamp'),
              'timestamp_start': timestamp_start,
              'timestamp_end': timestamp_end
              }

    return params


def prep_select(param, value):
    if type(value) is tuple:
        return f'lower({param}) IN :{param}'
    else:
        return f'{param} LIKE :{param}'

def gen_select(start, end, params):
    select = []
    expand_params = []
    for param in params:
        if params[param]:
            if param == 'report_id':
                select.append('report_id = :report_id')
            elif param == 'minimum_isk':
                select.append('isk >= :minimum_isk')
            elif param == 'victim_total_damage_received':
                select.append('victim_total_damage_received >= :victim_total_damage_received')
            elif param == 'max_total_participants':
                select.append('total_participants <= :max_total_participants')
            elif param == 'timestamp_start':
                select.append('timestamp >= :timestamp_start')
            elif param == 'timestamp_end':
                select.append('timestamp <= :timestamp_end')
            else:
                if type(params[param]) is tuple:
                    expand_params.append(param)
                    select.append(f'lower({param}) IN :{param}')
                else:
                    select.append(f'{param} LIKE :{param}')

    select = ' AND '.join(select)
    query = text(' '.join([start, select, end]))

    for p in expand_params:
        query = query.bindparams(bindparam(p, expanding=True))

    return query


def snuggly_check_corp(corp):
    if not corp:
        return None
    param = {'corp': corp}
    corp_poz = db.session.execute(text('''
                                        SELECT killer_corp, sum(isk)
                                        FROM Killmails
                                        WHERE killer_corp = :corp
                                        GROUP BY killer_corp
                                        ORDER BY sum(isk)
                                       '''), param).fetchone()
    corp_neg = db.session.execute(text('''
                                        SELECT victim_corp, sum(isk)
                                        FROM Killmails
                                        WHERE victim_corp = :corp
                                        GROUP BY victim_corp
                                        ORDER BY sum(isk)
                                       '''), param).fetchone()

    poz = 0 if not corp_poz else corp_poz[1]
    neg = 0 if not corp_neg else corp_neg[1]

    snuggly = round(neg / (poz + neg), 3) if poz else 1

    return snuggly


def snuggly_check_pilot(pilot):
    if not pilot:
        return None
    param = {'pilot': pilot}
    pilot_poz = db.session.execute(text('''
                                        SELECT killer_name, sum(isk)
                                        FROM Killmails
                                        WHERE killer_name = :pilot
                                        GROUP BY killer_name
                                        ORDER BY sum(isk)
                                       '''), param).fetchone()
    pilot_neg = db.session.execute(text('''
                                        SELECT victim_name, sum(isk)
                                        FROM Killmails
                                        WHERE victim_name = :pilot
                                        GROUP BY victim_name
                                        ORDER BY sum(isk)
                                       '''), param).fetchone()

    poz = 0 if not pilot_poz else pilot_poz[1]
    neg = 0 if not pilot_neg else pilot_neg[1]

    snuggly = round(neg / (poz + neg), 3) if poz else 1

    return snuggly

def snuggly_string(snuggly):
    if snuggly == 0:
        stringout = '0'
    elif snuggly == 1.0:
        stringout = '100'
    elif type(snuggly) == float and (snuggly * 100).is_integer():
        stringout = str(int(snuggly * 100))
    else:
        stringout = str(round(snuggly * 100, 3))
    return stringout


snuggly_corp_memo = {}
def snuggly_string_corp(corp):
    if corp in snuggly_corp_memo:
        return snuggly_corp_memo[corp]
    snuggly_corp_memo[corp] = snuggly_string(snuggly_check_corp(corp))
    return snuggly_corp_memo[corp]


snuggly_pilot_memo = {}
def snuggly_string_pilot(pilot):
    if pilot in snuggly_pilot_memo:
        return snuggly_pilot_memo[pilot]
    snuggly_pilot_memo[pilot] = snuggly_string(snuggly_check_pilot(pilot))
    return snuggly_pilot_memo[pilot]
    

### filters

@app.template_filter('urlify')
def urlify(text):
    return text.replace('+', '%2B').replace('*', '%2A') if text else None


@app.template_filter('get_system_sec')
def get_system_sec(system):
    if system in sec_lookup:
        return sec_lookup[system]
    system_rounded = get_rounded_sec(system)
    star_security = get_sec_status(system_rounded)
    sec_lookup[system] = star_security
    return star_security


@app.template_filter('is_faction')
def is_faction(shipname):
    if not shipname:
        return False
    if shipname.lower() in ['garmur', 'orthrus', 'barghest',
                    'astero', 'stratios', 'nestor',
                    'succubus', 'phantasm', 'nightmare',
                    'worm', 'gila', 'rattlesnake',
                    'daredevil', 'vigilant', 'vindicator',
                    'dramiel', 'cynabal', 'machariel',
                    'cruor', 'ashimmu', 'bhaalgorn']:
        return True
    return False


@app.template_filter('is_faction_possible')
def is_faction_possible(shipclass):
    if not shipclass:
        return False
    if shipclass.lower() in ['frigate', 'cruiser', 'battleship']:
        return True
    return False


app.jinja_env.filters['urlify'] = urlify
app.jinja_env.filters['get_system_sec'] = get_system_sec
app.jinja_env.filters['is_faction'] = is_faction
app.jinja_env.filters['is_faction_possible'] = is_faction_possible


@app.before_first_request
def app_setup():
    print("increasing cache size")
    db.session.execute(text('PRAGMA cache_size=-200000'))
    global truesec
    truesec = parse_truesec_csv()
    global sec_lookup
    sec_lookup = {}
    global invalid_systems
    invalid_systems = []


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


### routes


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

    oldest_time = db.session.execute(text('''SELECT last_refreshed 
                                                  FROM Months
                                                  ORDER BY month ASC
                                                  LIMIT 1''')).all()[0][0]                                        

    update_seconds_old = (datetime.now(timezone.utc) - parser.isoparse(update_time)).total_seconds()
    update_minutes_old = int(divmod(update_seconds_old , 60)[0])

    oldest_seconds_old = (datetime.now(timezone.utc) - parser.isoparse(oldest_time)).total_seconds()
    oldest_hours_old = int(divmod(oldest_seconds_old , 3600)[0])

    killmails = latest.all()
    csv = make_csv(killmails)
    
    return render_template('index.html', kms=killmails, csv=csv, update_age_minutes=update_minutes_old, oldest_hours=oldest_hours_old, title="latest")


@app.route('/search', methods=['GET'])
def search():
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400
    
    params = gen_params(request.args)
    start = "SELECT * FROM Killmails WHERE"
    end = "ORDER BY isk DESC LIMIT 10000"
    query = gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

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
    start = "SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails WHERE"
    end = "AND isk > 0 GROUP BY killer_name ORDER BY SUM(isk) DESC LIMIT 1000"
    query = gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/leaderboard?', '')
    return render_template('leaderboard.html', title="killmail search", kms=killmails, url_params=url_params)


@app.route('/loserboard', methods=['GET'])
def loserboard():
    for arg in request.args:
        if arg not in valid_columns:
            return "Very bad request", 400

    params = gen_params(request.args)
    start = "SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails WHERE"
    end = "AND isk > 0 GROUP BY victim_name ORDER BY SUM(isk) DESC LIMIT 1000"
    query = gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/loserboard?', '')
    return render_template('loserboard.html', title="killmail search", kms=killmails, url_params=url_params)


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


@app.route('/solo')
def solo():
    return redirect("/leaderboard?total_participants=1", code=302)


@app.route('/api/snuggly/pilot/<pilot>')
def api_snuggly_pilot(pilot):
    return make_response(snuggly_string_pilot(pilot), 200)


@app.route('/api/snuggly/corp/<corp>')
def api_snuggly_corp(corp):
    return make_response(snuggly_string_corp(corp), 200)


app.register_blueprint(routes)

if __name__ == "__main__":
    app.run()

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)