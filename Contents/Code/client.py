from settings import PLUGIN_ID
from utils import Track

from spotify_web.friendly import Spotify
from spotify_web.spotify import Logging
from threading import Lock


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self, username, password):
        """ Initializer

        :param username:       The username to connect to spotify with.
        :param password:       The password to authenticate with.
        """

        # Hook logging
        Logging.hook(3, Log.Debug)
        Logging.hook(2, Log.Info)
        Logging.hook(1, Log.Warn)
        Logging.hook(0, Log.Error)

        self.username = username
        self.password = password

        self.current_track = None
        self.track_lock = Lock()

        self.spotify = None

    def start(self):
        if self.spotify:
            self.shutdown()

        self.spotify = Spotify(self.username, self.password, log_level=3)

    def restart(self):
        self.start()

    def shutdown(self):
        self.spotify.api.shutdown()
        self.spotify = None

    #
    # Public methods
    #

    def is_logged_in(self):
        return self.spotify.logged_in()

    def search(self, query, query_type='all', max_results=50, offset=0):
        """ Execute a search

        :param query:          A query string.
        """
        return self.spotify.search(query, query_type, max_results, offset)

    #
    # Media
    #

    def get(self, uri):
        return self.spotify.objectFromURI(uri)

    def is_album_playable(self, album):
        """ Check if an album can be played by a client or not """
        return True

    def is_track_playable(self, track):
        """ Check if a track can be played by a client or not """
        return True

    def get_track_url(self, track):
        if self.current_track:
            # Send stop event for previous track
            self.spotify.api.send_track_event(
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
        self.spotify.api.send_track_event(track.getID(), 'play', 0)
        track_url = track.getFileURL(retries=1)

        # If first request failed, trigger re-connection to spotify
        retry_num = 0
        while not track_url and retry_num < 2:
            retry_num += 1

            Log.Info('get_track_url failed, re-connecting to spotify...')
            self.restart()

            # Update reference to spotify client (otherwise getFileURL request will fail)
            track.spotify = self.spotify

            Log.Info('Fetching track url...')
            self.spotify.api.send_track_event(track.getID(), 'play', 0)
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

    #
    # Playlists
    #

    def get_playlists(self):
        """ Return the user's playlists"""
        return self.spotify.getPlaylists()

    def get_starred(self):
        """ Return the user's starred tracks"""
        return self.get('spotify:user:%s:starred' % self.username)
