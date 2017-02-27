from flask_wtf import FlaskForm, RecaptchaField
from wtforms.validators import Email, Length, EqualTo, DataRequired
from wtforms import PasswordField, BooleanField, SubmitField, TextField
from wtforms.fields.html5 import EmailField
from app.models import UserRegister, SocialLogin

def validate_username(form, field): 
    user = UserRegister.query.filter_by(username=field.data).first()
    if user:
        field.errors.append("Username already registered!")
        return False
    return True

def validate_email(form, field):
    user = UserRegister.query.filter_by(email=field.data).first()
    if user:
        field.errors.append("Email already registered!")
        return False
    return True

class LoginForm(FlaskForm):
    email = EmailField("Email", [DataRequired(), Email()])
    password = PasswordField("Password", [DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    username = TextField("Username",  [DataRequired(), validate_username])
    email = EmailField("Email", [DataRequired(), Email(), validate_email])
    password = PasswordField("Password", [DataRequired(), Length(min=6, message="The min password length is 6 chars long.")])
    password_confirm = PasswordField("Confirm", [DataRequired(), EqualTo("password", message="Your passwords don't match.")])
    submit = SubmitField("Register")



    