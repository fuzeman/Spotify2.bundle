from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)


class AlbumGroup(Descriptor):
    __protobuf__ = metadata_pb2.AlbumGroup
    # TODO __node__ ?

    albums = PropertyProxy('album', 'Album')

    def find_available(self):
        if not self.albums:
            log.debug('No albums exist in the group')
            return None

        album = None

        # Try find an album that is available
        for album in self.albums:
            if album.is_available():
                break

        if album is None:
            log.debug('Unable to find available album in group')
            # Return first item as a placeholder
            return self.albums[0]

        log.debug('Found available album "%s"', album.uri)
        return album

    @classmethod
    def from_protobuf(cls, sp, data, parser):
        obj = super(AlbumGroup, cls).from_protobuf(sp, data, parser)

        # Return first available album (instead of the actual group)
        return obj.find_available()
