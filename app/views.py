import datetime
from app import app,db,bcrypt 
from flask import redirect, url_for, render_template, flash, request
from flask_login import login_user, logout_user, current_user
from sqlalchemy import exc
from oauth import OAuthSignIn
from models import Profile, FacebookAccount, TwitterAccount, Users
from forms import LoginForm, RegisterForm

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login/", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first() 
        if user is not None and bcrypt.check_password_hash(user.password, form.password.data):
            remember = form.remember.data
            user.login_count += 1
            user.last_login_ip = user.current_login_ip
            user.last_login_at = user.current_login_at
            user.current_login_ip = "10.0.0.1"
            user.current_login_at = datetime.datetime.now()
            profile = Profile.query.filter_by(id=user.profile_id).first()
            print profile, profile.screen_name, profile.id
            db.session.add(user)
            db.session.commit()
    
            login_user(profile,remember)
            return redirect(url_for("index"))
        else:
            flash("<strong>Invalid Credentials.</strong> Please try again.", "danger")
            return redirect(url_for("login"))
    return render_template(
        "login.html",
        form=form
        )

@app.route("/register/", methods=["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        profile = Profile(screen_name=form.username.data,email=form.email.data)
        db.session.add(profile)
        db.session.commit()
        user = Users(
            username = form.username.data,
            email = form.email.data,
            password = form.password.data,
            login_count = 1,
            current_login_ip = "10.0.0.0",
            current_login_at = datetime.datetime.now(),
            profile_id = profile.id 
            )
        db.session.add(user)
        db.session.commit()
        login_user(profile,True)
        flash("Welcome <strong>%s</strong> to Menu App. Please go to your inbox and confirm your email." % (user.username), "success")
        return redirect(url_for("index"))
    return render_template("register.html",form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/forgot-password/")
def forgot_password():
    return "forgot-password"

@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()

@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    provider, social_id, username, email = oauth.callback()
    print provider, social_id, username, email
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    if provider == "facebook":
        user = Profile.query.join(FacebookAccount,Profile.id==FacebookAccount.profile_id).filter(FacebookAccount.facebook_id==social_id).first() 
        if user is None:
            try:
                user = Profile(screen_name=username,email=email) 
                db.session.add(user)
                db.session.commit()
                fb_user = FacebookAccount(profile_id=user.id,facebook_id=social_id,name = username,email = email)
                db.session.add(fb_user)
                db.session.commit()
            except exc.IntegrityError:
                flash("The email you use for facebook is already registered in our system.  Login and merge your facebook acouunt in your profile section", "warning")
                return redirect(url_for('login'))
    if provider == "twitter":
        user = Profile.query.join(TwitterAccount,Profile.id==TwitterAccount.profile_id).filter(TwitterAccount.twitter_id==social_id).first()
        if user is None:
            user = Profile(screen_name=username,email="")
            db.session.add(user)
            db.session.commit()
            tw_user = TwitterAccount(profile_id=user.id, twitter_id=social_id, name=username)
            db.session.add(tw_user)
            db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))