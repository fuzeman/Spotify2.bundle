from threading import Event


class REvent(object):
    def __init__(self):
        self.result = None
        self.event = Event()

    def set(self, value):
        self.result = value

        return self.event.set()

    def wait(self, timeout=None):
        self.event.wait(timeout)

        return self.result
