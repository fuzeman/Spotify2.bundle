'''
HTTP Server for proxying Spotify streams to PMS clients
'''

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
from constants import BUFFER_SIZE, SERVER_PORT
from socket import gethostname
from socket import error as SocketError
import threading


class SpotifyHandler(BaseHTTPRequestHandler):
    ''' Handler implementation '''

    def do_GET(self):
        if self.server.is_track_url(self.path):
            self.handle_track_request()
        else:
            Log("Ignoring unrecognised request: %s" % self.path)
            self.send_error(404)

    def handle_track_request(self):
        Log("Handing track request: %s" % self.path)
        spotify_uri = self.server.get_spotify_track_uri(self.path)
        try:
            self.pipe = self.server.manager.play_track(spotify_uri)
            if not self.pipe:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-type", "audio/aiff")
            self.end_headers()
            Log("Streaming track data to client...")
            while 1:
                data = self.pipe.read(BUFFER_SIZE)
                if len(data) > 0:
                    self.wfile.write(data)
                    self.wfile.flush()
                if len(data) < BUFFER_SIZE:
                    break
            Log("Playback finished")
        except SocketError, e:
            Log("Socket closed by client")
        except Exception, e:
            Log("Exception streaming track: %s", e)
            Log(Plugin.Traceback())
        if self.pipe:
            self.pipe.close()


class StreamProxyServer(ThreadingMixIn, HTTPServer, threading.Thread):
    ''' Server implementation '''

    def __init__(self, manager, port = SERVER_PORT):
        HTTPServer.__init__(self, ('', port), SpotifyHandler)
        threading.Thread.__init__(self)
        self.manager = manager
        self.serving = False

    def run(self):
        Log("HTTP server listening on port: %s", self.server_port)
        self.serving = True
        while self.serving:
            self.handle_request()

    def stop(self):
        Log("Stopping HTTP server")
        self.serving = False
        self.join()
        Log("HTTP server stopped")

    def get_track_url(self, uri):
        return "http://%s:%d/track/%s.aiff" % (
            gethostname(), self.server_port, E(uri))

    def get_spotify_track_uri(self, url):
        return D(url.split("/")[-1].split(".")[0])

    def is_track_url(self, url):
        components = url.split("/")
        return len(components) == 3 and components[1] == "track"

