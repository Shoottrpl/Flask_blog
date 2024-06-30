from flask import render_template, url_for, request, flash, redirect
from flask_login import current_user, login_user, logout_user
from urllib.parse import urlsplit
import sqlalchemy as sa
from flask_babel import _
from app import db
from app.auth import bp
from app.models import User
from .forms import LoginForm, RegisterForm, ResetPasswordRequestForm, \
    ResetPasswordForm
from app.auth.email import send_password_reset_email


@bp.route('/login', methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile', username=current_user.name))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.name == form.name.data))
        if user is None or not user.check_password(form.psw.data):
            flash(_("Введен неверный пароль или логин"), 'error')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)

    return render_template('auth/login.html', form=form, title=_("Авторизация"))


@bp.route('/register', methods=["POST", "GET"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        u = User(name=form.name.data, email=form.email.data)
        u.set_password(form.psw.data)
        db.session.add(u)
        db.session.commit()
        if u:
            flash(_("Вы успешно зарегистрированы"), "success")
            return redirect(url_for('auth.login'))
        else:
            flash(_("Ошибка при добавлении в БД"), "error")

    return render_template('auth/register.html', title=_('Регистрация'), form=form)


@bp.route('/logout')
def logout():
    logout_user()
    flash(_("Вы вышли из аккаунта"), "success")
    return redirect(url_for('auth.login'))


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_form():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash(_('Инструкция по сбросу пароля отправлена на ваш email'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title=_('Смена пароля'),
                                        form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Пароль изменене'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', title=_('Смена пароля'), form=form)
