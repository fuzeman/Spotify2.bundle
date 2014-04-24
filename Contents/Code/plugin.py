from client import SpotifyClient
from routing import function_path, route_path
from utils import localized_format, authenticated, ViewMode, Track

from cachecontrol import CacheControl
from spotify_web.friendly import SpotifyArtist, SpotifyAlbum, SpotifyTrack
from threading import Lock
import locale
import requests


class SpotifyPlugin(object):
    def __init__(self):
        self.client = None
        self.server = None
        self.start()

        self.session = requests.session()
        self.session_cached = CacheControl(self.session)

        self.current_track = None

        self.track_lock = Lock()

    @property
    def username(self):
        return Prefs["username"]

    @property
    def password(self):
        return Prefs["password"]

    def preferences_updated(self):
        """ Called when the user updates the plugin preferences"""

        # Trigger a client restart
        self.start()

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
    def play(self, uri):
        """ Play a spotify track: redirect the user to the actual stream """
        Log('play(%s)' % repr(uri))

        if not uri:
            Log("Play track callback invoked with NULL URI")
            return

        if self.current_track:
            # Send stop event for previous track
            self.client.spotify.api.send_track_event(
                self.current_track.track.getID(),
                'stop',
                self.current_track.track.getDuration()
            )

        track = self.client.get(uri)

        return Redirect(self.get_track_url(track))

    def get_track_url(self, track):
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
        self.client.spotify.api.send_track_event(track.getID(), 'play', 0)
        track_url = track.getFileURL(retries=1)

        # If first request failed, trigger re-connection to spotify
        retry_num = 0
        while not track_url and retry_num < 3:
            retry_num += 1

            Log.Info('get_track_url failed, re-connecting to spotify...')
            self.start()

            # Update reference to spotify client (otherwise getFileURL request will fail)
            track.spotify = self.client.spotify

            Log.Info('Fetching track url...')
            self.client.spotify.api.send_track_event(track.getID(), 'play', 0)
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

    @staticmethod
    def select_image(images):
        if images.get('640'):
            return images['640']
        elif images.get('300'):
            return images['300']

        Log.Info('Unable to select image, available sizes: %s' % images.keys())
        return None

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
            self.add_playlist_to_directory(playlist, oc)

        return oc

    @authenticated
    def playlist(self, uri):
        pl = self.client.get(uri)

        if pl is None:
            # Unable to find playlist
            return MessageContainer(
                header=L("MSG_TITLE_UNKNOWN_PLAYLIST"),
                message='URI: %s' % uri
            )

        Log("Get playlist: %s", pl.getName().decode("utf-8"))
        Log.Debug('playlist truncated: %s', pl.obj.contents.truncated)

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
    def search(self, query, limit=7):
        """ Search asynchronously invoking the completion callback when done.

        :param query: Search query
        :type query: str

        :param limit: Number of items to list per type (artist, album, etc..)
        :type limit: int
        """
        Log('Searching for "%s"' % query)

        result = self.client.search(query)

        oc = ObjectContainer(title2="Results")

        def media_append(title, func, key=None):
            if key is None:
                key = title

            items = getattr(result, 'get%s' % key)()
            total = getattr(result, 'get%sTotal' % key)()

            if not items or not len(items):
                return

            self.add_section_header('%s (%s)' % (
                title,
                locale.format('%d', total, grouping=True)
            ), oc)

            for x in range(limit):
                if x < len(items):
                    func(items[x], oc)
                else:
                    # Add a placeholder to fix alignment on PHT
                    self.add_section_header('', oc)


        media_append('Artists', self.add_artist_to_directory)
        media_append('Albums', self.add_album_to_directory)
        media_append('Tracks', self.add_track_to_directory)
        media_append('Playlists', self.add_playlist_to_directory)

        if not len(oc):
            oc = MessageContainer(
                header=L("MSG_TITLE_NO_RESULTS"),
                message=localized_format("MSG_FMT_NO_RESULTS", query)
            )

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

    def create_track_object(self, track):
        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(key=function_path('play', uri=track.getURI(), ext='mp3'))],
                    container=Container.MP3,
                    audio_codec=AudioCodec.MP3
                )
            ],
            key=track.getName().decode("utf-8"),
            rating_key=track.getName().decode("utf-8"),
            title=track.getName().decode("utf-8"),
            album=track.getAlbum(nameOnly=True).decode("utf-8"),
            artist=track.getArtists(nameOnly=True),
            index=int(track.getNumber()),
            duration=int(track.getDuration()),
            thumb=function_path('image.png', uri=self.select_image(track.getAlbumCovers()))
        )

    def create_album_object(self, album):
        """ Factory method for album objects """
        title = album.getName().decode("utf-8")

        if Prefs["displayAlbumYear"] and album.year() != 0:
            title = "%s (%s)" % (title, album.year())

        return DirectoryObject(
            key=route_path('album', album.getURI()),
            title=title,
            thumb=function_path('image.png', uri=self.select_image(album.getCovers()))
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
        oc.add(
            DirectoryObject(
                key=route_path('artist', artist.getURI()),
                title=artist.getName().decode("utf-8"),
                thumb=function_path('image.png', uri=self.select_image(artist.getPortraits()))
            )
        )

    def add_playlist_to_directory(self, playlist, oc):
        oc.add(
            DirectoryObject(
                key=route_path('playlist', playlist.getURI()),
                title=playlist.getName().decode("utf-8"),
                thumb=R("placeholder-playlist.png")
            )
        )
