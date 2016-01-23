#!venv/bin/python
from flask import request, jsonify, url_for, render_template
from homl import app, db, auth
from models import *
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
import itertools


@app.route('/')
def index():
    return jsonify({'Fuck you': 'Fuck you'})


@app.route('/users', methods=['GET','POST'])
def users():
    if request.method == 'GET':
        users = UserDB.query.all()
        json_users = map(get_user_json, users)
        return jsonify(users=json_users)
    if request.method == 'POST':
        number = request.json.get('number')
        age = request.json.get('age')
        gender = request.json.get('gender')
        bio = request.json.get('bio')
        story = request.json.get('story')
        if number is None:
            return jsonify({'message': 'Number is missing'})
        user = UserDB.query.filter_by(number=number).first()
        if user is None: # Create new user
            if age is None: return jsonify({'error': 'Age is missing'});
            if gender is None: return jsonify({'error': 'Gender is missing'});
            if gender not in ['M', 'F']: return jsonify({'error': 'M/F?'});
            if bio is None: return jsonify({'error': 'Bio is missing'});
            user = UserDB(number=number, gender=gender,
                          age=age, bio=bio, story=story)
            db.session.add(user)
            db.session.commit()
            return jsonify({'message': 'Success'})
        else: # Update user info
            if age is not None: user.age = age;
            if gender is not None: user.gender = gender;
            if bio is not None: user.bio = bio;
            if story is not None: user.story = story;
            db.session.commit()
            return jsonify({'message': 'Success'})
    return jsonify({'error': 'Bad request'})


# Dump story matches
@app.route('/match', methods=['GET'])
def matches():
    if request.method == 'GET':
        matches = StoryMatchDB.query.all()
        json_matches = map(get_match_json, matches)
        return jsonify(matches=json_matches)
    return jsonify({'error': 'Bad request'})


# Dump story matches for a particular person
@app.route('/match/<number>', methods=['GET'])
def match(number):
    if request.method == 'GET':
        matches = StoryMatchDB.query.filter((StoryMatchDB.user1_id==number) | (StoryMatchDB.user2_id==number)).all()
        if not matches:
            return jsonify({'error': 'User does not exist'})
        json_matches = map(get_match_json, matches)
        return jsonify(matches=json_matches)
    return jsonify({'error': 'Bad request'})


# Location Storage. Posts into StoryMatch upon match lookups.
@app.route('/locations', methods=['GET','POST'])
def locations():
    if request.method == 'GET':
        locations = LocationStorageDB.query.all()
        json_locations = map(get_location_json, locations)
        return jsonify(locations=json_locations)
    if request.method == 'POST':
        user_id = request.json.get('user_id')
        lat = float(request.json.get('lat'))
        long = float(request.json.get('long'))
        time = datetime.now()

        # Add location to storage
        location = LocationStorageDB(user_id=user_id, lat=lat, long=long, time=time)
        db.session.add(location)
        db.session.commit()

        # Check all stored locations for matches. Post to story match when loc/time match
        ten_min_ago = time - timedelta(minutes=10)
        #locations_ten_min_ago = LocationStorageDB.query.filter_by(time >= ten_min_ago).all()
        locations = LocationStorageDB.query.all()
        locations_ten_min_ago = []
        for location in locations:
            if location.time > ten_min_ago:
                locations_ten_min_ago.append(location)

        for location in locations_ten_min_ago:
            distance = haversine(lat, long, location.lat, location.long)
            if distance < 1: # 1 kilometer radius
                # Post to story match db
                avg_lat = (lat+location.lat)/2
                avg_long = (long+location.long)/2
                match = StoryMatchDB(user1_id=user_id, user2_id=location.user_id,
                                     lat=avg_lat, long=avg_long, day=time.date())
                if match.user1_id != match.user2_id:
                    print match.user1_id, match.user2_id
                    matches = StoryMatchDB.query.filter(
                        (StoryMatchDB.user1_id==match.user1_id \
                            and StoryMatchDB.user2_id==match.user2_id \
                            and day > time.date() - timedelta(days=1)) | \
                        (StoryMatchDB.user2_id==match.user1_id \
                            and StoryMatchDB.user1_id==match.user2_id \
                            and day > time.date() - timedelta(days=1))).all()
                    if not matches:
                        db.session.add(match)

        # Save and return
        db.session.commit()
        return jsonify({'message': 'Success'})

    return jsonify({'error': 'Bad request'})


def get_user_json(user):
    return {'number': user.number,
            'age': user.age,
            'gender': user.gender,
            'bio': user.bio,
            'story': user.story }


def get_match_json(match):
    return {'id': match.id,
            'user1_id': match.user1_id,
            'user2_id': match.user2_id,
            'day': str(match.day),
            'lat': match.lat,
            'long': match.long }


def get_location_json(location):
    return {'id': location.id,
            'user_id': location.user_id,
            'lat': location.lat,
            'long': location.long,
            'time': str(location.time) }


# Calculate the great circle distance b/w two lat long points
def haversine(lat1, long1, lat2, long2):
    lat1, long1, lat2, long2 = map(radians, [lat1, long1, lat2, long2])
    dlong = long2 - long1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlong/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km
