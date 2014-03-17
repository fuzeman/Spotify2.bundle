from client import SpotifyClient
from settings import PLUGIN_ID, RESTART_URL, PREFIX, ROUTEBASE
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
                return self.access_denied_message(plugin, client)
            return func(*args, **kwargs)

        def access_denied_message(self, plugin, client):
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
                # Trigger a re-connect
                Log.Warn('Connection failed, reconnecting...')
                plugin.start()

                return MessageContainer(
                    header=L("MSG_TITLE_LOGIN_FAILED"),
                    message=L("MSG_TITLE_LOGIN_FAILED")
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

        self.current_track = None

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

        # Ensure previous client is shutdown
        if self.client:
            self.client.shutdown()

        self.client = SpotifyClient(self.username, self.password)

    @authenticated
    @route(ROUTEBASE + 'play')
    def play(self, uri):
        """ Play a spotify track: redirect the user to the actual stream """
        Log('play(%s)' % repr(uri))

        if not uri:
            Log("Play track callback invoked with NULL URI")
            return

        if self.current_track:
            # Send stop event for previous track
            self.client.spotify.api.send_track_event(
                self.current_track.getID(),
                'stop',
                self.current_track.getDuration()
            )

        self.current_track = self.client.get(uri)

        self.client.spotify.api.send_track_event(self.current_track.getID(), 'play', 0)
        return Redirect(self.current_track.getFileURL())

    @authenticated
    def artist(self, uri):
        """ Browse an artist.

        :param uri:            The Spotify URI of the artist to browse.
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
    def album(self, uri):
        """ Browse an album.

        :param uri:            The Spotify URI of the album to browse.
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
    def playlists(self):
        Log("playlists")

        oc = ObjectContainer(
            title2=L("MENU_PLAYLISTS"),
            view_group=ViewMode.Playlists
        )

        playlists = self.client.get_playlists()

        for playlist in playlists:
            oc.add(
                DirectoryObject(
                    key=Callback(self.playlist, uri=playlist.getURI()),
                    title=playlist.getName().decode("utf-8"),
                    thumb=R("placeholder-playlist.png")
                )
            )

        return oc

    @authenticated
    def playlist(self, uri):
        pl = self.client.get_playlist(uri)

        Log("Get playlist: %s", pl.getName().decode("utf-8"))

        oc = ObjectContainer(
            title2=pl.getName().decode("utf-8"),
            view_group=ViewMode.Tracks
        )

        for track in pl.getTracks():
            self.add_track_to_directory(track, oc)

        return oc

    @authenticated
    def starred(self):
        """ Return a directory containing the user's starred tracks"""
        Log("starred")

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
                    key=Callback(self.playlists),
                    title=L("MENU_PLAYLISTS"),
                    thumb=R("icon-default.png")
                ),
                DirectoryObject(
                    key=Callback(self.starred),
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

        artists = (a.getName().decode("utf-8") for a in track.getArtists())

        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(key=Callback(self.play, uri=track.getURI(), ext='mp3'))],
                    container=Container.MP3,
                    audio_codec=AudioCodec.MP3
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
            key=Callback(self.album, uri=album.getURI()),
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
                key=Callback(self.artist, uri=artist.getURI()),
                title=artist.getName().decode("utf-8"),
                thumb=R("placeholder-artist.png")
            )
        )
