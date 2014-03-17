from client import SpotifyClient
from settings import PLUGIN_ID, RESTART_URL, PREFIX
from utils import RunLoopMixin, assert_loaded, localized_format
from urllib import urlopen


def authenticated(func):
    """ Decorator used to force a valid session for a given call

    We must return a class with a __name__ property here since the Plex
    framework uses it to generate a route and it stops us assigning
    properties to function objects.
    """

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
                    header=L("MSG_TITLE_MISSING_LOGIN"),
                    message=L("MSG_BODY_MISSING_LOGIN")
                )
            elif not client.spotify.api.ws:
                return MessageContainer(
                    header=L("MSG_TITLE_LOGIN_IN_PROGRESS"),
                    message=L("MSG_BODY_LOGIN_IN_PROGRESS")
                )
            else:
                return MessageContainer(
                    header=L("MSG_TITLE_LOGIN_FAILED"),
                    message=client.login_error
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
    """ The main spotify plugin class """

    def __init__(self):
        self.client = None
        self.server = None
        self.start()

    @property
    def username(self):
        return Prefs["username"]

    @property
    def password(self):
        return Prefs["password"]

    def preferences_updated(self):
        """ Called when the user updates the plugin preferences

        Note: if a user changes the username and password and we have an
        existing client we need to restart the plugin to use the new details.
        libspotify doesn't play nice with username and password changes.
        """
        if not self.client:
            self.start()
        elif self.client.needs_restart(self.username, self.password):
            self.restart()
        else:
            Log("User details unchanged")

    def restart(self):
        """ Restart the plugin to pick up new authentication details

        Note: don't restart inline since it will make the framework barf.
        Instead schedule a callback on the ioloop's next tick
        """
        Log("Restarting plugin")
        if self.client:
            self.client.disconnect()
        self.schedule_timer(0.2, lambda: urlopen(RESTART_URL))

    def start(self):
        """ Start the Spotify client and HTTP server """
        if not self.username or not self.password:
            Log("Username or password not set: not logging in")
            return

        self.client = SpotifyClient(self.username, self.password)

        #self.server = SpotifyServer(self.client)
        #self.server.start()

    def play_track(self, uri):
        """ Play a spotify track: redirect the user to the actual stream """
        if not uri:
            Log("Play track callback invoked with NULL URI")
            return
        track_url = self.server.get_track_url(uri)
        Log("Redirecting client to stream proxied at: %s" % track_url)
        return Redirect(track_url)

    @authenticated
    def get_playlist(self, folder_id, index):
        playlists = self.client.get_playlists(folder_id)
        if len(playlists) < index + 1:
            return MessageContainer(
                header=L("MSG_TITLE_PLAYLIST_ERROR"),
                message=L("MSG_BODY_PLAYIST_ERROR")
            )
        playlist = playlists[index]
        tracks = list(playlist)
        Log("Get playlist: %s", playlist.name().decode("utf-8"))
        directory = ObjectContainer(
            title2=playlist.name().decode("utf-8"),
            view_group=ViewMode.Tracks)
        for track in assert_loaded(tracks):
            self.add_track_to_directory(track, directory)
        return directory

    @authenticated
    def get_artist_albums(self, uri):
        """ Browse an artist invoking the completion callback when done.

        :param uri:            The Spotify URI of the artist to browse.
        :param completion:     A callback to invoke with results when done.
        """
        artist = self.client.get(uri)

        oc = ObjectContainer(
            title2=artist.getName().decode("utf-8"),
            view_group=ViewMode.Tracks
        )

        for album in artist.getAlbums():
            self.add_album_to_directory(album, oc)

        return oc

    @authenticated
    def get_album_tracks(self, uri):
        """ Browse an album invoking the completion callback when done.

        :param uri:            The Spotify URI of the album to browse.
        :param completion:     A callback to invoke with results when done.
        """
        album = self.client.get(uri)

        oc = ObjectContainer(
            title2=album.getName().decode("utf-8"),
            view_group=ViewMode.Tracks
        )

        for track in album.getTracks():
            self.add_track_to_directory(track, oc)

        return oc

    @authenticated
    def get_playlists(self, folder_id=0):
        Log("Get playlists")
        directory = ObjectContainer(
            title2=L("MENU_PREFS"),
            view_group=ViewMode.Playlists)
        playlists = self.client.get_playlists(folder_id)
        for playlist in playlists:
            index = playlists.index(playlist)
            if playlist.type() in ['folder_start', 'folder_end', 'placeholder']:
                callback = Callback(
                    self.get_playlists, folder_id=playlist.id())
            else:
                callback = Callback(
                    self.get_playlist, folder_id=folder_id, index=index)
            directory.add(
                DirectoryObject(
                    key=callback,
                    title=playlist.name().decode("utf-8"),
                    thumb=R("placeholder-playlist.png")
                )
            )
        return directory

    @authenticated
    def get_starred_tracks(self):
        """ Return a directory containing the user's starred tracks"""
        Log("Get starred tracks")

        oc = ObjectContainer(
            title2=L("MENU_STARRED"),
            view_group=ViewMode.Tracks
        )

        starred = self.client.get_starred()

        for track in starred.getTracks():
            self.add_track_to_directory(track, oc)

        return oc

    @authenticated
    def search(self, query):
        """ Search asynchronously invoking the completion callback when done.

        :param query:          The query string to use.
        """
        Log('Searching for "%s"' % query)

        results = self.client.search(query)

        oc = ObjectContainer(title2="Results")

        for artist in results.getArtists():
            self.add_artist_to_directory(artist, oc)

        #for album in results.getAlbums():
        #    self.add_album_to_directory(album, oc)

        if not len(oc):
            if len(results.did_you_mean()):
                message = localized_format("MSG_FMT_DID_YOU_MEAN", results.did_you_mean())
            else:
                message = localized_format("MSG_FMT_NO_RESULTS", query)

            oc = MessageContainer(header=L("MSG_TITLE_NO_RESULTS"), message=message)

        return oc

    def main_menu(self):
        Log("Spotify main menu")

        return ObjectContainer(
            objects=[
                InputDirectoryObject(
                    key=Callback(self.search),
                    prompt=L("PROMPT_SEARCH"),
                    title=L("MENU_SEARCH"),
                    thumb=R("icon-default.png")
                ),
                DirectoryObject(
                    key=Callback(self.get_playlists),
                    title=L("MENU_PLAYLISTS"),
                    thumb=R("icon-default.png")
                ),
                DirectoryObject(
                    key=Callback(self.get_starred_tracks),
                    title=L("MENU_STARRED"),
                    thumb=R("icon-default.png")
                ),
                PrefsObject(
                    title=L("MENU_PREFS"),
                    thumb=R("icon-default.png")
                )
            ],
        )

    #
    # Create objects
    #

    def create_track_object(self, track):
        album = track.getAlbum()

        #thumbnail_url = self.server.get_art_url(album.getURI())
        callback = Callback(self.play_track, uri=track.getURI(), ext="aiff")

        artists = (a.getName().decode("utf-8") for a in track.getArtists())

        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(key=callback)],
                    )
            ],
            key=track.getName().decode("utf-8"),
            rating_key=track.getName().decode("utf-8"),
            title=track.getName().decode("utf-8"),
            album=album.getName().decode("utf-8"),
            artist=", ".join(artists),
            index=int(track.getNumber()),
            duration=int(track.getDuration()),
            #thumb=thumbnail_url
        )

    def create_album_object(self, album):
        """ Factory method for album objects """
        title = album.getName().decode("utf-8")

        if Prefs["displayAlbumYear"] and album.year() != 0:
            title = "%s (%s)" % (title, album.year())

        return DirectoryObject(
            key=Callback(self.get_album_tracks, uri=album.getURI()),
            title=title,
            #thumb=self.server.get_art_url(album.getURI())
        )

    #
    # Insert objects into container
    #

    def add_track_to_directory(self, track, oc):
        if not self.client.is_track_playable(track):
            Log("Ignoring unplayable track: %s" % track.name())
            return

        oc.add(self.create_track_object(track))

    def add_album_to_directory(self, album, oc):
        if not self.client.is_album_playable(album):
            Log("Ignoring unplayable album: %s" % album.name())
            return

        oc.add(self.create_album_object(album))

    def add_artist_to_directory(self, artist, oc):
        oc.add(
            DirectoryObject(
                key=Callback(self.get_artist_albums, uri=artist.getURI()),
                title=artist.getName().decode("utf-8"),
                thumb=R("placeholder-artist.png")
            )
        )
