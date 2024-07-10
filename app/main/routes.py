from datetime import datetime
from flask import render_template, url_for, request, flash, redirect, g, current_app
from flask_login import current_user, login_required
import sqlalchemy as sa
from flask_babel import _, get_locale
from langdetect import detect, LangDetectException

from app import db
from app.main import bp
from app.models import User, Post, Message, Notification
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, MessageForm
from app.translate import translate


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route("/", methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(title=form.title.data, text=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Пост опубликован'))
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html', posts=posts, form=form, prev_url=prev_url,
                           next_url=next_url)


@bp.route('/profile/<username>')
@login_required
def profile(username):
    user = db.first_or_404(sa.select(User).where(User.name == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.profile', username=user.name, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.profile', username=user.name, page=posts.prev_num) if posts.has_prev else None

    form = EmptyForm()
    return render_template('profile.html', title=_('Профиль'), user=user, posts=posts, form=form,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/profile/<username>/popup')
@login_required
def profile_popup(username):
    user = db.first_or_404(sa.Select(User).where(User.name == username))
    form = EmptyForm()
    return render_template('profile_popup.html', user=user, form=form)


@bp.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    form = EditProfileForm(current_user.name)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.about = form.about.data
        db.session.commit()
        flash(_('Изменения сохранены'))
        return redirect(url_for('main.profile', username=current_user.name))
    elif request.method == 'GET':
        form.name.data = current_user.name
        form.about.data = current_user.about
    return render_template('edit_profile.html', title=_('Изменение профиля'), form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(current_user.name == username)
        )
        if User is None:
            flash(_('Пользователя %(username)s не существует'))
            return redirect(url_for('main.index'))
        if User == current_user:
            flash(_('Нельзя подписаться на самого себя'))
            return redirect(url_for('main.profile', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('В подписаны на %(username)s'))
        return redirect(url_for('main.profile', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(current_user.name == username)
        )
        if User is None:
            flash(_('Пользователя %(username)s не существует'))
            return redirect(url_for('main.index'))
        if User == current_user:
            flash(_('Нельзя отписаться на самого себя'))
            return redirect(url_for('main.profile', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('Вы отписались от %(username)s'))
        return redirect(url_for('main.profile', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title=_('Лента'), posts=posts, prev_url=prev_url,
                           next_url=next_url)


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['target_language'])}


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Поиск'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = db.first_or_404(sa.Select(User).where(User.name == recipient))
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      text=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.unread_message_count())
        db.session.commit()
        flash(_('Ваще сообщение отправленно'))
        return redirect(url_for('main.profile', username=recipient))
    return render_template('send_message.html', title=_('Отправить сообщение'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    query = current_user.messages_received.select().order_by(
        Message.timestamp.desc())
    messages = db.paginate(query, page=page,
                           per_page=current_app.config['POSTS_PER_PAGE'],
                           error_out=False)

    next_url = url_for('main.messages', page=messages.next_num) if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)

@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    query = current_user.notifications.select().where(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]


@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_post'):
        flash(_('Задача экспорта находится в процессе выполнения'))
    else:
        current_user.launch_task('export_post', _('Экспорт публикаций...'))
        db.session.commit()
    return redirect(url_for('main.profile', username=current_user.name))
