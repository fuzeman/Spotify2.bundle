from threading import Lock
from urllib import urlopen
import logging

log = logging.getLogger(__name__)


class TrackReference(object):
    def __init__(self, client, uri):
        self.client = client
        self.uri = uri

        self.response = None
        self.info = None

        self.length = None

        self.buffer = ''
        self.read_lock = Lock()

    def fetch(self):
        if self.response:
            log.debug('[%s] already fetched track, returning from cache' % self.uri)
            return

        track = self.client.get(self.uri)
        track_url = self.client.get_track_url(track)

        self.response = urlopen(track_url)
        self.info = self.response.info()

        self.length = int(self.info.getheader('Content-Length'))

    def read(self, start, chunk_size=1024):
        # Check if range is in the buffer
        if start < len(self.buffer):
            log.debug('[%s] returning %s bytes from buffer' % (
                self.uri, len(self.buffer) - start
            ))
            return self.buffer[start:]

        with self.read_lock:
            # Read chunk from request stream
            chunk = self.response.read(chunk_size)

            # Store in buffer
            self.buffer = self.buffer + chunk

            return chunk
