'''
Spotify client
'''
from settings import PLUGIN_ID, POLL_INTERVAL, POLL_TIMEOUT
from spotify.manager import SpotifySessionManager
from spotify import Link, PlaylistFolder, connect
from time import time, sleep
from utils import RunLoopMixin, PCMToAIFFConverter, assert_loaded


class SpotifyClient(SpotifySessionManager, RunLoopMixin):
    ''' Spotify client that runs all code on a tornado ioloop

    This subclass is intended to be used in the context of an application
    that uses a tornado ioloop running on a single thread to do its work.
    All Spotify callbacks are bounced to the ioloop passed to the constructor
    so that it is not necessary to lock non thread-safe code.
    '''

    user_agent = PLUGIN_ID
    application_key = Resource.Load('spotify_appkey.key')

    def __init__(self, username, password, ioloop):
        ''' Initializer

        :param username:       The username to connect to spotify with.
        :param password:       The password to authenticate with.
        :param ioloop:         The tornado IOLoop instance to run on.
        '''
        super(SpotifyClient, self).__init__(username, password)
        self.ioloop = ioloop
        self.timer = None
        self.session = None
        self.login_error = None
        self.logging_in = False
        self.stop_callback = None
        self.audio_callback = None
        self.audio_converter = None
        self.playlist_folders = {}

    ''' Public methods (names with unscores are disallowed by Plex) '''

    def is_logging_in(self):
        return self.logging_in

    def is_logged_in(self):
        return self.session is not None

    def needs_restart(self, username, password):
        ''' Determines if the library should be restarted '''
        return self.username != username \
            or self.password != password

    def connect(self):
        ''' Connect to Spotify '''
        self.log("Connecting as %s" % self.username)
        self.logging_in = True
        self.schedule_periodic_check(connect(self))

    def disconnect(self):
        ''' Disconnect from Spotify '''
        if not self.session:
            return
        self.log("Logging out")
        self.session.logout()

    def is_album_playable(self, album):
        ''' Check if an album can be played by a client or not '''
        assert_loaded(album)
        return album.is_available()

    def is_track_playable(self, track):
        ''' Check if a track can be played by a client or not '''
        playable = True
        assert_loaded(track)
        if track.is_local():
            playable = False
        elif not track.availability():
            playable = False
        return playable

    def get_art(self, uri, callback):
        ''' Fetch and return album artwork.

        note:: Currently only album artowk can be retrieved.

        :param uri:            The spotify URI of the album to load art for.
        :param callback:       The callback to invoke when artwork is loaded.
                               Should take image data as a single parameter.
        '''
        self.log("Get artwork: %s" % uri)
        link = Link.from_string(uri)
        if link.type() != Link.LINK_ALBUM:
            raise RuntimeError("Non album artwork not supported")
        album = link.as_album()
        def browse_finished(browser):
            art = self.load_image(album.cover())
            self.log("Artwork loaded: %s" % album)
            callback(str(art.data()))
        return self.browse_album(album, browse_finished)

    def get_playlists(self, folder_id = 0):
        ''' Return the user's playlists

        :param folder_id       The id of the playlist folder to return.
        '''
        self.log("Get playlists (folder id: %s)" % folder_id)
        result = []
        if folder_id in self.playlist_folders:
            result = self.playlist_folders[folder_id]
        return result

    def get_starred_tracks(self):
        ''' Return the user's starred tracks

        TODO this should be made async with a callback rather than assuming
        the starred playlist is loaded (will fail if it isn't right now).
        '''
        self.log("Get starred")
        return assert_loaded(self.session.starred()) if self.session else None

    def search(self, query, callback):
        ''' Execute a search

        :param query:          A query string.
        :param callback:       A callback to invoke when the search is finished.
                               Should take the results list as a parameter.
        '''
        self.log("Search (query = %s)" % query)
        search = self.session.search(query = query, callback = callback)

    def browse_album(self, album, callback):
        ''' Browse an album, invoking the callback when done

        :param album:          An album instance to browse.
        :param callback:       A callback to invoke when the album is loaded.
                               Should take the browser as a single parameter.
        '''
        link = Link.from_album(album)
        def callback_wrapper(browser):
            self.log("Album browse complete: %s" % link)
            callback(browser)
        self.log("Browse album: %s" % link)
        browser = self.session.browse_album(album, callback_wrapper)
        return browser

    def browse_artist(self, artist, callback):
        ''' Browse an artist, invoking the callback when done

        :param artist:         An artist instance to browse.
        :param callback:       A callback to invoke when the album is loaded.
                               Should take the browser as a single parameter.
        '''
        link = Link.from_artist(artist)
        def callback_wrapper(browser):
            self.log("Artist browse complete: %s" % Link.from_artist(artist))
            callback(browser)
        self.log("Browse artist: %s" % link)
        browser = self.session.browse_artist(artist, callback_wrapper)
        return browser

    def stop_playback(self):
        ''' Stop playing the current stream '''
        if self.audio_converter is None:
            return
        self.log("Stop playback")
        self.session.play(0)
        self.cleanup()
        self.log("Playback stopped")

    def load_image(self, image_id):
        ''' Load an image from an image id

        Note: this currently polls as I had trouble waiting for callbacks
        when loading images

        :param image_id:         The spotify id of the image to load.
        '''
        image = self.session.image_create(image_id)
        return self.wait_until_loaded(image, POLL_TIMEOUT)

    def load_track(self, uri):
        ''' Load a track from a spotify URI

        Note: this currently polls as there is no API for browsing
        individual tracks

        :param uri:              The spotify URI of the track to load.
        '''
        track = Link.from_string(uri).as_track()
        return self.wait_until_loaded(track, POLL_TIMEOUT)

    def play_track(self, uri, audio_callback, stop_callback):
        ''' Start playing a spotify track

        :param uri:              The spotify URI of the track to play.
        :param audio_callback:   A callback to invoke when audio arrives.
                                 Return a boolean to indicate if more audio can
                                 be processed.
        :param stop_callback:    A callback to invoke when playback is stopped.
        '''
        self.log("Play track: %s" % uri)
        track = self.load_track(uri)
        self.stop_playback()
        self.session.load(track)
        self.session.play(True)
        self.audio_converter = PCMToAIFFConverter(track)
        self.audio_callback = audio_callback
        self.stop_callback = stop_callback

    ''' Utility methods '''

    def wait_until_loaded(self, spotify_object, timeout):
        ''' Poll a spotify object until it is loaded

        :param spotify_object:   The spotify object to poll.
        :param timeout:          A timeout in seconds.
        '''
        start = time()
        while not spotify_object.is_loaded() and start > time() - timeout:
            message = "Waiting for spotify object: %s" % spotify_object
            self.log(message, debug = True)
            self.session.process_events()
            sleep(POLL_INTERVAL)
        assert_loaded(spotify_object)
        return spotify_object

    def log(self, message, debug = False):
        ''' Logging helper function

        :param message:    The message to output to the log.
        :param debug:      Only output the message in debug mode?
        '''
        message = "SPOTIFY: %s" % message
        Log.Debug(message) if debug else Log(message)

    def schedule_periodic_check(self, session, timeout = 0):
        ''' Schedules the next periodic Spotify event processing call '''
        callback = lambda: self.periodic_check(session)
        self.timer = self.schedule_timer(timeout, callback)

    def periodic_check(self, session):
        ''' Process pending Spotify events and schedule the next check '''
        self.log("Processing events", debug = True)
        timeout = session.process_events()
        self.schedule_periodic_check(session, timeout / 1000.0)

    def cleanup(self):
        ''' Cleanup after a track ends explicitly or implicitly '''
        if self.stop_callback is not None:
            self.stop_callback()
            self.stop_callback = None
        self.audio_converter = None

    ''' Spotify callbacks '''

    def logged_in(self, session, error):
        ''' libspotify callback for login attempts '''
        self.logging_in = False
        if error:
            self.log("Error logging in: %s" % error)
            self.login_error = error
        else:
            self.log("Logged in")
            self.session = session
            self.session.playlist_container().add_loaded_callback(
                self.playlists_loaded_callback)

    def logged_out(self, session):
        ''' libspotiy callback for logout requests '''
        if not self.seesion:
            return
        self.log("Logged out")
        self.session = None
        self.cancel_timer(self.timer)

    def playlists_loaded_callback(self, container, userinfo):
        ''' Callback invoked when playlists are loaded '''
        current_folder = []
        folder_stack = []
        folder_map = {
            0 : current_folder
        }
        for playlist in list(self.session.playlist_container()):
            if isinstance(playlist, PlaylistFolder):
                if playlist.type() == "folder_start":
                    folder_stack.append(current_folder)
                    current_folder.append(playlist)
                    current_folder = []
                    folder_map[playlist.id()] = current_folder
                elif playlist.type() == "folder_end":
                    current_folder = folder_stack.pop()
            else:
                current_folder.append(playlist)
        self.playlist_folders = folder_map

    def end_of_track(self, session):
        ''' libspotify callback for when the current track ends '''
        self.log("Track ended")
        self.cleanup()

    def wake(self, session):
        ''' libspotify callback to wake the main thread '''
        self.log("Waking main thread", debug = True)
        self.schedule_periodic_check(session)

    def metadata_updated(self, sess):
        ''' libspotify callback when new metadata arrives '''
        self.log("Metadata update", debug = True)

    def log_message(self, sess, message):
        ''' libspotify callback for system messages '''
        self.log("Message (%s)" % message.strip())

    def connection_error(self, sess, error):
        ''' libspotify callback for connection errors '''
        if error is not None:
            self.log("Connection error (%s)" % error.strip())

    def message_to_user(self, sess, message):
        ''' libspotify callback for user messages '''
        self.log("User message (%s)" % message)

    def music_delivery(self, session, frames, frame_size, num_frames,
                       sample_type, sample_rate, channels):
        ''' Called when libspotify has audio data ready for consumption '''
        try:
            frames_converted = self.audio_converter.convert(frames, num_frames)
            if not self.audio_callback(self.audio_converter.get_pending_data()):
                self.stop_playback()
                return 0
            return frames_converted
        except Exception, e:
            if self.audio_converter:
                self.log("Playback error: %s" % Plugin.Traceback())
                self.stop_playback()
            return 0
