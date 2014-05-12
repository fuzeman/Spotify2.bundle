from dispatcher import Dispatcher
from track_reference import TrackReference
from util import log_progress

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

    def finish(self, track):
        # Send track completion events
        log.debug('[%s] Sending completion events', track.uri)
        track.finish()

        # Cleanup resources
        if track.uri not in self.cache:
            return

        log.debug('[%s] Releasing resources', track.uri)
        del self.cache[track.uri]

    def track(self, uri):
        log.debug('Received track request for "%s"', uri)

        # Call finish() if track has changed
        if self.current and uri != self.current.uri:
            self.finish(self.current)

        # Create new TrackReference (if one doesn't exist yet)
        if uri not in self.cache:
            log.debug('[%s] Creating new TrackReference' % uri)

            # Create new track reference
            self.cache[uri] = TrackReference(self, uri)

        # Get track reference from cache
        tr = self.cache[uri]

        # Start download
        tr.fetch()

        # Wait until track is ready
        tr.on_opened.wait(10)

        if not tr.success:
            self.current = None
            cherrypy.response.status = 500
            return

        # Update current
        self.current = tr

        r_start, r_end = self.handle_range(tr)

        log.debug('Streaming range: %s - %s', r_start, r_end)

        # Update headers
        cherrypy.response.headers['Accept-Ranges'] = 'bytes'
        cherrypy.response.headers['Content-Type'] = tr.response_headers.getheader('Content-Type')
        cherrypy.response.headers['Content-Length'] = r_end - r_start

        # Progressively return track from buffer
        return self.stream(tr, r_start, r_end)

    track._cp_config = {'response.stream': True}

    @staticmethod
    def stream(tr, r_start, r_end):
        position = r_start

        chunk_size_min = 6 * 1024
        chunk_size_max = 10 * 1024

        chunk_scale = 0
        chunk_size = chunk_size_min

        last_progress = None

        while True:
            # Adjust chunk_size
            if chunk_scale < 1:
                chunk_scale = 2 * (float(position) / tr.stream_length)
                chunk_size = int(chunk_size_min + (chunk_size_max * chunk_scale))

                if chunk_scale > 1:
                    chunk_scale = 1

            if position + chunk_size > r_end:
                chunk_size = r_end - position

            # Read chunk
            chunk = tr.read(position, chunk_size)

            if not chunk:
                log.debug('[%s] Finished at %s bytes (content-length: %s)' % (tr.uri, position, tr.stream_length))
                break

            last_progress = log_progress(tr, '  Streaming', position, last_progress)

            position = position + len(chunk)

            # Write chunk
            yield chunk

        log.debug('[%s] Stream Complete', tr.uri)

    def handle_range(self, tr):
        r_start, r_end = self.parse_range(cherrypy.request.headers.get('Range'))

        if not r_start and not r_end:
            return 0, tr.stream_length - 1

        if tr.stream_length - r_start < 1024 * 1024:
            log.debug('[%s] Rejected final bytes request', tr.uri)
            return 0, tr.stream_length - 1

        if r_end is None or r_end >= tr.stream_length:
            r_end = tr.stream_length - 1

        log.debug('[%s] Range: %s - %s', tr.uri, r_start, r_end)

        cherrypy.response.headers['Content-Range'] = 'bytes %s-%s/%s' % (r_start, r_end, tr.stream_length)
        cherrypy.response.status = 206

        return r_start, r_end

    @staticmethod
    def parse_range(value):
        if not value:
            return 0, None

        value = value.split('=')

        if len(value) != 2:
            return 0, None

        range_type, range = value

        if range_type != 'bytes':
            return 0, None

        range = range.split('-')

        if len(range) != 2:
            return 0, None

        return int(range[0] or 0), int(range[1]) if range[1] else None

    def get_track_url(self, uri):
        return "http://%s:%d/track/%s.mp3" % (
            socket.gethostname(), self.port, uri
        )
