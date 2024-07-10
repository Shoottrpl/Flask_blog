import sqlalchemy as sa
import sqlalchemy.orm as so
from app import create_app, db
from app.models import User, Post, Message, Notification, Task

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'db': db, 'User': User, 'Post': Post,
            'Messages': Notification, 'Notification': Notification, 'Task': Task}



