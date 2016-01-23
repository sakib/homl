"""
username: homl
password: homl
    name: homl
"""

import os
basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'mysql://homl:homl@localhost/homl'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SECRET_KEY = 'homl'
