from spotify.core.helpers import etree_convert
from spotify.core.revent import REvent
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.objects.image import Image
from spotify.proto import playlist4changes_pb2
from spotify.proto import playlist4content_pb2

import logging

log = logging.getLogger(__name__)


def create_image(uri):
    uri = Uri.from_uri(uri)

    if uri is None:
        return None

    return Image.from_id(uri.code)


class PlaylistItem(Descriptor):
    __protobuf__ = playlist4content_pb2.Item

    uri = PropertyProxy(func=Uri.from_uri)
    name = PropertyProxy

    added_by = PropertyProxy('attributes.added_by')

    def fetch(self, start=0, count=100, callback=None):
        if callback:
            return self.sp.playlist(self.uri, start, count, callback)

        # Fetch full playlist detail
        event = REvent()
        self.sp.playlist(self.uri, start, count, callback=lambda pl: event.set(pl))

        # Wait until result is available
        return event.wait()


class Playlist(Descriptor):
    __protobuf__ = playlist4changes_pb2.ListDump

    uri = PropertyProxy(func=Uri.from_uri)
    name = PropertyProxy('attributes.name')
    image = PropertyProxy(func=create_image)

    length = PropertyProxy
    position = PropertyProxy('contents.pos')

    items = PropertyProxy('contents.items', 'PlaylistItem')
    truncated = PropertyProxy('contents.truncated')

    @staticmethod
    def __parsers__():
        return [XML, Tunigo]

    def list(self, group=None, flat=False):
        if group:
            # Pull the code from a group URI
            parts = group.split(':')
            group = parts[2] if len(parts) == 4 else group

        path = []

        for item in self.items:
            if item.uri.type == 'start-group':
                # Ignore groups if we are returning a flat list
                if flat:
                    continue

                # Only return placeholders on the root level
                if (not group and not path) or (path and path[-1] == group):
                    # Return group placeholder
                    yield PlaylistItem(self.sp).dict_update({
                        'uri': Uri.from_uri('spotify:group:%s:%s' % (item.uri.code, item.uri.title)),
                        'name': item.uri.title
                    })

                path.append(item.uri.code)
                continue
            elif item.uri.type == 'end-group':
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
        if self.uri.type == 'rootlist':
            return self.fetch_playlists(group, flat)

        if self.uri.type in ['playlist', 'starred']:
            return self.fetch_tracks()

        return None

    def fetch_playlists(self, group=None, flat=False):
        for item in self.list(group, flat):
            # Return plain PlaylistItem for groups
            if item.uri.type == 'group':
                yield item
                continue

            yield item.fetch()

    def fetch_tracks(self, batch_size=100):
        position = 0

        while position < self.length:
            if position >= len(self.items):
                # Can we extend the playlist?
                if not self.extend(position, batch_size):
                    break

            # Get URI for each item
            uris = [item.uri for item in self.items[position:position + batch_size]]

            # Request full track metadata
            event = REvent()
            self.sp.metadata(uris, callback=lambda items: event.set(items))

            tracks = event.wait(10)

            # Check if there was a request timeout
            if tracks is None:
                log.warn('Timeout while fetching track metadata')
                break

            # Yield each track
            for track in tracks:
                yield track

            position += len(uris)

    def extend(self, start, count=100):
        # Can only extend truncated playlists
        if not self.truncated:
            return False

        event = REvent()
        self.sp.playlist(self.uri, start, count, callback=lambda pl: event.set(pl))

        playlist = event.wait(5)

        # Check if there was a request timeout
        if playlist is None:
            return False

        # Extend our 'items' collection
        self.items.extend(playlist.items)

        return True


class XML(Playlist):
    __tag__ = 'playlist'

    @classmethod
    def parse(cls, sp, data, parser):
        if type(data) is not dict:
            data = etree_convert(data)

        return Playlist(sp, {
            'uri': Uri.from_uri(data.get('uri')),
            'attributes': {
                'name': data.get('name')
            },
            'image': data.get('image')
        }, parser.XML, parser)


class Tunigo(Playlist):
    __tag__ = 'playlist'

    @classmethod
    def parse(cls, sp, data, parser):
        image_uri = None

        if data.get('image'):
            image_uri = 'spotify:image:' + data.get('image')

        return Playlist(sp, {
            'uri': Uri.from_uri(data.get('uri')),
            'attributes': {
                'name': data.get('title')
            },
            'image': image_uri
        }, parser.Tunigo, parser)
