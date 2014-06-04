from settings import PLUGIN_ID
from utils import Track

from spotify import Spotify
from threading import Lock, Event, Timer
import time


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self):
        self.current_track = None
        self.track_lock = Lock()

        self.username = None
        self.password = None

        self.proxy_tracks = True
        self.server = None

        self.sp = None
        self.reconnect_time = None
        self.reconnect_timer = None

        self.on_login = Event()

    def set_preferences(self, username, password, proxy_tracks):
        self.username = username
        self.password = password

        self.proxy_tracks = proxy_tracks

    def start(self):
        if self.sp:
            # TODO stop current Spotify client
            pass

        self.sp = Spotify()
        self.on_login = Event()

        self.sp.on('error', lambda message: Log.Error(message))\
               .on('close', self.on_close)

        self.sp.login(self.username, self.password, lambda: self.on_login.set())

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
        self.on_login = Event()

        # Start connecting...
        self.sp.connect()

    def connect_delayed(self):
        self.reconnect_timer = Timer(180, self.connect)
        self.reconnect_timer.start()

        Log.Info('Reconnection will be attempted again in 180 seconds')

    @property
    def constructed(self):
        return self.sp and self.on_login

    @property
    def ready(self):
        if not self.constructed:
            return False

        return self.on_login.wait(10)

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

    #
    # Media
    #

    def is_album_playable(self, album):
        """ Check if an album can be played by a client or not """
        return True

    def is_track_playable(self, track):
        """ Check if a track can be played by a client or not """
        return True

    def play(self, uri):
        if not uri:
            Log.Warn('Unable to play track with invalid "uri"')
            return

        Log.Debug('play proxy_tracks: %s' % self.proxy_tracks)

        # Return proxy URL (if enabled)
        if self.proxy_tracks and self.server:
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
