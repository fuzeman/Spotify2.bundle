from tornado.ioloop import IOLoop
from types import MethodType
from time import time
import threading
import new
import sys


class RunLoop(threading.Thread):
    ''' Thread subclass that manages an internal runloop to process requests '''

    class CallbackWrapper(object):
        ''' Class used to invoke callbacks on the IO loop synchronously '''
        def __init__(self, callback):
            super(RunLoop.CallbackWrapper, self).__init__()
            self.finished = threading.Event()
            self.callback = callback
            self.exc_info = None
            self.result = None

        def __call__(self, *args, **kwargs):
            try:
                self.result = self.callback(*args, **kwargs)
            except Exception, e:
                self.exc_info = sys.exc_info()
            self.finished.set()

        def wait_until_done(self):
            self.finished.wait()
            if self.exc_info:
                raise self.exc_info[1], None, self.exc_info[2]
            return self.result

    class Proxy(object):
        ''' Class used to trampoline callbacks onto the IO loop '''

        def __init__(self, runloop, target):
            super(RunLoop.Proxy, self).__init__()
            self.runloop = runloop
            self.target = target

        def invoke(self, method, *args, **kwargs):
            if threading.currentThread() == self.runloop:
                return method(*args, **kwargs)
            return self.runloop.invoke(lambda: method(*args, **kwargs))

        def __getattr__(self, aname):
            target = self.target
            result = getattr(target, aname)
            if isinstance(result, MethodType):
                return lambda *a, **k: self.invoke(result, *a, **k)
            return result

    def __init__(self, name = None):
        super(RunLoop, self).__init__(name = name)
        self.ioloop = IOLoop()

    def run(self):
        self.ioloop.start()

    def stop(self):
        self.ioloop.stop()
        self.join()

    def invoke(self, callback):
        wrapper = self.CallbackWrapper(callback)
        self.ioloop.add_callback(wrapper)
        return wrapper.wait_until_done()

    def invoke_async(self, callback):
        self.ioloop.add_callback(callback)

    def schedule_callback(self, delay, callback):
        deadline = time() + delay
        return self.ioloop.add_timeout(deadline, callback)

    def cancel_timer(self, timer):
        self.ioloop.remove_timeout(timer)

    def get_proxy(self, target, proxy_class = None):
        if not proxy_class:
            proxy_class = self.Proxy
        return proxy_class(self, target)
