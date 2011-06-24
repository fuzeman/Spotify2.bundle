'''
HTTP server that serves Spotify resources not supported by the main plugin
framework API (eg audio streams).
'''
from settings import REQUEST_TIMEOUT, SERVER_PORT
from socket import gethostname
from socket import error as SocketError
from time import time
from tornado.httpserver import HTTPServer
from tornado.web import Application, RequestHandler, HTTPError, asynchronous


def async_with_timeout(seconds):
    ''' Request decorator that makes them async with a timeout

    Note: should only be used with subclasses of SpotifyHandler.
    '''
    def finish_request(handler, start_time):
        assert(isinstance(handler, SpotifyHandler))
        stream = handler.request.connection.stream
        if handler.bytes_written or stream.writing():
            return
        duration = int(time() - start_time)
        Log("Request timed out after %d seconds" % duration)
        request.send_error(408)
    def decorator(func):
        func = asynchronous(func)
        def wrapper(*args, **kwargs):
            start_time = time()
            request = args[0]
            callback = lambda: finish_request(request, start_time)
            request.ioloop.add_timeout(time() + seconds, callback)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class SpotifyHandler(RequestHandler):
    ''' Base class for Spotify HTTP request handlers '''

    manager = None

    def __init__(self, *args, **kwargs):
        super(SpotifyHandler, self).__init__(*args, **kwargs)
        self.bytes_written = 0

    @property
    def ioloop(self):
        return self.manager.ioloop

    def decode_spotify_uri(self, spotify_uri):
        ''' Return a decoded spotify URI

        Assumes that any uri starting with the string 'spotify' is pre-decoded
        so it's easy to test handlers using curl.

        :param spotify_uri:   The URI string to decode.
        '''
        if spotify_uri.startswith("spotify"):
            return spotify_uri
        return D(spotify_uri)

    def handle_exception(self, error_message):
        ''' Handle unexpected exceptions '''
        Log(error_message)
        Log(Plugin.Traceback())
        self.finish()

    def send_data(self, data, finish):
        ''' Send data to the client

        :param data:          The data to send
        :param finish:        Should the connection be closed after sending?
        '''
        if self.request.connection.stream.closed():
            return False
        if data is None:
            raise HTTPError(404)
        self.write(data)
        self.bytes_written = self.bytes_written + len(data)
        self.finish() if finish else self.flush()
        return True


class ArtHandler(SpotifyHandler):
    ''' Handler for spotify art requests '''

    def __init__(self, *args, **kwargs):
        super(ArtHandler, self).__init__(*args, **kwargs)
        self.browser = None

    @async_with_timeout(REQUEST_TIMEOUT)
    def get(self, spotify_uri):
        spotify_uri = self.decode_spotify_uri(spotify_uri)
        Log("Handling art request: %s" % spotify_uri)
        try:
            callback = lambda data: self.send_data(data, finish = True)
            self.browser = self.manager.get_art(spotify_uri, callback)
            self.set_header("Content-type", "image/jpeg")
        except Exception:
            self.handle_exception("Unexpected error fetching artwork")


class TrackHandler(SpotifyHandler):
    ''' Handler for spotify track requests '''

    @asynchronous
    def get(self, spotify_uri):
        spotify_uri = self.decode_spotify_uri(spotify_uri)
        Log("Handling track request: %s" % spotify_uri)
        try:
            callback = lambda data: self.send_data(data, finish = False)
            self.manager.play_track(spotify_uri, callback, self.finish)
            self.set_header("Content-type", "audio/aiff")
            Log("Streaming track data to client...")
        except Exception:
            self.handle_exception("Unexpected error streaming audio")


class SpotifyServer(object):
    ''' The Spotify HTTP server that handles art and audio requests '''

    art_path = "/art/"
    track_path = "/track/"

    def __init__(self, manager, port = SERVER_PORT):
        SpotifyHandler.manager = manager
        app = Application([
            ("%s(.*).jpg" % self.art_path, ArtHandler),
            ("%s(.*).aiff" % self.track_path, TrackHandler)
        ])
        self.server = HTTPServer(app, no_keep_alive = True)
        self.manager = manager
        self.port = port

    def start(self):
        Log("Starting HTTP server on port %s" % self.port)
        self.server.bind(self.port)
        self.server.start()

    def get_art_url(self, uri):
        return "http://%s:%d%s%s.jpg" % (
            gethostname(), self.port, self.art_path, E(uri))

    def get_track_url(self, uri):
        return "http://%s:%d%s%s.aiff" % (
            gethostname(), self.port, self.track_path, E(uri))

