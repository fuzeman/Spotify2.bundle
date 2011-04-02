'''
Spotify session manager
'''
from spotify.manager import SpotifySessionManager
from spotify import Link
from tempfile import NamedTemporaryFile
from time import sleep
from constants import PLUGIN_ID, RESTART_URL
from utils import wait_until_ready, WritePipeWrapper
from os import pipe, fdopen
import aifc
import threading
import struct


class SessionManager(SpotifySessionManager, threading.Thread):

    user_agent = PLUGIN_ID
    application_key = Resource.Load('spotify_appkey.key')

    def __init__(self, username, password):
        self.session = None
        self.current_track = None
        self.pipe = None
        self.aiff_file = None
        self.logout_event = threading.Event()
        SpotifySessionManager.__init__(self, username, password)
        threading.Thread.__init__(self, name = 'SpotifySessionManagerThread')

    @property
    def playlists(self):
        lists = list(self.session.playlist_container()) if self.session else []
        return sorted(wait_until_ready(lists), key = lambda l: l.name())

    def run(self):
        Log("Attempting to log in to Spotify as %s", self.username)
        try:
            self.connect()
        except Exception, e:
            Log("Exception in session manager: %s", e)

    def stop(self):
        Log("Stopping session manager")
        self.stop_playback()
        self.logout()
        self.disconnect()
        self.join()
        Log("Session manager stopped")

    def stop_playback(self):
        @lock(self)
        def stop_playback():
            try:
                self.aiff_file.close() # will throw if it tries to seek
            except:
                pass
            if self.pipe:
                self.pipe.close()
            self.aiff_file = None
            self.current_track = None
            self.pipe = None

    def needs_restart(self, username, password):
        return self.username != username \
            or self.password != password

    def is_logging_in(self):
        return self.session is None \
            and not self.logout_event.isSet()

    def is_logged_in(self):
        return self.session is not None

    def create_aiff_wrapper(self):
        self.aiff_file = aifc.open(self.pipe, "wb")
        self.aiff_file.aifc()
        self.aiff_file.setsampwidth(2)
        self.aiff_file.setnchannels(2)
        self.aiff_file.setframerate(44100.0)
        self.aiff_file.setnframes(5090106)

    def play_track(self, uri):
        if not self.session:
            return
        self.stop_playback()
        @lock(self)
        def play_track():
            Log("Resolving Spotify URI: %s", uri)
            track = Link.from_string(uri).as_track()
            try:
                self.session.load(track)
            except:
                Log("Playback aborted: error loading track")
                return
            Log("Playing track: %s", track.name())
            self.current_track = track
            self.session.play(True)
        if not self.current_track:
            return
        read, write = pipe()
        client_pipe, self.pipe = fdopen(read,'r',0), WritePipeWrapper(write)
        return client_pipe

    def logout(self):
        if not self.session:
            return
        @lock(self)
        def logout():
            Log("Logging out of Spotify")
            self.session.logout()
        self.logout_event.wait()

    def logged_in(self, session, error):
        @lock(self)
        def logged_in():
            self.session = session
            Log("Logged in to Spotify")

    def logged_out(self, session):
        @lock(self)
        def logged_out():
            Log("Logged out of Spotify")
            self.session = None
            self.logout_event.set()

    def metadata_updated(self, sess):
        Log("SPOTIFY: metatadata update")

    def log_message(self, sess, data):
        Log("SPOTIFY: %s", data)

    def connection_error(self, sess, error):
        Log("SPOTIFY: connection_error")

    def message_to_user(self, sess, message):
        Log("SPOTIFY: message_to_user: " + str(message))

    def notify_main_thread(self, sess):
        Log("SPOTIFY: notify_main_thread")

    def music_delivery(self, sess, frames, frame_size, num_frames, sample_type,
                       sample_rate, channels):
        if not self.pipe:
            return
        if not self.aiff_file:
            self.create_aiff_wrapper()
        try:
            data = struct.pack('>' + str(len(frames)/2) + 'H',
                *struct.unpack('<' + str(len(frames)/2) + 'H', frames)
            )
            self.aiff_file.writeframesraw(data)
        except OSError, e:
            Log("Pipe closed by request handler")
            self.stop_playback()
        except Exception, e:
            Log("Error: %s" % e)
            Log("Type: %s" % type(e))
            Log(Plugin.Traceback())
            self.stop_playback()
