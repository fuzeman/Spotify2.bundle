from plugin.range import ContentRange
from plugin.util import log_progress, func_catch

from pyemitter import Emitter
from threading import Thread, Event
from requests import Request
import logging
import time

log = logging.getLogger(__name__)


class Stream(Emitter):
    chunk_size = 8192

    def __init__(self, track, num, r_range):
        """
        :type track: plugin.track.Track
        :type num: int
        :type r_range: plugin.range.Range
        """
        self.track = track
        self.server = track.server

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

        # Data buffering
        self.read_thread = None
        self.read_sleep = None

        self.buffer = bytearray()

        self.on_reading = Event()
        self.state = ''

    def log(self, message, *args, **kwargs):
        header = '[%s] [%s] ' % (self.track.uri, self.num)
        log.info(header + str(message), *args, **kwargs)

    def prepare(self):
        headers = {}

        if self.range:
            headers['Range'] = str(self.range)

        return headers

    def open(self):
        if self.state != '':
            return

        self.state = 'opening'
        self.emit('opening')

        future = self.server.session.get(
            self.track.info['uri'],
            headers=self.prepare(),
            stream=True
        )
        future.add_done_callback(self.callback)

    def callback(self, future):
        ex = future.exception()

        if ex:
            log.error('Request failed: %s', ex)
            return

        self.response = future.result()
        self.headers = self.response.headers

        self.state = 'opened'
        self.emit('opened')

        self.content_length = int(self.headers.get('Content-Length'))
        self.log('Content-Length: %s', self.content_length)

        self.content_range = ContentRange.parse(self.headers.get('Content-Range'))
        self.log('Content-Range: %s', self.content_range)

        if self.content_range:
            self.total_length = self.content_range.length
        else:
            # Build dummy ContentRange
            self.content_range = ContentRange(
                start=0,
                end=self.content_length - 1,
                length=self.content_length
            )

            self.total_length = self.content_length

        self.log('Total-Length: %s', self.total_length)

        if self.headers.get('Content-Type') == 'text/xml':
            # Error, log response
            self.log(self.response.content)
            return

        # Read back entire stream
        self.read_thread = Thread(target=func_catch, args=(self.run,))
        self.read_thread.start()

    def run(self):
        self.state = 'reading'
        self.emit('reading')
        self.on_reading.set()

        last_progress = None

        for chunk in self.response.iter_content(self.chunk_size):
            self.buffer.extend(chunk)
            self.emit('received', len(chunk))

            last_progress = log_progress(self, '[%s]   Reading' % self.num, len(self.buffer), last_progress)

        self.state = 'buffered'
        self.emit('buffered')

    def iter(self, c_range):
        """
        :type c_range: plugin.range.ContentRange
        """
        position = 0
        end = self.content_range.end + 1

        last_progress = None
        ev_received = Event()

        @self.on('received')
        def on_received(chunk_size):
            ev_received.set()

        if c_range:
            position = c_range.start - self.content_range.start
            end = (c_range.end - self.content_range.start) + 1

            log.debug(
                '[%s] [%s] Streaming - c_range: %s, position: %s, end: %s',
                self.track.uri, self.num,
                c_range, position, end
            )

        while position < self.content_length:
            data = self.buffer[position:]

            if data:
                last_progress = log_progress(self, '[%s] Streaming' % self.num, position, last_progress, length=end)
                position += len(data)
                yield str(data)
            elif self.state != 'buffered':
                ev_received.clear()
                ev_received.wait()
            else:
                break

        self.off('received', on_received)

        log.info('[%s] [%s] Complete', self.track.uri, self.num)
