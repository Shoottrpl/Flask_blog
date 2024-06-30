from datetime import datetime
import unittest
from app import create_app, db
from app.models import User, Post
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(name='user_test', email='user_test@mail.com')
        u.set_password('user1')
        self.assertFalse(u.check_password('user2'))
        self.assertTrue(u.check_password('user1'))

    def test_avatar(self):
        u = User(name='user_test', email='user_test@mail.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                          '9d9bd312c1e8f62964521832cccc0607?'
                                          'd=identicon&s=128'))

    def test_follow(self):
        u1 = User(name='user_test_1', email='user_test_1@mail.com')
        u2 = User(name='user_test_2', email='user_test_2@mail.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        following = db.session.scalars(u1.following.select()).all()
        followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u2.followers_count(),1)
        self.assertEqual(u1.following_count(), 1)
        u1_following = db.session.scalars(u1.following.select()).all()
        u2_followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(u1_following[0].name, 'user_test_2')
        self.assertEqual(u2_followers[0].name, 'user_test_1')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u2.followers_count(), 0)
        self.assertEqual(u1.following_count(), 0)

    def test_follow_post(self):
        # create four users
        u1 = User(name='user_test_1', email='user_test_1@mail.com')
        u2 = User(name='user_test_2', email='user_test_2@mail.com')
        u3 = User(name='user_test_3', email='user_test_3@mail.com')
        u4 = User(name='user_test_4', email='user_test_4@mail.com')
        db.session.add_all([u1, u2, u3, u4])

        #create four posts
        now = datetime.utcnow()
        p1 = Post(title='test_title_1', text='test_text_1', created=now, author=u1)
        p2 = Post(title='test_title_2', text='test_text_2', created=now, author=u2)
        p3 = Post(title='test_title_3', text='test_text_3', created=now, author=u3)
        p4 = Post(title='test_title_4', text='test_text_4', created=now, author=u4)
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        #setup the followers
        u1.follow(u2) #user_test_1 following user_test_2
        u1.follow(u3) #user_test_1 following user_test_3
        u2.follow(u4) # user_test_2 following user_test_4
        u3.follow(u4) # user_test_3 following user_test_4

        #check the following post of each user
        f1 = db.session.scalars(u1.following_posts()).all()
        f2 = db.session.scalars(u2.following_posts()).all()
        f3 = db.session.scalars(u3.following_posts()).all()
        f4 = db.session.scalars(u4.following_posts()).all()
        self.assertEqual(f1, [p1, p2, p3,])
        self.assertEqual(f2, [p2, p4 ])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])

if __name__ == '__main__':
    unittest.main(verbosity=2)