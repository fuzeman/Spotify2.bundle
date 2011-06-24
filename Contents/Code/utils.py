'''
Common utility functions
'''
from settings import SEND_QUEUE_SIZE
from os import pipe, fdopen
from time import sleep
from Queue import Queue
from time import time
from threading import Event
import aifc
import struct
import os


class IOLoopProxy(object):
    ''' Class used to proxy requests to an IOLoop instance

    A convenience class that lets worker threads bounce requests to an
    IOLoop and wait for the responses synchronously.
    '''

    class Future(object):
        ''' Invokes callbacks on the IOLoop and waits for the result '''
        def __init__(self, callback):
            super(IOLoopProxy.Future, self).__init__()
            self.finished = Event()
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

    class Timeout(Exception):
        ''' Exception thrown when a callback times out '''
        pass

    def __init__(self, ioloop):
        self.ioloop = ioloop

    def invoke(self, callback, timeout = None):
        ''' Invoke a callback on the IOLoop and wait for the result.

        :param callback:     The callable to invoke on the IOLoop.
        :param timeout:      An optional timeout (in seconds) for the operation.
                             If a timeout is given and reached an exception will
                             be thrown.
        '''
        future = type(self).Future(callback)
        self.ioloop.add_callback(future)
        return future.wait_until_done()


class RunLoopMixin(object):
    ''' Mixin class that adds ioloop convenience methods '''

    def invoke_async(self, callback):
        self.ioloop.add_callback(callback)

    def schedule_timer(self, delay, callback):
        deadline = time() + delay
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


class FIFO(object):
    ''' A FIFO with file-like input and output.'''

    class PipeWrapper(object):
        def __init__(self, pipe, mode):
            super(FIFO.PipeWrapper, self).__init__()
            self.pipe = fdopen(pipe, mode, 0)
            self.position = 0

        def close(self):
            self.pipe.close()

        def tell(self):
            return self.position

    class Input(PipeWrapper):
        def __init__(self, pipe):
            super(FIFO.Input, self).__init__(pipe, "w")

        def flush(self):
            self.pipe.flush()

        def write(self, bytes):
            self.position = self.position + len(bytes)
            self.pipe.write(bytes)

    class Output(PipeWrapper):
        def __init__(self, pipe):
            super(FIFO.Output, self).__init__(pipe, "r")

        def read(self, no_bytes):
            bytes = self.pipe.read(no_bytes)
            self.position = self.position + len(bytes)
            return bytes

    def __init__(self):
        read, write = pipe()
        self.output = self.Output(read)
        self.input = self.Input(write)

    def close(self):
        self.input.flush()
        self.input.close()

    @property
    def bytes_written(self):
        return self.input.position

    @property
    def bytes_read(self):
        return self.output.position

    @property
    def bytes_pending(self):
        return self.bytes_written - self.bytes_read

    def read(self):
        return self.output.read(self.bytes_pending)


class PCMToAIFFConverter(object):
    ''' Class to convert Spotify PCM audio data to an AIFF audio stream '''

    def __init__(self, track):
        self.track = Track(track)
        self.buffer = FIFO()
        self.aiff_stream = self.create_aiff_wrapper(
            self.buffer.input, self.track)

    def close(self):
        self.aiff_stream.close()

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
        return self.aiff_stream.writeframesraw(data)

    def get_pending_data(self):
        return self.buffer.output.read(self.buffer.bytes_pending)


class NotReadyError(Exception):
    ''' Exception thrown when a libspotify object is not loaded '''
    pass


def assert_loaded(objects):
    ''' Wait until libspotify objects are loaded and ready to use '''
    instances = [objects] if hasattr(objects, "is_loaded") else objects
    for instance in instances:
        if not instance.is_loaded():
            raise NotReadyError()
    return objects
