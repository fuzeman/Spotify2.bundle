from spotify.commands.base import Command
from spotify.commands.flash_key import FLASH_KEY

import logging

log = logging.getLogger(__name__)


class PingFlash2(Command):
    def process(self, ping):
        ping = ping.split(' ')
        pong = "undefined 0"

        if len(ping) >= 20:
            result = []

            for idx, code in FLASH_KEY:
                val = int(ping[idx])

                result.append(str(val ^ code if type(code) is int else code[val]))

            pong = ' '.join(result)

        log.debug('received ping %s, sending pong: %s' % (ping, pong))

        return self.send('sp/pong_flash2', pong)
