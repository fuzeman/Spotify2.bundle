from util import log_progress

from threading import Thread, Event
from urllib import urlopen
import logging
import time

log = logging.getLogger(__name__)


class TrackReference(object):
    buffer_wait_ms = 100
    buffer_wait = buffer_wait_ms / 1000.0

    def __init__(self, server, uri):
        self.server = server
        self.uri = uri

        self.buffer = bytearray()
        self.metadata = None

        self.on_opened = Event()

        # stream info (from 'sp/track_uri')
        self.stream_info = None
        self.stream_length = None

        # download response
        self.response = None
        self.response_thread = None
        self.response_headers = None

        # track state
        self.reading = False
        self.reading_start = None

        self.playing = False
        self.finished = False

    @property
    def success(self):
        return self.stream_info and 'uri' in self.stream_info

    def fetch(self):
        if self.response:
            log.debug('[%s] already fetched track, returning from cache' % self.uri)
            return

        self.server.sp.metadata(self.uri, self.on_metadata)

    def on_metadata(self, metadata):
        self.metadata = metadata

        # Ensure track is actually available (check restrictions)
        if not self.metadata.is_available():
            # Try find alternative track that is available
            if not self.metadata.find_alternative():
                log.warn('Unable to find alternative for track "%s"', self.metadata.uri)

        # Request the track_uri
        self.metadata.track_uri(self.on_track_uri)

    def on_track_uri(self, response):
        self.stream_info = response.get('result')

        if not self.success:
            log.warn('Invalid track_uri response')
            return

        self.response = urlopen(self.stream_info['uri'])
        self.response_headers = self.response.info()

        log.info('Opened "%s"', self.stream_info['uri'])
        log.info('Info: %s', self.response_headers)

        self.stream_length = int(self.response_headers.getheader('Content-Length'))
        log.info('Length: %s', self.stream_length)

        if self.response_headers.getheader('Content-Type') == 'text/xml':
            # Error, log response
            log.debug(self.response.read())
        else:
            # Download track for streaming
            self.response_thread = Thread(target=self.run)
            self.response_thread.start()

        self.on_opened.set()

    def run(self):
        chunk_size = 1024
        last_progress = None

        self.reading = True

        while True:
            chunk = self.response.read(chunk_size)
            #log.debug('[%s] Received %s bytes', self.uri, len(chunk))

            self.buffer.extend(chunk)

            if not chunk:
                break

            last_progress = log_progress(self, 'Downloading', len(self.buffer), last_progress)

        self.reading = False
        log.debug('[%s] Download Complete', self.uri)

    def read(self, start, chunk_size=1024):
        if not self.playing:
            self.metadata.track_event(self.stream_info['lid'], 3, 0)
            self.reading_start = time.time()
            self.playing = True

        while self.reading and len(self.buffer) < start + 1:
            time.sleep(self.buffer_wait)

        return self.buffer[start:start + chunk_size]

    def finish(self):
        if self.finished:
            return

        self.finished = True

        position = 0

        if self.reading_start:
            position = time.time() - self.reading_start

        position_ms = int(position * 1000)

        if position_ms > self.metadata.duration:
            position_ms = self.metadata.duration

        log.debug('position_ms: %s, duration: %s', position_ms, self.metadata.duration)

        self.metadata.track_end(self.stream_info['lid'], position_ms)
