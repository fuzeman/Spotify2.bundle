from spotify.commands.base import Command

import logging

log = logging.getLogger(__name__)


class PingFlash2(Command):
    key = [[7, 203], [15, 15], [1, 96], [19, 93], [3, 165], [14, 130], [12, 16], [4, 6], [6, 225], [13, 37]]

    def process(self, ping):
        parts = ping.split(' ')
        pong = "undefined 0"

        if len(parts) >= 20:
            result = []

            for x in range(len(self.key)):
                idx = self.key[x][0]
                xor = self.key[x][1]

                result.append(str(int(parts[idx]) ^ xor))

            pong = ' '.join(result)

        log.debug('received ping %s, sending pong: %s' % (ping, pong))

        return self.send('sp/pong_flash2', pong)
