from app import app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

db=SQLAlchemy(app)
migrate=Migrate(app,db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String, unique=True)
    passhash=db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(64), nullable=True)
    profile_pic=db.Column(db.String(256))
    is_admin=db.Column(db.Boolean, nullable=False,default=False)

    books=db.relationship('Book', backref='user',lazy=True, cascade='all, delete-orphan')

class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(32), unique=False, nullable=False)
    date_created=db.Column(db.Date, nullable=False)
    description = db.Column(db.String(256), nullable=False)

    books=db.relationship('Book', backref='section',lazy=True, cascade='all, delete-orphan')

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    bname = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    author_name = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pages=db.Column(db.Integer, nullable=False)
    volume_no = db.Column(db.Integer)
    issue_date=db.Column(db.Date, nullable=True)
    return_date=db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cover=db.Column(db.String(256))
    request_counts=db.Column(db.Integer,default=0)

    section_id=db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)

class Mybook(db.Model):
    book_id=db.Column(db.Integer, db.ForeignKey('book.id'), primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_date=db.Column(db.Date, nullable=False)
    return_date=db.Column(db.Date, nullable=False)

    user = db.relationship('User', backref='user_books')
    book = db.relationship('Book')

class UserFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    submitted_at = db.Column(db.Date, nullable=False)

    user = db.relationship('User', backref='user_feedback',lazy=True)

class BookRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User', backref='book_requests')
    book = db.relationship('Book')
    

with app.app_context():
    db.create_all()
    admin=User.query.filter_by(is_admin=True).first()
    if not admin:
        password_hash=generate_password_hash('admin')
        admin=User(username='admin',passhash=password_hash,name='Admin',is_admin=True)
        db.session.add(admin)
        db.session.commit()