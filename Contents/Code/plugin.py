'''
Spotify plugin
'''
from session import SessionManager
from utils import wait_until_ready, create_track_object
from spotify import Link
from constants import PLUGIN_ID, RESTART_URL
from server import StreamProxyServer


class ViewMode(object):
    Tracks = "Tracks"
    Playlists = "Playlists"

    @classmethod
    def AddModes(cls, plugin):
        plugin.AddViewGroup(cls.Tracks, "List", "songs")
        plugin.AddViewGroup(cls.Playlists, "List", "items")


class SpotifyPlugin(object):
    ''' The main spotify plugin class '''

    def __init__(self):
        self.manager = None
        self.server = None
        self.start_session_manager()

    @property
    def logged_in(self):
        return self.manager and self.manager.is_logged_in()

    @property
    def is_logging_in(self):
        return self.manager and self.manager.is_logging_in()

    @property
    def username(self):
        return Prefs["username"]

    @property
    def password(self):
        return Prefs["password"]

    @property
    def access_denied_message(self):
        if self.is_logging_in:
            return MessageContainer(
                header = "Login in Progress",
                message = "We're still trying to open a Spotify session..."
            )
        else:
            return MessageContainer(
                header = 'Login Failed',
                message = 'Check your email and password in the preferences'
            )

    def preferences_updated(self):
        if not self.manager:
            self.start_session_manager()
        elif self.manager.needs_restart(self.username, self.password):
            Log("Scheduling plugin restart with updated user details")
            Thread.CreateTimer(1, self.restart)
        else:
            Log("User details unchanged")

    def restart(self):
        if self.manager:
            self.manager.stop()
        if self.server:
            self.server.stop()
        HTTP.Request(RESTART_URL, immediate = True)

    def start_session_manager(self):
        if not self.username or not self.password:
            return
        self.manager = SessionManager.create(self.username, self.password)
        self.manager.connect()
        self.start_http_server(self.manager)

    def start_http_server(self, manager):
        self.server = StreamProxyServer(manager)
        self.server.start()

    def play_track(self, uri):
        if not uri:
            Log("Play track callback invoked with NULL URI")
            return
        track_url = self.server.get_track_url(uri)
        Log("Redirecting client to stream proxied at: %s" % track_url)
        return Redirect(track_url)

    def add_track_to_directory(self, directory, track):
        if not self.manager.is_playable(track):
            Log("Ignoring unplayable track: %s" % track.name())
            return
        album_uri = str(Link.from_album(track.album()))
        track_uri = str(Link.from_track(track, 0))
        thumbnail_url = self.server.get_art_url(album_uri)
        callback = Callback(self.play_track, uri = track_uri, ext = "aiff")
        directory.add(create_track_object(track, callback, thumbnail_url))

    def get_playlist(self, index):
        playlists = self.manager.get_playlists()
        if len(playlists) < index + 1:
            return MessageContainer(
                header = "Error Retrieving Playlist",
                message = "The selected playlist details could not be found"
            )
        playlist = playlists[index]
        tracks = list(playlist)
        Log("Get playlist: %s", playlist.name().decode("utf-8"))
        directory = ObjectContainer(
            title2 = playlist.name().decode("utf-8"),
            filelabel = '%A - %T',
            view_group = ViewMode.Tracks)
        for track in wait_until_ready(tracks):
            self.add_track_to_directory(directory, track)
        return directory

    def get_playlists(self):
        Log("Get playlists")
        if not self.logged_in:
            return self.access_denied_message
        directory = ObjectContainer(
            title2 = "Playlists",
            view_group = ViewMode.Playlists)
        playlists = self.manager.get_playlists()
        for playlist in playlists:
            no_tracks = len(playlist)
            if not no_tracks:
                Log("Ignoring empty playlist: %s", playlist.name())
                continue
            index = playlists.index(playlist)
            info_label = (
                "%s %s" % (no_tracks, "tracks" if no_tracks > 1 else "track"))
            directory.add(
                DirectoryObject(
                    key = Callback(self.get_playlist, index = index),
                    title = playlist.name().decode("utf-8"),
                    infoLabel = info_label,
                    thumb = R("placeholder-playlist.png")
                )
            )
        return directory

    def get_artist_albums(self, uri):
        artist = Link.from_string(uri).as_artist()
        Log("Get artist albums: " + artist.name().decode("utf-8"))
        browser = self.manager.browse_artist(artist)
        albums = list(browser)
        directory = ObjectContainer(
            title2 = artist.name().decode("utf-8"),
            view_group = ViewMode.Tracks)
        for album in albums:
            album_uri = str(Link.from_album(album))
            directory.add(
                DirectoryObject(
                    key = Callback(self.get_album_tracks, uri = album_uri),
                    title = album.name().decode("utf-8"),
                    thumb = self.server.get_art_url(album_uri)
                )
            )
        return directory

    def get_album_tracks(self, uri):
        album = Link.from_string(uri).as_album()
        Log("Get album: " + album.name())
        browser = self.manager.browse_album(album)
        tracks = list(browser)
        directory = ObjectContainer(
            title2 = album.name().decode("utf-8"),
            view_group = ViewMode.Tracks)
        for track in tracks:
            self.add_track_to_directory(directory, track)
        return directory

    def search(self, query, artists = False, albums = False, **kwargs):
        Log("Search for %s: %s" % ("artists" if artists else "albums", query))
        results = self.manager.search(query)
        directory = ObjectContainer(title2 = "Results")
        for artist in results.artists() if artists else ():
            artist_uri = str(Link.from_artist(artist))
            directory.add(
                DirectoryObject(
                    key = Callback(self.get_artist_albums, uri = artist_uri),
                    title = artist.name().decode("utf-8"),
                    thumb = R("placeholder-artist.png")
                )
            )
        for album in results.albums() if albums else ():
            album_uri = str(Link.from_album(album))
            directory.add(
                DirectoryObject(
                    key = Callback(self.get_album_tracks, uri = album_uri),
                    title = album.name().decode("utf-8"),
                    thumb = self.server.get_art_url(album_uri)
                )
            )
        return directory

    def search_menu(self):
        Log("Search menu")
        return ObjectContainer(
            title2 = "Search",
            objects = [
                InputDirectoryObject(
                    key = Callback(self.search, albums = True),
                    prompt = L("Search for Albums"),
                    title = L('Search Albums'),
                    thumb = R("icon-default.png")
                ),
                InputDirectoryObject(
                    key = Callback(self.search, artists = True),
                    prompt = L("Search for Artists"),
                    title = L('Search Artists'),
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
                    title = L('Playlists'),
                    thumb = R("icon-default.png")
                ),
                DirectoryObject(
                    key = Callback(self.search_menu),
                    title = L('Search'),
                    thumb = R("icon-default.png")
                ),
                PrefsObject(
                    title = L('Preferences...'),
                    thumb = R("icon-default.png")
                )
            ],
        )
