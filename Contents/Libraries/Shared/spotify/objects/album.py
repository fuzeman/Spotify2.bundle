from spotify.core.helpers import convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)


class Album(Descriptor):
    __protobuf__ = metadata_pb2.Album
    __node__ = 'album'

    gid = PropertyProxy
    uri = PropertyProxy('gid', func=lambda gid: Uri.from_gid('album', gid))
    name = PropertyProxy

    artists = PropertyProxy('artist', 'Artist')
    type = PropertyProxy

    label = PropertyProxy
    date = PropertyProxy(func=PropertyProxy.parse_date)
    popularity = PropertyProxy

    genres = PropertyProxy('genre')
    covers = PropertyProxy('cover', 'Image')
    external_ids = PropertyProxy('external_id', 'ExternalId')

    discs = PropertyProxy('disc', 'Disc')
    # review - []
    copyrights = PropertyProxy('copyright', 'Copyright')
    restrictions = PropertyProxy('restriction', 'Restriction')
    # related - []
    # sale_period - []
    cover_group = PropertyProxy('cover_group', 'ImageGroup')

    def is_available(self):
        message = ''

        for restriction in self.restrictions:
            success, message = restriction.check()

            if success:
                return True

        log.debug('Album "%s" not available (%s)', self.uri, message)
        return False

    @property
    def tracks(self):
        # Iterate through each disc and return a flat track list
        for disc in self.discs:

            for track in disc.tracks:
                yield track

    @classmethod
    def from_dict(cls, sp, data, types):
        uri = Uri.from_id('album', data.get('id'))

        return cls(sp, {
            'gid': uri.to_gid(),
            'name': data.get('name'),
            'artist': [
                {
                    'id': data.get('artist-id'),
                    'name': data.get('artist-name')
                }
            ],
            'type': cls.get_type(data.get('album-type')),
            'cover': cls.get_covers(data),
            'popularity': convert(data.get('popularity'), float),
            'restriction': data.get('restrictions'),
            'external_id': data.get('external-ids')
        }, types)

    @classmethod
    def get_type(cls, value):
        if value == 'album':
            return 1L

        if value == 'single':
            return 2L

        if value == 'compilation':
            return 3L

        return None

    @classmethod
    def get_covers(cls, data):
        if 'cover' not in data:
            return []

        return [
            {
                'file_id': data.get('cover'),
                'size': 0
            },
            {
                'file_id': data.get('cover-small'),
                'size': 1
            },
            {
                'file_id': data.get('cover-large'),
                'size': 2
            }
        ]
