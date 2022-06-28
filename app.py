from flask import Flask, url_for, redirect, session, render_template, request, flash, make_response

from myConfig import Config
from flask_sqlalchemy import SQLAlchemy
#from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, current_user, logout_user, login_required
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
#migrate = Migrate(app, db)
login_manager = LoginManager(app)


chat_user = db.Table(
    'Список Участников Чата',
    db.Column('chat_id', db.Integer(), db.ForeignKey('Чат.chat_id')),
    db.Column('email', db.String(320), db.ForeignKey('Пользователь.email'))
)


class User(db.Model, UserMixin):
    __tablename__ = 'Пользователь'
    email = db.Column(db.String(320), primary_key=True)
    name = db.Column(db.String(60))
    telephone = db.Column(db.String(15), unique=True)
    login = db.Column(db.String(32), unique=True)
    password = db.Column(db.String(500))
    info = db.Column(db.String(70))
    date_registration = db.Column(db.DateTime, default=str(datetime.now())[:10])
    # theme =
    photo = db.Column(db.BLOB, nullable=True)

    # Получаем аватар пользователя
    def GetAvatar(self, app):
        img = None
        if not self.photo:
            try:
                with app.open_resource(app.root_path + url_for('static', filename='images/Avatar.png'),
                                       'rb') as f:
                    img = f.read()
            except FileNotFoundError as e:
                print(f'Не найден аватар по умолчанию: {str(e)}')
        else:
            img = self.photo

        return img

    # Верификация типа изображения
    def VerifyExt(self, filename):
        ext = filename.rsplit('.', 1)[1]
        if ext in ('png', 'PNG'):
            return True
        return False

    # Обновление аватара
    def UpdateAvatar(self, avatar):
        if not avatar:
            return False
        try:
            self.photo = avatar
            db.session.commit()
        except Exception as e:
            print(f'Ошибка обновления аватара в БД: {str(e)}')
            return False
        return True

    # Удаление аватара
    def RemoveAvatar(self):
        try:
            self.photo = None
            db.session.commit()
        except Exception as e:
            print(f'Ошибка удаления аватара из БД: {str(e)}')
            return False
        return True


class Chat(db.Model):
    __tablename__ = 'Чат'
    chat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_name = db.Column(db.String(32))
    chat_description = db.Column(db.String(70))
    chat_creator = db.Column(db.String(320), db.ForeignKey('Пользователь.email'))

    # Для получения доступа к связанным объектам
    cats = db.relationship('User', secondary=chat_user, backref=db.backref('tasks', lazy='dynamic'))


class Message(db.Model):
    __tablename__ = 'Сообщение'
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('Чат.chat_id'))
    message_sender = db.Column(db.String(320), db.ForeignKey('Пользователь.email'))
    message_content = db.Column(db.String(120))
    message_date_sent = db.Column(db.DateTime, default=str(datetime.now())[:19])
    message_status = db.Column(db.Integer, default=0)


@login_manager.user_loader
def load_user(user_id):

    session['user'] = user_id
    # return User.query.get(user_id)


@app.route('/logout')
def logout():

    logout_user()
    return redirect(url_for('authorization'))


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
    if request.method == "POST":
        isValidName(error, not_error, request.form['name'])
        isValidLogin(error, not_error, request.form['login'])
        isValidPhone(error, not_error, request.form['phone'])
        isValidEmail(error, not_error, request.form['reg_email'])
        isValidPassword(error, not_error, request.form['reg_password'], request.form['confirm_password'])

        sql = text("select count(*) from 'Пользователь' where email=='{}'".format(request.form['reg_email'].lower()))
        user = [row for row in db.engine.execute(sql)]
        isValidUser(error, user[0][0])

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

            sql = text("select p1.email, p2.email "
                       "from 'Пользователь' p1 inner join 'Пользователь' p2 "
                       "    on p1.email !=p2.email and p1.email == '{}'".format(request.form['reg_email'].lower()))

            table = [row for row in db.engine.execute(sql)]
            for row in table:
                try:
                    user1, user2 = row
                    #sql_chat = text("insert into 'Чат' (chat_name, chat_description, chat_creator) VALUES (user2, 'friend', user1)")
                    #db.engine.execute(sql)

                    #sql_new_chat = text("select * from 'Чат' where chat_name=='{}' and chat_creator=='{}'".format(user2, user1))
                    #new_chat = db.engine.execute(sql_new_chat)

                    user_in_db = db.session.query(User).filter_by(email=user1).first()
                    user_in_db_2 = db.session.query(User).filter_by(email=user2).first()

                    chat = Chat(chat_name=user2, chat_description='friend', chat_creator=user1)
                    chat.cats.append(user_in_db)
                    chat.cats.append(user_in_db_2)
                    db.session.add(chat)
                    db.session.flush()
                except:
                    # Если были ошибки, то откатываемся назад
                    db.session.rollback()
                    print("Ошибка добавления в БД")
                # Сохраняем изменения в таблице
                db.session.commit()


            return redirect(url_for('authorization'))
        else:
            return render_template('Registration.html', title='Registration', message=[error, not_error])

    return render_template('Registration.html', title='Registration', message=[error, not_error])


@app.route('/', methods=['GET', 'POST'])
def authorization():
    if request.method == 'POST':
        error = {}
        sql = text("select count(*) as ct from 'Пользователь' where email=='{}'".format(request.form['email'].lower()))
        user = [row for row in db.engine.execute(sql)]
        isValidUser(error, user[0][0])

        if error:
            error = {}
            sql = text("select email, password from 'Пользователь' where email=='{}'".format(request.form['email'].lower()))
            info_user = [row for row in db.engine.execute(sql)]
            email, password = info_user[0]
        else:
            return render_template('Authorization.html', title='Authorization', message='Ошибка ввода данных')

        if check_password_hash(password, request.form['password']):
            load_user(email)

            sql = text('')

            return render_template('HomePage.html', title='HomePage')
        else:
            return render_template('Authorization.html', title='Authorization', message='Ошибка ввода данных')

    return render_template('Authorization.html', title='Authorization')


@app.route('/HomePage', methods=['GET', 'POST'])
def homepage():
    return render_template('HomePage.html')


#Обработчик удаления аватара пользователя
@app.route('/removeavatar', methods=['POST', 'GET'])
@login_required
def removeavatar():
    result = current_user.RemoveAvatar()
    if not result:
        flash('Ошибка удаления аватара', 'error')
    flash('Аватар успешно удален', 'success')
    return redirect('/HomePage')


# Обработчик получения аватара пользователя
@app.route('/useravatar')
@login_required
def useravatar():
    user = current_user
    img = user.GetAvatar(app)
    if not img:
        return ""

    h = make_response(img)
    h.headers['Content-Type'] = '/Image/png'
    return h


# Обработчик загрузки аватара пользователя
@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and current_user.VerifyExt(file.filename):
            try:
                img = file.read()
                result = current_user.UpdateAvatar(img)
                if not result:
                    flash('Ошибка обновления аватара', 'error')
                flash('Аватар успешно обновлен', 'success')
            except FileNotFoundError as e:
                flash('Ошибка обновления аватара', 'error')
                return redirect(url_for('index'))
        return redirect(f'/Profile/{current_user.id}')
    else:
        return redirect(f'/Profile/{current_user.id}')


@app.route('/deletemessage', methods=['POST', 'GET'])
def deletemessage():
    messageid = request.form['submit']
    try:
        sql = text('delete from Сообщение '
                   ' where message_id == ' + str(messageid))
        db.engine.execute(sql)
    except:
        flash('Ошибка удаления сообщения')
    return redirect(url_for('homepage'))

if __name__ == '__main__':
    app.run(debug=True)
