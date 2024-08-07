import util
from urllib.parse import quote_plus, unquote_plus
from re import sub


def register(jinja_env):
    jinja_env.filters['urlify'] = urlify
    jinja_env.filters['urldecode'] = urldecode
    jinja_env.filters['removeshipsonly'] = removeshipsonly
    jinja_env.filters['get_system_sec'] = get_system_sec
    jinja_env.filters['is_faction'] = is_faction
    jinja_env.filters['is_faction_possible'] = is_faction_possible
    jinja_env.filters['rewrite_limit'] = rewrite_limit
    jinja_env.filters['validate_event'] = validate_event
    jinja_env.filters['is_category_capital'] = is_category_capital
    jinja_env.filters['pluralize'] = pluralize
    jinja_env.filters['alphasort'] = alphasort
    jinja_env.filters['team_corp_list'] = team_corp_list
    jinja_env.filters['other_teams_corp_list'] = other_teams_corp_list
    jinja_env.filters['date_from_datestring'] = date_from_datestring


def urlify(text):
    return quote_plus(text)


def urldecode(text):
    return unquote_plus(text)


def removeshipsonly(text):
    return text.replace('shipsonly/', '') if text else None


def get_system_sec(system):
    if system in util.sec_lookup:
        return util.sec_lookup[system]
    system_rounded = util.get_rounded_sec(system)
    star_security = util.get_sec_status(system_rounded)
    util.sec_lookup[system] = star_security
    return star_security


def is_faction(shipname):
    if not shipname:
        return False
    if shipname.lower() in ['garmur', 'orthrus', 'barghest',
                            'astero', 'stratios', 'nestor',
                            'succubus', 'phantasm', 'nightmare',
                            'worm', 'gila', 'rattlesnake',
                            'daredevil', 'vigilant', 'vindicator',
                            'dramiel', 'cynabal', 'machariel',
                            'cruor', 'ashimmu', 'bhaalgorn',
                            'fiend', 'chameleon', 'saleon',
                            'adrestia']:
        return True
    return False


def is_faction_possible(shipclass):
    if not shipclass:
        return False
    if shipclass.lower() in ['frigate', 'cruiser', 'battleship']:
        return True
    return False


def rewrite_limit(url, new_limit):
    return sub(r'&?limit=\d+', '', url) + '&limit=' + str(new_limit)


def validate_event(event):
    try:
        assert type(util.date_to_timestamp(event['date'])) == int
        assert len(event['corp']) > 0 and len(event['corp']) < 5
        assert len(event['team']) > 0
        assert event['event'].lower() == 'join' or event['event'].lower() == 'leave'
    except AssertionError:
        return False
    return True


def is_category_capital(ship_category):
    if ship_category in util.capital_classes:
        return True
    else:
        return False


def pluralize(word, number):
    if number == 0 or number > 1:
        if word[-1] == 'y':
            word = word[:-1] + 'ie'
        return word + 's'
    else:
        return word


def alphasort(l):
    return sorted(l)


def team_corp_list(team):
    corps = []
    for alliance in team['alliances']:
        for corp in team['alliances'][alliance]:
            corps.append(corp)
    return ','.join(corps)


def other_teams_corp_list(teams, this_team):
    corps = []
    for team in teams:
        if team != this_team:
            for alliance in teams[team]['alliances']:
                for corp in teams[team]['alliances'][alliance]:
                    corps.append(corp)
    return ','.join(corps)



def date_from_datestring(datestring):
    return datestring.split(' ')[0]