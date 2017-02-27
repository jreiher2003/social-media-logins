import random
from flask import current_app, url_for, request, session
from rauth import OAuth2Service, OAuth1Service
import json
from werkzeug.utils import redirect


class OAuthLogin(object):
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.client_id = credentials['id']
        self.client_secret = credentials['secret']

    # user is redirected to the provider's page to authenticate there
    def begin_auth(self):
        pass

    def get_url_with_authorization_code(self):
        return url_for('oauth_callback', provider=self.provider_name, _external=True)

    def get_user_data(self):
        pass

    @classmethod
    def get_provider(cls, provider_name):
        if cls.providers is None:
            cls.providers = {}
            for provider_class in cls.__subclasses__():
                # print cls.__subclasses__()
                provider = provider_class()
                cls.providers[provider.provider_name] = provider
        return cls.providers[provider_name]


class FacebookLogin(OAuthLogin):
    def __init__(self):
        super(FacebookLogin, self).__init__('facebook')
        self.service = OAuth2Service(
                name='facebook',
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_url='https://graph.facebook.com/oauth/authorize',
                access_token_url='https://graph.facebook.com/oauth/access_token',
                base_url='https://graph.facebook.com/'
        )

    def begin_auth(self):
        return redirect(self.service.get_authorize_url(
                scope='public_profile,email',
                response_type='code',
                redirect_uri=self.get_url_with_authorization_code()
        ))

    def get_user_data(self):
        if 'code' not in request.args:
            return None, None, None, None#, None, None
        oauth_session = self.service.get_auth_session(
                data={'code': request.args['code'],
                      'grant_type': 'authorization_code',
                      'redirect_uri': self.get_url_with_authorization_code()})
        me = oauth_session.get('me?fields=id,email,name,gender,age_range,picture').json()
        # print me['name'], me['gender'],me['age_range'],me['picture']['data']['url']
        return (
            'facebook',
            'facebook$' + str(me['id']),
            me.get('name'),  
            me.get('email'),
            # None,
            # None,
        )


class TwitterSignIn(OAuthLogin):
    def __init__(self):
        super(TwitterSignIn, self).__init__('twitter')
        self.service = OAuth1Service(
            name='twitter',
            consumer_key=self.client_id,
            consumer_secret=self.client_secret,
            request_token_url='https://api.twitter.com/oauth/request_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            access_token_url='https://api.twitter.com/oauth/access_token',
            base_url='https://api.twitter.com/1.1/'
        )

    def begin_auth(self):
        request_token = self.service.get_request_token(
            params={'oauth_callback': self.get_url_with_authorization_code()}
        )
        session['request_token'] = request_token
        return redirect(self.service.get_authorize_url(request_token[0]))

    def get_user_data(self):
        request_token = session.pop('request_token')
        if 'oauth_verifier' not in request.args:
            return None, None, None, None#, None, None
        oauth_session = self.service.get_auth_session(
            request_token[0],
            request_token[1],
            data={'oauth_verifier': request.args['oauth_verifier']}
        )
        me = oauth_session.get('account/verify_credentials.json').json()
        social_id = 'twitter$' + str(me.get('id'))
        username = me.get('screen_name')
        return 'twitter', social_id, username, None#, None, None   # Twitter does not provide email

class LinkedinLogin(OAuthLogin):
    def __init__(self):
        super(LinkedinLogin, self).__init__('linkedin')
        self.service = OAuth2Service(
                name='linkedin',
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_url='https://www.linkedin.com/uas/oauth2/authorization',
                access_token_url='https://www.linkedin.com/uas/oauth2/accessToken',
                base_url='https://api.linkedin.com/v1/'
        )

    def begin_auth(self):
        return redirect(self.service.get_authorize_url(
                scope='r_emailaddress r_basicprofile',
                response_type='code',
                state=''.join(str(random.randrange(9)) for _ in range(24)),
                redirect_uri=self.get_url_with_authorization_code()
        ))

    def get_user_data(self):
        if 'code' not in request.args:
            return None, None, None, None#, None, None
        data = {'code': request.args['code'],
                      'grant_type': 'authorization_code',
                      'redirect_uri': self.get_url_with_authorization_code()}
        json_decoder = json.loads
        params = {'decoder': json_decoder,
                  'bearer_auth': False}
        session = self.service.get_auth_session(data=data, **params)
        r = session.get('people/~:(id,email-address,first-name,last-name)', params={
                        'format': 'json',
                        'oauth2_access_token': session.access_token}, bearer_auth=False)
        me = r.json()
        email = me['emailAddress']
        first_name = me['firstName']
        last_name = me['lastName']
        return (
            'linkedin',
            'linkedin$' + str(me['id']),
            first_name + ' ' + last_name,
            email,
            # first_name,
            # last_name,
        )

class GithubLogin(OAuthLogin):
    def __init__(self):
        super(GithubLogin, self).__init__('github')
        self.service = OAuth2Service(
                name='github',
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_url='https://github.com/login/oauth/authorize',
                access_token_url='https://github.com/login/oauth/access_token',
                base_url='https://api.github.com'
        )

    def begin_auth(self):
        return redirect(self.service.get_authorize_url(
                scope='user',
                response_type='code',
                redirect_uri=self.get_url_with_authorization_code()
        ))

    def get_user_data(self):
        if 'code' not in request.args:
            return None, None, None, None#, None, None
        oauth_session = self.service.get_auth_session(
                data={'code': request.args['code'],
                      'grant_type': 'authorization_code',
                      'redirect_uri': self.get_url_with_authorization_code()})
        me = oauth_session.get('user?fields=email,name,login').json()
        return (
            'github',
            'github$' + str(me['id']),
            me.get('name'),
            me.get('email'),
            # me.get('login')
            # me.get('name').split()[0],
        )

class GoogleLogin(OAuthLogin):
    def __init__(self):
        super(GoogleLogin, self).__init__('google')
        self.service = OAuth2Service(
                name='google',
                client_id=self.client_id,
                client_secret=self.client_secret,
                authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
                access_token_url='https://www.googleapis.com/oauth2/v4/token',
                base_url='https://www.googleapis.com'
        )

    def begin_auth(self):
        return redirect(self.service.get_authorize_url(
                scope='email profile',
                response_type='code',
                redirect_uri=self.get_url_with_authorization_code()
        ))

    def get_user_data(self):
        if 'code' not in request.args:
            return None, None, None, None
        data = {'code': request.args['code'],
                      'grant_type': 'authorization_code',
                      'redirect_uri': self.get_url_with_authorization_code()}
        response = self.service.get_raw_access_token(data=data)
        response = response.json()
        oauth2_session = self.service.get_session(response['access_token'])
        me = oauth2_session.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        first_name = me.get('given_name')
        last_name = me.get('family_name')
        return (
            'google',
            'google$' + str(me['id']),
            me.get('name'),
            me.get('email'),
            # first_name,
            # last_name,
            # None
        )