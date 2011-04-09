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


class AudioStream(object):
    def __init__(self, track):
        self.position = 0
        self.buffer = StringIO()
        self.aiff_stream = self.create_aiff_wrapper(
            self.buffer,
            track)
        read, write = pipe()
        self.consumer_stream = fdopen(read,'r',0)
        self.output_stream = fdopen(write, 'w', 0)
        #fcntl(self.output_stream, F_SETFL, O_NONBLOCK)

    @property
    def output(self):
        return self.consumer_stream

    @property
    def pending_bytes(self):
        return self.buffer.getvalue()[self.position:]

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
        chunk = self.pending_bytes
        self.output_stream.write(chunk)
        self.position = self.position + len(chunk)
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
