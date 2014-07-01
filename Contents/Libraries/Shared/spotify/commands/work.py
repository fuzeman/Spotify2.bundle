from spotify.commands.base import Command

import execjs
import logging
import traceback

log = logging.getLogger(__name__)

WORK_RUNNER = """
var main = {
  args: null,

  reply: function() {
    main.args = Array.prototype.slice.call(arguments);
  },

  run: function() {
    %s

    return main.args;
  }
};
"""


class DoWork(Command):
    def process(self, payload):
        log.debug("got work, payload: %s", payload)

        try:
            ctx = execjs.compile(WORK_RUNNER % payload)
            result = ctx.eval('main.run.call(main)')
        except execjs.RuntimeUnavailable, ex:
            self.emit('error', 'JavaScript runtime is not available, try installing node.js (http://nodejs.org)')
            return
        except Exception, ex:
            log.warn('Unable to run work - %s - %s', ex, traceback.format_exc())
            return

        log.debug('result: %s' % result)

        self.send("sp/work_done", result)
