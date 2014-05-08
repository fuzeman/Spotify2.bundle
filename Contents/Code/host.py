from client import SpotifyClient
from containers import Containers
from routing import function_path, route_path
from plugin.server import Server
from utils import authenticated, ViewMode

from cachecontrol import CacheControl
import requests
import time


class SpotifyHost(object):
    def __init__(self):
        self.client = None
        self.server = None
        self.start()

        self.session = requests.session()
        self.session_cached = CacheControl(self.session)

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
        """ Called when the user updates the plugin preferences"""

        # Trigger a client restart
        self.start()

    def start(self):
        """ Start the Spotify client and HTTP server """
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

    @authenticated
    def play(self, uri):
        """ Play a spotify track: redirect the user to the actual stream """
        Log('play(%s)' % repr(uri))

        return Redirect(self.client.play(uri))

    def get_uri_image(self, uri):
        obj = self.client.get(uri)
        images = None

        if isinstance(obj, SpotifyArtist):
            images = obj.getPortraits()
        elif isinstance(obj, SpotifyAlbum):
            images = obj.getCovers()
        elif isinstance(obj, SpotifyTrack):
            images = obj.getAlbum().getCovers()

        return self.select_image(images)

    @authenticated
    def image(self, uri):
        if not uri:
            # TODO media specific placeholders
            return Redirect(R('placeholder-artist.png'))

        if uri.startswith('spotify:'):
            # Fetch object for spotify URI and select image
            image_url = self.get_uri_image(uri)

            if not image_url:
                # TODO media specific placeholders
                return Redirect(R('placeholder-artist.png'))
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
            callback(Containers.playlists(playlists, **kwargs))

    @authenticated
    def playlist(self, uri, callback):
        @self.sp.playlist(uri)
        def on_playlist(playlist):
            Log("Got playlist: %s", playlist.name)
            Log.Debug('playlist truncated: %s', playlist.truncated)

            callback(Containers.playlist(playlist))

    @authenticated
    def starred(self):
        """ Return a directory containing the user's starred tracks"""
        Log("starred")

        oc = ObjectContainer(
            title2=L("MENU_STARRED"),
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        starred = self.client.get_starred()

        for track in starred.getTracks():
            self.add_track_to_directory(track, oc)

        return oc

    def metadata(self, track_uri):
        Log.Debug('fetching metadata for track_uri: "%s"', track_uri)

        oc = ObjectContainer()

        track = self.client.get(track_uri)
        self.add_track_to_directory(track, oc)

        return oc

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

    #
    # Create objects
    #

    def get_track_location(self, track):
        if self.client.proxy_tracks and self.server:
            return self.server.get_track_url(track.getURI())

        return function_path('play', uri=track.getURI(), ext='mp3')

    def create_album_object(self, album):
        """ Factory method for album objects """
        title = album.getName().decode("utf-8")

        if Prefs["displayAlbumYear"] and album.getYear() != 0:
            title = "%s (%s)" % (title, album.getYear())

        image_url = self.select_image(album.getCovers())

        return AlbumObject(
            key=route_path('album', album.getURI()),
            rating_key=album.getURI(),

            title=title,
            artist=album.getArtists(nameOnly=True),

            track_count=album.getNumTracks(),
            source_title='Spotify',

            art=function_path('image.png', uri=image_url),
            thumb=function_path('image.png', uri=image_url),
        )

    #
    # Insert objects into container
    #

    def add_section_header(self, title, oc):
        oc.add(
            DirectoryObject(
                key='',
                title=title
            )
        )

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
        image_url = self.select_image(artist.getPortraits())

        oc.add(
            ArtistObject(
                key=route_path('artist', artist.getURI()),
                rating_key=artist.getURI(),

                title=artist.getName().decode("utf-8"),
                source_title='Spotify',

                art=function_path('image.png', uri=image_url),
                thumb=function_path('image.png', uri=image_url)
            )
        )
