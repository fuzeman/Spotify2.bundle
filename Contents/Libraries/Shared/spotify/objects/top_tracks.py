from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class TopTracks(Descriptor):
    __protobuf__ = metadata_pb2.TopTracks

    country = PropertyProxy
    tracks = PropertyProxy('track', 'Track')
