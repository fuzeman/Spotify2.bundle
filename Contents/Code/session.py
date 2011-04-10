'''
Spotify session manager
'''
from spotify.manager import SpotifySessionManager
from spotify import Link, runloop, connect
from tempfile import TemporaryFile
from constants import PLUGIN_ID, DEBUG,
from utils import AudioStream
import threading


class ThreadSafeSessionManager(SpotifySessionManager):
    ''' Spotify session manager that uses a runloop to manage callbacks

    Create instances of this class using the create() factory method.
    '''

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

    def track_ended(self, session):
        self.log("Track ended")
        #self.session.unload()

    def logged_in(self, session, error):
        self.log("Logged in", check_thread = False)
        self.session = session

    def logged_out(self, session):
        self.log("Logged out", check_thread = False)
        self.session = None
        self.logout_event.set()

    def end_of_track(self, session):
        ''' Called when the current track ends '''
        self.loop.invoke_async(lambda: self.track_ended(session))

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
        self.audio_stream = None

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
        self.log("Search (query = %s)" % query)
        search = self.session.search(
            query = query, callback = lambda results: None)
        self.wait_for_objects(search)
        return search

    def browse_album(self, album):
        self.log("Browse album: %s" % album)
        browser = self.session.browse_album(album, lambda browser: None)
        self.wait_for_objects(browser)
        return browser

    def stop_playback(self):
        if not self.audio_stream:
            return
        self.log("Stop playback")
        self.audio_stream.close()
        self.audio_stream = None

    def play_track(self, uri):
        try:
            self.log("Play track: %s" % uri)
            track = Link.from_string(uri).as_track()
            self.stop_playback()
            self.session.load(track)
            self.session.play(True)
            self.audio_stream = AudioStream(track)
            return self.audio_stream.output
        except Exception, e:
            self.log("Playback aborted: error loading track: %s" % e)
            self.stop_playback()

    def music_delivery(self, session, frames, frame_size, num_frames,
                       sample_type, sample_rate, channels):
        ''' Called when libspotify has audio data ready for consumption '''
        try:
            return self.audio_stream.process_frames(frames, num_frames)
        except Exception, e:
            if self.audio_stream:
                self.log("Playback error: %s" % e, check_thread = False)
                self.main_thread_proxy.stop_playback()
            return 0
