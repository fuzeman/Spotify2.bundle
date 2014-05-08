from spotify.objects import NODE_MAP, NAME_MAP

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
        # total-<media>
        setattr(self, '%s_total' % key, xml.find('total-%s' % key).text)

        # <media>
        items = getattr(self, key)

        for node in xml.find(key):
            items.append(self.parse_node(sp, node))

    @classmethod
    def parse_node(cls, sp, node):
        parser_cls = NODE_MAP.get(node.tag)

        if parser_cls is None:
            log.warn('Unable to parse node with tag "%s"', node.tag)
            return None

        return parser_cls.from_node(sp, node, NAME_MAP)
