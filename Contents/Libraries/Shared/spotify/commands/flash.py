from spotify.commands.base import Command

import logging
import urllib

log = logging.getLogger(__name__)


class PingFlash2(Command):
    host = 'spflash.herokuapp.com'

    def process(self, ping):
        version = self.sp.config.get('cdn')

        if version:
            pos = version.rfind('/')

            if pos >= 0:
                version = version[pos + 1:]
            else:
                version = None

        if not version:
            version = 'generic'

        self.session.get(
            'http://%s/%s/get?ping=%s' % (
                self.host, version,
                urllib.quote(ping)
            )
        ).add_done_callback(self.on_result)

    def on_result(self, future):
        if not self.validate(future):
            return

        res = future.result()

        # Validate response
        if res.status_code != 200:
            # 503 = Backend service timeout
            if res.status_code == 503:
                self.emit('error', 'PingFlash2 - service unavailable')
                return

            self.emit('error', 'PingFlash2 - service returned unexpected status code (%s)' % res.status_code)
            return

        if not res.text:
            self.emit('error', 'PingFlash2 - response doesn\'t look valid')
            return

        self.send('sp/pong_flash2', res.text)

    def validate(self, future):
        ex = future.exception()

        if not ex:
            return True

        if ex.args:
            ex = ex.args[0].reason

        self.emit('close', *ex)
        return False
