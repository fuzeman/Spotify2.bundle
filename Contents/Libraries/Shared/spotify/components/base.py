from requests_futures.sessions import FuturesSession
import logging

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36'

log = logging.getLogger(__name__)


class Component(object):
    def __init__(self, sp=None):
        self.sp = sp

        self.session = None

        # Inherit session from global
        if self.sp:
            self.session = self.sp.session

    def create_session(self, user_agent):
        self.session = FuturesSession()

        # Update headers
        self.session.headers.update({
            'User-Agent': user_agent or USER_AGENT
        })

    def send(self, name, *args):
        return self.sp.send(name, *args)

    def build(self, name, *args):
        return self.sp.build(name, *args)

    def send_request(self, request):
        return self.sp.send_request(request)

    def send_message(self, message):
        self.sp.send(message)

    @staticmethod
    def request_wrapper(request, callback=None):
        def on_error(func, *args):
            log.debug('Error %s returned for request: %s', repr(args), request)

            if func:
                func(None)

        def on_bound(func):
            # Bind to 'error' (so we know the real callback 'func')
            request.on('error', lambda *args: on_error(func, *args))

            # Send request
            request.send()

        return request.on(
            'success', callback,
            on_bound=on_bound
        )
