#!venv/bin/python
from flask import request, jsonify, url_for, render_template
from homl import app, db, auth
from models import *
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
import itertools
import urllib
import json


@app.route('/')
def index():
    return jsonify({'PSA': 'I love League of Legends!!!'})


@app.route('/users', methods=['GET','POST'])
def users():
    if request.method == 'GET':
        users = UserDB.query.all()
        json_users = map(get_user_json, users)
        return jsonify(users=json_users)
    if request.method == 'POST':
        number = request.json.get('number')
        username = request.json.get('username')
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
            if gender not in ['M', 'F', 'O']: return jsonify({'error': 'M/F/O?'});
            if bio is None: return jsonify({'error': 'Bio is missing'});
            user = UserDB(number=number, gender=gender, age=age,
                          username=username, bio=bio, story=story)
            db.session.add(user)
            db.session.commit()
            return jsonify({'message': 'Success'})
        else: # Update user info
            if age is not None: user.age = age;
            if username is not None: user.username = username;
            if gender is not None: user.gender = gender;
            if bio is not None: user.bio = bio;
            if story is not None: user.story = story;
            db.session.commit()
            return jsonify({'message': 'Success'})
    return jsonify({'error': 'Bad request'})


# Dump story matches
@app.route('/crime', methods=['GET'])
def crime():
    if request.method == 'GET':
        #matches = StoryMatchDB.query.all()
        #json_matches = map(get_match_json, matches)
        #return jsonify(matches=json_matches)

        # Return # of crimes in a 1km radius
        crime = {}
        url = 'https://www.opendataphilly.org/api/action/datastore_search?resource_id=3e00a40d-8444-418c-b3a6-bef5524b90a2&limit=1000'
        f = urllib.urlopen(url)
        results = json.loads(f.read())
        results = results["result"]["records"]

        lat = 40.025283
        long = -75.221278

        for x in results:
            lat2 = x["POINT_Y"]
            long2 = x["POINT_X"]
            if lat2 is None or long2 is None:
                continue # idiots
            lat2 = float(lat2)
            long2 = float(long2)
            distance = haversine(lat, long, lat2, long2)
            print distance
            if distance < 1:
                if x["TEXT_GENERAL_CODE"] in crime.keys():
                    crime[x["TEXT_GENERAL_CODE"]] += 1
                else:
                    crime[x["TEXT_GENERAL_CODE"]] = 1

        #crime = sorted(crime.items(), key=lambda x:x[1], reverse=True)

        return jsonify(results=crime, sum=sum(crime.itervalues()))

    return jsonify({'error': 'Bad request'})


# Dump story matches for a particular person.
# Optional argument date in month-day-year gives all matches for a given day.
# Optional argument dates (any value) gives all possible dates to scroll through
@app.route('/match/<number>', methods=['GET'])
def match(number):
    if request.method == 'GET':
        date = request.args.get("date")
        dates = request.args.get("dates")
        if dates is not None:
            dates = db.session.execute('SELECT DISTINCT day FROM story_match WHERE user2_id=\''+number+'\' OR user1_id=\''+number+'\'')
            dates_json = map(get_date_json, dates)
            return jsonify(dates=dates_json)
        if date is not None:
            date = datetime.strptime(date, '%m-%d-%Y').date()
            matches = StoryMatchDB.query.filter(((StoryMatchDB.user1_id==number) | (StoryMatchDB.user2_id==number)) & (StoryMatchDB.day==date)).order_by(StoryMatchDB.day).all()
        else:
            matches = StoryMatchDB.query.filter((StoryMatchDB.user1_id==number) | (StoryMatchDB.user2_id==number)).order_by(StoryMatchDB.day).all()
        if not matches:
            return jsonify({'error': 'No matches exist'})
        json_matches = []
        for match in matches:
            json_matches.append(get_specific_match_json(match, number))
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
                    matches = db.session.query(StoryMatchDB).filter(
                            StoryMatchDB.user1_id==match.user1_id, \
                            StoryMatchDB.user2_id==match.user2_id, \
                            StoryMatchDB.day>time.date()-timedelta(days=1))
                    matches2 = db.session.query(StoryMatchDB).filter(
                            StoryMatchDB.user2_id==match.user1_id, \
                            StoryMatchDB.user1_id==match.user2_id, \
                            StoryMatchDB.day>time.date()-timedelta(days=1))
                    if matches.first() is None and matches2.first() is None:
                        db.session.add(match)

        # Save and return
        db.session.commit()

        # Return # of crimes in a 1km radius
        crime = {}
        url = 'https://www.opendataphilly.org/api/action/datastore_search?resource_id=3e00a40d-8444-418c-b3a6-bef5524b90a2&limit=1000'
        f = urllib.urlopen(url)
        results = json.loads(f.read())
        results = results["result"]["records"]

        for x in results:
            lat2 = x["POINT_Y"]
            long2 = x["POINT_X"]
            if lat2 is None or long2 is None:
                continue # idiots
            distance = haversine(lat, long, float(lat2), float(long2))
            #print distance
            if distance > 1:
                continue
            if x["TEXT_GENERAL_CODE"] in crime.keys():
                crime[x["TEXT_GENERAL_CODE"]] += 1
            else:
                crime[x["TEXT_GENERAL_CODE"]] = 1

        return jsonify(results=crime, sum=sum(crime.itervalues()))

    return jsonify({'error': 'Bad request'})


def get_user_json(user):
    return {'number': user.number,
            'username': user.username,
            'age': user.age,
            'gender': user.gender,
            'bio': user.bio,
            'story': user.story }


def get_specific_match_json(match, user_id):
    if match.user1_id == user_id:
        user = UserDB.query.filter_by(number=match.user2_id).first()
    elif match.user2_id == user_id:
        user = UserDB.query.filter_by(number=match.user1_id).first()
    user_json = get_user_json(user)
    return {'id': match.id,
            'match': user_json,
            'day': datetime.strftime(match.day, "%m-%d-%Y"),
            'lat': match.lat,
            'long': match.long }


def get_match_json(match):
    return {'id': match.id,
            'user1_id': match.user1_id,
            'user2_id': match.user2_id,
            'day': datetime.strftime(match.day, "%m-%d-%Y"),
            'lat': match.lat,
            'long': match.long }


def get_location_json(location):
    return {'id': location.id,
            'user_id': location.user_id,
            'lat': location.lat,
            'long': location.long,
            'time': str(location.time) }


def get_date_json(date):
    date = str(date)[15:26]
    return {'date': datetime.strptime(date, "%Y, %m, %d").strftime("%m-%d-%Y") }


# Calculate the great circle distance b/w two lat long points
def haversine(lat1, long1, lat2, long2):
    lat1, long1, lat2, long2 = map(radians, [lat1, long1, lat2, long2])
    dlong = long2 - long1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlong/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km
