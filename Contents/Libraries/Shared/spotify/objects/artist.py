from spotify.core.helpers import convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import math


class Artist(Descriptor):
    __protobuf__ = metadata_pb2.Artist
    __node__ = 'artist'

    gid = PropertyProxy
    uri = PropertyProxy('gid', func=lambda gid: Uri.from_gid('artist', gid))
    name = PropertyProxy

    popularity = PropertyProxy
    top_track = PropertyProxy

    albums = PropertyProxy('album_group', 'AlbumGroup')
    singles = PropertyProxy('single_group', 'AlbumGroup')
    compilations = PropertyProxy('compilation_group', 'AlbumGroup')
    appears_on = PropertyProxy('appears_on_group', 'AlbumGroup')

    genres = PropertyProxy('genre')
    external_ids = PropertyProxy('external_id', 'ExternalId')

    portraits = PropertyProxy('portrait', 'Image')
    biographies = PropertyProxy('biography')

    activity_periods = PropertyProxy('activity_period')
    restrictions = PropertyProxy('restriction')
    related = PropertyProxy('related')

    is_portrait_album_cover = PropertyProxy('is_portrait_album_cover')
    portrait_group = PropertyProxy('portrait_group')

    @classmethod
    def from_node_dict(cls, sp, data, types):
        uri = Uri.from_id('artist', data.get('id'))

        return cls(sp, {
            'gid': uri.to_gid(),
            'uri': uri,
            'name': data.get('name'),
            'portrait': cls.get_portraits(data),
            'popularity': float(data.get('popularity')) if data.get('popularity') else None,
            'restriction': data.get('restrictions')
        }, types)

    @classmethod
    def from_dict(cls, sp, data, types):
        uri = Uri.from_uri(data.get('uri'))

        internal = {
            'name': data.get('name'),
            'gid': uri.to_gid()
        }

        # Portrait
        image_uri = data.get('imageUri')

        if image_uri:
            internal['portrait'] = [
                {
                    'file_id': image_uri[image_uri.rfind('/') + 1:],
                    'size': 0
                }
            ]

        return cls(sp, internal, types)

    @classmethod
    def get_portraits(cls, data):
        portrait = data.get('portrait', None)
        if portrait is None:
            return

        width = convert(portrait.get('width'), float)
        height = convert(portrait.get('height'), float)

        if not width or not height:
            return

        return [
            {
                '$source': 'node',
                'file_id': portrait.get('id'),
                'size': 0,
                'width': width,
                'height': height
            },
            {
                '$source': 'node',
                'file_id': portrait.get('small'),
                'size': 1,
                'width': math.ceil(width * 0.32),
                'height': math.ceil(height * 0.32)
            },
            {
                '$source': 'node',
                'file_id': portrait.get('large'),
                'size': 2,
                'width': math.ceil(width * 3.2),
                'height': math.ceil(height * 3.2)
            }
        ]
