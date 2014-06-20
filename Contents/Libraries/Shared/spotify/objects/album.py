from spotify.core.helpers import convert, etree_convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)


class Album(Descriptor):
    __protobuf__ = metadata_pb2.Album

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

    @staticmethod
    def __parsers__():
        return [MercuryJSON, XML, Tunigo]

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


class MercuryJSON(Album):
    @classmethod
    def parse(cls, sp, data, parser):
        return Album(sp, {
            'name': data.get('name'),
            'gid': Uri.from_uri(data.get('uri')).to_gid(),
            'artist': [
                {
                    'uri': data.get('artistUri'),
                    'name': data.get('artistName')
                }
            ],
            'cover': [
                {
                    'imageUri': data.get('imageUri'),
                }
            ]
        }, parser.MercuryJSON, parser)


class XML(Album):
    __tag__ = 'album'

    @classmethod
    def parse(cls, sp, data, parser):
        if type(data) is not dict:
            data = etree_convert(data)

        return Album(sp, {
            'gid': Uri.from_id('album', data.get('id')).to_gid(),
            'name': data.get('name'),
            'artist': [
                {
                    '$source': 'node',
                    'id': data.get('artist-id'),
                    'name': data.get('artist-name')
                }
            ],
            'type': cls.get_type(data.get('album-type')),
            'cover': cls.get_covers(data),
            'popularity': convert(data.get('popularity'), float),
            'restriction': data.get('restrictions'),
            'external_id': data.get('external-ids')
        }, parser.XML, parser)

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
                '$source': 'node',
                'file_id': data.get('cover'),
                'size': 0
            },
            {
                '$source': 'node',
                'file_id': data.get('cover-small'),
                'size': 1
            },
            {
                '$source': 'node',
                'file_id': data.get('cover-large'),
                'size': 2
            }
        ]


class Tunigo(Album):
    __tag__ = 'release'

    @classmethod
    def parse(cls, sp, data, parser):
        return Album(sp, {
            'gid': Uri.from_uri(data.get('uri')).to_gid(),
            'name': data.get('albumName'),
            'artist': [
                {
                    'artistName': data.get('artistName')
                }
            ],
            'cover': [
                {
                    'image': data.get('image')
                }
            ],
        }, parser.Tunigo, parser)
