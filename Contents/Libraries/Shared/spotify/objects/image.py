from spotify.core import RESOURCE_HOST
from spotify.core.helpers import convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

SIZES = {
    0: '300',
    1: '60',
    2: '640',
    3: '160'
}


class Image(Descriptor):
    __protobuf__ = metadata_pb2.Image

    file_uri = PropertyProxy('file_id', func=lambda file_id: Uri.from_gid('image', file_id))

    size = PropertyProxy()

    width = PropertyProxy
    height = PropertyProxy

    @property
    def file_url(self):
        if not self.file_uri or type(self.file_uri) is not Uri:
            return None

        return 'https://%s/%s/%s' % (
            RESOURCE_HOST,
            SIZES.get(self.size, self.width),
            self.file_uri.to_id(size=40)
        )

    @classmethod
    def from_node_dict(cls, sp, data, types):
        return cls(sp, {
            'file_id': Uri.from_id('image', data.get('file_id')).to_gid(size=40),

            'size': convert(data.get('size'), long),

            'width': convert(data.get('width'), long),
            'height': convert(data.get('height'), long)
        }, types)

    @classmethod
    def from_id(cls, id, size=3):
        return cls(None, {
            'file_id': Uri.from_id('image', id).to_gid(size=40),
            'size': 3
        })
