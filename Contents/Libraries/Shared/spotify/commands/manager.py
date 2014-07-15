from spotify.commands import DoWork, PingFlash2

from pyemitter import Emitter
import logging

log = logging.getLogger(__name__)


class CommandManager(Emitter):
    def __init__(self, sp):
        self.sp = sp

        self.handlers = {
            'do_work': DoWork(sp),
            'ping_flash2': PingFlash2(sp)
        }

        # Attach 'error' listeners
        for command in self.handlers.values():
            command.on('error', self.on_error)

    def process(self, name, *args):
        if name in self.handlers:
            self.handlers[name].process(*args)
            return True

        return False

    def on_error(self, message):
        log.warn('Error returned from command handler, disconnecting...')

        # Trigger disconnection
        self.sp.disconnect()

        # Fire 'error'
        self.emit('error', message)
