from datetime import datetime, timezone
from dateutil import parser
from dateutil.relativedelta import relativedelta
from csv import writer, reader, DictReader
from re import sub
from math import copysign
from sqlalchemy.sql import bindparam, text
from os import path
from db import db
from requests import get
from collections import defaultdict
import io
import pandas
import json

basedir = path.abspath(path.dirname(__file__))


def date_to_timestamp(datestring, end=False):
    if not datestring:
        return None
    try:
        date_obj = parser.isoparse(datestring)
    except:
        print(f"[!] bad date: '{datestring}'")
        return None
    if end:
        timestamp = datetime.combine(
            date_obj, date_obj.max.time(), tzinfo=timezone.utc).timestamp()
    else:
        timestamp = datetime.combine(
            date_obj, date_obj.min.time(), tzinfo=timezone.utc).timestamp()
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
    with open(path.join(basedir, '../stars-all.csv')) as trueseccsv:
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
    param = sub('_', '\_', param)
    return sub('\*', '%', param)


def gen_params(request_args):
    timestamp_start = date_to_timestamp(request_args.get('date_start'))
    timestamp_end = date_to_timestamp(request_args.get('date_end'), end=True)

    if timestamp_start and timestamp_end and timestamp_start > timestamp_end:
        timestamp_start, timestamp_end = None, None

    params = {
        'report_id': request_args.get('report_id'),
        'killer_corp': prep_param(request_args.get('killer_corp')),
        'killer_name': prep_param(request_args.get('killer_name')),
        'minimum_isk': parse_isk_total(request_args.get('isk')),
        'victim_ship_type': prep_param(request_args.get('victim_ship_type'), fuzzy=True),
        'victim_ship_category': prep_param(request_args.get('victim_ship_category')),
        'victim_name': prep_param(request_args.get('victim_name')),
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
                select.append(
                    'victim_total_damage_received >= :victim_total_damage_received')
            elif param == 'max_total_participants':
                select.append('total_participants <= :max_total_participants')
            elif param == 'timestamp_start':
                select.append('timestamp >= :timestamp_start')
            elif param == 'timestamp_end':
                select.append('timestamp <= :timestamp_end')
            elif param == 'limit':
                continue
            else:
                if type(params[param]) is tuple:
                    expand_params.append(param)
                    select.append(f'lower({param}) IN :{param}')
                else:
                    select.append(f"{param} LIKE :{param} ESCAPE '\\'")

    select = ' AND '.join(select)
    query = text(' '.join([start, select, end]))

    for p in expand_params:
        query = query.bindparams(bindparam(p, expanding=True))

    return query


def snuggly_calc_corp(corp):
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


def snuggly_calc_pilot(pilot):
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


def stat_percent_string(snuggly):
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


def snuggly_lookup_corp(corp):
    # if corp in snuggly_corp_memo:
    #     return snuggly_corp_memo[corp]
    snuggly_corp_memo[corp] = stat_percent_string(snuggly_calc_corp(corp))
    return snuggly_corp_memo[corp]


snuggly_pilot_memo = {}


def snuggly_lookup_pilot(pilot):
    # if pilot in snuggly_pilot_memo:
    #     return snuggly_pilot_memo[pilot]
    snuggly_pilot_memo[pilot] = stat_percent_string(snuggly_calc_pilot(pilot))
    return snuggly_pilot_memo[pilot]


main_classes = ['Shuttle', 'Frigate', 'Destroyer', 'Cruiser', 'Battlecruiser', 'Battleship',
                'Carrier', 'Dreadnought', 'Freighter', 'Jump Freighter', 'Force Auxiliary',
                'Industrial Ship']
alt_classes = ['Structure', '-']
all_classes = main_classes + alt_classes


def get_alltime_class(ship_class):
    if ship_class == None:
        return '-'
    if ship_class in main_classes:
        return ship_class
    elif ship_class == 'Command Destroyer':
        return 'Destroyer'
    elif ship_class == 'Industrial Command Ship':
        return 'Industrial Ship'
    else:
        return 'Structure'


def get_db_age_latest():

    update_time = db.session.execute(text('''SELECT last_refreshed
                                                  FROM Months
                                                  ORDER BY month DESC
                                                  LIMIT 1''')).all()[0][0]
    update_seconds_old = (datetime.now(timezone.utc) -
                          parser.isoparse(update_time)).total_seconds()
    update_minutes_old = int(divmod(update_seconds_old, 60)[0])

    return update_minutes_old


def get_db_age_oldest():

    oldest_time = db.session.execute(text('''SELECT last_refreshed
                                                  FROM Months
                                                  ORDER BY month ASC
                                                  LIMIT 1''')).all()[0][0]
    oldest_seconds_old = (datetime.now(timezone.utc) -
                          parser.isoparse(oldest_time)).total_seconds()
    oldest_hours_old = int(divmod(oldest_seconds_old, 3600)[0])

    return oldest_hours_old


def get_today_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_all_months():
    return pandas.date_range(parser.isoparse('2020-08-13').replace(day=1), get_today_iso(), freq='MS').strftime("%Y-%m").tolist()


def get_month_start_stamp(month_string):
    start_datetime = parser.isoparse(month_string).replace(day=1)
    start_stamp = datetime.combine(
        start_datetime, start_datetime.min.time(), tzinfo=timezone.utc).timestamp()
    return start_stamp


def get_month_end_stamp(month_string):
    start_datetime = parser.isoparse(month_string).replace(day=1)
    end_datetime = (start_datetime + relativedelta(months=1))
    end_stamp = datetime.combine(
        end_datetime, end_datetime.min.time(), tzinfo=timezone.utc).timestamp()
    return end_stamp


def get_mode_columns(mode):
    if mode.lower() == 'corp':
        return 'killer_corp', 'victim_corp'
    elif mode.lower() == 'pilot':
        return 'killer_name', 'victim_name'
    elif mode.lower() == 'ship':
        return 'killer_ship_type', 'victim_ship_type'
    else:
        return False, False


def get_now_stamp():
    return int(datetime.now(timezone.utc).timestamp())


def spaceteam_make_base_url(sheet_id):
    return 'https://docs.google.com/spreadsheets/d/e/' + sheet_id + '/pub?output=csv'


spaceteam_metadata_cache = defaultdict(dict)


def spaceteam_get_metadata(sheet_id):
    if sheet_id in spaceteam_metadata_cache:
        # 10 minute cache time
        if get_now_stamp() - spaceteam_metadata_cache[sheet_id]['timestamp'] < 60 * 10:
            return spaceteam_metadata_cache[sheet_id]['metadata']
    base_url = spaceteam_make_base_url(sheet_id)
    metadata_url = base_url + '&gid=0'
    metadata_in = get(metadata_url).text.splitlines()[1:]
    metadata = {}
    metadata['conflict'] = None
    metadata['start_date'] = None
    metadata['end_date'] = None
    metadata['moderator'] = None
    metadata['teams'] = []
    for row in metadata_in:
        k, v = row.split(',')
        if k.lower() == 'conflict':
            metadata['conflict'] = v
        elif k.lower() == 'conflict_start':
            metadata['start_date'] = v
        elif k.lower() == 'conflict_end':
            metadata['end_date'] = v
        elif k.lower() == 'moderator':
            metadata['moderator'] = v
        elif k.lower() == 'team':
            metadata['teams'].append(v)

    spaceteam_metadata_cache[sheet_id] = {
        'timestamp': get_now_stamp(), 'metadata': metadata}
    return metadata


def spaceteam_validate_metadata(metadata):
    try:
        assert metadata['conflict'] != None
        assert metadata['start_date'] != None
        assert metadata['moderator'] != None
        assert len(metadata['teams']) > 0
        assert type(date_to_timestamp(metadata['start_date'])) == int
        if metadata['end_date']:
            assert type(date_to_timestamp(metadata['end_date'])) == int
            assert date_to_timestamp(metadata['end_date'], end=True) > date_to_timestamp(
                metadata['start_date'])
    except AssertionError:
        return False
    return True


def spaceteam_validate_events(events):
    for event in events:
        try:
            assert type(date_to_timestamp(event['date'])) == int
            assert len(event['corp']) > 0 and len(event['corp']) < 5
            assert len(event['team']) > 0
            assert event['event'].lower(
            ) == 'join' or event['event'].lower() == 'leave'
        except AssertionError:
            return False
    return True


def spaceteam_make_event_url(base_url):
    events_gid = '1577917373'
    return base_url + '&gid=' + events_gid


spaceteam_event_cache = defaultdict(dict)


def spaceteam_get_events(sheet_id):
    if sheet_id in spaceteam_event_cache:
        # 10 minute cache time
        if get_now_stamp() - spaceteam_event_cache[sheet_id]['timestamp'] < 60 * 10:
            return spaceteam_event_cache[sheet_id]['events']
    base_url = spaceteam_make_base_url(sheet_id)
    events = list(DictReader(io.StringIO(
        get(spaceteam_make_event_url(base_url)).text)))
    processed = []
    for e in events:
        end = True if e['event'].lower() == 'join' else False
        e['timestamp'] = date_to_timestamp(e['date'], end=end)
        processed.append(e)
    sort = sorted(processed, key=lambda d: d['timestamp'])
    spaceteam_event_cache[sheet_id] = {
        'timestamp': get_now_stamp(), 'events': sort}
    return sort


def spaceteam_get_corps(sheet_id):
    corps = {}
    events = spaceteam_get_events(sheet_id)

    for e in events:
        if e['event'].lower() == 'join':
            if e['corp'] not in corps:
                corps[e['corp'].upper()] = {'current_team': e['team'], 'current_alliance': e['alliance'], 'history': [
                    {'event': 'join', 'date': e['date'], 'team': e['team']}]}
            else:
                corps[e['corp']]['current_team'] = e['team']
                corps[e['corp']]['current_alliance'] = e['alliance']
                corps[e['corp']]['history'].append(
                    {'event': 'join', 'date': e['date'], 'team': e['team']})
        if e['event'].lower() == 'leave':
            if e['corp'] not in corps:
                continue
            else:
                corps[e['corp']]['current_team'] = None
                corps[e['corp']]['current_alliance'] = e['alliance']
                corps[e['corp']]['history'].append(
                    {'event': 'leave', 'date': e['date']})

    return corps


def spaceteam_get_teams(corps):
    teams = {}
    for corp in corps:
        team = corps[corp]['current_team']
        if corps[corp]['current_alliance'] == '':
            alliance = 'Naked'
        else:
            alliance = corps[corp]['current_alliance']
        if team not in teams:
            teams[team] = {'alliances': {alliance: [corp]}}
        else:
            if alliance not in teams[team]['alliances']:
                teams[team]['alliances'][alliance] = [corp]
            else:
                teams[team]['alliances'][alliance].append(corp)
    return teams


def spaceteam_get_alliances(corps):
    alliances = {}
    for corp in corps:
        if corps[corp]['current_alliance'] not in alliances:
            alliances[corps[corp]['current_alliance']] = [corp]
        else:
            alliances[corps[corp]['current_alliance']].append(corp)
    return alliances


def spaceteam_get_corp_range(hist):
    ranges = []
    last_join_time = None
    last_join_team = None
    for i, event in enumerate(hist):
        end = True if event['event'].lower() == 'leave' else False
        event_stamp = date_to_timestamp(event['date'], end=end)
        if event['event'].lower() == 'join':
            if i == len(hist) - 1:
                range = {'join': event_stamp,
                         'leave': None, 'team': event['team']}
                ranges.append(range)
            else:
                last_join_time = event_stamp
                last_join_team = event['team']
        if event['event'].lower() == 'leave':
            range = {'join': last_join_time,
                     'leave': event_stamp, 'team': last_join_team}
            ranges.append(range)
            last_join_time = None
            last_join_team = None

    return ranges


def spaceteam_get_all_corp_ranges(corps):
    all_ranges = {}
    for corp in corps:
        hist = corps[corp]['history']
        ranges = spaceteam_get_corp_range(hist)
        all_ranges[corp] = ranges
    return all_ranges


def spaceteam_get_team_membership(corp, timestamp, ranges):
    for range in ranges[corp]:
        if range['leave'] == None:
            leave = date_to_timestamp('2200-12-31', end=True)
        else:
            leave = range['leave']
        if timestamp > range['join'] and timestamp < leave:
            return range['team']
    return None


def spaceteam_kms_to_teams(kms, corps, teams):
    team_kms = {}
    for team in teams:
        if team:
            team_kms[team] = []
    corp_ranges = spaceteam_get_all_corp_ranges(corps)
    for km in kms:
        killer_corp = km._mapping['killer_corp']
        victim_corp = km._mapping['victim_corp']
        if killer_corp and victim_corp:
            if killer_corp in corps and victim_corp in corps:
                killer_team = spaceteam_get_team_membership(
                    killer_corp, km._mapping['timestamp'], corp_ranges)
                if killer_team:
                    victim_team = spaceteam_get_team_membership(
                        victim_corp, km._mapping['timestamp'], corp_ranges)
                    if killer_team and victim_team and killer_team != victim_team:
                        team_kms[killer_team].append(km)

    return team_kms


def spaceteam_team_stats(kms):
    stats = defaultdict(int)
    stats['isk'] = 0
    for km in kms:
        stats[km._mapping['victim_ship_category']
              ] += 1 if km._mapping['victim_ship_category'] else 0
        stats['isk'] += km._mapping['isk']
    return stats


def spaceteam_all_team_stats(team_kms):
    team_stats = {}
    for team in team_kms:
        if team:
            team_stats[team] = spaceteam_team_stats(team_kms[team])
    return team_stats


def timestamp_minutes_old(timestamp):
    seconds_old = get_now_stamp() - timestamp
    return int(divmod(seconds_old, 60)[0])


structure_classes = ['Capsuleer Outpost', 'Corporation Outpost I',
                     'Corporation Outpost II', 'Ansiblex Stargate', 'Analytical Computer',
                     'Anomaly Observation Array', 'Base Detection Array', 'Bounty Management Center',
                     'Cynosural Beacon Tower', 'Cynosural Jammer Tower', 'Insurance Office', 'Pirate Detection Array',
                     'Space Lab', 'Tax Center']
spaceteam_structure_classes = ['Citadel']
spaceteam_structure_classes += structure_classes
subcap_classes = ['Capsule', 'Shuttle', 'Frigate', 'Destroyer',
                  'Cruiser', 'Battlecruiser', 'Battleship', 'Industrial Ship']
capital_classes = ['Carrier', 'Dreadnought',  'Force Auxiliary', 'Freighter',
                   'Jump Freighter', 'Capital Industrial Ship', 'Versatile Assault Ship', 'Supercarrier']


def lowsec_calc_pilot(pilot):
    if not pilot:
        return None
    param = {'pilot': pilot}
    kills = db.session.execute(text('''
                                        SELECT killer_name, isk, system
                                        FROM Killmails
                                        WHERE killer_name = :pilot
                                       '''), param).fetchall()

    total_null = 0
    total_low = 0

    for kill in kills:
        if get_sec_status(get_rounded_sec(kill[2])) == 'lowsec':
            total_low += kill[1]
        else:
            total_null += kill[1]

    lowsec_rating = round(
        total_low / (total_null + total_low), 3) if total_null else 1

    return lowsec_rating


lowsec_pilot_memo = {}


def lowsec_lookup_pilot(pilot):
    if pilot in lowsec_pilot_memo:
        return lowsec_pilot_memo[pilot]
    lowsec_pilot_memo[pilot] = stat_percent_string(lowsec_calc_pilot(pilot))
    return lowsec_pilot_memo[pilot]


def lowsec_calc_corp(corp):
    if not corp:
        return None
    param = {'corp': corp}
    kills = db.session.execute(text('''
                                        SELECT killer_corp, isk, system
                                        FROM Killmails
                                        WHERE killer_corp = :corp
                                       '''), param).fetchall()

    total_null = 0
    total_low = 0

    for kill in kills:
        if get_sec_status(get_rounded_sec(kill[2])) == 'lowsec':
            total_low += kill[1]
        else:
            total_null += kill[1]

    lowsec_rating = round(
        total_low / (total_null + total_low), 3) if total_null else 1

    return lowsec_rating


lowsec_corp_memo = {}


def lowsec_lookup_corp(corp):
    if corp in lowsec_corp_memo:
        return lowsec_corp_memo[corp]
    lowsec_corp_memo[corp] = stat_percent_string(lowsec_calc_corp(corp))
    return lowsec_corp_memo[corp]


global truesec
truesec = parse_truesec_csv()
global sec_lookup
sec_lookup = {}
global invalid_systems
invalid_systems = []


def filter_valid_system(sys):
    if sys in truesec:
        return True
    else:
        return False


def map_all_kills():
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       ''')).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_date_kills(date_start, date_end):
    timestamp_start = date_to_timestamp(date_start)
    timestamp_end = date_to_timestamp(date_end, end=True)
    params = {'timestamp_start': timestamp_start,
              'timestamp_end': timestamp_end}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE timestamp >= :timestamp_start
                                        AND timestamp <= :timestamp_end
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), params).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_pilot_kills(pilot):
    param = {'pilot': pilot}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE killer_name = :pilot
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_corp_kills(corp):
    param = {'corp': corp}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE killer_corp = :corp
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_ship_kills(ship):
    param = {'ship': ship}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE killer_ship_type = :ship
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_pilot_deaths(pilot):
    param = {'pilot': pilot}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE victim_name = :pilot
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_corp_deaths(corp):
    param = {'corp': corp}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE victim_corp = :corp
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_ship_deaths(ship):
    param = {'ship': ship}
    query = db.session.execute(text('''
                                        SELECT system, sum(isk)
                                        FROM Killmails
                                        WHERE victim_ship_type = :ship
                                        GROUP BY system
                                        ORDER BY sum(isk) desc
                                       '''), param).fetchall()
    systems = {}
    for sys in query:
        if filter_valid_system(sys[0]):
            systems[sys[0]] = sys[1]
    return systems


def map_positivity_merge(kills, deaths):
    return {k: kills.get(k, 0) + (deaths.get(k, 0) * -1) for k in set(kills) | set(deaths)}


def get_top_corps(number):
    params = {'number': number}
    result = db.session.execute(text('''
                                        SELECT killer_corp, sum(isk)
                                        FROM Killmails
                                        GROUP BY killer_corp
                                        ORDER BY sum(isk) desc
                                        LIMIT :number
                                       '''), params).fetchall()
    corps = []
    for c in result:
        if c[0] is not None:
            corps.append(c[0])
    return corps

def round_if_float(number):
    if type(number) == float:
        return round(number)
    else:
        return number

def get_ship_avg(ship, months_ago):
    startstamp = (datetime.now(timezone.utc) - relativedelta(months=months_ago)).timestamp()
    params = {'ship': ship, 'startstamp': startstamp}
    recent_result = db.session.execute(text('''
                                        SELECT count(isk), avg(isk)
                                        FROM Killmails
                                        WHERE victim_ship_type = :ship
                                        AND timestamp >= :startstamp
                                       '''), params).fetchone()
    full_result = db.session.execute(text('''
                                        SELECT count(isk), avg(isk)
                                        FROM Killmails
                                        WHERE victim_ship_type = :ship
                                       '''), params).fetchone()

    return {'ship': ship, 'recent_count': recent_result[0], 'recent_avg': round_if_float(recent_result[1]),
            'total_count': full_result[0], 'full_avg': round_if_float(full_result[1])}


