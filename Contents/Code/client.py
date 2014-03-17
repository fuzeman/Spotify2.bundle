from settings import PLUGIN_ID

from spotify_web.friendly import Spotify
from spotify_web.spotify import Logging


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self, username, password):
        """ Initializer

        :param username:       The username to connect to spotify with.
        :param password:       The password to authenticate with.
        """

        self.spotify = Spotify(username, password)
        self.spotify.api.set_log_level(3)

        # Hook logging
        Logging.hook(3, Log.Debug)
        Logging.hook(2, Log.Info)
        Logging.hook(1, Log.Warn)
        Logging.hook(0, Log.Error)

    #
    # Public methods
    #

    def is_logged_in(self):
        return self.spotify.logged_in()

    def shutdown(self):
        self.spotify.api.shutdown()

    def search(self, query, query_type="all", max_results=50, offset=0):
        """ Execute a search

        :param query:          A query string.
        """

        return self.spotify.search(query, query_type, max_results, offset)

    def get(self, uri):
        return self.spotify.objectFromURI(uri)

    def is_album_playable(self, album):
        """ Check if an album can be played by a client or not """

        return True

    def is_track_playable(self, track):
        """ Check if a track can be played by a client or not """

        return True

    def get_art(self, uri, callback):
        """ Fetch and return album artwork.

        note:: Currently only album artowk can be retrieved.

        :param uri:            The spotify URI of the album to load art for.
        :param callback:       The callback to invoke when artwork is loaded.
                               Should take image data as a single parameter.
        """

        pass

    def get_playlists(self):
        """ Return the user's playlists"""

        return self.spotify.getPlaylists()

    def get_playlist(self, uri=None, id=None):
        for pl in self.get_playlists():
            if pl.getURI() == uri or pl.getID() == id:
                return pl

        return None

    def get_starred(self):
        """ Return the user's starred tracks

        TODO this should be made async with a callback rather than assuming
        the starred playlist is loaded (will fail if it isn't right now).
        """

        return self.get_playlist(id='starred')


    def load_image(self, uri, image_id):
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
