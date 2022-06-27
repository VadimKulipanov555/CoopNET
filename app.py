from flask import Flask, url_for, redirect, session, render_template, request

from myConfig import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, logout_user
import phonenumbers
import re
from datetime import datetime
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash


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


# region Проверки полей

regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')


def isValidName(error, not_error, name):
    minName = 1
    maxName = 60

    if len(name) <= minName or len(name) > maxName:
        error['name'] = 'Ваше имя должно быть от {} до {}'.format(minName, maxName)
    else:
        not_error['name'] = name


def isValidLogin(error, not_error, login):
    minLogin = 1
    maxLogin = 32

    if len(login) <= minLogin or len(login) > maxLogin:
        error['login'] = 'Ваш логин должен быть от {} до {}'.format(minLogin, maxLogin)
    else:
        not_error['login'] = login

def isValidPhone(error, not_error, phone):
    try:
        my_number = phonenumbers.parse(phone, 'RUS')
        if not phonenumbers.is_valid_number(my_number):
            error['phone'] = 'Неверный номер телефона'
        else:
            not_error['phone'] = phone
    except:
        error['phone'] = 'Неверный номер телефона'


def isValidEmail(error, not_error, email):

    minEmail = 1
    maxEmail = 320

    if len(email) <= minEmail or len(email) > maxEmail:
        error['email'] = ['Ваш email должен быть от {} до {}'.format(minEmail, maxEmail)]

    if not re.fullmatch(regex, email):
        if 'email' in error:
            error['email'].append('В E-mail используются неверные символы')
        else:
            error['email'] = ['В E-mail используются неверные символы']

    if 'email' not in error.keys():
        not_error['email'] = email


def isValidPassword(error, not_error, password, confirm_password):

    if not password == confirm_password:
        error['password'] = 'Пароли не совпадают'
    else:
        not_error['password'] = password


def isValidUser(error, user):
    if user != 0:
        error['user_exists'] = 'Пользователь с таким email уже существует!'
# endregion


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    error = {}
    not_error = {}
    print('Hello')
    if request.method == "POST":
        isValidName(error, not_error, request.form['name'])
        isValidLogin(error, not_error, request.form['login'])
        isValidPhone(error, not_error, request.form['phone'])
        isValidEmail(error, not_error, request.form['reg_email'])
        isValidPassword(error, not_error, request.form['reg_password'], request.form['confirm_password'])

        sql = text("select count(*) from 'Пользователь' where email=='{}'".format(request.form['reg_email'].lower()))
        user = db.engine.execute(sql)
        isValidUser(error, user)

        print('Hello 1')
        print(error)
        print(not_error)

        if not error:
            sql = text("INSERT INTO 'Пользователь' (email, name, telephone, login, password, info, date_registration) "
                       "VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(request.form['reg_email'].lower(),
                                                                                   request.form['name'],
                                                                                   request.form['phone'],
                                                                                   request.form['login'],
                                                                                   generate_password_hash(request.form['reg_password']),
                                                                                   'Напишите информацию о себе',
                                                                                   datetime.utcnow()))
            print('Запрос был оформлен')
            db.engine.execute(sql)

            return redirect(url_for('authorization'))
        else:
            return render_template('Registration.html', title='Registration', message=[error, not_error])

    return render_template('Registration.html', title='Registration', message=[error, not_error])


@app.route('/', methods=['GET', 'POST'])
def authorization():
    return render_template('Authorization.html', title='Authorization')


if __name__ == '__main__':
    app.run(debug=True)
