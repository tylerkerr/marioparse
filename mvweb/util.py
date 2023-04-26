from datetime import datetime, timezone
from dateutil import parser
from dateutil.relativedelta import relativedelta
from csv import writer, reader
from re import sub
from math import copysign
from sqlalchemy.sql import bindparam, text
from os import path
from db import db
import io
import pandas

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


global truesec
truesec = parse_truesec_csv()
global sec_lookup
sec_lookup = {}
global invalid_systems
invalid_systems = []
