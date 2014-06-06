from spotify.core.helpers import set_defaults
from spotify.tunigo.response import TunigoResponse

from pyemitter import Emitter
import urllib
import time
import logging

log = logging.getLogger(__name__)


class TunigoRequest(Emitter):
    base_url = "https://api.tunigo.com/v3/space/%s?%s"
    base_params = {
        'suppress_response_codes': 1,
        'locale':   'en',
        'product':  'premium',
        'version':  '6.31.1',
        'platform': 'web'
    }

    def __init__(self, sp, name, params):
        self.sp = sp
        self.name = name
        self.params = params

        self.url = None

        self.prepare()

    def send(self):
        self.sp.session.get(self.url)\
            .add_done_callback(self.process)

        return self

    def process(self, future):
        ex = future.exception()

        if ex:
            self.emit('error', ex)
            return

        res = future.result()

        if res.status_code != 200:
            self.emit('error', 'request failed - status code: %s', res.status_code)
            return

        response = TunigoResponse.construct(self.sp, res.json())
        self.emit('success', response)

    def prepare(self):
        params = set_defaults(self.params, self.base_params)
        params['dt'] = time.strftime("%Y-%m-%dT%H:%M:%S")
        params['region'] = self.sp.country or 'us'

        query = urllib.urlencode(params)

        self.url = self.base_url % (
            self.name, query
        )
