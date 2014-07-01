from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class ImageGroup(Descriptor):
    __protobuf__ = metadata_pb2.ImageGroup

    images = PropertyProxy('image', 'Image')
