from homl import app, db


class UserDB(db.Model):
    __tablename__ = 'users'
    number = db.Column(db.String(40), primary_key=True, nullable=False, autoincrement=False)
    username = db.Column(db.String(15), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    bio = db.Column(db.String(100), nullable=False)
    story = db.Column(db.String(5000), nullable=True)


class StoryMatchDB(db.Model):
    __tablename__ = 'story_match'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user1_id = db.Column(db.String(40), nullable=False)
    user2_id = db.Column(db.String(40), nullable=False)
    day = db.Column(db.Date, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    long = db.Column(db.Float, nullable=False)


class LocationStorageDB(db.Model):
    __tablename__ = 'location_storage'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.String(40), db.ForeignKey('users.number'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    long = db.Column(db.Float, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
