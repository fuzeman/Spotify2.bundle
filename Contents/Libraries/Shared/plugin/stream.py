from plugin.range import ContentRange
from plugin.util import log_progress, func_catch

from threading import Thread
from urllib2 import Request, urlopen
import logging
import time

log = logging.getLogger(__name__)


class Stream(object):
    buffer_wait_ms = 100
    buffer_wait = buffer_wait_ms / 1000.0

    chunk_size_min = 6 * 1024
    chunk_size_max = 10 * 1024

    def __init__(self, track, num, r_range):
        """
        :type track: plugin.track.Track
        :type num: int
        :type r_range: plugin.range.Range
        """
        # Stream request
        self.track = track
        self.num = num
        self.range = r_range

        # HTTP request/response
        self.request = None
        self.response = None
        self.headers = None

        # Content info
        self.content_range = None
        self.content_length = None
        self.total_length = None

        # Read buffer
        self.thread = None
        self.buffer = bytearray()

        # State
        self.opened = False
        self.reading = False

    def log(self, message, *args, **kwargs):
        header = '[%s] [%s] ' % (self.track.uri, self.num)
        log.info(header + str(message), *args, **kwargs)

    def prepare(self):
        headers = {}

        if self.range:
            headers['Range'] = str(self.range)

        self.request = Request(self.track.info['uri'], headers=headers)

    def open(self):
        if self.opened:
            return

        self.opened = True

        self.prepare()
        self.response = urlopen(self.request)

        self.headers = self.response.info()

        self.log('Opened')

        self.content_length = int(self.headers.getheader('Content-Length'))
        self.log('Content-Length: %s', self.content_length)

        self.content_range = ContentRange.parse(self.headers.getheader('Content-Range'))
        self.log('Content-Range: %s', self.content_range)

        if self.content_range:
            self.total_length = self.content_range.length
        else:
            # Build dummy ContentRange
            self.content_range = ContentRange(
                start=0,
                end=self.content_length,
                length=self.content_length
            )

            self.total_length = self.content_length

        self.log('Total-Length: %s', self.total_length)

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

    def iter(self, c_range):
        """
        :type c_range: plugin.range.ContentRange
        """
        position = 0
        end = None

        chunk_scale = 0
        chunk_size = self.chunk_size_min

        last_progress = None

        if c_range:
            log.debug('[%s] [%s] Streaming Content-Range: %s', self.track.uri, self.num, c_range)

            position = c_range.start - self.content_range.start
            log.debug('[%s] [%s] Position: %s', self.track.uri, self.num, position)

        while True:
            # Adjust chunk_size
            if chunk_scale < 1:
                chunk_scale = 2 * (float(position) / self.content_length)
                chunk_size = int(self.chunk_size_min + (self.chunk_size_max * chunk_scale))

                if chunk_scale > 1:
                    chunk_scale = 1

            if position + chunk_size > self.content_length:
                chunk_size = self.content_length - position

            # Read chunk
            chunk = self.read(position, chunk_size)

            if not chunk:
                log.info('[%s] [%s] Finished at %s bytes (content-length: %s)' % (self.track.uri, self.num, position, self.content_length))
                break

            last_progress = log_progress(self, '[%s] Streaming' % self.num, position, last_progress)

            position = position + len(chunk)

            # Write chunk
            yield chunk

        log.info('[%s] [%s] Complete', self.track.uri, self.num)
