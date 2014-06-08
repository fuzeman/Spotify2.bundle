from routing import function_path
from settings import PLUGIN_ID
from utils import Track

from spotify import Spotify
from threading import Lock, Event, Timer
import time


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self, host):
        self.host = host

        self.current_track = None
        self.track_lock = Lock()

        self.server = None

        self.sp = None
        self.reconnect_time = None
        self.reconnect_timer = None

        self.ready_event = Event()

    def start(self):
        if self.sp:
            # TODO stop current Spotify client
            pass

        self.sp = Spotify()
        self.ready_event = Event()

        self.sp.on('error', lambda message: Log.Error(message))\
               .on('close', self.on_close)

        self.sp.login(self.host.username, self.host.password, self.on_login)

    def on_login(self):
        # Refresh server info
        self.host.refresh()

        # Release request hold
        self.ready_event.set()

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
    # Media
    #

    def track_url(self, track):
        if self.host.proxy_tracks and self.server:
            return self.server.get_track_url(track.uri, hostname=self.host.hostname)

        return function_path('play', uri=str(track.uri), ext='mp3')

    def play(self, uri):
        if not uri:
            Log.Warn('Unable to play track with invalid "uri"')
            return

        Log.Debug('play proxy_tracks: %s' % self.host.proxy_tracks)

        # Return proxy URL (if enabled)
        if self.host.proxy_tracks and self.server:
            return self.server.get_track_url(uri)

        # Get the track and return a direct stream URL
        Log.Error('Direct streaming is not supported yet (enable "Proxy tracks (via PMS)" to resolve this)')
        raise NotImplementedError()

        return self.get_track_url(self.get(uri))

    def get_track_url(self, track):
        if self.current_track:
            # Send stop event for previous track
            self.sp.api.send_track_event(
                self.current_track.track.getID(),
                'stop',
                self.current_track.track.getDuration()
            )

        if not track:
            return None

        self.track_lock.acquire()

        Log.Debug(
            'Acquired track_lock, current_track: %s',
            repr(self.current_track)
        )

        if self.current_track and self.current_track.matches(track):
            Log.Debug('Using existing track: %s', repr(self.current_track))
            self.track_lock.release()

            return self.current_track.url

        # Reset current state
        self.current_track = None

        # First try get track url
        self.sp.api.send_track_event(track.getID(), 'play', 0)
        track_url = track.getFileURL(retries=1)

        # If first request failed, trigger re-connection to spotify
        retry_num = 0
        while not track_url and retry_num < 2:
            retry_num += 1

            Log.Info('get_track_url failed, re-connecting to spotify...')
            self.start()  # (restarts the connection)

            # Update reference to spotify client (otherwise getFileURL request will fail)
            track.spotify = self.sp

            Log.Info('Fetching track url...')
            self.sp.api.send_track_event(track.getID(), 'play', 0)
            track_url = track.getFileURL(retries=1)

        # Finished
        if track_url:
            self.current_track = Track.create(track, track_url)
            Log.Info('Current Track: %s', repr(self.current_track))
        else:
            self.current_track = None
            Log.Warn('Unable to fetch track URL (connection problem?)')

        Log.Debug('Retrieved track_url: %s', repr(track_url))
        self.track_lock.release()
        return track_url
