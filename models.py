from datetime import datetime
from app import db
from flask_login import LoginManager, UserMixin, login_user, logout_user


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
    info = db.Column(db.String(70))
    date_registration = db.Column(db.DateTime, default=str(datetime.now())[:10])
    # theme =
    # photo =


class Chat(db.Model):
    __tablename__ = 'Чат'
    chat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_name = db.Column(db.String(32))
    chat_description = db.Column(db.String(70))
    chat_creator = db.Column(db.String(320), db.ForeignKey('Пользователь.email'))

    # Для получения доступа к связанным объектам
    cats = db.relationship('Category', secondary=chat_user, backref=db.backref('tasks', lazy='dynamic'))


class Message(db.Model):
    __tablename__ = 'Сообщение'
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('Чат.chat_id'))
    message_sender = db.Column(db.String(320), db.ForeignKey('Пользователь.email'))
    message_content = db.Column(db.String(120))
    message_date_sent = db.Column(db.DateTime, default=str(datetime.now())[:19])
    message_status = db.Column(db.Integer, default=0)
