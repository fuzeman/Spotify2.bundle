from threading import Event, Lock
import logging
import time

log = logging.getLogger('spotify2.%s' % __name__)


class Direct(object):
    def __init__(self, client):
        self.client = client

        self.cur_track = None
        self.cur_stream = None

        self.start_time = None
        self.lock = Lock()

    @property
    def sp(self):
        return self.client.sp

    @property
    def position(self):
        value = 0

        if self.start_time:
            value = int((time.time() - self.start_time) * 1000)

        if value > self.cur_track.duration:
            return self.cur_track.duration

        return value

    def get(self, uri):
        """Fetch track stream

        :param uri: Track URI
        :type uri: str
        """
        log.debug('get - waiting for lock')

        with self.lock:
            log.debug('get - uri: %s', uri)

            # Finish previous track
            self.finish()

            ev_metadata = Event()
            ev_stream = Event()

            # Metadata
            @self.sp.metadata(uri)
            def on_metadata(track):
                self.cur_track = track
                ev_metadata.set()

            ev_metadata.wait()

            # Stream info
            @self.cur_track.track_uri()
            def on_track_uri(stream):
                self.cur_stream = stream.get('result')
                ev_stream.set()

            ev_stream.wait()

            # Start streaming track
            return self.start()

    def start(self):
        log.debug('[%s] Sending "track_event" (3)', self.cur_track.uri)

        self.cur_track.track_event(self.cur_stream['lid'], 3, 0)

        self.start_time = time.time()

        return self.cur_stream['uri']

    def finish(self):
        if not self.cur_track:
            return

        position = self.position

        log.debug(
            '[%s] Sending "track_end" (position: %s, duration: %s)',
            self.cur_track.uri, position, self.cur_track.duration
        )

        self.cur_track.track_end(self.cur_stream['lid'], position)

        self.cur_track = None
        self.cur_stream = None
