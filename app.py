from flask import Flask, url_for, redirect, render_template, request, flash, make_response

from myConfig import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, logout_user, login_required, login_user
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
login_manager = LoginManager(app)

# region БД
chat_user = db.Table(
    'Список Участников Чата',
    db.Column('chat_id', db.Integer(), db.ForeignKey('Чат.chat_id')),
    db.Column('user_id', db.String(320), db.ForeignKey('Пользователь.id'))
)


class User(db.Model, UserMixin):
    __tablename__ = 'Пользователь'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True)
    name = db.Column(db.String(60))
    telephone = db.Column(db.String(15), unique=True)
    login = db.Column(db.String(32), unique=True)
    password = db.Column(db.String(500))
    info = db.Column(db.String(70))
    date_registration = db.Column(db.DateTime, default=datetime.utcnow)
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

    def __repr__(self):
        return '<User $r>' % self.id


class Chat(db.Model):
    __tablename__ = 'Чат'
    chat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_name = db.Column(db.String(32))
    chat_description = db.Column(db.String(70))
    chat_photo = db.Column(db.BLOB, nullable=True)
    chat_creator = db.Column(db.Integer, db.ForeignKey('Пользователь.id'))

    # Для получения доступа к связанным объектам
    cats = db.relationship('User', secondary=chat_user, backref=db.backref('tasks', lazy='dynamic'))

    # Получаем аватар пользователя
    def GetAvatar(self, app):
        img = None
        if not self.chat_photo:
            try:
                with app.open_resource(app.root_path + url_for('static', filename='images/ChatAvatar.png'),
                                       'rb') as f:
                    img = f.read()
            except FileNotFoundError as e:
                print(f'Не найден аватар по умолчанию: {str(e)}')
        else:
            img = self.chat_photo

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
            self.chat_photo = avatar
            db.session.commit()
        except Exception as e:
            print(f'Ошибка обновления аватара в БД: {str(e)}')
            return False
        return True

    # Удаление аватара
    def RemoveAvatar(self):
        try:
            self.chat_photo = None
            db.session.commit()
        except Exception as e:
            print(f'Ошибка удаления аватара из БД: {str(e)}')
            return False
        return True


class Message(db.Model):
    __tablename__ = 'Сообщение'
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('Чат.chat_id'))
    message_sender = db.Column(db.Integer, db.ForeignKey('Пользователь.id'))
    message_content = db.Column(db.String(120))
    message_date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    message_status = db.Column(db.Integer, default=0)
#endregion


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


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


# region SQL
# Необходимо еще возвращать id собеседника
def gettingChats():
    # Получаем все чаты пользователя
    sql = text("select inf.chat_id, me, friend, p.email, message_id, message_sender, message_content, message_date_sent, message_status "
               "from (  select * "
               "from (  select info_chat.chat_id, me, friend, message_id, message_sender, message_content, message_date_sent, message_status "
               "from (  select f_chat.chat_id, f_chat.user_id as me, s_chat.user_id as friend "
               "from 'Список Участников Чата' f_chat inner join 'Список Участников Чата' s_chat on f_chat.chat_id==s_chat.chat_id "
               "where f_chat.user_id=='{}' and f_chat.user_id!=s_chat.user_id and f_chat.chat_id not in (select chat_id from 'Чат' where chat_description=='chat') "
               ") info_chat left outer join 'Сообщение' mes on info_chat.chat_id == mes.chat_id "
               "order by message_date_sent desc "
               ") chat_mes "
               "group by chat_mes.chat_id) inf inner join 'Пользователь' p on inf.friend == p.id".format(current_user.id))
    return [row for row in db.engine.execute(sql)]


# Получаем все групповые чаты авторизованного пользователя (Оптимизировано)
def gettingGroupChats():

    sql = text("select chat_id, chat_name, chat_description, chat_creator, message_id, message_content, message_date_sent, message_status "
               "from (select chInfo.*, c.message_id, c.message_content, c.message_date_sent, c.message_status "
               "from (select myCh.*, ch.chat_name, ch.chat_description, ch.chat_creator "
               "from (select chat_id "
               "from 'Список Участников Чата' "
               "where user_id=='{}') myCh inner join 'Чат' ch on myCh.chat_id==ch.chat_id "
               "where chat_description == 'chat' ) chInfo left outer join 'Сообщение' c on chInfo.chat_id==c.chat_id "
               "order by message_date_sent desc) info "
               "group by info.chat_id".format(current_user.id))

    return [row for row in db.engine.execute(sql)]


# Получаем все сообщения одного чата по его id (Оптимизировано)
def receivingChatMessages(chat_id):
    sql = text("select mes.message_id, mes.chat_id, mes.message_sender, user.name, mes.message_content, mes.message_date_sent, mes.message_status "
               "from (select * "
               "from 'Сообщение' "
               "where chat_id == '{}' "
               "order by message_date_sent asc) mes left join 'Пользователь' user on mes.message_sender = user.id ".format(chat_id))

    return [row for row in db.engine.execute(sql)]


# Получаем список участников чата по id чата (Оптимизировано)
def gettingChatParticipants(chat_id):
    sql = text("select user_id "
               "from 'Список Участников Чата' "
               "where chat_id=='{}' and user_id != '{}'".format(chat_id, current_user.id))

    return db.engine.execute(sql).first()


# Получаем имя чата по id пользователя (Оптимизировано)
# Используется только для P2P чатов
def gettingChatNameById(user_id):
    sql = text("select email "
               "from 'Пользователь' "
               "where id == '{}'".format(user_id))

    return db.engine.execute(sql).first()


# Получаем информацию о пользователе P2P чата по id пользователя (Оптимизировано)
def chatParticipantProfile(user_id):
    sql = text("select id, email, name, telephone, login, info, date_registration "
               "from 'Пользователь' "
               "where id == '{}' ".format(user_id))

    return db.engine.execute(sql).first()


def userInformation(user):

    if user is not None:
        sql = text("select count(*) from 'Пользователь' where email=='{}'".format(user))
    else:
        sql = text("select * "
                   "from 'Пользователь' "
                   "where id != '{}'".format(current_user.id))
    return [row for row in db.engine.execute(sql)]
# endregion


# Страница регистрации (Оптимизировано)
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))
    error = {}
    not_error = {}
    if request.method == "POST":
        phone = f"+7{request.form['phone']}"
        isValidName(error, not_error, request.form['name'])
        isValidLogin(error, not_error, request.form['login'])
        isValidPhone(error, not_error, phone)
        isValidEmail(error, not_error, request.form['reg_email'])
        isValidPassword(error, not_error, request.form['reg_password'], request.form['confirm_password'])

        user = userInformation(request.form['reg_email'].lower())
        isValidUser(error, user[0][0])

        if not error:
            # Добавление нового пользователя
            sql = text("INSERT INTO 'Пользователь' (email, name, telephone, login, password, info, date_registration) "
                       "VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(request.form['reg_email'].lower(),
                                                                                  request.form['name'],
                                                                                  phone,
                                                                                  request.form['login'],
                                                                                  generate_password_hash(request.form['reg_password']),
                                                                                  'Напишите информацию о себе',
                                                                                  datetime.utcnow()))
            db.engine.execute(sql)

            sql = text("select p1.id, p1.email, p2.id, p2.email "
                       "from 'Пользователь' p1 inner join 'Пользователь' p2 "
                       "    on p1.email !=p2.email and p1.email == '{}'".format(request.form['reg_email'].lower()))

            table = [row for row in db.engine.execute(sql)]
            for row in table:
                try:
                    user1_id, user1_email, user2_id, user2_email = row

                    user_in_db = db.session.query(User).filter_by(email=user1_email).first()
                    user_in_db_2 = db.session.query(User).filter_by(email=user2_email).first()

                    chat = Chat(chat_name=user2_email, chat_description='friend', chat_creator=user1_id)
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


# Страница авторизации (Оптимизировано)
@app.route('/', methods=['GET', 'POST'])
def authorization():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))
    if request.method == 'POST':
        error = {}

        user = userInformation(request.form['email'].lower())
        isValidUser(error, user[0][0])

        if error:
            error.clear()
            sql = text("select email, password from 'Пользователь' where email=='{}'".format(request.form['email'].lower()))
            info_user = [row for row in db.engine.execute(sql)]
            email, password = info_user[0]
        else:
            return render_template('Authorization.html', title='Authorization', message='Ошибка ввода данных')

        if check_password_hash(password, request.form['password']):
            user = User.query.filter_by(email=request.form['email'].lower()).first()
            login_user(user)
            load_user(email)

            return redirect(url_for('homepage'))
        else:
            return render_template('Authorization.html', title='Authorization', message='Ошибка ввода данных')

    return render_template('Authorization.html', title='Authorization')


# Главная страница (Оптимизировано)
@app.route('/HomePage', methods=['GET', 'POST'])
@login_required
def homepage():
    user = current_user
    chat_name = ''

    selectedchat = request.args.get('selectedchat', type=int)

    chat = gettingChats()
    chat.extend(gettingGroupChats())

    all_user = userInformation(None)

    if selectedchat is not None:
        messages_chat = ''
        chatparticipants = ''
        chat_id = selectedchat

        sql = text("select * "
                   "from 'Чат' "
                   "where chat_id == {}".format(chat_id))
        selectedchat = db.engine.execute(sql).first()

        sql = text("select id, email "
                   "from 'Пользователь' "
                   "where id in (select user_id "
                   "from 'Список Участников Чата' "
                   "where chat_id == {} and user_id != '{}')".format(chat_id, current_user.id))
        chatparticipants = [row for row in db.engine.execute(sql)]

        sql = text("UPDATE 'Сообщение' "
                   "set message_status = 1 "
                   "where chat_id == {} and message_sender !='{}'".format(chat_id, current_user.id))

        db.engine.execute(sql)

        messages_chat = receivingChatMessages(chat_id)

        chat_user_id = gettingChatParticipants(chat_id)

        if selectedchat[2] == 'chat':
            chat_name = (selectedchat[1],)
        else:
            chat_name = gettingChatNameById(chat_user_id[0])

        companion = chatParticipantProfile(chat_user_id[0])

        return render_template('HomePage.html',
                               user=user,
                               myChat=chat,
                               name=chat_name,
                               message=messages_chat,
                               companion=companion,
                               chat_id=chat_id,
                               all_user=all_user,
                               selectedchat=selectedchat,
                               chatparticipants=chatparticipants)
    else:
        return render_template('HomePage.html',
                               user=user,
                               myChat=chat,
                               name=chat_name,
                               #message=messages_chat,
                               all_user=all_user,
                               #selectedchat=selectedchat,
                               #chatparticipants=chatparticipants
                               )


# Обработчик удаления аватара пользователя (Оптимизировано)
@app.route('/removeavatar', methods=['POST', 'GET'])
@login_required
def removeavatar():
    result = current_user.RemoveAvatar()
    if not result:
        flash('Ошибка удаления аватара', 'error')
    flash('Аватар успешно удален', 'success')
    return redirect(url_for('homepage'))


# Обработчик удаления аватара чата (Оптимизировано)
@app.route('/removechatavatar', methods=['POST', 'GET'])
@login_required
def removechatavatar():
    chatfield = request.args.get('chatfield')
    chat = Chat.query.filter_by(chat_id=chatfield).first()
    result = chat.RemoveAvatar()
    if not result:
        flash('Ошибка удаления аватара', 'error')
    flash('Аватар успешно удален', 'success')
    return redirect(url_for('homepage', selectedchat=chat.chat_id))


# Обработчик получения аватара пользователя (Оптимизировано)
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


# Обработчик загрузки аватара пользователя (Оптимизировано)
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
            except FileNotFoundError:
                flash('Ошибка обновления аватара', 'error')
                return redirect(url_for('homepage'))
        return redirect(url_for('homepage'))
    else:
        return redirect(url_for('homepage'))


# Обработчик загрузки аватара чата (Оптимизировано)
@app.route('/chatupload', methods=['POST', 'GET'])
@login_required
def chatupload():
    if request.method == 'POST':
        chatfield = request.args.get('chatfield')
        chat = Chat.query.filter_by(chat_id=chatfield).first()

        file = request.files.get('file_chat')
        if file and chat.VerifyExt(file.filename):
            try:
                img = file.read()
                result = chat.UpdateAvatar(img)
                if not result:
                    flash('Ошибка обновления аватара', 'error')
                flash('Аватар успешно обновлен', 'success')
            except FileNotFoundError:
                flash('Ошибка обновления аватара', 'error')
                return redirect(url_for('homepage', selectedchat=chat.chat_id))
        return redirect(url_for('homepage', selectedchat=chat.chat_id))
    else:
        return redirect(url_for('homepage'))


# Получаем аватар пользователя (Оптимизировано)
@app.route('/getuseravatar', methods=['POST', 'GET'])
@login_required
def getuseravatar():
    userfield = request.args.get('userfield')
    user = User.query.filter_by(id=userfield).first()

    img = user.GetAvatar(app)
    if not img:
        return ""

    h = make_response(img)
    h.headers['Content-Type'] = '/Image/png'
    return h


# Получаем аватар чата (Оптимизировано)
@app.route('/getchatavatar', methods=['POST', 'GET'])
@login_required
def getchatavatar():
    chatfield = request.args.get('chatfield')
    chat = Chat.query.filter_by(chat_id=chatfield).first()

    img = chat.GetAvatar(app)
    if not img:
        return ""

    h = make_response(img)
    h.headers['Content-Type'] = '/Image/png'
    return h


# Удаление сообщения из чата (Оптимизировано)
@app.route('/deletemessage', methods=['POST', 'GET'])
@login_required
def deletemessage():
    messageid = request.form['submit']
    selectedchat = request.args.get('chat_id')
    try:
        sql = text('delete from Сообщение '
                   ' where message_id == ' + str(messageid))
        db.engine.execute(sql)
    except:
        flash('Ошибка удаления сообщения')

    return redirect(url_for('homepage', selectedchat=selectedchat))


# Отправка сообщения в чат (Оптимизировано)
@app.route('/sendmessage', methods=['POST'])
@login_required
def sendmessage():
    chat_id = request.args.get('chat_id')
    message_content = request.form.get('MessageText')

    sql = text("insert into 'Сообщение' ('chat_id', 'message_sender', 'message_content', 'message_date_sent', 'message_status') "
               "values ({}, {}, '{}', '{}', '0') ".format(chat_id, current_user.id, message_content, datetime.utcnow()))

    db.engine.execute(sql)

    return redirect(url_for('homepage', selectedchat=chat_id))
    # chat = gettingChats()
    #
    # sql = text("select * "
    #            "from 'Чат' "
    #            "where chat_id == {}".format(chat_id))
    # selectedchat = db.engine.execute(sql).first()
    #
    # sql = text("select email "
    #            "from 'Список Участников Чата' "
    #            "where chat_id == {} and email != '{}' ".format(chat_id, current_user.email))
    # chatparticipants = [row for row in db.engine.execute(sql)]
    #
    # chat.extend(gettingGroupChats())
    #
    # messages_chat = receivingChatMessages(chat_id)
    #
    # chat_name = gettingChatParticipants(chat_id)
    #
    # companion = chatParticipantProfile(chat_name[0])
    #
    # return render_template('HomePage.html',
    #                        user=current_user,
    #                        myChat=chat,
    #                        name=chat_name,
    #                        message=messages_chat,
    #                        companion=companion,
    #                        chat_id=chat_id,
    #                        selectedchat=selectedchat,
    #                        chatparticipants=chatparticipants)


# Создание нового группового чата (Оптимизировано)
@app.route('/creatingchat', methods=['POST'])
@login_required
def creatingChat():

    chat_name = request.form['ChatNameCreate']
    # Люди в чате
    group = [current_user.id]

    for number, row in enumerate(request.form.items()):
        if number != 0:
            group.append(row[0])

    if chat_name is not None:

        sql = text("INSERT INTO 'Чат' (chat_name, chat_description, chat_creator) "
                   "VALUES ('{}','{}','{}')".format(chat_name, 'chat', current_user.id))
        db.engine.execute(sql)

        sql = text("select * "
                   "from 'Чат' "
                   "where chat_creator == '{}'"
                   "order by chat_id desc "
                   "limit 1".format(current_user.id))

        new_group_chat = db.engine.execute(sql).first()

        # Проходимся по каждому человеку
        for people in group:
            sql = text("INSERT INTO 'Список Участников Чата' (chat_id, user_id) "
                       "VALUES ({},'{}')".format(new_group_chat[0], people))
            db.engine.execute(sql)

        return redirect(url_for('homepage', selectedchat=new_group_chat[0]))

    return redirect(url_for('homepage'))


# Страница ошибки 404 (Оптимизировано)
@app.errorhandler(404)
def pageNotFound(error):
    return render_template('Page404.html'), 404


# Страница ошибки 401 (Оптимизировано)
@app.errorhandler(401)
def pageNotFound(error):
    return render_template('Page401.html'), 401


if __name__ == '__main__':
    app.run(debug=True)
