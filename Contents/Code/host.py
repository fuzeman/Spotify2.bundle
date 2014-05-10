from client import SpotifyClient
from containers import Containers
from plugin.server import Server
from routing import route_path
from search import SpotifySearch
from utils import authenticated, ViewMode

from cachecontrol import CacheControl
import requests


class SpotifyHost(object):
    def __init__(self):
        self.client = None
        self.server = None
        self.start()

        self.search = SpotifySearch(self)

        self.session = requests.session()
        self.session_cached = CacheControl(self.session)

        self.containers = Containers(self)

    @property
    def username(self):
        return Prefs["username"]

    @property
    def password(self):
        return Prefs["password"]

    @property
    def proxy_tracks(self):
        return Prefs['proxy_tracks']

    @property
    def sp(self):
        if not self.client:
            return None

        return self.client.sp

    def preferences_updated(self):
        # Trigger a client restart
        self.start()

    def start(self):
        if not self.username or not self.password:
            Log("Username or password not set: not logging in")
            return

        if not self.client:
            self.client = SpotifyClient()

        # Start server (if 'proxy_tracks' is enabled)
        if not self.server and self.proxy_tracks:
            self.server = Server(self.client)
            self.server.start()

        # Stop server if 'proxy_tracks' has been disabled
        if self.server and not self.proxy_tracks:
            self.server.stop()
            self.server = None

        # Update reference on SpotifyClient
        self.client.server = self.server

        # Update preferences and start/restart the client
        self.client.set_preferences(self.username, self.password, self.proxy_tracks)
        self.client.start()

    #
    # Routes
    #

    @authenticated
    def play(self, uri):
        """ Play a spotify track: redirect the user to the actual stream """
        Log('play(%s)' % repr(uri))

        return Redirect(self.client.play(uri))

    @authenticated
    def image(self, uri):
        if not uri:
            # TODO media specific placeholders
            return Redirect(R('placeholder-artist.png'))

        if uri.startswith('spotify:'):
            # TODO image for URI
            raise NotImplementedError()
        else:
            # pre-selected image provided
            Log.Debug('Using pre-selected image URL: "%s"' % uri)
            image_url = uri

        return self.session_cached.get(image_url).content

    @authenticated
    def artist(self, uri):
        """ Browse an artist.

        :param uri:            The Spotify URI of the artist to browse.
        """
        artist = self.client.get(uri)

        oc = ObjectContainer(
            title2=artist.getName().decode("utf-8"),
            content=ContainerContent.Albums
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
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        for track in album.getTracks():
            self.add_track_to_directory(track, oc)

        return oc

    @authenticated
    def playlists(self, callback, **kwargs):
        @self.sp.user.playlists()
        def on_playlists(playlists):
            callback(self.containers.playlists(playlists, **kwargs))

    @authenticated
    def playlist(self, uri, callback):
        @self.sp.playlist(uri)
        def on_playlist(playlist):
            Log("Got playlist: %s", playlist.name)
            Log.Debug('playlist truncated: %s', playlist.truncated)

            callback(self.containers.playlist(playlist))

    @authenticated
    def starred(self, callback):
        return SpotifyHost.playlist(self, 'spotify:user:%s:starred' % self.sp.username, callback)

    @authenticated
    def metadata(self, uri, callback):
        Log.Debug('fetching metadata for uri: "%s"', uri)

        @self.sp.metadata(uri)
        def on_track(track):
            callback(self.containers.metadata(track))

    @authenticated
    def search(self, query, callback, type='all', count=7, plain=False):
        self.search.run(query, callback, type, count, plain)

    def main_menu(self):
        return ObjectContainer(
            objects=[
                InputDirectoryObject(
                    key=route_path('search'),
                    prompt=L("PROMPT_SEARCH"),
                    title=L("MENU_SEARCH"),
                    thumb=R("icon-default.png")
                ),
                DirectoryObject(
                    key=route_path('playlists'),
                    title=L("MENU_PLAYLISTS"),
                    thumb=R("icon-default.png")
                ),
                DirectoryObject(
                    key=route_path('starred'),
                    title=L("MENU_STARRED"),
                    thumb=R("icon-default.png")
                ),
                PrefsObject(
                    title=L("MENU_PREFS"),
                    thumb=R("icon-default.png")
                )
            ],
        )
