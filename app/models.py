from datetime import datetime
from time import time
from typing import Optional

from sqlalchemy_utils import URLType
import sqlalchemy as sa
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask_login import UserMixin
from hashlib import md5
import jwt
from app import db, login
from app.search import add_to_index, remove_from_index, query_index


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = sa.select(cls).where(cls.id.in_(ids)).order_by(
            db.case(*when, value=cls.id))
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


followers = sa.Table(
    'followers',
    db.metadata,
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    id = db.mapped_column(db.Integer, primary_key=True)
    name = db.mapped_column(db.String(50), nullable=False, unique=True)
    email = db.mapped_column(db.String(100), nullable=False, unique=True)
    about = db.mapped_column(db.String(140), nullable=True)
    psw_hash = db.mapped_column(db.Text(256), nullable=True)
    last_seen = db.mapped_column(db.DateTime, default=lambda: datetime.utcnow())
    last_message_read_time: db.Mapped[Optional[datetime]]

    posts: db.WriteOnlyMapped['Post'] = db.relationship(
        back_populates='author')
    following: db.WriteOnlyMapped['User'] = db.relationship(secondary=followers,
                                                            primaryjoin=(followers.c.follower_id == id),
                                                            secondaryjoin=(followers.c.followed_id == id),
                                                            back_populates='followers')
    followers: db.WriteOnlyMapped['User'] = db.relationship(secondary=followers,
                                                            primaryjoin=(followers.c.followed_id == id),
                                                            secondaryjoin=(followers.c.follower_id == id),
                                                            back_populates='following')

    messages_sent: db.WriteOnlyMapped['Message'] = db.relationship(
        foreign_keys='Message.sender_id', back_populates='author')
    messages_received: db.WriteOnlyMapped['Message'] = db.relationship(
        foreign_keys='Message.recipient_id', back_populates='recipient')

    def set_password(self, password):
        self.psw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.psw_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = db.aliased(User)
        Follower = db.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )
    def unread_message_count(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        query = sa.select(Message).where(Message.recipient == self,
                                         Message.timestamp > last_read_time)
        return db.session.scalar(sa.select(sa.func.count()).select_from(
            query.subquery()))

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, id)

    def __repr__(self):
        return f"<user {self.id}>"


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class Post(SearchableMixin, db.Model):
    __searchable__ = ['text']
    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    title: db.Mapped[str] = db.mapped_column(db.String(50), nullable=False)
    text: db.Mapped[str] = db.mapped_column(db.String(140), nullable=False)
    timestamp: db.Mapped[datetime] = db.mapped_column(db.DateTime, default=lambda: datetime.utcnow())
    language: db.Mapped[Optional[str]] = db.mapped_column(db.String(5))

    user_id: db.Mapped[int] = db.mapped_column(sa.ForeignKey(User.id))

    author: db.Mapped[User] = db.relationship('User', backref='post', uselist=False)

    def __repr__(self):
        return f"<post {self.id}>"


class Message(db.Model):
    id: db.Mapped[int] = db.mapped_column(primary_key=True)
    sender_id: db.Mapped[int] = db.mapped_column(sa.ForeignKey(User.id))
    recipient_id: db.Mapped[int] = db.mapped_column(sa.ForeignKey(User.id))
    body: db.Mapped[str] = db.mapped_column(sa.String(140))
    timestamp: db.Mapped[datetime] = db.mapped_column(default=lambda: datetime.utcnow())

    author: db.Mapped[User] = db.relationship(
        foreign_keys='Message.sender_id',
        back_populates='messages_sent'
    )
    recipient: db.Mapped[User] = db.relationship(
        foreign_keys='Message.recipient_id',
        back_populates='messages_received'
    )

    def __repr__(self):
        return f'<message {self.id}>'


