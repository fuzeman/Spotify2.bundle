'''
Spotify plugin
'''
from session import SessionManager
from utils import wait_until_ready
from spotify import Link
from constants import PLUGIN_ID, RESTART_URL


class SpotifyPlugin(object):
    ''' The main spotify plugin class '''

    def __init__(self):
        self.manager = None
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
        self.manager.stop()
        HTTP.Request(RESTART_URL, immediate = True)

    def start_session_manager(self):
        if not self.username or not self.password:
            return
        self.manager = SessionManager(self.username, self.password)
        self.manager.start()

    def play_track(self, uri):
        track_path = self.manager.play_track(uri)
        if not track_path:
            return
        stream = Stream.LocalFile(track_path, size=100000)
        return Redirect(stream)

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
            artists = (a.name().decode("utf-8") for a in track.artists())
            uri = str(Link.from_track(track, 0))
            callback = Callback(self.play_track, uri = uri, ext = "aiff")
            directory.add(
                TrackObject(
                    items = [
                        MediaObject(
                            parts = [PartObject(key = callback)],
                        )
                    ],
                    key = "Track",
                    title = track.name().decode("utf-8"),
                    artist = ", ".join(artists),
                    index = track.index(),
                    duration = int(track.duration())
                )
            )
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
                    infoLabel = info_label
                )
            )
        return directory

    def main_menu(self):
        Log("Spotify main menu")
        menu = ObjectContainer(
            title2 = "Spotify",
            objects = [
                DirectoryObject(
                    key = Callback(self.get_playlists),
                    title = L('Playlists')
                ),
                PrefsObject(
                    title = L('Preferences...')
                )
            ]
        )
        return menu
