from spotify.commands.base import Command

import execjs
import logging

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

        ctx = execjs.compile(WORK_RUNNER % payload)
        result = ctx.eval('main.run.call(main)')

        log.debug('result: %s' % result)

        self.send("sp/work_done", result)
