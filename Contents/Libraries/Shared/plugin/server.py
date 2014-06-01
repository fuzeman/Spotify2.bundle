from plugin.dispatcher import Dispatcher
from plugin.track import Track
from plugin.util import log_progress, parse_range

from threading import Lock
import cherrypy
import logging
import socket

log = logging.getLogger(__name__)


class Server(object):
    def __init__(self, plugin_host, port=12555):
        self.plugin_host = plugin_host

        self.port = port

        self.cache = {}

        self.current = None

        self.lock_get = Lock()
        self.lock_end = Lock()

    @property
    def sp(self):
        return self.plugin_host.sp

    def start(self):
        # CherryPy
        cherrypy.config.update({
            'server.socket_host': '0.0.0.0',
            'server.socket_port': self.port
        })

        cherrypy.tree.mount(None, config={
            '/': {
                'request.dispatch': Dispatcher(self)
            }
        })

        cherrypy.engine.start()

    def stop(self):
        cherrypy.engine.stop()

    def track(self, uri):
        log.debug('Received track request for "%s"', uri)

        # Call end() if track has changed
        if self.current and uri != self.current.uri:
            self.track_end(self.current)

        # Get or create track
        tr = self.track_get(uri)

        # Update current
        self.current = tr

        r_start, r_end = parse_range(cherrypy.request.headers.get('Range'))
        log.debug('[%s] Range: %s - %s', tr.uri, r_start, r_end)

        sr = tr.stream(r_start, r_end)
        sr.open()

        # Update headers
        cherrypy.response.headers['Accept-Ranges'] = 'bytes'
        cherrypy.response.headers['Content-Type'] = sr.headers['Content-Type']
        cherrypy.response.headers['Content-Length'] = sr.length

        if r_start or r_end:
            cherrypy.response.headers['Content-Range'] = sr.headers['Content-Range']
            cherrypy.response.status = 206

        # Progressively return track from buffer
        return self.stream(sr)

    track._cp_config = {'response.stream': True}

    def track_get(self, uri):
        self.lock_get.acquire()

        # Create new track (if one doesn't exist yet)
        if uri not in self.cache:
            log.debug('[%s] Creating new Track' % uri)

            # Create new track reference
            self.cache[uri] = Track(self, uri)

        self.lock_get.release()

        # Get track from cache
        return self.cache[uri]

    def track_end(self, track):
        self.lock_end.acquire()

        # Send "track_end" event
        self.current.end()

        # Cleanup resources
        if track.uri not in self.cache:
            self.lock_end.release()
            return

        log.debug('[%s] Releasing resources', track.uri)
        del self.cache[track.uri]

        self.lock_end.release()

    @staticmethod
    def stream(sr):
        tr = sr.track

        position = 0

        chunk_size_min = 6 * 1024
        chunk_size_max = 10 * 1024

        chunk_scale = 0
        chunk_size = chunk_size_min

        last_progress = None

        while True:
            # Adjust chunk_size
            if chunk_scale < 1:
                chunk_scale = 2 * (float(position) / sr.length)
                chunk_size = int(chunk_size_min + (chunk_size_max * chunk_scale))

                if chunk_scale > 1:
                    chunk_scale = 1

            if position + chunk_size > sr.length:
                chunk_size = sr.length - position

            # Read chunk
            chunk = sr.read(position, chunk_size)

            if not chunk:
                log.info('[%s] [%s] Finished at %s bytes (content-length: %s)' % (tr.uri, sr.num, position, sr.length))
                break

            last_progress = log_progress(sr, '[%s] Streaming' % sr.num, position, last_progress)

            position = position + len(chunk)

            # Write chunk
            yield chunk

        log.info('[%s] [%s] Complete', tr.uri, sr.num)

    def get_track_url(self, uri):
        return "http://%s:%d/track/%s.mp3" % (
            socket.gethostname(), self.port, uri
        )
