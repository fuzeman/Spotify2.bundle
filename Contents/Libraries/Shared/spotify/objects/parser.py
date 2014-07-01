from spotify.objects.album import Album
from spotify.objects.album_group import AlbumGroup
from spotify.objects.artist import Artist
from spotify.objects.audio_file import AudioFile
from spotify.objects.copyright import Copyright
from spotify.objects.disc import Disc
from spotify.objects.external_id import ExternalId
from spotify.objects.image import Image
from spotify.objects.image_group import ImageGroup
from spotify.objects.playlist import Playlist, PlaylistItem
from spotify.objects.restriction import Restriction
from spotify.objects.top_tracks import TopTracks
from spotify.objects.track import Track
from spotify.objects.user import User

import logging
import sys

log = logging.getLogger(__name__)


ALL = [
    'Album',
    'AlbumGroup',
    'Artist',
    'AudioFile',
    'Copyright',
    'Disc',
    'ExternalId',
    'Image',
    'ImageGroup',
    'Playlist',
    'PlaylistItem',
    'Restriction',
    'TopTracks',
    'Track',
    'User'
]

NAME_MAP = dict([
    (key, getattr(sys.modules[__name__], key))
    for key in ALL
])


def legacy_map(map, cls):
    tag = getattr(cls, '__node__', None)

    if not tag:
        return

    map[tag] = cls


def discover():
    result = {'XML': {}}

    for cls in NAME_MAP.values():
        class_parsers(cls, result)

    return result


def class_parsers(cls, result=None, flat=False):
    cls_name = cls.__name__

    if result is None:
        result = {'XML': {}}

    if getattr(cls, '__protobuf__', None):
        result['Protobuf'] = cls

    if not hasattr(cls, '__parsers__'):
        if flat:
            result['XML'] = cls
        else:
            legacy_map(result['XML'], cls)
    else:
        for parser in cls.__parsers__():
            name = parser.__name__

            if name not in result:
                result[name] = {}

            if flat:
                result[name] = parser
            else:
                tag = getattr(parser, '__tag__', cls_name)
                result[name][tag] = parser

    return result


class Parser(object):
    Protobuf = 'Protobuf'
    MercuryJSON = 'MercuryJSON'
    XML = 'XML'
    Tunigo = 'Tunigo'

    NAMES = NAME_MAP
    TYPES = discover()

    @classmethod
    def get(cls, source, tag):
        if source not in cls.TYPES:
            raise ValueError('Unknown data type "%s"' % source)

        types = cls.TYPES

        if tag in cls.NAMES:
            return cls.from_descriptor(source, cls.NAMES[tag])

        # Look for tag in type map
        if tag in types[source]:
            return types[source][tag]

        log.warn('Unknown tag "%s" for data type "%s"', tag, source)
        return None

    @classmethod
    def from_descriptor(cls, source, descriptor):
        types = class_parsers(descriptor, flat=True)

        if source not in types:
            log.warn('Unable to find "%s" parser for %s', source, descriptor)
            return None

        return types[source]

    @classmethod
    def parse(cls, sp, source, tag, data):
        descriptor = cls.get(source, tag)

        return cls.construct(sp, source, descriptor, data)

    @classmethod
    def construct(cls, sp, source, descriptor, data):
        if not descriptor:
            log.warn('Invalid descriptor provided')
            return None

        parser = cls.from_descriptor(source, descriptor)

        if hasattr(parser, 'parse'):
            return parser.parse(sp, data, cls)

        if source == cls.XML:
            if type(data) is dict:
                return parser.from_node_dict(sp, data, cls)

            return parser.from_node(sp, data, cls)

        if source == cls.Protobuf:
            return parser.from_protobuf(sp, data, cls)

        log.warn('Unknown old-style data type')
        return None
