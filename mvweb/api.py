from flask import Blueprint, make_response
from csv import DictWriter
from db import db
from sqlalchemy.sql import text
from datetime import datetime
import util
import json
import io

apiroutes = Blueprint('api', __name__)


@apiroutes.route('/api/snuggly/pilot/<pilot>')
def api_snuggly_pilot(pilot):
    snug = util.snuggly_lookup_pilot(pilot)
    # if float(snug) == 100:
    #     span = '<span class="hisec">'
    # elif 50 < float(snug) < 100:
    #     span = '<span class="lowsec">'
    # else:
    #     span = '<span class="nullsec">'
    resp = '<div>' + snug + "%</span> snuggly</div>"
    if snug != '100':
        lowsec = util.lowsec_lookup_pilot(pilot)
        # if float(lowsec) >= 50:
        #     span = '<span class="lowsec">'
        # else:
        #     span = '<span class="nullsec">'
        resp += '<div>' + lowsec + "%</span> lowsec</div>"
    return make_response(resp, 200)


@apiroutes.route('/api/rawsnug/pilot/<pilot>')
def api_rawsnug_pilot(pilot):
    snug = util.snuggly_lookup_pilot(pilot)
    return make_response(snug, 200)


@apiroutes.route('/api/snuggly/corp/<corp>')
def api_snuggly_corp(corp):
    snug = util.snuggly_lookup_corp(corp)
    resp = '<div>' + snug + "%</span> snuggly</div>"
    if snug != '100':
        lowsec = util.lowsec_lookup_corp(corp)
        resp += '<div>' + lowsec + "%</span> lowsec</div>"
    return make_response(resp, 200)


@apiroutes.route('/api/timeline/pilot/<pilot>')
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


@apiroutes.route('/api/timeline/corp/<corp>')
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


bombers = ('Purifier', 'Purifier II', 'Purifier III',
           'Manticore', 'Manticore II', 'Manticore III',
           'Nemesis', 'Nemesis II', 'Nemesis III',
           'Hound', 'Hound II', 'Hound III')


@apiroutes.route('/api/timeline/ship/<ship>')
def api_timeline_ship(ship):
    if ship.lower() == 'bombers':
        params = {'ship': bombers}
        ship_op = 'IN'
        ship_value = "('" + "','".join(bombers) + "')"
    else:
        params = {'ship': ship}
        ship_op = 'LIKE'
        ship_value = ':ship'
    kill_rows = db.session.execute(text(f'''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_ship_type {ship_op} {ship_value}
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text(f'''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_ship_type {ship_op} {ship_value}
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


@apiroutes.route('/api/timeline/shipsonly/ship/<ship>')
def api_timeline_shipsonly_ship(ship):
    if ship.lower() == 'bombers':
        params = {'ship': bombers}
        ship_op = 'IN'
        ship_value = "('" + "','".join(bombers) + "')"
    else:
        params = {'ship': ship}
        ship_op = 'LIKE'
        ship_value = ':ship'
    kill_rows = db.session.execute(text(f'''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE killer_ship_type {ship_op} {ship_value}
                                    ORDER BY timestamp
    '''), params=params)
    death_rows = db.session.execute(text(f'''
                                    SELECT isk, victim_ship_type, timestamp, image_url
                                    FROM Killmails
                                    WHERE victim_ship_type {ship_op} {ship_value}
                                    ORDER BY timestamp
    '''), params=params)
    kills = [tuple(row) for row in kill_rows]
    deaths = [(row[0] * -1, row[1], row[2], row[3]) for row in death_rows]
    merge = sorted(kills + deaths, key=lambda x: x[2])
    cur = 0
    dataset = []
    for kill in merge:
        if kill[1] in util.structure_classes:
            continue
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@apiroutes.route('/api/timeline/shipsonly/pilot/<pilot>')
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
        if kill[1] in util.structure_classes:
            continue
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@apiroutes.route('/api/timeline/shipsonly/corp/<corp>')
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
        if kill[1] in util.structure_classes:
            continue
        dataset.append({'date': int(kill[2]) * 1000, 'ship': kill[1],
                       'shipval': kill[0], 'isk': cur + kill[0], 'url': kill[3]})
        cur = cur + kill[0]
    result_json = json.dumps(dataset)
    return make_response(result_json, 200)


@apiroutes.route('/api/alltime')
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


@apiroutes.route('/api/alltime_ships')
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


@apiroutes.route('/api/alltime_ships_csv')
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


@apiroutes.route('/api/heatmap/all')
def api_heatmap_all():
    return make_response(util.map_all_kills(), 200)


@apiroutes.route('/api/heatmap/dates/<start>/<end>')
def api_heatmap_dates(start, end):
    return make_response(util.map_date_kills(start, end), 200)


@apiroutes.route('/api/heatmap/pilot/<pilot>/<mode>')
def api_heatmap_pilot(pilot, mode):
    if mode == 'kills':
        return make_response(util.map_pilot_kills(pilot), 200)
    elif mode == 'deaths':
        return make_response(util.map_pilot_deaths(pilot), 200)
    elif mode == 'positivity':
        return make_response(util.map_positivity_merge(util.map_pilot_kills(pilot), util.map_pilot_deaths(pilot)), 200)
    else:
        return "Very bad request", 400


@apiroutes.route('/api/heatmap/corp/<corp>/<mode>')
def api_heatmap_corp(corp, mode):
    if mode == 'kills':
        return make_response(util.map_corp_kills(corp), 200)
    elif mode == 'deaths':
        return make_response(util.map_corp_deaths(corp), 200)
    elif mode == 'positivity':
        return make_response(util.map_positivity_merge(util.map_corp_kills(corp), util.map_corp_deaths(corp)), 200)
    else:
        return "Very bad request", 400


@apiroutes.route('/api/heatmap/ship/<ship>/<mode>')
def api_heatmap_ship(ship, mode):
    if mode == 'kills':
        return make_response(util.map_ship_kills(ship), 200)
    elif mode == 'deaths':
        return make_response(util.map_ship_deaths(ship), 200)
    elif mode == 'positivity':
        return make_response(util.map_positivity_merge(util.map_ship_kills(ship), util.map_ship_deaths(ship)), 200)
    else:
        return "Very bad request", 400
