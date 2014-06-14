from plugin.dispatcher import Dispatcher
from plugin.profiles import ProfileManager
from plugin.range import Range
from plugin.track import Track

from requests_futures.sessions import FuturesSession
from threading import Lock, Event
import cherrypy
import cherrypy.wsgiserver
import logging
import os
import socket
import traceback

log = logging.getLogger(__name__)


class Server(object):
    def __init__(self, plugin_host, port=12555):
        self.plugin_host = plugin_host
        self.port = port

        self.profiles = ProfileManager()
        self.session = FuturesSession()
        self.cache = {}

        self.current = None

        self.lock_get = Lock()
        self.lock_end = Lock()

    @property
    def sp(self):
        return self.plugin_host.sp

    def start(self):
        # Load profiles
        self.profiles.load_directory(os.path.join(self.plugin_host.bundle_path, 'Profiles'))

        # CherryPy
        cherrypy.config.update({
            'engine.autoreload.on': False,

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
        try:
            return self.track_handle(uri)
        except Exception, ex:
            log.error('%s - %s', ex, traceback.format_exc())

    track._cp_config = {'response.stream': True}

    def track_handle(self, uri):
        log.info('Received request for "%s"', uri)

        # Parse request
        r_profile = self.profiles.match(cherrypy.request.headers)
        r_range = None

        if r_profile.supports_ranges:
            r_range = Range.parse(cherrypy.request.headers.get('Range'))

        log.info('Profile: "%s", Range: %s', r_profile.name, repr(r_range))

        # Call end() if track has changed
        if self.current and uri != self.current.uri:
            self.track_end(self.current)

        # Get or create track
        track = self.track_get(uri)

        # Update current
        self.current = track

        stream = track.stream(r_range)

        if not stream:
            log.warn('Unable to build stream (region restrictions, etc..)')
            cherrypy.response.status = 404
            return

        stream.open()

        stream.on_reading.wait()
        log.debug('stream ready')

        c_range = None
        r_length = None

        if r_profile.supports_ranges:
            cherrypy.response.headers['Accept-Ranges'] = 'bytes'

            if r_range:
                # Parse request range
                c_range = r_range.content_range(stream.total_length)
                r_length = (c_range.end - c_range.start + 1)

        # Set headers
        cherrypy.response.headers['Content-Type'] = stream.headers['Content-Type']
        cherrypy.response.headers['Content-Length'] = r_length or stream.total_length

        if c_range:
            log.info('[%s] Content-Range: %s', track.uri, repr(c_range))

            cherrypy.response.headers['Content-Range'] = str(c_range)
            cherrypy.response.status = 206

        # Stream response
        return stream.iter(c_range)

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
        log.debug('[%s] Track ended', track.uri)

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

    def get_track_url(self, uri, hostname=None):
        if not hostname:
            hostname = socket.gethostname()

        return "http://%s:%d/track/%s.mp3" % (
            hostname, self.port, uri
        )
