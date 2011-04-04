'''
Common utility functions
'''
from time import sleep
import os


class WritePipeWrapper(object):
    ''' Simple class that wraps a pipe and provides a file like interface '''

    def __init__(self, pipe):
        self.pipe = os.fdopen(pipe, 'w', 0)
        self.bytes_written = 0

    def close(self):
        self.pipe.close()

    def flush(self):
        self.pipe.flush()

    def tell(self):
        return self.bytes_written

    def write(self, bytes):
        self.bytes_written = self.bytes_written + len(bytes)
        self.pipe.write(bytes)


def wait_until_ready(objects, interval = 0.1):
    ''' Wait until Spotify model instances are ready to use '''
    instances = objects if not isinstance(objects, list) else list(objects)
    for instance in instances:
        while not instance.is_loaded():
            sleep(interval)
    return objects


def create_track_object(track, callback):
    ''' Factory for track directory objects '''
    artists = (a.name().decode("utf-8") for a in track.artists())
    return TrackObject(
        items = [
            MediaObject(
                parts = [PartObject(key = callback)],
            )
        ],
        key = "Track",
        title = track.name().decode("utf-8"),
        artist = ", ".join(artists),
        index = track.index(),
        duration = int(track.duration())
    )
