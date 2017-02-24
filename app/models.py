import os
import datetime
from app import db,bcrypt

from sqlalchemy.ext.hybrid import hybrid_property

class Profile(db.Model):
    __tablename__ = "profile"
    id = db.Column(db.Integer, primary_key=True)
    screen_name = db.Column(db.String(50))
    avatar = db.Column(db.String(), default="user.jpg")
    email = db.Column(db.String(255), nullable=False, unique=True)
    users = db.relationship('Users')
    facebook_profile = db.relationship('FacebookAccount', back_populates="profile_fb")
    twitter_profile = db.relationship('TwitterAccount', back_populates="profile_tw")

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True) 
    email = db.Column(db.String(255), nullable=False, unique=True)
    _password = db.Column(db.String(255), nullable=False) #hybrid column
    confirmed = db.Column(db.Boolean(), default=False) 
    confirmed_at = db.Column(db.DateTime)
    date_created = db.Column(db.DateTime,  default=datetime.datetime.utcnow)
    date_modified = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    current_login_at = db.Column(db.DateTime)
    current_login_ip = db.Column(db.String(45))
    login_count = db.Column(db.Integer, default=0) 
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id', ondelete='CASCADE'), index=True)

    @hybrid_property 
    def password(self):
        return self._password 

    @password.setter 
    def _set_password(self, plaintext):
        self._password = bcrypt.generate_password_hash(plaintext)

class FacebookAccount(db.Model):
    __tablename__ = "facebook_account"
    id = db.Column(db.Integer, primary_key=True)
    facebook_id = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id', ondelete='CASCADE'), index=True)
    profile_fb = db.relationship('Profile', back_populates="facebook_profile")
    
class TwitterAccount(db.Model):
    __tablename__ = "twitter_account"
    id = db.Column(db.Integer, primary_key=True)
    twitter_id = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id', ondelete='CASCADE'), index=True)
    profile_tw = db.relationship('Profile', back_populates="twitter_profile")
    