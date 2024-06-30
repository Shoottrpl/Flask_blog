import sqlalchemy as sa
from flask import request
from flask_babel import _, lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import ValidationError, DataRequired, Email, Length, EqualTo

from app import db
from app.models import User


class EditProfileForm(FlaskForm):
    name = StringField(_l("Имя:"), validators=[Length(min=4, max=100, message=_("Имя должен быть от 4 до 100 символов"))])
    about = TextAreaField(_l("О себе"), validators=[Length(min=0, max=140, message=_("Текст должен быть до 140 символов" ))])
    submit = SubmitField(_l("Отправить"))

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_name(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(User.name==self.original_username))
            if user is not None:
                raise ValidationError(_('Пользователь с таким именем уже существует, выбирите другое'))


class EmptyForm(FlaskForm):
    submit = SubmitField(_('Отправить'))


class PostForm(FlaskForm):
    title = StringField(_l("Заголовок"),
                        validators=[Length(min=4, max=100, message=_("Имя должен быть от 4 до 100 символов"))])
    post = TextAreaField(_l('Напишите что-то'),
                         validators=[Length(min=1, max=140, message=_("Текст должен быть до 140 символов" ))])
    submit = SubmitField(_l('Отправить'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l("Email: "), validators=[Email(_("Некорректный email"))])
    submit = SubmitField(_l('Отправить'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Пароль'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Повтор пароля'), validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Отправить'))


class SearchForm(FlaskForm):
    q = StringField(_l('Поиск'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'meta' not in kwargs:
            kwargs['meta'] = {'csrf': False}
        super(SearchForm, self).__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField(_l('Сообщение'), validators=[
        DataRequired(), Length(min=0, max=140)])
    submit = SubmitField(_l('Отправить'))


