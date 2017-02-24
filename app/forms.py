from flask_wtf import FlaskForm, RecaptchaField
from wtforms.validators import Email, Length, EqualTo, DataRequired
from wtforms import PasswordField, BooleanField, SubmitField, TextField
from wtforms.fields.html5 import EmailField

from app.models import Users,FacebookAccount

class LoginForm(FlaskForm):
    email = EmailField("Email", [DataRequired(), Email()])
    password = PasswordField("Password", [DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    username = TextField("Username",  [DataRequired()])
    email = EmailField("Email", [DataRequired(), Email()])
    password = PasswordField("Password", [DataRequired(), Length(min=6, message="The min password length is 6 chars long.")])
    password_confirm = PasswordField("Confirm", [DataRequired(), EqualTo("password", message="Your passwords don't match.")])
    submit = SubmitField("Register")

    def validate(self):
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = Users.query.filter_by(email=self.email.data).first()
        fb_user = FacebookAccount.query.filter_by(email=self.email.data).first()
        if user or fb_user:
            self.email.errors.append("Email already registered")
            return False
        return True