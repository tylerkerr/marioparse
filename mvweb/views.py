from flask import Blueprint, render_template, request, redirect, send_file, make_response
from csv import DictWriter
from datetime import datetime
from datetime import datetime, timezone
from sqlalchemy.sql import text
from db import db, get_valid_columns
import util
import json
import io

routes = Blueprint('views', __name__)


@routes.route('/')
def index():
    latest = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    ORDER BY timestamp DESC
                                    LIMIT 50
                                  '''))

    killmails = latest.all()
    csv = util.make_csv(killmails)

    return render_template('index.html', kms=killmails, csv=csv, update_age_minutes=util.get_db_age_latest(), oldest_hours=util.get_db_age_oldest(), title="latest")


@routes.route('/top/day')
def top_day():
    now = int(datetime.now(timezone.utc).timestamp())
    one_day_ago = now - 24 * 60 * 60
    params = {'one_day_ago': one_day_ago}
    latest = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    WHERE timestamp > :one_day_ago
                                    ORDER BY isk DESC
                                    LIMIT 100
                                  '''), params)

    killmails = latest.all()
    if len(killmails) > 0:
        csv = util.make_csv(killmails)
    else:
        csv = None

    return render_template('top.html', period='day', kms=killmails, csv=csv, update_age_minutes=util.get_db_age_latest(), oldest_hours=util.get_db_age_oldest(), title="top daily")


@routes.route('/top/week')
def top_week():
    now = int(datetime.now(timezone.utc).timestamp())
    one_week_ago = now - 7 * 24 * 60 * 60
    params = {'one_week_ago': one_week_ago}
    latest = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    WHERE timestamp > :one_week_ago
                                    ORDER BY isk DESC
                                    LIMIT 100
                                  '''), params)

    killmails = latest.all()
    if len(killmails) > 0:
        csv = util.make_csv(killmails)
    else:
        csv = None

    return render_template('top.html', period='week', kms=killmails, csv=csv, update_age_minutes=util.get_db_age_latest(), oldest_hours=util.get_db_age_oldest(), title="top weekly")


@routes.route('/top/month')
def top_month():
    now = int(datetime.now(timezone.utc).timestamp())
    one_month_ago = now - 30 * 24 * 60 * 60
    params = {'one_month_ago': one_month_ago}
    latest = db.session.execute(text('''
                                    SELECT * FROM Killmails
                                    WHERE timestamp > :one_month_ago
                                    ORDER BY isk DESC
                                    LIMIT 100
                                  '''), params)

    killmails = latest.all()
    if len(killmails) > 0:
        csv = util.make_csv(killmails)
    else:
        csv = None

    return render_template('top.html', period='month', kms=killmails, csv=csv, update_age_minutes=util.get_db_age_latest(), oldest_hours=util.get_db_age_oldest(), title="top monthly")


@routes.route('/search', methods=['GET'])
def search():
    for arg in request.args:
        if arg not in get_valid_columns():
            return "Very bad request", 400

    limit_arg = request.args.get('limit')
    if limit_arg and limit_arg.isdigit():
        limit = limit_arg
    else:
        limit = 1000
    new_limit = 50000

    params = util.gen_params(request.args)
    start = "SELECT * FROM Killmails WHERE"
    end = f"ORDER BY isk DESC LIMIT {limit}"
    query = util.gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    if request.args.get("csv", default=False, type=bool):
        csv = util.make_csv(killmails)
        datestamp = datetime.now().strftime("%Y-%m-%d")
        filename = '&'.join([f"{key}={val}" for key, val in (
            request.args.items()) if key != 'csv']) + f'-{datestamp}.csv'
        return send_file(csv, download_name=filename, as_attachment=True)

    isk_total = sum(km._mapping['isk'] for km in killmails)

    return render_template('search.html', title="killmail search", kms=killmails, isk_total=isk_total, timestamp_start=params['timestamp_start'], timestamp_end=params['timestamp_end'], limit=limit, new_limit=new_limit)


@routes.route('/leaderboard', methods=['GET'])
def leaderboard():
    for arg in request.args:
        if arg not in get_valid_columns():
            return "Very bad request", 400

    params = util.gen_params(request.args)
    start = "SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails WHERE"
    end = "AND isk > 0 GROUP BY killer_name ORDER BY SUM(isk) DESC LIMIT 1000"
    query = util.gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/leaderboard?', '')
    return render_template('leaderboard.html', title="killmail search", kms=killmails, url_params=url_params)


@routes.route('/loserboard', methods=['GET'])
def loserboard():
    for arg in request.args:
        if arg not in get_valid_columns():
            return "Very bad request", 400

    params = util.gen_params(request.args)
    start = "SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails WHERE victim_name NOT NULL AND victim_name != '' AND victim_name != '[2' AND victim_name != '[7' AND"
    end = "AND isk > 0 GROUP BY victim_name ORDER BY SUM(isk) DESC LIMIT 1000"
    query = util.gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/loserboard?', '')
    return render_template('loserboard.html', title="killmail search", kms=killmails, url_params=url_params)


@routes.route('/positivity')
def positivity_redirect():
    return redirect("/positivity/corp", code=302)

@routes.route('/positivity/<mode>')
def positivity(mode):
    poz_col, neg_col = util.get_mode_columns(mode)
    if not poz_col:
        return "Very bad request", 400
    poz = db.session.execute(text(f'''
                                        SELECT {poz_col}, sum(isk)
                                        FROM Killmails
                                        WHERE {poz_col} NOT NULL AND {poz_col} != '' AND {poz_col} != '[2' AND {poz_col} != '[7'
                                        GROUP BY {poz_col}
                                        ORDER BY sum(isk)
    '''))
    neg = db.session.execute(text(f'''
                                        SELECT {neg_col}, sum(isk)
                                        FROM Killmails
                                        WHERE {neg_col} NOT NULL AND {neg_col} != '' AND {neg_col} != '[2' AND {neg_col} != '[7'
                                        GROUP BY {neg_col}
                                        ORDER BY sum(isk)
    '''))
    score = {}
    for entity in poz:
        score[entity[0]] = entity[1]
    for entity in neg:
        if not entity[0] in score:
            score[entity[0]] = entity[1] * -1
        else:
            score[entity[0]] = score[entity[0]] - entity[1]
    sorted_score = dict(
        sorted(score.items(), key=lambda item: item[1], reverse=True))
    return render_template('positivity.html', title="positivity", score=sorted_score, mode=mode, poz=poz_col, neg=neg_col)


@routes.route('/bullying')
def bullying_redirect():
    return redirect("/bullying/corp", code=302)

@routes.route('/bullying/<mode>')
def bullying(mode):
    poz_col, neg_col = util.get_mode_columns(mode)
    if not poz_col:
        return "Very bad request", 400
    bullies = db.session.execute(text(f'''
                                        SELECT {poz_col}, {neg_col}, sum(isk)
                                        FROM Killmails
                                        WHERE {poz_col} not null AND {neg_col} not null AND {poz_col} != '' AND {poz_col} != '[2' AND {poz_col} != '[7' AND {neg_col} != '' AND {neg_col} != '[2' AND {neg_col} != '[7'
                                        GROUP BY {poz_col}, {neg_col}
                                        ORDER BY sum(isk) desc
                                        LIMIT 500
    '''))
    return render_template('bullying.html', title="bullying olympics", bullies=bullies, mode=mode, poz=poz_col, neg=neg_col)


@routes.route('/timeline/pilot/<pilot>')
def timeline_pilot(pilot):
    return render_template('timeline.html', title="timeline", type="pilot", lookup=pilot)


@routes.route('/timeline/corp/<corp>')
def timeline_corp(corp):
    return render_template('timeline.html', title="timeline", type="corp", lookup=corp)


@routes.route('/timeline/shipsonly/pilot/<pilot>')
def timeline_pilot_shipsonly(pilot):
    return render_template('timeline.html', title="timeline", type="shipsonly/pilot", lookup=pilot)


@routes.route('/timeline/shipsonly/corp/<corp>')
def timeline_corp_shipsonly(corp):
    return render_template('timeline.html', title="timeline", type="shipsonly/corp", lookup=corp)


@routes.route('/alltime')
def alltime():
    return render_template('alltime.html', title="alltime")


@routes.route('/solo')
def solo():
    return redirect("/leaderboard?total_participants=1", code=302)


@routes.route('/destruction')
def destruction():
    months = util.get_all_months()
    results = []
    for month in months:
        params = {
            'month_start': util.get_month_start_stamp(month),
            'month_end': util.get_month_end_stamp(month)
        }
        row = db.session.execute(text('''
                                        SELECT count(report_id), sum(isk)
                                        FROM Killmails
                                        WHERE timestamp > :month_start AND timestamp < :month_end
    '''), params=params).fetchone()
        results.append((month,) + row._data)

    return render_template('destruction.html', title="destruction", months=results)


# api


@routes.route('/api/snuggly/pilot/<pilot>')
def api_snuggly_pilot(pilot):
    return make_response(util.snuggly_string_pilot(pilot), 200)


@routes.route('/api/snuggly/corp/<corp>')
def api_snuggly_corp(corp):
    return make_response(util.snuggly_string_corp(corp), 200)


@routes.route('/api/timeline/pilot/<pilot>')
def api_timeline_pilot(pilot):
    params = {'pilot': pilot}
    kill_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_name LIKE :pilot
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_name LIKE :pilot
                                    ORDER BY timestamp
    '''), params=params)
    kills = [tuple(row) for row in kill_rows]
    deaths = [(row[0] * -1, row[1], row[2], row[3]) for row in death_rows]
    merge = sorted(kills + deaths, key=lambda x: x[2])
    cur = 0
    dataset = []
    for kill in merge:
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@routes.route('/api/timeline/corp/<corp>')
def api_timeline_corp(corp):
    params = {'corp': corp}
    kill_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_corp LIKE :corp
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_corp LIKE :corp
                                    ORDER BY timestamp
    '''), params=params)
    kills = [tuple(row) for row in kill_rows]
    deaths = [(row[0] * -1, row[1], row[2], row[3]) for row in death_rows]
    merge = sorted(kills + deaths, key=lambda x: x[2])
    cur = 0
    dataset = []
    for kill in merge:
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


structure_classes = ['Capsuleer Outpost', 'Corporation Outpost I',
                     'Corporation Outpost II', 'Ansiblex Stargate', 'Analytical Computer',
                     'Anomaly Observation Array', 'Base Detection Array', 'Bounty Management Center',
                     'Cynosural Beacon Tower', 'Cynosural Jammer Tower', 'Insurance Office', 'Pirate Detection Array',
                     'Space Lab', 'Tax Center']


@routes.route('/api/timeline/shipsonly/pilot/<pilot>')
def api_timeline_shipsonly_pilot(pilot):
    params = {'pilot': pilot}
    kill_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_name LIKE :pilot
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_name LIKE :pilot
                                    ORDER BY timestamp
    '''), params=params)
    kills = [tuple(row) for row in kill_rows]
    deaths = [(row[0] * -1, row[1], row[2], row[3]) for row in death_rows]
    merge = sorted(kills + deaths, key=lambda x: x[2])
    cur = 0
    dataset = []
    for kill in merge:
        if kill[1] in structure_classes:
            continue
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@routes.route('/api/timeline/shipsonly/corp/<corp>')
def api_timeline_shipsonly_corp(corp):
    params = {'corp': corp}
    kill_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_corp LIKE :corp
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text('''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_corp LIKE :corp
                                    ORDER BY timestamp
    '''), params=params)
    kills = [tuple(row) for row in kill_rows]
    deaths = [(row[0] * -1, row[1], row[2], row[3]) for row in death_rows]
    merge = sorted(kills + deaths, key=lambda x: x[2])
    cur = 0
    dataset = []
    for kill in merge:
        if kill[1] in structure_classes:
            continue
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@routes.route('/api/alltime')
def api_alltime():
    kill_rows = db.session.execute(text('''
                                    SELECT isk, timestamp
                                    FROM Killmails
                                    ORDER BY timestamp
    '''))
    kills = kill_rows.all()
    kill_days = {}
    for row in kills:
        day = datetime.utcfromtimestamp(
            row._mapping['timestamp']).strftime("%Y-%m-%d")
        if day in kill_days:
            kill_days[day] = kill_days[day] + row._mapping['isk']
        else:
            kill_days[day] = row._mapping['isk']
    return make_response(json.dumps(kill_days), 200)


@routes.route('/api/alltime_ships')
def api_alltime_ships():
    kill_rows = db.session.execute(text('''
                                    SELECT isk, timestamp, victim_ship_category
                                    FROM Killmails
                                    ORDER BY timestamp
    '''))
    kills = kill_rows.all()
    kill_days = {}
    for row in kills:
        day = datetime.utcfromtimestamp(
            row._mapping['timestamp']).strftime("%Y-%m-%d")
        isk = row._mapping['isk']
        ship_class = util.get_alltime_class(
            row._mapping['victim_ship_category'])
        if day in kill_days:
            if ship_class in kill_days[day]:
                kill_days[day][ship_class] = kill_days[day][ship_class] + isk
            else:
                kill_days[day][ship_class] = isk
        else:
            kill_days[day] = {}
            kill_days[day][ship_class] = isk
    kills_flat = []
    for day in kill_days:
        flat = {}
        flat['day'] = day
        for ship_class in kill_days[day]:
            flat[ship_class] = kill_days[day][ship_class]
        for c in util.all_classes:
            if not c in flat:
                flat[c] = 0
        kills_flat.append(flat)
    return make_response(json.dumps(kills_flat), 200)


@routes.route('/api/alltime_ships_csv')
def api_alltime_ships_csv():
    kill_rows = db.session.execute(text('''
                                    SELECT isk, timestamp, victim_ship_category
                                    FROM Killmails
                                    ORDER BY timestamp
    '''))
    kills = kill_rows.all()
    kill_days = {}
    csv = io.StringIO()
    w = DictWriter(csv, fieldnames=util.all_classes)
    for row in kills:
        day = datetime.utcfromtimestamp(
            row._mapping['timestamp']).strftime("%Y-%m-%d")
        isk = row._mapping['isk']
        ship_class = util.get_alltime_class(
            row._mapping['victim_ship_category'])
        if day in kill_days:
            if ship_class in kill_days[day]:
                kill_days[day][ship_class] = kill_days[day][ship_class] + isk
            else:
                kill_days[day][ship_class] = isk
        else:
            kill_days[day] = {}
            kill_days[day][ship_class] = isk

    print(util.all_classes)
    csv = io.StringIO()
    w = DictWriter(csv, fieldnames=['day'] + util.all_classes)
    w.writeheader()
    for day in kill_days:
        row = kill_days[day]
        row['day'] = day
        for c in util.all_classes:
            if not c in row:
                row[c] = 0
        w.writerow(row)

    return make_response(csv.getvalue(), 200)
