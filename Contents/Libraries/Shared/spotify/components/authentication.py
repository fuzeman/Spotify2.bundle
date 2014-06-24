from spotify.components.base import Component

from pyemitter import Emitter
import json
import logging
import re

RE_LANDING = re.compile(
    r"new\sSpotify.Web.Login\(.*?(?P<params>\{.*\}),\s*?\d+,\s*?Spotify\.Web\.App.*?\);",
    re.IGNORECASE | re.DOTALL
)

AUTH_ERRORS = {
    'invalid_credentials': 'Invalid account credentials provided, check your username/password'
}

log = logging.getLogger(__name__)


class Authentication(Component, Emitter):
    auth_host = 'play.spotify.com'
    auth_path = '/xhr/json/auth.php'
    landing_path = '/'

    def __init__(self, sp):
        super(Authentication, self).__init__(sp)

        self.credentials = {'type': 'anonymous'}
        self.landing_params = None

    def login(self, username=None, password=None):
        if username and password:
            self.credentials = {
                'username': username,
                'password': password,
                'type': 'sp'
            }

        self.connect()

    def login_facebook(self, uid, token):
        self.credentials = {
            'fbuid': uid,
            'token': token,
            'type': 'fb'
        }

        self.connect()

    def connect(self):
        self.session.get(
            'https://%s%s' % (self.auth_host, self.landing_path)
        ).add_done_callback(self.on_landing)

    def on_landing(self, future):
        if not self.validate(future):
            return

        res = future.result()

        if res.status_code != 200:
            self.emit('error', 'Landing - error, code %s' % res.status_code)
            return

        log.debug(
            'Landing - success, code: %s, content-type: %s',
            res.status_code,
            res.headers['content-type']
        )

        # Find landing page parameters
        match = RE_LANDING.search(res.content)

        if not match:
            self.emit('error', 'Unable to find parameters on landing page')
            return

        self.landing_params = json.loads(match.group('params'))

        log.debug(
            'Landing - CSRF token: %s, tracking ID: %s',
            self.landing_params['csrftoken'],
            self.landing_params['trackingId']
        )

        # Authenticate with Spotify
        login_payload = {
            'secret': self.landing_params['csrftoken'],
            'trackingId': self.landing_params['trackingId'],
            'landingURL': self.landing_params['tracking']['landingURL'],
            'referrer': self.landing_params['tracking']['referrer'],
            'cf': ''
        }

        login_payload.update(self.credentials)

        self.session.post(
            'https://%s%s' % (self.auth_host, self.auth_path),
            login_payload
        ).add_done_callback(self.on_auth)

    def on_auth(self, future):
        if not self.validate(future):
            return

        res = future.result()

        if res.status_code != 200:
            self.emit('error', 'Authenticate - error, code %s' % res.status_code)
            return

        log.debug(
            'Authenticate - success, code: %s, content-type: %s',
            res.status_code,
            res.headers['content-type']
        )

        data = res.json()

        if data['status'] == 'ERROR':
            error = data.get('error', 'unknown')
            message = data.get('message')

            if not message:
                message = AUTH_ERRORS.get(error, 'Unknown')

            self.emit('error', '%s (%s)' % (message, error))
            return

        self.emit('authenticated', data['config'])

    def validate(self, future):
        ex = future.exception()

        if not ex:
            return True

        if ex.args:
            ex = ex.args[0].reason

        self.emit('close', *ex)
        return False
