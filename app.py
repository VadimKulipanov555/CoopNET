from flask import Flask, url_for, redirect, session
from myConfig import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, logout_user

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coopNet.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):

    session['user'] = user_id
    # return User.query.get(user_id)


@app.route('/logout')
def logout():

    logout_user()
    return redirect(url_for('login'))


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
