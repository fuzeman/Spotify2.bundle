'''
HTTP Server for proxying Spotify streams to PMS clients
'''

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from constants import LOCALHOST, SERVER_PORT
from socket import gethostname
import threading


class SpotifyHandler(BaseHTTPRequestHandler):
    ''' Handler implementation '''

    def do_GET(self):
        if self.server.is_track_url(self.path):
            self.handle_track_request()
        else:
            Log("Ignoring unrecognised request: %s" % self.path)
            self.send_response(404)

    def handle_track_request(self):
        Log("Handing track request: %s" % self.path)
        self.send_response(404)


class StreamProxyServer(HTTPServer, threading.Thread):
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

    def is_track_url(self, url):
        components = url.split("/")
        return len(components) == 3 and components[1] == "track"

