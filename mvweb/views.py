from flask import Blueprint, render_template, request, redirect, send_file
from datetime import datetime, timezone
from sqlalchemy.sql import text
from db import db, get_valid_columns
from urllib.parse import unquote_plus
import util


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

    params = util.gen_params(request.args)
    params['limit'] = limit
    start = "SELECT * FROM Killmails WHERE"
    end = f"ORDER BY isk DESC LIMIT :limit"
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

    return render_template('search.html', title="killmail search", kms=killmails, isk_total=isk_total, timestamp_start=params['timestamp_start'], timestamp_end=params['timestamp_end'], limit=limit)


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


@routes.route('/systemboard', methods=['GET'])
def systemboard():
    for arg in request.args:
        if arg not in get_valid_columns():
            return "Very bad request", 400

    params = util.gen_params(request.args)
    start = "SELECT *, COUNT(report_id), SUM(ISK) FROM Killmails WHERE system NOT NULL AND"
    end = "AND isk > 0 GROUP BY system ORDER BY SUM(isk) DESC LIMIT 1000"
    query = util.gen_select(start, end, params)

    kms = db.session.execute(query, params=params)

    killmails = kms.all()
    url_params = request.full_path.replace('/systemboard?', '')
    return render_template('systemboard.html', title="killmail search", kms=killmails, url_params=url_params)


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


@routes.route('/spaceteam/')
def spaceteams():
    return render_template('spaceteam-index.html', title="spaceteams")


team_km_cache = {}


@routes.route('/spaceteam/stats/<sheet_id>')
def spaceteam_stats(sheet_id):
    metadata = util.spaceteam_get_metadata(sheet_id)
    events = util.spaceteam_get_events(sheet_id)
    meta_validation = util.spaceteam_validate_metadata(metadata)
    event_validation = util.spaceteam_validate_events(events)
    if not meta_validation and not event_validation:
        return redirect(f"/spaceteam/check/{sheet_id}", code=301)

    corps = util.spaceteam_get_corps(sheet_id)
    teams = util.spaceteam_get_teams(corps)
    alliances = util.spaceteam_get_alliances(corps)

    params = {
        'start_date': util.date_to_timestamp(metadata['start_date']),
        'end_date': util.date_to_timestamp(metadata['end_date']) if metadata['end_date'] else int(
            datetime.now(timezone.utc).timestamp())
    }

    kms = db.session.execute(text(f'''
                                    SELECT *
                                    FROM Killmails
                                    WHERE timestamp > :start_date AND timestamp < :end_date
                                    ORDER BY timestamp
    '''), params=params).fetchall()

    if sheet_id in team_km_cache:
        if util.get_now_stamp() - team_km_cache[sheet_id]['timestamp'] < 60 * 10:
            team_kms = team_km_cache[sheet_id]['cache']
            data_age = util.timestamp_minutes_old(
                team_km_cache[sheet_id]['timestamp'])
        else:
            team_kms = util.spaceteam_kms_to_teams(kms, corps, teams)
            team_km_cache[sheet_id] = {
                'timestamp': util.get_now_stamp(), 'cache': team_kms}
            data_age = 0
    else:
        team_kms = util.spaceteam_kms_to_teams(kms, corps, teams)
        team_km_cache[sheet_id] = {
            'timestamp': util.get_now_stamp(), 'cache': team_kms}
        data_age = 0
    team_stats = util.spaceteam_all_team_stats(team_kms)

    return render_template('spaceteam.html', title="spaceteams", metadata=metadata, team_kms=team_kms, data_age=data_age, team_stats=team_stats, teams=teams, alliances=alliances, subcaps=util.subcap_classes, caps=util.capital_classes, structures=util.spaceteam_structure_classes)


@routes.route('/spaceteam/check/<sheet_id>')
def checkteam(sheet_id):
    base_url = util.spaceteam_make_base_url(sheet_id)
    events_url = util.spaceteam_make_event_url(sheet_id)
    metadata = util.spaceteam_get_metadata(sheet_id)
    events = util.spaceteam_get_events(sheet_id)
    meta_validation = util.spaceteam_validate_metadata(metadata)
    event_validation = util.spaceteam_validate_events(events)
    corps = util.spaceteam_get_corps(sheet_id)
    teams = util.spaceteam_get_teams(corps)
    alliances = util.spaceteam_get_alliances(corps)
    corp_ranges = util.spaceteam_get_all_corp_ranges(corps)
    return render_template('checkteam.html', title="spaceteams", base_url=base_url, events_url=events_url, metadata=metadata,
                           meta_validation=meta_validation, event_validation=event_validation,
                           corps=corps, teams=teams, alliances=alliances, events=events, ranges=corp_ranges)


@routes.route('/timeline/pilot/<pilot>')
def timeline_pilot(pilot):
    return render_template('timeline.html', title="timeline", type="pilot", lookup=unquote_plus(pilot))


@routes.route('/timeline/corp/<corp>')
def timeline_corp(corp):
    return render_template('timeline.html', title="timeline", type="corp", lookup=corp)


@routes.route('/timeline/ship/<ship>')
def timeline_ship(ship):
    return render_template('timeline.html', title="timeline", type="ship", lookup=ship)


@routes.route('/timeline/shipsonly/pilot/<pilot>')
def timeline_pilot_shipsonly(pilot):
    return render_template('timeline.html', title="timeline", type="shipsonly/pilot", lookup=unquote_plus(pilot))


@routes.route('/timeline/shipsonly/corp/<corp>')
def timeline_corp_shipsonly(corp):
    return render_template('timeline.html', title="timeline", type="shipsonly/corp", lookup=corp)


@routes.route('/timeline/shipsonly/ship/<ship>')
def timeline_ship_shipsonly(ship):
    return render_template('timeline.html', title="timeline", type="shipsonly/ship", lookup=ship)


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


@routes.route('/corphist')
def corphist():
    months = util.get_all_months()

    return render_template('corpline.html', title="cool corps", topcorps=util.get_top_corps(20))


@routes.route('/heatmap')
def heatmap():
    return render_template('tsukimap.html', title="heatmap")


@routes.route('/corporation/<corp>')
def corp_page(corp):
    return render_template('corporation.html', title=f"corporation: {corp.upper()}", corp=corp)