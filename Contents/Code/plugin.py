'''
Spotify plugin
'''
from spotify.manager import SpotifySessionManager
import threading

PLUGIN_ID = "com.plexapp.plugins.spotify"
RESTART_URL = "http://localhost:32400/:/plugins/%s/restart" % PLUGIN_ID

class SessionManager(SpotifySessionManager, threading.Thread):

    def __init__(self, username, password):
        self.session = None
        self.logout_event = threading.Event()
        self.application_key = Resource.Load('spotify_appkey.key')
        SpotifySessionManager.__init__(self, username, password)
        threading.Thread.__init__(self, name = 'SpotifySessionManagerThread')

    @property
    def playlists(self):
        return list(self.session.playlist_container()) if self.session else []

    def run(self):
        Log("Attempting to log in to Spotify as %s", self.username)
        try:
            self.connect()
        except Exception, e:
            Log("Exception in session manager: %s", e)

    def stop(self):
        Log("Stopping session manager")
        self.logout()
        self.disconnect()
        self.join()
        Log("Session manager stopped")

    def needs_restart(self, username, password):
        return self.username != username \
            or self.password != password

    def is_logging_in(self):
        return self.session is None \
            and not self.logout_event.isSet()

    def is_logged_in(self):
        return self.session

    def logout(self):
        if not self.session:
            return
        Log("Logging out of Spotify")
        self.session.logout()
        self.logout_event.wait()
        self.session = None

    def logged_in(self, session, error):
        self.session = session
        Log("Logged in to Spotify")

    def logged_out(self, session):
        Log("Logged out of Spotify")
        self.session = None
        self.logout_event.set()

    def connection_error(self, sess, error):
        Log("SPOTIFY: connection_error")

    def message_to_user(self, sess, message):
        Log("SPOTIFY: message_to_user: " + str(message))

    def notify_main_thread(self, sess):
        Log("SPOTIFY: notify_main_thread")


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

    def get_playlist(self, index):
        playlists = self.manager.playlists
        if len(playlists) < index + 1:
            return MessageContainer(
                header = "Error Retrieving Playlist",
                message = "The selected playlist details could not be found"
            )
        playlist = playlists[index]
        Log("Get playlist: %s", playlist.name().decode("utf-8"))
        directory = ObjectContainer()

        '''
        TrackItem(
          PlayTrack,
          title = track.name(),
          artist = ", ".join(map(lambda artist: artist.name(), track.artists())),
          album = track.album(),
          index = track.index(),
          thumb = server.art(str(Link.from_album(track.album()))),
          duration = int(track.duration()),
          contextKey = track.name(),
          contextArgs = {}
        ),

        '''


    def get_playlists(self):
        Log("Get playlists")
        if not self.logged_in:
            return self.access_denied_message
        directory = ObjectContainer(title2 = "Playlists")
        playlists = self.manager.playlists
        for playlist in playlists:
            if not playlist.is_loaded():
                continue
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
