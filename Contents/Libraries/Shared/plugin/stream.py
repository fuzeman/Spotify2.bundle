from plugin.range import ContentRange
from plugin.util import log_progress, func_catch

from pyemitter import Emitter
from threading import Thread, Event, Lock
from revent import REvent
import logging

log = logging.getLogger(__name__)


class Stream(Emitter):
    chunk_size = 10240  # 10kB

    def __init__(self, track, num, r_range):
        """
        :type track: plugin.track.Track
        :type num: int
        :type r_range: plugin.range.Range
        """
        self.track = track
        self.server = track.server

        self.stream_num = num
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
        self.read_event = Event()
        self.read_sleep = None

        self.buffer = bytearray()

        self.on_reading = REvent()
        self.state = ''

        self.request_lock = Lock()
        self.request_seq = 0

    def log(self, message, *args, **kwargs):
        header = '[%s] [%s] ' % (self.track.uri, self.stream_num)
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
            log.warn('Request failed: %s', ex)
            self.on_reading.set(False)
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
            self.on_reading.set(False)
            return

        # Read back entire stream
        self.read_event.set()

        self.read_thread = Thread(target=func_catch, args=(self.run,))
        self.read_thread.start()

    def run(self):
        self.state = 'reading'
        self.emit('reading')
        self.on_reading.set(True)

        last_progress = None

        for chunk in self.response.iter_content(self.chunk_size):
            self.buffer.extend(chunk)
            self.emit('received', len(chunk), __suppress=True)

            last_progress = log_progress(self, '[%s]     Reading' % self.stream_num, len(self.buffer), last_progress)

            self.read_event.wait()

        self.state = 'buffered'
        self.emit('buffered')

    def iter(self, c_range):
        """
        :type c_range: plugin.range.ContentRange
        """
        with self.request_lock:
            num = self.request_seq
            self.request_seq += 1

        position = 0
        end = self.content_range.end + 1

        last_progress = None
        ev_received = Event()

        @self.on('received')
        def on_received(*args):
            ev_received.set()

        if c_range:
            position = c_range.start - self.content_range.start
            end = (c_range.end - self.content_range.start) + 1

            log.debug(
                '[%s] [%s:%s] Streaming - c_range: %s, position: %s, end: %s',
                self.track.uri, self.stream_num,
                num, c_range, position, end
            )

        while position < self.content_length:
            chunk_size = end - position

            # Clamp to maximum `chunk_size`
            if chunk_size > self.chunk_size:
                chunk_size = self.chunk_size

            data = self.buffer[position:position + chunk_size]

            if data:
                last_progress = log_progress(
                    self, '[%s:%s] Streaming' % (self.stream_num, num),
                    position, last_progress, length=end
                )
                position += len(data)
                yield str(data)
            elif self.state != 'buffered':
                ev_received.clear()
                ev_received.wait()
            else:
                break

        self.off('received', on_received)

        log.info(
            '[%s] [%s:%s] Complete',
            self.track.uri, self.stream_num,
            num
        )
