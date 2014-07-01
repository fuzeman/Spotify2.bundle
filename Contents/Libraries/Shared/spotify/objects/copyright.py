from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class Copyright(Descriptor):
    __protobuf__ = metadata_pb2.Copyright

    type = PropertyProxy
    text = PropertyProxy
