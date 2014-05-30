from plugin.util import log_progress, func_catch

from threading import Thread
from urllib2 import Request, urlopen
import logging
import time

log = logging.getLogger(__name__)


class Stream(object):
    buffer_wait_ms = 100
    buffer_wait = buffer_wait_ms / 1000.0

    def __init__(self, track, num, start, end):
        self.track = track
        self.num = num

        self.start = start
        self.end = end

        self.request = None

        self.response = None
        self.headers = None
        self.length = None

        self.thread = None
        self.buffer = bytearray()

        self.opened = False
        self.reading = False

    def log(self, message, *args, **kwargs):
        header = '[%s] [%s] ' % (self.track.uri, self.num)
        log.info(header + str(message), *args, **kwargs)

    def prepare(self):
        headers = {}

        if self.start or self.end:
            headers['Range'] = 'bytes=%s-%s' % (
                self.start or '',
                self.end or ''
            )

        self.request = Request(self.track.info['uri'], headers=headers)

    def open(self):
        if self.opened:
            return

        self.opened = True

        self.prepare()
        self.response = urlopen(self.request)

        self.headers = self.response.info()

        self.log('Opened')

        self.length = int(self.headers.getheader('Content-Length'))
        self.log('Content-Length: %s', self.length)

        if self.headers.getheader('Content-Type') == 'text/xml':
            # Error, log response
            self.log(self.response.read())
            return

        # Read back entire stream
        self.thread = Thread(target=func_catch, args=(self.run,))
        self.thread.start()

    def read(self, position, chunk_size=1024):
        self.track.on_read()

        while self.reading and len(self.buffer) < position + 1:
            time.sleep(self.buffer_wait)

        return self.buffer[position:position + chunk_size]

    def run(self):
        chunk_size = 1024
        last_progress = None

        self.reading = True

        self.log('Reading...')

        while True:
            chunk = self.response.read(chunk_size)

            self.buffer.extend(chunk)

            if not chunk:
                break

            last_progress = log_progress(self, '[%s]   Reading' % self.num, len(self.buffer), last_progress)

        self.reading = False
        self.log('Read finished')
