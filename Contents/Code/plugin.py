'''
Spotify plugin
'''
from session import SessionManager
from utils import wait_until_ready, create_track_object
from spotify import Link
from constants import PLUGIN_ID, RESTART_URL
from server import StreamProxyServer


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
        self.manager = SessionManager(self.username, self.password)
        self.manager.start()
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

    def get_playlist(self, index):
        playlists = self.manager.playlists
        if len(playlists) < index + 1:
            return MessageContainer(
                header = "Error Retrieving Playlist",
                message = "The selected playlist details could not be found"
            )
        playlist = playlists[index]
        tracks = list(playlist)
        Log("Get playlist: %s", playlist.name().decode("utf-8"))
        directory = ObjectContainer(
            title2 = playlist.name().decode("utf-8"), filelabel = '%A - %T')
        for track in wait_until_ready(tracks):
            if not self.manager.is_playable(track):
                Log("Ignoring unplayable track: %s" % track.name())
                continue
            album_uri = str(Link.from_album(track.album()))
            track_uri = str(Link.from_track(track, 0))
            thumbnail_url = self.server.get_art_url(album_uri)
            callback = Callback(self.play_track, uri = track_uri, ext = "aiff")
            directory.add(create_track_object(track, callback, thumbnail_url))
        return directory

    def get_playlists(self):
        Log("Get playlists")
        if not self.logged_in:
            return self.access_denied_message
        directory = ObjectContainer(title2 = "Playlists")
        playlists = self.manager.playlists
        for playlist in wait_until_ready(playlists):
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

    def main_menu(self):
        Log("Spotify main menu")
        menu = ObjectContainer(
            objects = [
                DirectoryObject(
                    key = Callback(self.get_playlists),
                    title = L('Playlists'),
                    thumb = R("icon-default.png")
                ),
                PrefsObject(
                    title = L('Preferences...'),
                    thumb = R("icon-default.png")
                )
            ],
        )
        return menu
