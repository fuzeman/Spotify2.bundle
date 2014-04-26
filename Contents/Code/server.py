from settings import SERVER_PORT

from socket import gethostname
from tornado.httpserver import HTTPServer
from tornado.web import Application, RequestHandler, HTTPError, asynchronous
import logging
import requests

log = logging.getLogger('server')


class SpotifyHandler(RequestHandler):
    """ Base class for Spotify HTTP request handlers """

    client = None

    def __init__(self, *args, **kwargs):
        super(SpotifyHandler, self).__init__(*args, **kwargs)
        self.bytes_written = 0

    def handle_exception(self, error_message):
        """ Handle unexpected exceptions """
        Log(error_message)
        Log(Plugin.Traceback())
        self.finish()

    def send_data(self, data, finish=False):
        """ Send data to the client

        :param data:          The data to send
        """
        if self.request.connection.stream.closed():
            return False

        if data is None:
            raise HTTPError(404)

        self.write(data)
        self.bytes_written = self.bytes_written + len(data)
        self.finish() if finish else self.flush()
        return True


class TrackHandler(SpotifyHandler):
    """ Handler for spotify track requests """

    def __init__(self, *args, **kwargs):
        super(SpotifyHandler, self).__init__(*args, **kwargs)

        self.bytes_written = 0

    @asynchronous
    def get(self, uri):
        try:
            track = self.client.get(uri)
            track_url = self.client.get_track_url(track)

            self.set_header('Content-Type', 'audio/mpeg')

            r = requests.get(track_url, stream=True, timeout=3)

            for chunk in r.iter_content(200 * 1024):
                if chunk:
                    self.send_data(chunk)

            self.finish()

        except Exception, ex:
            self.send_data(str(ex))

        self.finish()

        #try:
        #    callback = lambda data: self.send_data(data)

        #    self.client.play_track(uri, callback, self.finish)
        #    self.set_header("Content-type", "audio/mp3")

        #    Log("Streaming track data to client...")
        #except Exception:
        #    self.handle_exception("Unexpected error streaming audio")


class SpotifyServer(object):
    """ The Spotify HTTP server that handles art and audio requests """

    track_path = "/track/"

    def __init__(self, client, port=SERVER_PORT):
        SpotifyHandler.client = client

        self.client = client
        self.port = port

        app = Application([
            ("%s(.*).mp3" % self.track_path, TrackHandler)
        ])

        self.server = HTTPServer(app, no_keep_alive=True)

    def start(self):
        log.debug("Starting HTTP server on port %s" % self.port)
        self.server.bind(self.port)
        self.server.start()

    def get_track_url(self, uri):
        return "http://%s:%d%s%s.mp3" % (gethostname(), self.port, self.track_path, E(uri))
