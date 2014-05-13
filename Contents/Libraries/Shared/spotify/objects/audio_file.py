from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class AudioFile(Descriptor):
    __protobuf__ = metadata_pb2.AudioFile

    file_id = PropertyProxy
    format = PropertyProxy
