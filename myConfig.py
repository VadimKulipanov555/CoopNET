import os
basedir = os.path.abspath(os.path.dirname(__file__))


# you-will-never-guess
class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'coopnet'