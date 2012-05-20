'''
Spotify plugin
'''
from client import SpotifyClient
from settings import PLUGIN_ID, RESTART_URL
from spotify import Link
from server import SpotifyServer
from utils import RunLoopMixin, assert_loaded, localized_format
from urllib import urlopen


def authenticated(func):
    ''' Decorator used to force a valid session for a given call

    We must return a class with a __name__ property here since the Plex
    framework uses it to generate a route and it stops us assigning
    properties to function objects.
    '''
    class decorator(object):
        @property
        def __name__(self):
            return func.func_name

        def __call__(self, *args, **kwargs):
            plugin = args[0]
            client = plugin.client
            if not client or not client.is_logged_in():
                return self.access_denied_message(client)
            return func(*args, **kwargs)

        def access_denied_message(self, client):
            if not client:
                return MessageContainer(
                    header = L("MSG_TITLE_MISSING_LOGIN"),
                    message = L("MSG_BODY_MISSING_LOGIN")
                )
            elif client.is_logging_in():
                return MessageContainer(
                    header = L("MSG_TITLE_LOGIN_IN_PROGRESS"),
                    message = L("MSG_BODY_LOGIN_IN_PROGRESS")
                )
            else:
                return MessageContainer(
                    header = L("MSG_TITLE_LOGIN_FAILED"),
                    message = client.login_error
                )
    return decorator()


class ViewMode(object):
    Tracks = "Tracks"
    Playlists = "Playlists"

    @classmethod
    def AddModes(cls, plugin):
        plugin.AddViewGroup(cls.Tracks, "List", "songs")
        plugin.AddViewGroup(cls.Playlists, "List", "items")


class SpotifyPlugin(RunLoopMixin):
    ''' The main spotify plugin class '''

    def __init__(self, ioloop):
        self.ioloop = ioloop
        self.client = None
        self.server = None
        self.browsers = {}
        self.start()

    @property
    def username(self):
        return Prefs["username"]

    @property
    def password(self):
        return Prefs["password"]

    def preferences_updated(self):
        ''' Called when the user updates the plugin preferences

        Note: if a user changes the username and password and we have an
        existing client we need to restart the plugin to use the new details.
        libspotify doesn't play nice with username and password changes.
        '''
        if not self.client:
            self.start()
        elif self.client.needs_restart(self.username, self.password):
            self.restart()
        else:
            Log("User details unchanged")

    def restart(self):
        ''' Restart the plugin to pick up new authentication details

        Note: don't restart inline since it will make the framework barf.
        Instead schedule a callback on the ioloop's next tick
        '''
        Log("Restarting plugin")
        if self.client:
            self.client.disconnect()
        self.schedule_timer(0.2, lambda: urlopen(RESTART_URL))

    def start(self):
        ''' Start the Spotify client and HTTP server '''
        if not self.username or not self.password:
            Log("Username or password not set: not logging in")
            return
        self.client = SpotifyClient(self.username, self.password, self.ioloop)
        self.client.connect()
        self.server = SpotifyServer(self.client)
        self.server.start()

    def play_track(self, uri):
        ''' Play a spotify track: redirect the user to the actual stream '''
        if not uri:
            Log("Play track callback invoked with NULL URI")
            return
        track_url = self.server.get_track_url(uri)
        Log("Redirecting client to stream proxied at: %s" % track_url)
        return Redirect(track_url)

    def create_track_object(self, track):
        ''' Factory for track directory objects '''
        album_uri = str(Link.from_album(track.album()))
        track_uri = str(Link.from_track(track, 0))
        thumbnail_url = self.server.get_art_url(album_uri)
        callback = Callback(self.play_track, uri = track_uri, ext = "aiff")
        artists = (a.name().decode("utf-8") for a in track.artists())
        return TrackObject(
            items = [
                MediaObject(
                    parts = [PartObject(key = callback)],
                )
            ],
            key = track.name().decode("utf-8"),
            rating_key = track.name().decode("utf-8"),
            title = track.name().decode("utf-8"),
            album = track.album().name().decode("utf-8"),
            artist = ", ".join(artists),
            index = track.index(),
            duration = int(track.duration()),
            thumb = thumbnail_url
       )

    def create_album_object(self, album):
        ''' Factory method for album objects '''
        album_uri = str(Link.from_album(album))
        title = album.name().decode("utf-8")
        if Prefs["displayAlbumYear"] and album.year() != 0:
            title = "%s (%s)" % (title, album.year())
        return DirectoryObject(
            key = Callback(self.get_album_tracks, uri = album_uri),
            title = title,
            thumb = self.server.get_art_url(album_uri)
        )

    def add_track_to_directory(self, track, directory):
        if not self.client.is_track_playable(track):
            Log("Ignoring unplayable track: %s" % track.name())
            return
        directory.add(self.create_track_object(track))

    def add_album_to_directory(self, album, directory):
        if not self.client.is_album_playable(album):
            Log("Ignoring unplayable album: %s" % album.name())
            return
        directory.add(self.create_album_object(album))

    def add_artist_to_directory(self, artist, directory):
        artist_uri = str(Link.from_artist(artist))
        directory.add(
            DirectoryObject(
                key = Callback(self.get_artist_albums, uri = artist_uri),
                title = artist.name().decode("utf-8"),
                thumb = R("placeholder-artist.png")
            )
        )

    @authenticated
    def get_playlist(self, folder_id, index):
        playlists = self.client.get_playlists(folder_id)
        if len(playlists) < index + 1:
            return MessageContainer(
                header = L("MSG_TITLE_PLAYLIST_ERROR"),
                message = L("MSG_BODY_PLAYIST_ERROR")
            )
        playlist = playlists[index]
        tracks = list(playlist)
        Log("Get playlist: %s", playlist.name().decode("utf-8"))
        directory = ObjectContainer(
            title2 = playlist.name().decode("utf-8"),
            view_group = ViewMode.Tracks)
        for track in assert_loaded(tracks):
            self.add_track_to_directory(track, directory)
        return directory

    @authenticated
    def get_artist_albums(self, uri, completion):
        ''' Browse an artist invoking the completion callback when done.

        :param uri:            The Spotify URI of the artist to browse.
        :param completion:     A callback to invoke with results when done.
        '''
        artist = Link.from_string(uri).as_artist()
        def browse_finished(browser):
            del self.browsers[uri]
            albums = list(browser)
            directory = ObjectContainer(
                title2 = artist.name().decode("utf-8"),
                view_group = ViewMode.Tracks)
            for album in albums:
                self.add_album_to_directory(album, directory)
            completion(directory)
        self.browsers[uri] = self.client.browse_artist(artist, browse_finished)

    @authenticated
    def get_album_tracks(self, uri, completion):
        ''' Browse an album invoking the completion callback when done.

        :param uri:            The Spotify URI of the album to browse.
        :param completion:     A callback to invoke with results when done.
        '''
        album = Link.from_string(uri).as_album()
        def browse_finished(browser):
            del self.browsers[uri]
            tracks = list(browser)
            directory = ObjectContainer(
                title2 = album.name().decode("utf-8"),
                view_group = ViewMode.Tracks)
            for track in tracks:
                self.add_track_to_directory(track, directory)
            completion(directory)
        self.browsers[uri] = self.client.browse_album(album, browse_finished)

    @authenticated
    def get_playlists(self, folder_id = 0):
        Log("Get playlists")
        directory = ObjectContainer(
            title2 = L("MENU_PREFS"),
            view_group = ViewMode.Playlists)
        playlists = self.client.get_playlists(folder_id)
        for playlist in playlists:
            index = playlists.index(playlist)
            if playlist.type() in ['folder_start', 'folder_end', 'placeholder']:
                callback = Callback(
                    self.get_playlists, folder_id = playlist.id())
            else:
                callback = Callback(
                    self.get_playlist, folder_id = folder_id, index = index)
            directory.add(
                DirectoryObject(
                    key = callback,
                    title = playlist.name().decode("utf-8"),
                    thumb = R("placeholder-playlist.png")
                )
            )
        return directory

    @authenticated
    def get_starred_tracks(self):
        ''' Return a directory containing the user's starred tracks'''
        Log("Get starred tracks")
        directory = ObjectContainer(
            title2 = L("MENU_STARRED"),
            view_group = ViewMode.Tracks)
        starred = list(self.client.get_starred_tracks())
        for track in starred:
            self.add_track_to_directory(track, directory)
        return directory

    @authenticated
    def search(self, query, completion, artists = False, albums = False):
        ''' Search asynchronously invoking the completion callback when done.

        :param query:          The query string to use.
        :param completion:     A callback to invoke with results when done.
        :param artists:        Determines whether artist matches are returned.
        :param albums:         Determines whether album matches are returned.
        '''
        params = "%s: %s" % ("artists" if artists else "albums", query)
        Log("Search for %s" % params)
        def search_finished(results, userdata):
            Log("Search completed: %s" % params)
            result = ObjectContainer(title2 = "Results")
            for artist in results.artists() if artists else ():
                self.add_artist_to_directory(artist, result)
            for album in results.albums() if albums else ():
                self.add_album_to_directory(album, result)
            if not len(result):
                if len(results.did_you_mean()):
                    message = localized_format(
                        "MSG_FMT_DID_YOU_MEAN", results.did_you_mean())
                else:
                    message = localized_format("MSG_FMT_NO_RESULTS", query)
                result = MessageContainer(
                    header = L("MSG_TITLE_NO_RESULTS"), message = message)
            completion(result)
        self.client.search(query, search_finished)

    @authenticated
    def search_menu(self):
        Log("Search menu")
        return ObjectContainer(
            title2 = L("MENU_SEARCH"),
            objects = [
                InputDirectoryObject(
                    key = Callback(self.search, albums = True),
                    prompt = L("PROMPT_ALBUM_SEARCH"),
                    title = L("MENU_ALBUM_SEARCH"),
                    thumb = R("icon-default.png")
                ),
                InputDirectoryObject(
                    key = Callback(self.search, artists = True),
                    prompt = L("PROMPT_ARTIST_SEARCH"),
                    title = L("MENU_ARTIST_SEARCH"),
                    thumb = R("icon-default.png")
                )
            ],
        )

    def main_menu(self):
        Log("Spotify main menu")
        return ObjectContainer(
            objects = [
                DirectoryObject(
                    key = Callback(self.get_playlists),
                    title = L("MENU_PLAYLISTS"),
                    thumb = R("icon-default.png")
                ),
                DirectoryObject(
                    key = Callback(self.search_menu),
                    title = L("MENU_SEARCH"),
                    thumb = R("icon-default.png")
                ),
                DirectoryObject(
                    key = Callback(self.get_starred_tracks),
                    title = L("MENU_STARRED"),
                    thumb = R("icon-default.png")
                ),
                PrefsObject(
                    title = L("MENU_PREFS"),
                    thumb = R("icon-default.png")
                )
            ],
        )
