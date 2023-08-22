import sqlite3
import os
import json
import pandas
import sys
import requests
from requests import get
from datetime import datetime, timezone
from dateutil import parser
from dateutil.relativedelta import relativedelta
from time import sleep
from re import search, sub
from urllib import parse


'''
sample killmail object:
{
  "id": "1eda1cae-b0fd-6ace-ad38-7fc908788205",
  "report_id": 8108929,
  "killer_corp": "SHIE",
  "killer_name": "Agnes Milfstein",
  "isk": 20261432,
  "date_killed": "2023-02-01 00:34:02",
  "image_url": "https://echoes.mobi/killmails/8108929.png",
  "victim_ship_type": "Coercer Interdictor",
  "victim_ship_category": "Destroyer",
  "external_provider": null,
  "victim_name": "CyberJinn",
  "victim_corp": "SELF",
  "system": "VFK-IV",
  "constellation": "VW7-YN",
  "region": "Deklein",
  "victim_total_damage_received": 3809,
  "total_participants": 6,
  "killer_ship_type": "Tempest Striker",
  "killer_ship_category": "Battleship"
}
'''

# constants

this_path = os.path.dirname(os.path.abspath(__file__))
db_filename = 'km.db'
db_name = this_path + '/' + db_filename
baseurl = 'https://echoes.mobi/killboard/export'
headers = {
    'User-Agent': 'honk-mariobot-parse/0.1 (bearand@discord)'
}

launch_date = "2020-08-13"

with open(this_path + '/ignore.json') as ignorejson:
    ignore_kms = json.load(ignorejson)


with open(this_path + '/webhooks.json') as webhooksjson:
    webhooks = json.load(webhooksjson)


# database setup

def db_init(db_name):
    global conn
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    global c
    c = conn.cursor()


def db_open(db_name):
    if os.path.exists(db_name):
        db_init(db_name)
        print("[+] db connection established")
    else:
        db_init(db_name)
        print("[-] initializing database")
        create_tables(db_name)
        print('[+] db initialized')


def create_tables(db_name):
    c.execute('DROP TABLE IF EXISTS "Killmails"')
    c.execute('DROP TABLE IF EXISTS "Status"')
    c.execute('DROP TABLE IF EXISTS "Months"')
    c.executescript('''
    CREATE TABLE "Killmails" (
	"id"	                        TEXT NOT NULL PRIMARY KEY UNIQUE,
	"report_id"	                    INTEGER NOT NULL,
    "killer_corp"	                TEXT,
    "killer_name"                   TEXT NOT NULL,
    "isk"                           INTEGER NOT NULL,
    "date_killed"                   TEXT NOT NULL,
    "image_url"                     TEXT NOT NULL,
    "victim_ship_type"              TEXT,
    "victim_ship_category"          TEXT,
    "external_provider"             TEXT,
    "victim_name"                   TEXT,
    "victim_corp"                   TEXT,
    "system"                        TEXT,
    "constellation"                 TEXT,
    "region"                        TEXT,
    "victim_total_damage_received"  INTEGER,
    "total_participants"            INTEGER,
    "killer_ship_type"              TEXT,
    "killer_ship_category"          TEXT,
    "timestamp"                     INTEGER
    );
    CREATE INDEX IF NOT EXISTS "IX_ISK" ON "Killmails" (
	"isk"
    );
    CREATE INDEX IF NOT EXISTS "IX_TotalDamage" ON "Killmails" (
	"victim_total_damage_received"
    );
    CREATE INDEX IF NOT EXISTS "IX_TotalParticipants" ON "Killmails" (
	"total_participants"
    );
    CREATE INDEX IF NOT EXISTS "IX_Timestamp" ON "Killmails" (
    "timestamp"
    );
    CREATE INDEX IF NOT EXISTS "IX_RecordID" ON "Killmails" (
    "record_id"
    );
    ''')

    c.execute('''
    CREATE TABLE "Status" (
    "last_refresh_time"     TEXT NOT NULL
    );
    ''')

    c.execute('''
    CREATE TABLE "Months" (
    "month"             TEXT NOT NULL PRIMARY KEY UNIQUE,
    "last_refreshed"    TEXT NOT NULL
    );
    ''')

    c.execute('''
    CREATE TABLE "Discorded" (
    "report_id"     INTEGER NOT NULL PRIMARY KEY UNIQUE
    );
    ''')

    conn.commit()


# date stuff


def nowstamp():
    return int(datetime.now().timestamp())


def is_this_month(month_iso):
    if month_iso == get_this_month():
        return True
    return False


def is_month_current(month_iso):
    print(f"[-] checking if month {month_iso} is current")
    result = check_month_status(month_iso)
    if not result:
        return False
    status = parser.isoparse(result)
    now = datetime.now(timezone.utc)
    if not status:
        print(f"[-] no data for month {month_iso}")
        return False
    difference = now - status
    data_age_hours = (difference.seconds / 60 / 60) + (difference.days * 24)
    if is_this_month(month_iso):
        limit = 0.5
    else:
        limit = 48
    if data_age_hours <= limit:
        print(f"[+] month {month_iso} is {data_age_hours} hours old, current")
        return True
    print(f"[+] month {month_iso} is {data_age_hours} hours old, too old")
    return False


def get_today_american():
    # american format
    return datetime.now(timezone.utc).strftime("%m-%d-%Y")


def get_today_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_this_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_all_months():
    return pandas.date_range(parser.isoparse(launch_date).replace(day=1), get_today_iso(), freq='MS').strftime("%Y-%m").tolist()


# queries


def query(query_text, args=(), one=False):
    cursor = conn.execute(query_text, args)
    results = cursor.fetchall()
    cursor.close()
    return (results[0] if results else None) if one else results


def get_report_id(report_id):
    c.execute(f'SELECT * FROM Killmails WHERE report_id={report_id}')
    return dict(c.fetchone())


def check_month_status(month_iso):
    c.execute(f'SELECT * FROM Months WHERE month="{month_iso}"')
    fetch = c.fetchone()
    if fetch:
        result = fetch[1]
        print(f"[-] the result of checking month {month_iso} was {result}")
        return result
    else:
        return None


def update_month_status(month):
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        'REPLACE INTO Months (month, last_refreshed) VALUES (?, ?)', (month, now))
    print(f"[+] updated month {month} with last_refreshed of {now}")
    conn.commit()


def cull_ignored(km_dict):
    clean = []
    for km in km_dict:
        if str(km['report_id']) not in ignore_kms:
            clean.append(km)
    return clean


def write_km_dict(km_dict):
    c.executemany('''
                INSERT OR REPLACE INTO "Killmails"
                (id, report_id, killer_corp, killer_name, isk, date_killed,
                 image_url, victim_ship_type, victim_ship_category, external_provider,
                 victim_name, victim_corp, system, constellation, region,
                 victim_total_damage_received, total_participants, killer_ship_type, 
                 killer_ship_category, timestamp)
                VALUES
                (:id, :report_id, :killer_corp, :killer_name, :isk, :date_killed,
                 :image_url, :victim_ship_type, :victim_ship_category, :external_provider,
                 :victim_name, :victim_corp, :system, :constellation, :region,
                 :victim_total_damage_received, :total_participants, :killer_ship_type, 
                 :killer_ship_category, :timestamp)
              ''', km_dict)
    conn.commit()


def update_discorded(report_id):
    c.execute('''
                 INSERT INTO "Discorded" VALUES (?)
              ''', (report_id,))
    conn.commit()


def check_if_discorded(report_id):
    c.execute('''
                 SELECT report_id from "Discorded" where report_id = ?
                ''', (report_id,))
    fetch = c.fetchone()
    if fetch:
        return True
    else:
        return False

# scraping


def download_export(start, end):
    url = f"{baseurl}/{start}/{end}"
    response = get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        return False


def download_kills(start_date, end_date):
    km_json = json.loads(download_export(start_date, end_date))
    print(f"[+] got month {month} with {len(km_json)} killmails")
    stamped_kms = []
    for km in km_json:
        if km['external_provider'] == 'auxilus' and km['victim_corp'] == None and km['victim_name']:
            victim_corp = search(r'\[[A-Z0-9]{1,4}\] ', km['victim_name'])
            if victim_corp:
                km['victim_corp'] = victim_corp[0][1:len(victim_corp[0])-2]
                km['victim_name'] = km['victim_name'][len(victim_corp[0]):]

        if km['killer_corp'] and (len(str(km['killer_corp'])) > 4 or ']' in str(km['killer_corp'])):
            if ']' in str(km['killer_corp']):
                problem = search(r'\].*', str(km['killer_corp']))[0]
                km['killer_corp'] = km['killer_corp'][:len(
                    km['killer_corp']) - len(problem)]
            if len(km['killer_corp']) > 4:
                km['killer_corp'] = km['killer_corp'][:4]

        if km['victim_corp'] and (len(str(km['victim_corp'])) > 4 or ']' in str(km['victim_corp'])):
            fixed = sub(r'[^a-zA-Z0-9]', '', str(km['victim_corp']))
            if len(fixed) > 4:
                if fixed[0] == 'I':
                    fixed = fixed[1:]
                else:
                    fixed = fixed[:4]
            km['victim_corp'] = fixed

        timestamp = int(parser.isoparse(km['date_killed']).timestamp())
        # discard killmails that occur over 6 hours in the future
        if timestamp > (nowstamp() + (60 * 60 * 6)):
            continue
        # test server killmails: id < 10k and timestamp after jan 1 2022
        if km['report_id'] == None or km['report_id'] < 10000 and timestamp > 1640995200:
            continue
        km['timestamp'] = timestamp
        stamped_kms.append(km)
    return stamped_kms


def format_msg(km):
    return f'[{km["killer_corp"] if km["killer_corp"] else ""}] {km["killer_name"]} killed {km["victim_name"]}\'s {km["victim_ship_type"]} worth {km["isk"]:,} isk'


def send_chat(km, webhook):
    killer_snug = get(f'https://marioview.honk.click/api/rawsnug/pilot/{km["killer_name"]}').text
    victim_snug = get(f'https://marioview.honk.click/api/rawsnug/pilot/{km["victim_name"]}').text
    data = {"content": format_msg(km),
            "username": 'Marioview',
            "avatar_url": 'https://marioview.honk.click/static/img/logo-32px.png',
            "embeds": [{
                "color": 14177041,
                "image": {
                    "url": km['image_url']
                }
            },
            {
                "color": 14177041,
                "description": f"[[km on mobi](https://echoes.mobi/killboard/view/killmail/{km['id']})] [[killer stats ⟨{killer_snug}% snuggly⟩]({'https://marioview.honk.click/search?killer_name=' + parse.quote(km['killer_name'])})] [[victim stats ⟨{victim_snug}% snuggly⟩]({'https://marioview.honk.click/search?victim_name=' + parse.quote(km['victim_name'])})]"
            }]
            }
    response = requests.post(webhook, json=data)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print("[!] HTTP error follows:")
        print(err)
        print("[!] failed message:", 'Marioview' + ': ' + data['content'])


if __name__ == "__main__":
    db_open(db_name)

    km_count = query('select count(distinct id) from killmails;', one=True)
    print(f"[-] db has {km_count[0]} killmails")

    all_months = get_all_months()

    if sys.argv[1] == 'all' or len(sys.argv) == 1:
        for month in get_all_months():
            if not is_month_current(month):
                print(f"[-] downloading month {month}")
                start_datetime = parser.isoparse(month).replace(day=1)
                start_date = start_datetime.strftime("%m-%d-%Y")
                end_datetime = (start_datetime + relativedelta(months=1))
                end_date = end_datetime.strftime("%m-%d-%Y")
                month_json = download_kills(start_date, end_date)
                write_km_dict(cull_ignored(month_json))
                update_month_status(month)
                sleep(3)  # be nice to mario
            else:
                print(f"[-] skipping month {month}, already have it")
    elif sys.argv[1] == 'month':
        month = get_this_month()
        start_datetime = parser.isoparse(month).replace(day=1)
        start_date = start_datetime.strftime("%m-%d-%Y")
        end_datetime = (start_datetime + relativedelta(months=1))
        end_date = end_datetime.strftime("%m-%d-%Y")
        print(f"[-] downloading month {month}")
        month_json = download_kills(start_date, end_date)
        write_km_dict(cull_ignored(month_json))
        update_month_status(month)
    elif sys.argv[1] == 'day':
        month = get_this_month()
        day = '08-21-2023'
        # day = get_today_american()
        print(f"[-] downloading day {day}")
        day_json = download_kills(day, day)
        write_km_dict(day_json)
        update_month_status(month)
        km_count = 0
        for km in day_json:
            if km['isk'] >= 9000000000 and km['total_participants'] == 1 or km['isk'] >= 15000000000:
                if not check_if_discorded(km['report_id']):
                    update_discorded(km['report_id'])
                    print(f'[-] discord blasting {km["report_id"]}')
                    for hook in webhooks:
                        send_chat(km, hook)
                    km_count += 1
                    sleep(km_count)

    c.close()
    conn.close()
