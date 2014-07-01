from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class Disc(Descriptor):
    __protobuf__ = metadata_pb2.Disc

    number = PropertyProxy
    name = PropertyProxy
    tracks = PropertyProxy('track', 'Track')
