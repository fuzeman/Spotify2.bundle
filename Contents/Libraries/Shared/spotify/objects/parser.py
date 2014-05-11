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
from spotify.objects.track import Track
from spotify.objects.user import User

import sys


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
    'Track',
    'User'
]

NAME_MAP = dict([
    (key, getattr(sys.modules[__name__], key))
    for key in ALL
])

NODE_MAP = dict([
    (getattr(cls, '__node__'), cls)
    for cls in NAME_MAP.values()
    if getattr(cls, '__node__', None)
])
