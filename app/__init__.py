import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config["DEBUG"] = True
app.config['OAUTH_CREDENTIALS'] = {
    'facebook': {
        'id': '231015064035835',
        'secret': 'd688bfa5a4488201d316cf0acddd45d7'
    },
    'twitter': {
        'id': 'XIhymb80u5I7D6cCqomQue3HB',
        'secret': 'bthFdmSejZ8SvRtOJ7GkgyGMySqCK6Y4JbZx4DuG2RRq1NcPRA'
    }
}

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
lm = LoginManager(app)
from app import views
from app.models import Profile

lm.login_view = 'index'

@lm.user_loader
def load_user(id):
    return Profile.query.get(int(id))