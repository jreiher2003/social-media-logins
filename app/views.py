import datetime
from app import app,db,bcrypt 
from flask import redirect, url_for, render_template, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import exc
from models import Users, SocialLogin, UserRegister, AsyncOperation, AsyncOperationStatus, ProviderName, TodoItem
from forms import LoginForm, RegisterForm
from oauth import OAuthLogin
from task import taskman

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new-todo', methods=['GET', 'POST'])
@login_required
def new_todo():
    if request.method == 'POST':
        todo = TodoItem(
            name=request.form['name'],
            deadline_date=datetime.datetime.strptime(request.form['deadline_date'],"%m/%d/%Y").date(),
            users_id=current_user.id)
        db.session.add(todo)
        db.session.commit()
        return redirect(url_for('success'))
    return render_template('new-todo.html', page='new-todo')

@app.route('/mark-done/<int:todo_id>', methods=['POST'])
@login_required
def mark_done(todo_id):
    print todo_id
    if request.method == 'POST':
        todo = TodoItem.query.filter_by(id=todo_id).one()
        print "line 33", todo.id, todo.name, todo.is_done
        todo.is_done = True
        db.session.add(todo)
        db.session.commit()
        return redirect('/success')

# renders a loader page
@app.route('/preloader')
def preloader():
    return render_template('preloader.html')

# renders an error page
@app.route('/error')
def error():
    return render_template('error.html')

@app.route('/add-login')
def add_login_page():
    return render_template('add-login.html')

@app.route("/login/", methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_register = UserRegister.query.filter_by(email=form.email.data).first() 
        if user_register is not None and bcrypt.check_password_hash(user_register.password, form.password.data):
            users = Users.query.filter_by(id=user.users_id).first()
            remember = form.remember.data
            users.login_count += 1
            users.last_login_ip = users.current_login_ip
            users.last_login_at = users.current_login_at
            users.current_login_ip = "10.0.0.1"
            users.current_login_at = datetime.datetime.now()
            print users, users.screen_name, users.id
            db.session.add(users)
            db.session.commit()
    
            login_user(users,remember)
            return redirect(url_for("success"))
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
        users = Users(
            screen_name=form.username.data,
            email=form.email.data,
            login_count = 1,
            current_login_ip = "10.0.0.0",
            current_login_at = datetime.datetime.now(),
            )
        db.session.add(users)
        db.session.commit()
        user_register = UserRegister(
            username = form.username.data,
            email = form.email.data,
            password = form.password.data,
            users_id = users.id 
            )
        db.session.add(user_register)
        db.session.commit()
        login_user(users,True)
        flash("Welcome <strong>%s</strong> to Menu App. Please go to your inbox and confirm your email." % (user_register.username), "success")
        return redirect(url_for("success"))
    return render_template("register.html",form=form)

@app.route('/logout/')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index'))

@app.route("/delete-user/", methods=["POST"])
@login_required
def delete_user():
    if request.method == "POST":
        db.session.query(Users).filter_by(id=current_user.id).delete()
        db.session.query(SocialLogin).filter_by(users_id=current_user.id).delete()
        db.session.query(UserRegister).filter_by(users_id=current_user.id).delete()
        db.session.query(TodoItem).filter_by(users_id=current_user.id).delete()
        db.session.commit()
        session.clear()
        flash("You just deleted your account.", "danger")
        return redirect(url_for('index'))

@app.route("/forgot-password/")
def forgot_password():
    return "forgot-password"

@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthLogin.get_provider(provider)
    return oauth.begin_auth()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    session["provider"] = str(provider)
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    # store in the session id of the asynchronous operation
    status_pending = AsyncOperationStatus.query.filter_by(code='pending').first()
    provider_name = ProviderName.query.filter_by(name=provider).first()
    async_operation = AsyncOperation(async_operation_status_id=status_pending.id, provider_name_id=provider_name.id)
    db.session.add(async_operation)
    db.session.commit()
    # store in a session the id of asynchronous operation
    session['async_operation_id'] = str(async_operation.id)
    taskman.add_task(external_auth, provider)
    return redirect(url_for('preloader'))

# returns status of the async operation in facebookAuthStatus.js
@app.route('/get-status')
def get_status():
    if 'async_operation_id' in session:
        async_operation_id = session['async_operation_id']
        print 'line 143', async_operation_id
        # retrieve from database the status of the stored in session async operation
        async_operation = AsyncOperation.query.filter_by(id=async_operation_id).first()
        code = async_operation.async_operation_status_id
        print code, type(code)
        s = AsyncOperationStatus.query.filter_by(id=code).first()
        status = s.code 
        print status
    else:
        print "async operation not in session"
        return redirect(url_for(error))
    return status

def external_auth(provider):   
    # provider = session["provider"]     
    oauth = OAuthLogin.get_provider(provider)
    provider, social_id, username, email = oauth.get_user_data()
    print provider, social_id, username, email
    if social_id is None:
        flash('Authentication failed.')
        status_error = AsyncOperationStatus.query.filter_by(name="error").first()
        async_operation = AsyncOperation.query.filter_by(id=int(session['async_operation_id'])).first()
        async_operation.async_operation_status_id = status_error.id 
        db.session.add(async_operation)
        db.session.commit()
        return redirect(url_for('index'))
    try:
        #brings up user by soical media login id
        social_login = SocialLogin.query.filter_by(social_login_id=social_id).first()
        print "line 173", social_login.social_login_id
    except AttributeError:
        social_login = None
    if social_login is None:
        if not current_user.is_active:
            # user logs in via oauth for the first time via social media and no register
            user = Users(
                    screen_name=username,
                    email=email,
                    login_count = 1,
                    current_login_ip = "10.0.0.0",
                    current_login_at = datetime.datetime.now(),
                    ) 
            db.session.add(user)
            db.session.commit()
            provider_name = ProviderName.query.filter_by(name=provider).first()
            print "line 193", provider_name.name 
            social_login = SocialLogin(social_login_id=social_id, name=username, email=email, users_id=user.id, provider_name_id=provider_name.id)
            db.session.add(social_login)
            db.session.commit()
        else:
            # user is logged but has not connected a social account 
            user = Users.query.filter_by(id=current_user.id).first()
            provider_name = ProviderName.query.filter_by(name=provider).first()
            print "line 202", provider_name.name 
            social_login = SocialLogin(social_login_id=social_id, name=username, email=email, users_id=user.id, provider_name_id=provider_name.id)
            db.session.add(social_login)
            db.session.commit()
            print "add a new social_login 201" 
    # user is already logged in via social and wants to connect more social accounts
    elif current_user.is_active:
        todo_items = db.session.query(TodoItem).join(Users).join(SocialLogin).filter_by(social_login_id=social_id).all()
        for todo_item in todo_items:
            todo_item.users_id = current_user.id 
            db.session.add(todo_item)
        # existing user login
        social_login = SocialLogin.query.filter_by(social_login_id=social_id).first() 
        print "line 209", social_login.social_login_id 
        # other user logins that are be connected to the same account like the login that user wants to connect
        social_logins = SocialLogin.query.filter_by(users_id=social_login.users_id).all()
        for login in social_logins:
            login.users_id = current_user.id 
            db.session.add(social_login)
        db.session.commit()
    # user is logging in via social media for 2nd time or more
    # change the status of the async operation for 'ok' and insert the value of the user id
    # to the async_operation table
    status_ok = AsyncOperationStatus.query.filter_by(code='ok').first()
    async_operation = AsyncOperation.query.filter_by(id=int(session['async_operation_id'])).first()
    async_operation.async_operation_status_id = status_ok.id
    print "line 221", social_login.id
    async_operation.social_id = social_login.id#SocialLogin.query.filter_by(id=social_login.id).first()
    db.session.add(async_operation)
    db.session.commit()

@app.route('/success')
def success():
    if 'async_operation_id' in session:
        async_operation_id = int(session['async_operation_id'])
        async_operation = AsyncOperation.query.filter_by(id=async_operation_id).join(SocialLogin).first()
        social_login = SocialLogin.query.filter_by(id=async_operation.social_id).first()
        users = Users.query.filter_by(id = social_login.users_id).first()
        users.login_count += 1
        users.last_login_ip = users.current_login_ip
        users.last_login_at = users.current_login_at
        users.current_login_ip = "10.0.0.1"
        users.current_login_at = datetime.datetime.now()
        print "line 238", users, users.screen_name, users.id
        db.session.add(users)
        db.session.commit()
        login_user(users, True)
    print "line 242"
    connected_providers = db.session.query(ProviderName.name).join(SocialLogin).join(Users).filter_by(id=current_user.id).all()
    subquery = db.session.query(ProviderName.name).join(SocialLogin).join(Users).filter_by(id=current_user.id).subquery()
    unconnected_providers = db.session.query(ProviderName.name).filter(~ProviderName.name.in_(subquery)).all()
    todos = TodoItem.query.filter_by(users_id=current_user.id).all()
    return render_template('my-logins.html', connected_providers=connected_providers,
                           unconnected_providers=unconnected_providers, todos=todos)