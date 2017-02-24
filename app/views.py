import datetime
from app import app,db,bcrypt 
from flask import redirect, url_for, render_template, flash, request, session
from flask_login import login_user, logout_user, current_user
from sqlalchemy import exc
from models import Profile, FacebookAccount, TwitterAccount, Users, AsyncOperation, AsyncOperationStatus
from forms import LoginForm, RegisterForm
from oauth import OAuthSignIn
from task import taskman

@app.route('/')
def index():
    return render_template('index.html')

# renders a loader page
@app.route('/preloader')
def preloader():
    return render_template('preloader.html')

# renders an error page
@app.route('/error')
def error():
    return render_template('error.html')

@app.route("/login/", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first() 
        if user is not None and bcrypt.check_password_hash(user.password, form.password.data):
            profile = Profile.query.filter_by(id=user.profile_id).first()
            remember = form.remember.data
            profile.login_count += 1
            profile.last_login_ip = profile.current_login_ip
            profile.last_login_at = profile.current_login_at
            profile.current_login_ip = "10.0.0.1"
            profile.current_login_at = datetime.datetime.now()
            print profile, profile.screen_name, profile.id
            db.session.add(profile)
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
        profile = Profile(
            screen_name=form.username.data,
            email=form.email.data,
            login_count = 1,
            current_login_ip = "10.0.0.0",
            current_login_at = datetime.datetime.now(),
            )
        db.session.add(profile)
        db.session.commit()
        user = Users(
            username = form.username.data,
            email = form.email.data,
            password = form.password.data,
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
    session["provider"] = str(provider)
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    # store in the session id of the asynchronous operation
    status_pending = AsyncOperationStatus.query.filter_by(code='pending').first()
    async_operation = AsyncOperation(async_operation_status_id=status_pending.id)
    db.session.add(async_operation)
    db.session.commit()
    # store in a session the id of asynchronous operation
    session['async_operation_id'] = str(async_operation.id)
    taskman.add_task(external_auth)
    return redirect(url_for('preloader'))

# returns status of the async operation in facebookAuthStatus.js
@app.route('/get-status')
def get_status():
    if 'async_operation_id' in session:
        async_operation_id = session['async_operation_id']
        print async_operation_id
        # retrieve from database the status of the stored in session async operation
        async_operation = AsyncOperation.query.filter_by(id=async_operation_id).join(AsyncOperationStatus).first()
        status = str(async_operation.status.code)
        print async_operation.status.code
    else:
        print "async operation not in session"
        return redirect(url_for(error))
    return status

def external_auth():   
    provider = session["provider"]     
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
                user = Profile(
                    screen_name=username,
                    email=email,
                    login_count = 1,
                    current_login_ip = "10.0.0.0",
                    current_login_at = datetime.datetime.now(),
                    ) 
                db.session.add(user)
                db.session.commit()
                fb_user = FacebookAccount(profile_id=user.id,facebook_id=social_id,name = username,email = email)
                db.session.add(fb_user)
                db.session.commit()
                # change the status of the async operation for 'ok' and insert the value of the user id
                # to the async_operation table
                status_ok = AsyncOperationStatus.query.filter_by(code='ok').first()
                async_operation = AsyncOperation.query.filter_by(id=session['async_operation_id']).first()
                async_operation.async_operation_status_id = status_ok.id
                async_operation.facebook_account_id = fb_user.id
                db.session.add(async_operation)
                db.session.commit()
            except exc.IntegrityError:
                flash("The email you use for facebook is already registered in our system.  Login and merge your facebook acouunt in your profile section", "warning")
                return redirect(url_for('login'))
        status_ok = AsyncOperationStatus.query.filter_by(code='ok').first()
        async_operation = AsyncOperation.query.filter_by(id=session['async_operation_id']).first()
        async_operation.async_operation_status_id = status_ok.id
        async_operation.facebook_account_id = user.id
        db.session.add(async_operation)
        db.session.commit()
    if provider == "twitter":
        user = Profile.query.join(TwitterAccount,Profile.id==TwitterAccount.profile_id).filter(TwitterAccount.twitter_id==social_id).first()
        if user is None:
            try:
                user = Profile(screen_name=username,email="")
                db.session.add(user)
                db.session.commit()
                tw_user = TwitterAccount(profile_id=user.id, twitter_id=social_id, name=username)
                db.session.add(tw_user)
                db.session.commit()
                status_ok = AsyncOperationStatus.query.filter_by(code='ok').first()
                async_operation = AsyncOperation.query.filter_by(id=session['async_operation_id']).first()
                async_operation.async_operation_status_id = status_ok.id
                async_operation.twitter_account_id = tw_user.id
                db.session.add(async_operation)
                db.session.commit()
            except exc.IntegrityError:
                flash("The email you use for facebook is already registered in our system.  Login and merge your facebook acouunt in your profile section", "warning")
                return redirect(url_for('login'))
        status_ok = AsyncOperationStatus.query.filter_by(code='ok').first()
        async_operation = AsyncOperation.query.filter_by(id=session['async_operation_id']).first()
        async_operation.async_operation_status_id = status_ok.id
        async_operation.twitter_account_id = user.id
        db.session.add(async_operation)
        db.session.commit()

    

@app.route('/success')
def success():
    if 'async_operation_id' and 'facebook' in session:
        async_operation_id = session['async_operation_id']
        async_operation = AsyncOperation.query.filter_by(id=async_operation_id).join(FacebookAccount).first()
        fb = FacebookAccount.query.filter_by(id=async_operation.facebook_account_id).first()
        profile = Profile.query.filter_by(id = fb.profile_id).first()
        profile.login_count += 1
        profile.last_login_ip = profile.current_login_ip
        profile.last_login_at = profile.current_login_at
        profile.current_login_ip = "10.0.0.1"
        profile.current_login_at = datetime.datetime.now()
        print profile, profile.screen_name, profile.id
        db.session.add(profile)
        db.session.commit()
        login_user(profile, True)
    if 'async_operation_id' and 'twitter' in session:
        async_operation_id = session['async_operation_id']
        async_operation = AsyncOperation.query.filter_by(id=async_operation_id).join(TwitterAccount).first()
        tw = TwitterAccount.query.filter_by(id=async_operation.twitter_account_id).first()
        profile = Profile.query.filter_by(id = tw.profile_id).first()
        profile.login_count += 1
        profile.last_login_ip = profile.current_login_ip
        profile.last_login_at = profile.current_login_at
        profile.current_login_ip = "10.0.0.1"
        profile.current_login_at = datetime.datetime.now()
        print profile, profile.screen_name, profile.id
        db.session.add(profile)
        db.session.commit()
        login_user(profile, True)
    return redirect(url_for('index'))