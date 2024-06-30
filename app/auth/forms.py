import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, PasswordField
from wtforms.validators import ValidationError, DataRequired, Email, Length, EqualTo

from app import db
from app.models import User


class LoginForm(FlaskForm):
    name = StringField(_l("Логин: "),
                       validators=[Length(min=4, max=100, message=_("Имя должен быть от 4 до 100 символов"))])
    psw = PasswordField(_l("Пароль: "), validators=[DataRequired(), Length(min=4, max=100,
                                                                           message=_(
                                                                               "Пароль должен быть от 4 до 100 символов"))])
    remember = BooleanField(_l("Запомнить"), default=False)
    submit = SubmitField(_l("Войти"))


class RegisterForm(FlaskForm):
    name = StringField(_l("Имя:"),
                       validators=[Length(min=4, max=100, message=_("Имя должен быть от 4 до 100 символов"))])
    email = StringField(_l("Email: "), validators=[Email(_("Некорректный email"))])
    psw = PasswordField(_l("Пароль: "), validators=[DataRequired(), Length(min=4, max=100,
                                                                           message=_(
                                                                               "Пароль должен быть от 4 до 100 символов"))])

    psw2 = PasswordField(_l("Повтор пароля: "),
                         validators=[DataRequired(), EqualTo('psw', message=_("Пароли не совпадают"))])
    submit = SubmitField(_l("Регестрация"))

    def validate_name(self, name):
        user = db.session.scalar(sa.select(User).where(User.name == name.data))
        if user is not None:
            raise ValidationError(_('Пользователь с таким именем уже существует'))

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError(_('Пользователь с такой почтой уже существует'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l("Email: "), validators=[Email(_("Некорректный email"))])
    submit = SubmitField(_l('Отправить'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Пароль'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Повтор пароля'), validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Отправить'))
