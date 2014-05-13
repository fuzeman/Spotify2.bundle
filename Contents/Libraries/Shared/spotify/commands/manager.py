from spotify.commands import DoWork, PingFlash2


class CommandManager(object):
    def __init__(self, sp):
        self.handlers = {
            'do_work': DoWork(sp),
            'ping_flash2': PingFlash2(sp)
        }

    def process(self, name, *args):
        if name in self.handlers:
            self.handlers[name].process(*args)
            return True

        return False
