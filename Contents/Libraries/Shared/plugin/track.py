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
        self.ended = False

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

    def on_track_error(self, error):
        self.info_ev.set()

        log.debug('track error: %s', error)

    def stream(self, r_range):
        """
        :rtype: plugin.stream.Stream
        """

        if r_range:
            r_range = r_range.start, r_range.end
        else:
            r_range = 0, None

        r_start, r_end = r_range

        # Check for existing stream (with same range)
        if r_range in self.streams:
            log.debug('Returning existing stream (r_range: %s)', r_range)
            return self.streams[r_range]

        for s_range in self.streams:
            s_start, s_end = s_range

            if s_start > r_start:
                continue

            if s_end != r_end:
                if r_end is None or s_end is None:
                    continue

                if s_end < r_end:
                    continue

            log.debug('Returning existing stream with similar range (s_range: %s)', s_range)
            return self.streams[s_range]

        log.debug('Building stream for track (r_range: %s)', r_range)

        if self.metadata is None:
            # Fetch metadata
            self.server.sp.metadata(self.uri, self.on_metadata)
            self.metadata_ev.wait()

        if self.info is None:
            # Fetch stream info
            self.metadata.track_uri(self.on_track_uri)\
                         .on('error', self.on_track_error)

            self.info_ev.wait(timeout=5)

        # Validate stream info
        if not self.info or 'uri' not in self.info:
            return None

        # Create new stream
        stream = Stream(self, len(self.streams), r_range)

        self.streams[r_range] = stream
        return stream

    def on_read(self):
        if self.playing:
            return

        self.metadata.track_event(self.info['lid'], 3, 0)

        self.reading_start = time.time()
        self.playing = True

    @property
    def position(self):
        """Get estimated player position for track

        :returns: Position (in milliseconds)
        :rtype: int
        """
        position = 0

        if self.reading_start:
            position = int((time.time() - self.reading_start) * 1000)

        if position > self.metadata.duration:
            return self.metadata.duration

        return position

    def end(self):
        """Send track end/completion events"""
        if not self.playing or self.ended:
            return

        log.debug('[%s] Sending "track_end" event (position: %s)', self.uri, self.position)

        self.metadata.track_end(self.info['lid'], self.position)
        self.ended = True
