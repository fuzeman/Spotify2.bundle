from spotify.core.revent import REvent
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import playlist4changes_pb2
from spotify.proto import playlist4content_pb2


class PlaylistItem(Descriptor):
    __protobuf__ = playlist4content_pb2.Item

    uri = PropertyProxy
    name = PropertyProxy

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

    def list(self, group=None, flat=False):
        if group:
            # Pull the code from a group URI
            parts = group.split(':')
            group = parts[2] if len(parts) == 4 else group

        path = []

        for item in self.items:
            if item.uri.startswith('spotify:start-group'):
                # Ignore groups if we are returning a flat list
                if flat:
                    continue

                # Group start tag
                parts = item.uri.split(':')

                if len(parts) != 4:
                    continue

                code, title = parts[2:4]

                # Only return placeholders on the root level
                if (not group and not path) or (path and path[-1] == group):
                    # Group placeholder
                    yield PlaylistItem(self.sp).dict_update({
                        'uri': 'spotify:group:%s:%s' % (code, title),
                        'name': title
                    })

                path.append(code)
                continue
            elif item.uri.startswith('spotify:end-group'):
                # Group close tag
                if path and path.pop() == group:
                    return

                continue

            if group is None:
                # Ignore if we are inside a group
                if path and not flat:
                    continue
            else:
                # Ignore if we aren't inside the specified group
                if not path or path[-1] != group:
                    continue

            # Return item
            yield item

    def fetch(self, group=None, flat=False):
        for item in self.list(group, flat):
            # Return plain PlaylistItem for groups
            if item.uri.startswith('spotify:group'):
                yield item
                continue

            # Fetch playlist metadata (to find the name)
            event = REvent()
            self.sp.playlist(item.uri, count=0, callback=lambda pl: event.set(pl))

            # Wait until result is available (to keep playlist order)
            yield event.wait()

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
