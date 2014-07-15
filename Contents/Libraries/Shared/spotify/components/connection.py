from spotify.components.base import Component
from spotify.core.helpers import repr_trim
from spotify.core.request import Request

from pyemitter import Emitter
from threading import Lock, Timer
from ws4py.client.threadedclient import WebSocketClient
import json
import logging

log = logging.getLogger(__name__)


class Connection(Component, Emitter):
    heartbeat_interval = 180  # (in seconds)

    def __init__(self, sp):
        super(Connection, self).__init__(sp)

        self.client = None
        self.connected = False
        self.disconnecting = False

        self.heartbeat_timer = None

        self.seq = 0
        self.requests = {}

        self.send_lock = Lock()

    def reset(self):
        self.connected = False
        self.disconnecting = False

        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
            self.heartbeat_timer = None

        self.seq = 0
        self.requests = {}

        self.send_lock = Lock()

    def connect(self, url):
        if self.client:
            return

        self.reset()

        self.client = Client(self, url)\
            .on('open', self.on_open)\
            .on('message', self.on_message)\
            .on('close', self.on_close)

        log.info('Connecting to "%s"' % url)
        self.client.connect()

    def disconnect(self):
        if not self.connected:
            return

        self.disconnecting = True
        self.connected = False

        if self.client:
            self.client.close()
            self.client = None

    def on_open(self):
        log.debug('WebSocket "open" event')

        if self.connected:
            return

        self.send_connect()

    def on_message(self, message):
        if message is None:
            log.warn('empty messaged received')
            return

        # Parse json message
        try:
            data = json.loads(message)
        except Exception, e:
            self.emit('error', 'Unable to decode message (%s): %s' % (e, message))
            return

        # Handle commands (do_work, ping_flash2, etc..)
        if 'message' in data:
            return self.emit('command', *data['message'])

        mid = data.get('id')

        # Request doesn't exist
        if mid not in self.requests:
            log.warn('Unhandled message received with id %s' % mid)
            return

        request = self.requests[mid]

        # Delete request from map, not needed anymore
        del self.requests[mid]

        # Process the response (fire callbacks)
        request.process(data)

    def on_close(self, code, reason=None):
        log.info('Spotify connection closed')

        if self.disconnecting:
            log.debug('Client requested disconnect, ignoring "close" event')
            self.reset()
            return

        self.disconnect()
        self.reset()

        self.emit('close', code=code, reason=reason)

    def send(self, name, *args):
        return self.build(name, *args)\
                   .send()

    def build(self, name, *args):
        return Request(self.sp, name, args)

    def send_request(self, request):
        # Build message
        message = request.build(self.seq)

        if not message:
            return None

        # Store request (to trigger callback on response)
        self.requests[self.seq] = request
        self.seq += 1

        # Build and send request
        self.send_message(message)

        return request

    def send_message(self, message):
        if self.client is None:
            raise Exception('Unable to send message, socket has been closed')

        encoded = json.dumps(message, separators=(',', ':'))
        log.debug('send encoded: %s' % repr_trim(encoded))

        with self.send_lock:
            self.client.send(encoded)

    def send_connect(self):
        log.debug('send_connect()')

        args = self.sp.config['credentials'][0].split(':', 2)
        args[2] = args[2].decode('string_escape')

        self.build('connect', *args)\
            .on('success', self.on_connect)\
            .pipe('error', self)\
            .send()

    def send_heartbeat(self):
        self.build('sp/echo', 'h')\
            .pipe('error', self)\
            .send()

    def schedule_heartbeat(self):
        if not self.connected:
            pass

        def heartbeat_trigger():
            # Send heartbeat ('sp/echo')
            self.send_heartbeat()

            # Schedule next heartbeat
            self.schedule_heartbeat()

        self.heartbeat_timer = Timer(self.heartbeat_interval, heartbeat_trigger)
        self.heartbeat_timer.start()

    def on_connect(self, message):
        log.debug('SpotifyConnection "connect" event: %s', message)

        if message.get('result') != 'ok':
            # TODO: handle possible error case
            log.error('unable to connect')
            return

        log.debug('connected')
        self.connected = True

        # Schedule initial heartbeat
        self.schedule_heartbeat()

        self.emit('connect')


class Client(WebSocketClient, Emitter):
    threading = True
    threading_workers = 4

    def __init__(self, connection, *args, **kwargs):
        WebSocketClient.__init__(self, *args, **kwargs)
        self._connection = connection

        self.daemon = True

    def opened(self):
        self.emit('open')

    def received_message(self, message):
        self.emit('message', message=message.data)

    def closed(self, code, reason=None):
        self.emit('close', code=code, reason=reason)
