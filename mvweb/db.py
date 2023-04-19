from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

db = SQLAlchemy()

def get_valid_columns():
    valid_columns = [c[1] for c in db.session.execute(text('pragma table_info(Killmails)'))]
    valid_columns.append('date_start')
    valid_columns.append('date_end')
    valid_columns.append('csv')
    valid_columns.append('limit')
    return valid_columns

class Killmails(db.Model):
    id = db.Column(db.String, primary_key=True, nullable=False, unique=True)
    report_id = db.Column(db.Integer, nullable=False)
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
    killer_ship_category = db.Column(db.String)
    timestamp = db.Column(db.Integer)

    def __repr__(self):
        return f'<Killmail {self.report_id}>'
