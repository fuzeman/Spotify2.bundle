from spotify.core.helpers import convert
from spotify.objects import Parser

from lxml import etree
import logging

log = logging.getLogger(__name__)


class SearchResponse(object):
    media_types = [
        'artists',
        'albums',
        'tracks',
        'playlists'
    ]

    def __init__(self):
        self.artists = []
        self.artists_total = None

        self.albums = []
        self.albums_total = None

        self.tracks = []
        self.tracks_total = None

        self.playlists = []
        self.playlists_total = None

    @classmethod
    def parse(cls, sp, data):
        xml = etree.fromstring(data['result'].encode('utf-8'))

        obj = cls()

        for m in cls.media_types:
            obj.media_update(sp, xml, m)

        return obj

    def media_update(self, sp, xml, key):
        node_total = xml.find('total-%s' % key)

        # Media doesn't exist?
        if node_total is None:
            return

        # total-<media>
        setattr(self, '%s_total' % key, convert(node_total.text, int))

        # <media>
        items = getattr(self, key)

        for node in xml.find(key):
            items.append(self.parse_node(sp, node))

    @classmethod
    def parse_node(cls, sp, node):
        return Parser.parse(sp, 'XML', node.tag, node)
