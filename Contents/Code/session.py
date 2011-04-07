'''
Spotify session manager
'''
from spotify.manager import SpotifySessionManager
from spotify import Link
from tempfile import TemporaryFile
from constants import PLUGIN_ID, RESTART_URL
from utils import wait_until_ready, WritePipeWrapper
from os import pipe, fdopen
import aifc
import threading
import struct

class Track(object):
    def __init__(self, track):
        self.track = track
        self.sample_rate = 44100.0
        self.frames_played = 0

    @property
    def total_frames(self):
        return int(self.track.duration() / 1000.0 * self.sample_rate)

    @property
    def is_finished(self):
        return self.frames_played >= self.total_frames

    def add_played_frames(self, frame_count):
        self.frames_played = self.frames_played + frame_count


class SessionManager(SpotifySessionManager, threading.Thread):

    user_agent = PLUGIN_ID
    application_key = Resource.Load('spotify_appkey.key')

    def __init__(self, username, password):
        self.session = None
        self.current_track = None
        self.pipe = None
        self.output_file = None
        self.logout_event = threading.Event()
        self.lock = threading.RLock()
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
        if not self.current_track:
            return
        Log("Session: stop playback")
        self.lock.acquire()
        self.session.stop()
        try:
            self.output_file.close() # will throw if it tries to seek
        except:
            pass
        if self.pipe:
            self.pipe.close()
        self.output_file = None
        self.current_track = None
        self.pipe = None
        self.lock.release()

    def is_playable(self, track):
        Log("Session: is playable")
        playable = True
        self.lock.acquire()
        wait_until_ready(track)
        if self.session.is_local(track):
            playable = False
        elif not self.session.is_available(track):
            playable = False
        self.lock.release()
        return playable

    def needs_restart(self, username, password):
        return self.username != username \
            or self.password != password

    def is_logging_in(self):
        return self.session is None \
            and not self.logout_event.isSet()

    def is_logged_in(self):
        return self.session is not None

    def create_aiff_wrapper(self, output_stream, track):
        aiff_file = aifc.open(self.pipe, "wb")
        aiff_file.aifc()
        aiff_file.setsampwidth(2)
        aiff_file.setnchannels(2)
        aiff_file.setframerate(track.sample_rate)
        aiff_file.setnframes(track.total_frames)
        return aiff_file

    def play_track(self, uri):
        Log("Session: play track")
        if not self.session:
            return
        self.lock.acquire()
        self.stop_playback()
        result = None
        Log("Resolving Spotify URI: %s", uri)
        track = Link.from_string(uri).as_track()
        try:
            self.session.load(track)
            self.session.play(True)
            self.current_track = Track(track)
            Log("Playing track: %s", track.name())
            read, write = pipe()
            self.pipe = WritePipeWrapper(write)
            self.output_file = self.create_aiff_wrapper(
                self.pipe,
                self.current_track
            )
            result = fdopen(read,'r',0)
        except:
            Log("Playback aborted: error loading track")
            self.stop_playback()
        self.lock.release()
        return result

    def get_art(self, uri):
        Log("Session: get art")
        if not self.session:
            return
        self.lock.acquire()
        resut = None
        image_id = None
        link = Link.from_string(uri)
        if link.type() == Link.LINK_ALBUM:
            album = link.as_album()
            image_id = album.cover()
        if image_id:
            image = self.session.image_create(image_id)
            wait_until_ready(image)
            result = TemporaryFile()
            data = image.data()
            result.write(data)
            result.seek(0)
        self.lock.release()
        return result

    def browse_album(self, album):
        Log("Session: browse album")
        def browse_finished(browse):
            pass
        if not self.session:
            return
        self.lock.acquire()
        browser = self.session.browse_album(
            album,
            browse_finished)
        wait_until_ready(browser)
        self.lock.release()
        return browser

    def search(self, query):
        Log("Session: search")
        def search_finished(results):
            pass
        if not self.session:
            return
        self.lock.acquire()
        search = self.session.search(
            query = query,
            callback = search_finished)
        wait_until_ready(search)
        self.lock.release()
        return search

    def logout(self):
        Log("Session: logout")
        if not self.session:
            return
        self.lock.acquire()
        Log("Logging out of Spotify")
        self.session.logout()
        self.lock.release()
        self.logout_event.wait()

    def logged_in(self, session, error):
        Log("Session: logged in")
        self.lock.acquire()
        self.session = session
        Log("Logged in to Spotify")
        self.lock.release()

    def logged_out(self, session):
        Log("Session: logged out")
        self.lock.acquire()
        Log("Logged out of Spotify")
        self.session = None
        self.logout_event.set()
        self.lock.release()

    def metadata_updated(self, sess):
        Log("SPOTIFY: metatadata update")

    def log_message(self, sess, data):
        Log("SPOTIFY: %s", data)

    def connection_error(self, sess, error):
        Log("SPOTIFY: connection_error")

    def message_to_user(self, sess, message):
        Log("SPOTIFY: message_to_user: " + str(message))

    def music_delivery(self, sess, frames, frame_size, num_frames, sample_type,
                       sample_rate, channels):
        if not self.pipe:
            return
        try:
            data = struct.pack('>' + str(len(frames)/2) + 'H',
                *struct.unpack('<' + str(len(frames)/2) + 'H', frames)
            )
            self.output_file.writeframesraw(data)
            self.current_track.add_played_frames(num_frames)
            if self.current_track.is_finished:
                Log("Finished playing track: %s", self.current_track.name())
                self.stop_playback()
        except (IOError, OSError), e:
            Log("Pipe closed by request handler")
            self.stop_playback()
        except Exception, e:
            Log("Error: %s" % e)
            Log("Type: %s" % type(e))
            Log(Plugin.Traceback())
            self.stop_playback()
