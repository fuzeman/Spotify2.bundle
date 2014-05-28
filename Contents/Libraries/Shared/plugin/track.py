from plugin.stream import Stream

from threading import Event
import logging
import time

log = logging.getLogger(__name__)


class Track(object):
    def __init__(self, server, uri):
        self.server = server
        self.uri = uri

        self.metadata = None
        self.metadata_ev = Event()

        self.info = None
        self.info_ev = Event()

        self.buffer = bytearray()
        self.streams = {}

        # Track state
        self.reading_start = None

        self.playing = False
        self.finished = False

    def on_metadata(self, metadata):
        self.metadata = metadata

        # Ensure track is actually available (check restrictions)
        if not self.metadata.is_available():
            # Try find alternative track that is available
            if not self.metadata.find_alternative():
                log.warn('Unable to find alternative for track "%s"', self.metadata.uri)

        self.metadata_ev.set()

    def on_track_uri(self, response):
        self.info = response.get('result')
        self.info_ev.set()

        log.debug('received track info: %s', self.info)

    def stream(self, start, end):
        sr_range = start, end

        if sr_range in self.streams:
            log.debug('Returning existing stream (start: %s, end: %s)', start, end)
            return self.streams[sr_range]

        log.debug('Building stream for track (start: %s, end: %s)', start, end)

        if self.metadata is None:
            self.server.sp.metadata(self.uri, self.on_metadata)
            self.metadata_ev.wait()

        if self.info is None:
            self.metadata.track_uri(self.on_track_uri)
            self.info_ev.wait()

        if not self.info or 'uri' not in self.info:
            return None

        stream = Stream(self, len(self.streams), start, end)

        self.streams[sr_range] = stream
        return stream

    def on_read(self):
        if self.playing:
            return

        self.metadata.track_event(self.info['lid'], 3, 0)

        self.reading_start = time.time()
        self.playing = True

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

        self.metadata.track_end(self.info['lid'], position_ms)
