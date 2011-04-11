'''
Common utility functions
'''
from constants import SEND_QUEUE_SIZE
from cStringIO import StringIO
from fcntl import fcntl, F_SETFL
from os import pipe, fdopen, O_NONBLOCK
from time import sleep
from Queue import Queue
import aifc
import struct
import os


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

    def __init__(self, output_stream, track):
        self.aiff_stream = self.create_aiff_wrapper(output_stream, track)

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

    def convert(self, frames):
        data = struct.pack('>' + str(len(frames)/2) + 'H',
            *struct.unpack('<' + str(len(frames)/2) + 'H', frames))
        self.aiff_stream.writeframesraw(data)


class AudioStream(object):
    ''' Convert and stream PCM audio data to a client via a queue '''

    def __init__(self, track):
        self.buffer = FIFO()
        self.track = Track(track)
        self.converter = PCMToAIFFConverter(self.buffer.input, self.track)
        self.output_queue = Queue(SEND_QUEUE_SIZE)

    @property
    def output(self):
        return self.output_queue

    @property
    def is_finished(self):
        return self.track.is_finished

    def close(self):
        ''' Close the stream '''
        Log("Close stream")
        self.output_queue.put('')

    def process_frames(self, frames, frame_count):
        ''' Process PCM returning the number of frames consumed '''
        if self.output_queue.full():
            return 0
        self.converter.convert(frames)
        self.output_queue.put(self.buffer.read())
        self.track.add_played_frames(frame_count)
        return frame_count



def wait_until_ready(objects, interval = 0.1):
    ''' Wait until Spotify model instances are ready to use '''
    instances = [objects] if hasattr(objects, "is_loaded") else objects
    for instance in instances:
        while not instance.is_loaded():
            sleep(interval)
    return objects
