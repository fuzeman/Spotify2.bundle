from settings import PLUGIN_ID

from spotify_web.spotify import SpotifyAPI, Logging
from threading import Thread


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self, username, password):
        """ Initializer

        :param username:       The username to connect to spotify with.
        :param password:       The password to authenticate with.
        """

        self.username = username
        self.password = password

        self.connect_thread = None

        self.sp = SpotifyAPI(self.login_callback)
        self.sp.set_log_level(3)

        # Hook logging
        Logging.hook(3, Log.Debug)
        Logging.hook(2, Log.Info)
        Logging.hook(1, Log.Warn)
        Logging.hook(0, Log.Error)

        self.is_logging_in = False

    #
    # Public methods
    #

    @property
    def is_logged_in(self):
        return self.sp.is_logged_in

    def connect(self):
        """ Connect to Spotify """

        self.is_logging_in = True

        self.connect_thread = Thread(target=self.connect_handler)
        self.connect_thread.start()

        Log.Debug('Connecting as "%s', self.username)

    def connect_handler(self):
        try:
            self.sp.connect(self.username, self.password)
        except Exception, ex:
            Log.Warn(ex)
            Log.Warn(Plugin.Traceback())

    def disconnect(self):
        """ Disconnect from Spotify """

        pass

    def is_album_playable(self, album):
        """ Check if an album can be played by a client or not """

        pass

    def is_track_playable(self, track):
        """ Check if a track can be played by a client or not """

        pass

    def get_art(self, uri, callback):
        """ Fetch and return album artwork.

        note:: Currently only album artowk can be retrieved.

        :param uri:            The spotify URI of the album to load art for.
        :param callback:       The callback to invoke when artwork is loaded.
                               Should take image data as a single parameter.
        """

        pass

    def get_playlists(self, folder_id = 0):
        """ Return the user's playlists

        :param folder_id       The id of the playlist folder to return.
        """

        pass

    def get_starred_tracks(self):
        """ Return the user's starred tracks

        TODO this should be made async with a callback rather than assuming
        the starred playlist is loaded (will fail if it isn't right now).
        """

        pass

    def search(self, query, callback):
        """ Execute a search

        :param query:          A query string.
        :param callback:       A callback to invoke when the search is finished.
                               Should take the results list as a parameter.
        """

        pass

    def browse_album(self, album, callback):
        """ Browse an album, invoking the callback when done

        :param album:          An album instance to browse.
        :param callback:       A callback to invoke when the album is loaded.
                               Should take the browser as a single parameter.
        """

        pass

    def browse_artist(self, artist, callback):
        """ Browse an artist, invoking the callback when done

        :param artist:         An artist instance to browse.
        :param callback:       A callback to invoke when the album is loaded.
                               Should take the browser as a single parameter.
        """

        pass

    def load_image(self, uri, image_id, callback):
        """ Load an image from an image id

        :param image_id:       The spotify id of the image to load.
        :param callback:       A callback to invoke when the image is loaded.
                               Should take the image as a single parameter.
        """

        pass

    def load_track(self, uri):
        """ Load a track from a spotify URI

        Note: this currently polls as there is no API for browsing
        individual tracks

        :param uri:              The spotify URI of the track to load.
        """

        pass

    def play_track(self, uri, audio_callback, stop_callback):
        """ Start playing a spotify track

        :param uri:              The spotify URI of the track to play.
        :param audio_callback:   A callback to invoke when audio arrives.
                                 Return a boolean to indicate if more audio can
                                 be processed.
        :param stop_callback:    A callback to invoke when playback is stopped.
        """

        pass

    def stop_playback(self):
        """ Stop playing the current stream """

        pass

    #
    # Spotify callbacks
    #

    def login_callback(self, sp, logged_in):
        self.is_logging_in = False

        if logged_in:
            Log.Info('Logged in successfully')
        else:
            Log.Warn('Unable to login')
