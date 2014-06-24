from direct import Direct
from routing import function_path

from spotify import Spotify
from threading import Event, Timer
import logging
import time


class SpotifyClient(object):
    def __init__(self, host):
        self.host = host

        self.direct = Direct(self)
        self.server = None

        self.sp = None
        self.reconnect_time = None
        self.reconnect_timer = None

        self.ready_event = Event()
        self.errors = []

    def start(self):
        if self.sp:
            # TODO stop current Spotify client
            pass

        self.sp = Spotify()

        self.ready_event = Event()
        self.errors = []

        self.sp.on('error', self.on_error)\
               .on('close', self.on_close)

        self.sp.login(self.host.username, self.host.password, self.on_login)

    def on_login(self):
        # Refresh server info
        self.host.refresh()

        # Release request hold
        self.ready_event.set()

    def on_error(self, message):
        self.errors.append((logging.ERROR, message))
        Log.Error(message)

    def on_close(self, code, reason=None):
        # Force re-authentication
        self.sp.authenticated = False

        # Reconnect
        self.connect()

    def connect(self):
        # Rate-limit re-connections
        if self.reconnect_time:
            span = time.time() - self.reconnect_time
            Log.Debug('Last reconnection attempt was %s seconds ago', span)

            # Delay next reconnection
            if span < 120:
                self.connect_delayed()
                return

        Log.Info('Attempting reconnection to Spotify...')

        self.reconnect_time = time.time()

        # Hold requests while we re-connect
        self.ready_event = Event()

        # Start connecting...
        self.sp.connect()

    def connect_delayed(self):
        self.reconnect_timer = Timer(180, self.connect)
        self.reconnect_timer.start()

        Log.Info('Reconnection will be attempted again in 180 seconds')

    @property
    def constructed(self):
        return self.sp and self.ready_event

    @property
    def ready(self):
        if not self.constructed:
            return False

        return self.ready_event.wait(10)

    def shutdown(self):
        self.sp.api.shutdown()
        self.sp = None

    #
    # Public methods
    #

    def search(self, query, query_type='all', max_results=50, offset=0):
        """ Execute a search

        :param query:          A query string.
        """
        return self.sp.search(query, query_type, max_results, offset)

    def artist_uris(self, artist):
        top_tracks = self.artist_top_tracks(artist)

        # Top Track URIs
        track_uris = []

        if top_tracks:
            track_uris = [tr.uri for tr in top_tracks.tracks if tr is not None]

        # Album URIs
        album_uris = [al.uri for al in artist.albums if al is not None]

        return track_uris, album_uris

    def artist_top_tracks(self, artist):
        for tt in artist.top_tracks:
            # TopTracks matches account region?
            if tt.country == self.sp.country:
                return tt

        # Unable to find TopTracks for account region
        return None

    #
    # Streaming
    #

    def track_url(self, track):
        if self.host.proxy_tracks and self.server:
            return self.server.get_track_url(str(track.uri), hostname=self.host.hostname)

        return function_path('play', uri=str(track.uri), ext='mp3')

    def stream_url(self, uri):
        if self.host.proxy_tracks and self.server:
            return self.server.get_track_url(str(uri), hostname=self.host.hostname)

        return self.direct.get(uri)

    def get_last_error(self):
        if not self.errors:
            return None, ''

        return self.errors[-1]
