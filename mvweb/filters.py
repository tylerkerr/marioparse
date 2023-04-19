import util
from re import sub


def register(jinja_env):
    jinja_env.filters['urlify'] = urlify
    jinja_env.filters['removeshipsonly'] = removeshipsonly
    jinja_env.filters['get_system_sec'] = get_system_sec
    jinja_env.filters['is_faction'] = is_faction
    jinja_env.filters['is_faction_possible'] = is_faction_possible
    jinja_env.filters['rewrite_limit'] = rewrite_limit


def urlify(text):
    return text.replace('+', '%2B').replace('*', '%2A') if text else None


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
                            'cruor', 'ashimmu', 'bhaalgorn']:
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