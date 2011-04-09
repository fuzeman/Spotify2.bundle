'''
Common utility functions
'''
from cStringIO import StringIO
from fcntl import fcntl, F_SETFL
from os import pipe, fdopen, O_NONBLOCK
from time import sleep
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


class FIFOBuffer(object):
    ''' Provides a FIFO buffer with file-like input and output.'''

    class PipeWrapper(object):
        def __init__(self, pipe, mode):
            super(FIFOBuffer.PipeWrapper, self).__init__()
            self.pipe = fdopen(pipe, mode, 0)
            self.position = 0

        def close(self):
            self.pipe.close()

        def tell(self):
            return self.position

    class Input(PipeWrapper):
        def __init__(self, pipe):
            super(FIFOBuffer.Input, self).__init__(pipe, "w")

        def flush(self):
            self.pipe.flush()

        def write(self, bytes):
            self.position = self.position + len(bytes)
            self.pipe.write(bytes)

    class Output(PipeWrapper):
        def __init__(self, pipe):
            super(FIFOBuffer.Output, self).__init__(pipe, "r")

        def read(self, no_bytes):
            bytes = self.pipe.read(no_bytes)
            self.position = self.position + len(bytes)
            return bytes

    def __init__(self):
        read, write = pipe()
        self.output = self.Output(read)
        self.input = self.Input(write)

    def close(self):
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

    @property
    def data(self):
        return self.output.read(self.bytes_pending)


class AudioStream(object):
    ''' Class to convert Spotify PCM audio data to an AIFF audio stream '''

    def __init__(self, track):
        self.buffer = FIFOBuffer()
        self.aiff_stream = self.create_aiff_wrapper(self.buffer.input, track)
        read, write = pipe()
        self.consumer_stream = fdopen(read,'r', 0)
        self.output_stream = fdopen(write, 'w', 0)
        #fcntl(self.output_stream, F_SETFL, O_NONBLOCK)

    @property
    def output(self):
        return self.consumer_stream

    def close(self):
        self.aiff_stream.close()
        self.output_stream.write(self.pending_bytes)
        self.output_stream.flush()
        self.output_stream.close()

    def create_aiff_wrapper(self, output_stream, track):
        aiff_file = aifc.open(output_stream, "wb")
        aiff_file.aifc()
        aiff_file.setsampwidth(2)
        aiff_file.setnchannels(2)
        aiff_file.setframerate(track.sample_rate)
        aiff_file.setnframes(track.total_frames)
        return aiff_file

    def write(self, frames):
        data = struct.pack('>' + str(len(frames)/2) + 'H',
            *struct.unpack('<' + str(len(frames)/2) + 'H', frames))
        self.aiff_stream.writeframesraw(data)
        self.output_stream.write(self.buffer.data)
        return True



def wait_until_ready(objects, interval = 0.1):
    ''' Wait until Spotify model instances are ready to use '''
    instances = [objects] if hasattr(objects, "is_loaded") else objects
    for instance in instances:
        while not instance.is_loaded():
            sleep(interval)
    return objects


def create_track_object(track, callback, thumbnail_url):
    ''' Factory for track directory objects '''
    artists = (a.name().decode("utf-8") for a in track.artists())
    return TrackObject(
        items = [
            MediaObject(
                parts = [PartObject(key = callback)],
            )
        ],
        key = track.name().decode("utf-8"),
        title = track.name().decode("utf-8"),
        artist = ", ".join(artists),
        index = track.index(),
        duration = int(track.duration()),
        thumb = thumbnail_url
    )
