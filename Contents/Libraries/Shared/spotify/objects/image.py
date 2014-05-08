from spotify.core.helpers import convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class Image(Descriptor):
    __protobuf__ = metadata_pb2.Image

    file_id = PropertyProxy
    size = PropertyProxy

    width = PropertyProxy
    height = PropertyProxy

    @classmethod
    def from_dict(cls, sp, data, types):
        uri = Uri.from_id('image', data.get('file_id'))

        return cls(sp, {
            'file_id': uri.to_gid(),
            'size': convert(data.get('size'), long),

            'width': convert(data.get('width'), long),
            'height': convert(data.get('height'), long)
        }, types)
