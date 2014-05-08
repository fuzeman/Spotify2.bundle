from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import playlist4changes_pb2
from spotify.proto import playlist4content_pb2


class PlaylistItem(Descriptor):
    __protobuf__ = playlist4content_pb2.Item

    uri = PropertyProxy

    added_by = PropertyProxy('attributes.added_by')


class Playlist(Descriptor):
    __protobuf__ = playlist4changes_pb2.ListDump
    __node__ = 'playlist'

    uri = PropertyProxy
    name = PropertyProxy('attributes.name')
    image = PropertyProxy

    length = PropertyProxy
    position = PropertyProxy('contents.pos')

    items = PropertyProxy('contents.items', 'PlaylistItem')
    truncated = PropertyProxy('contents.truncated')

    @classmethod
    def from_dict(cls, sp, data, types):
        uri = Uri.from_uri(data.get('uri'))

        return cls(sp, {
            'uri': uri,
            'attributes': {
                'name': data.get('name')
            },
            'image': data.get('image')
        }, types)
