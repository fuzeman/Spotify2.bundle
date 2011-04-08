'''
Spotify session manager
'''
from spotify.manager import SpotifySessionManager
from spotify import Link, runloop, connect
from tempfile import TemporaryFile
from constants import PLUGIN_ID
from utils import WritePipeWrapper
from os import pipe, fdopen
import aifc
import threading
import struct


'''
For extra detailed logging switch this on
'''
DEBUG = False


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


class ThreadSafeSessionManager(SpotifySessionManager):
    ''' Spotify session manager that uses a runloop to manage callbacks
    Create instances of this class using the create() factory method '''

    user_agent = PLUGIN_ID
    application_key = Resource.Load('spotify_appkey.key')

    @classmethod
    def create(cls, username, password):
        return cls(username, password).main_thread_proxy

    def __init__(self, username, password):
        super(ThreadSafeSessionManager, self).__init__(username, password)
        self.timer = None
        self.session = None
        self.logout_event = threading.Event()
        self.loop = runloop.RunLoop("SpotifySessionManager")

    @property
    def main_thread_proxy(self):
        ''' Return a proxy that bounces requests to the main Spotify thread'''
        proxy = self.loop.get_proxy(self)
        proxy.connect = self.connect
        proxy.log = self.log
        return proxy

    def is_logging_in(self):
        return self.session is None \
            and not self.logout_event.isSet()

    def is_logged_in(self):
        return self.session is not None

    def is_session_thread(self):
        ''' Is the current thread the session thread '''
        return threading.currentThread() == self.loop

    def log(self, message, debug = False, check_thread = True):
        if debug and not DEBUG:
            return
        prefix = "SPOTIFY:"
        if check_thread and not self.is_session_thread():
            prefix = "SPOTIFY (WRONG THREAD):"
        thread_id = getattr(thread, "ident", "Unknown")
        Log("%s %s" % (prefix, message))

    def schedule_periodic_check(self, session, timeout = 0):
        ''' Schedules the next periodic Spotify event processing call '''
        callback = lambda: self.periodic_check(session)
        self.timer = self.loop.schedule_callback(timeout, callback)

    def periodic_check(self, session):
        ''' Process pending Spotify events and schedule the next check '''
        self.log("Processing events", debug = True)
        timeout = session.process_events()
        self.schedule_periodic_check(session, timeout / 1000.0)

    def wait_for_objects(self, objects):
        ''' Wait until a spotify object or objects are ready '''
        instances = [objects] if hasattr(objects, "is_loaded") else objects
        for instance in instances:
            while not instance.is_loaded() and self.session:
                if self.is_session_thread():
                    self.session.process_events()
                else:
                    sleep(interval)
        return instances

    def connect(self):
        ''' Connect to Spotify '''
        self.log("Connecting", check_thread = False)
        self.loop.start()
        self.schedule_periodic_check(connect(self))

    def disconnect(self):
        ''' Disconnect from Spotify '''
        self.log("Disconnecting", check_thread = False)
        if self.timer:
            self.loop.cancel_timer(self.timer)
        self.loop.stop()

    def logout(self):
        if not self.session:
            return
        self.log("Logging out", check_thread = Falseo)
        self.session.logout()
        self.logout_event.wait()

    def logged_in(self, session, error):
        self.log("Logged in", check_thread = False)
        self.session = session

    def logged_out(self, session):
        self.log("Logged out", check_thread = False)
        self.session = None
        self.logout_event.set()

    def wake(self, session):
        self.log("Waking main thread", debug = True, check_thread = False)
        self.schedule_periodic_check(session)

    def metadata_updated(self, sess):
        self.log("Metadata update", check_thread = False)

    def log_message(self, sess, data):
        self.log("Message (%s)" % data, check_thread = False)

    def connection_error(self, sess, error):
        self.log("Connection error (%s)" % error, check_thread = False)

    def message_to_user(self, sess, message):
        self.log("User message (%s)" % message, check_thread = False)


class SessionManager(ThreadSafeSessionManager):

    def __init__(self, username, password):
        super(SessionManager, self).__init__(username, password)
        self.current_track = None
        self.pipe = None
        self.output_file = None

    def is_playable(self, track):
        ''' Check if a track can be played by a client or not '''
        playable = True
        self.wait_for_objects(track)
        if self.session.is_local(track):
            playable = False
        elif not self.session.is_available(track):
            playable = False
        return playable

    def needs_restart(self, username, password):
        return self.username != username \
            or self.password != password

    def create_aiff_wrapper(self, output_stream, track):
        ''' Create an aiff wrapper for an output stream '''
        aiff_file = aifc.open(self.pipe, "wb")
        aiff_file.aifc()
        aiff_file.setsampwidth(2)
        aiff_file.setnchannels(2)
        aiff_file.setframerate(track.sample_rate)
        aiff_file.setnframes(track.total_frames)
        return aiff_file

    def create_image_file(self, image_id):
        ''' Create an file containing a spotify image '''
        if not image_id:
            self.log("Can't create image with empty id")
            return
        image = self.session.image_create(image_id)
        self.wait_for_objects(image)
        result = TemporaryFile()
        result.write(image.data())
        result.seek(0)
        return result

    def get_art(self, uri):
        if not self.session:
            return
        self.log("Get artwork: %s" % uri)
        link = Link.from_string(uri)
        if link.type() != Link.LINK_ALBUM:
            self.log("Ignoring non album artwork")
            return
        album = link.as_album()
        return self.create_image_file(album.cover())

    def get_playlists(self):
        ''' Return the user's playlists ordered by name '''
        self.log("Get playlists")
        lists = list(self.session.playlist_container()) if self.session else []
        return sorted(self.wait_for_objects(lists), key = lambda l: l.name())

    def search(self, query):
        if not self.session:
            return
        self.log("Search (query = %s)" % query)
        search = self.session.search(
            query = query, callback = lambda results: None)
        self.wait_for_objects(search)
        return search

    def browse_album(self, album):
        if not self.session:
            return
        self.log("Browse album: %s" % album)
        browser = self.session.browse_album(album, lambda browser: None)
        self.wait_for_objects(browser)
        return browser

    def stop_playback(self):
        if not self.current_track:
            return
        self.log("Stop playback")
        try:
            self.output_file.close() # will throw if it tries to seek
        except:
            pass
        if self.pipe:
            self.pipe.close()
        self.output_file = None
        self.current_track = None
        self.pipe = None

    def play_track(self, uri):
        if not self.session:
            return
        self.log("Play track: %s" % uri)
        self.stop_playback()
        track = Link.from_string(uri).as_track()
        try:
            self.session.load(track)
            self.session.play(True)
            self.current_track = Track(track)
            read, write = pipe()
            self.pipe = WritePipeWrapper(write)
            self.output_file = self.create_aiff_wrapper(
                self.pipe,
                self.current_track
            )
            return fdopen(read,'r',0)
        except:
            self.log("Playback aborted: error loading track")
            self.stop_playback()

    def music_delivery(self, sess, frames, frame_size, num_frames, sample_type,
                       sample_rate, channels):
        ''' Called when libspotify has audio data ready for consumption '''
        if not self.pipe:
            return
        try:
            data = struct.pack('>' + str(len(frames)/2) + 'H',
                *struct.unpack('<' + str(len(frames)/2) + 'H', frames)
            )
            self.output_file.writeframesraw(data)
            self.current_track.add_played_frames(num_frames)
            if self.current_track.is_finished:
                message = "Finished playing: %s", self.current_track.name()
                self.log(message, check_thread = False)
                self.main_thread_proxy.stop_playback()
            return num_frames
        except (IOError, OSError), e:
            self.log("Pipe closed by request handler", check_thread = False)
            self.main_thread_proxy.stop_playback()
        except Exception, e:
            self.log("Playback error: %s" % e, check_thread = False)
            self.main_thread_proxy.stop_playback()

