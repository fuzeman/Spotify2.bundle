'''
Utility classes / functions
'''
from time import time
from threading import Event
import aifc
import struct
import sys


class IOLoopProxy(object):
    ''' Class used to proxy requests to an IOLoop instance

    A convenience class that lets worker threads bounce requests to an
    IOLoop and wait for the responses synchronously.
    '''

    class FutureBase(object):
        ''' Base class for "Future" implementations '''
        def __init__(self, callback, args, kwargs):
            self.finished = Event()
            self.callback = callback
            self.args = args
            self.kwargs = kwargs
            self.exc_info = None
            self.result = None

        def finish(self, result):
            self.result = result
            self.finished.set()

        def handle_exception(self):
            self.exc_info = sys.exc_info()
            self.finished.set()

        def wait_until_done(self):
            Log("Waiting for callback to complete")
            self.finished.wait()
            Log("Callback completed")
            if self.exc_info:
                raise self.exc_info[1], None, self.exc_info[2]
            return self.result

    class AsyncFuture(FutureBase):
        ''' Invokes async calls on the IOLoop with a completion callback

        Callbacks invoked using an AsyncFuture instance should accept
        a parameter named 'completion' which should be invoked when the
        task completes to unblock the caller.
        '''
        def __call__(self):
            try:
                self.kwargs["completion"] = self.finish
                self.callback(*self.args, **self.kwargs)
            except Exception:
                self.handle_exception()

    class Future(FutureBase):
        ''' Invokes sync calls on the IOLoop and waits for the result '''
        def __call__(self):
            try:
                self.finish(self.callback(*self.args, **self.kwargs))
            except Exception:
                self.handle_exception()

    def __init__(self, ioloop):
        ''' Initializer

        :param ioloop:       The tornado ioloop to bounce calls to.
        '''
        self.ioloop = ioloop

    def invoke(self, callback, args = (), kwargs = {},
               timeout = None, async = False):
        ''' Invoke a callback on the IOLoop and wait for the result.

        :param callback:     The callable to invoke on the IOLoop.
        :param args:         A optional tuple of args to pass to the callback.
        :param kwargs:       A optional dict of kwargs to pass to the callback.
        :param timeout:      An optional timeout (in seconds) for the operation.
                             If a timeout is given and reached an exception will
                             be thrown.
        :param async:        Pass True if the callback is asyncronous.
                             An async callback should accept a "completion"
                             parameter which should be used to return the
                             result when the callback is done.
        '''
        if async:
            future = type(self).AsyncFuture(callback, args, kwargs)
        else:
            future = type(self).Future(callback, args, kwargs)
        self.ioloop.add_callback(future)
        return future.wait_until_done()


class RunLoopMixin(object):
    ''' Mixin class that adds ioloop convenience methods '''

    def wrap_callback(self, callback):
        ''' Return a wrapper function that catches and logs exceptions '''
        def wrapper():
            try:
                callback()
            except:
                Log("Exception in callback: %s" % callback)
                Log(Plugin.Traceback())
        return wrapper

    def invoke_async(self, callback):
        ''' Invoke a callback on the io thread.

        Safe to call from any thread '''
        self.ioloop.add_callback(self.wrap_callback(callback))

    def schedule_timer(self, delay, callback):
        ''' Schedule a callback after a given interval.

        Callback will be invoked on the io thread '''
        deadline = time() + delay
        callback = self.wrap_callback(callback)
        return self.ioloop.add_timeout(deadline, callback)

    def cancel_timer(self, timer):
        self.ioloop.remove_timeout(timer)


class Track(object):
    def __init__(self, track):
        self.track = track
        self.sample_rate = 44100.0
        self.frames_played = 0

    @property
    def total_frames(self):
        return int(self.track.duration() / 1000.0 * self.sample_rate)

    @property
    def is_finished(self):
        return self.frames_played >= self.total_frames

    def add_played_frames(self, frame_count):
        self.frames_played = self.frames_played + frame_count


class PCMToAIFFConverter(object):
    ''' Class to convert Spotify PCM audio data to an AIFF audio stream '''

    class Buffer(object):
        def __init__(self, callback):
            self.length = 0
            self.callback = callback

        def write(self, bytes):
            self.length = self.length + len(bytes)
            if not self.callback(bytes):
                raise EOFError()

        def tell(self):
            return self.length

        def seek(self, *args):
            pass

    def __init__(self, track, callback):
        self.track = Track(track)
        self.aiff_stream = self.create_aiff_wrapper(
            self.Buffer(callback), self.track)

    def create_aiff_wrapper(self, output_stream, track):
        aiff_file = aifc.open(output_stream, "wb")
        aiff_file.aifc()
        aiff_file.setsampwidth(2)
        aiff_file.setnchannels(2)
        aiff_file.setframerate(track.sample_rate)
        aiff_file.setnframes(track.total_frames)
        return aiff_file

    def convert(self, frames, frame_count):
        data = struct.pack('>' + str(len(frames)/2) + 'H',
            *struct.unpack('<' + str(len(frames)/2) + 'H', frames))
        self.track.add_played_frames(frame_count)
        if not self.track.is_finished:
            self.aiff_stream.writeframesraw(data)
        return frame_count


class NotReadyError(Exception):
    ''' Exception thrown when a libspotify object is not loaded '''
    pass


def are_loaded(instances):
    for instance in instances:
        if not instance.is_loaded():
            return False
    return True


def assert_loaded(objects):
    ''' Wait until libspotify objects are loaded and ready to use '''
    if not are_loaded([objects] if hasattr(objects, "is_loaded") else objects):
        raise NotReadyError()
    return objects


def localized_format(key, args):
    ''' Return the a localized string formatted with the given args '''
    return str(L(key)) % args
