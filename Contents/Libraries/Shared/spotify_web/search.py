from lxml import etree
from spotify_web.spotify import IMAGE_HOST, SpotifyUtil


class SpotifySearch():
    def __init__(self, spotify, query, query_type, max_results, offset):
        self.spotify = spotify
        self.query = query
        self.query_type = query_type
        self.max_results = max_results
        self.offset = offset
        self.populate()

    def populate(self):
        xml = self.spotify.api.search_request(self.query, query_type=self.query_type, max_results=self.max_results, offset=self.offset)
        xml = xml[38:]  # trim UTF8 declaration
        self.result = etree.fromstring(xml)

        # invalidate cache
        self._Cache__cache = {}

    def next(self):
        self.offset += self.max_results
        self.populate()

    def prev(self):
        self.offset = self.offset - self.max_results if self.offset >= self.max_results else 0
        self.populate()

    def getName(self):
        return "Search "+self.query_type+": "+self.query

    # Tracks
    def getTracks(self):
        return self.getObjects('track')

    def getTracksTotal(self):
        return self.getTotal('track')

    def getNumTracks(self):
        return len(self.getTracks())

    # Albums
    def getAlbums(self):
        return self.getObjects('album')

    def getAlbumsTotal(self):
        return self.getTotal('album')

    # artists
    def getArtists(self):
        return self.getObjects('artist')

    def getArtistsTotal(self):
        return self.getTotal('artist')

    # Playlists
    def getPlaylists(self):
        return self.getObjects('playlist')

    def getPlaylistsTotal(self):
        return self.getTotal('playlist')

    def getObjByID(self, result, obj_type):
        elems = result.find(obj_type+"s")
        if elems is None:
            elems = []

        ids = [elem[0].text for elem in list(elems)]
        objs = self.spotify.objectFromID(obj_type, ids)

        return objs

    def getObjByURI(self, result, obj_type):
        elems = result.find(obj_type+"s")
        if elems is None:
            elems = []

        uris = [elem[0].text for elem in list(elems)]
        objs = self.spotify.objectFromURI(uris, asArray=True)

        return objs

    def parse(self, obj_type, item):
        if obj_type == 'artist':
            return Artist.parse(item)

        if obj_type == 'album':
            return Album.parse(item)

        if obj_type == 'track':
            return Track.parse(item)

        if obj_type == 'playlist':
            return Playlist.parse(item)

        raise NotImplementedError('Unknown obj_type specified')

    def getObjects(self, obj_type):
        container = self.result.find(obj_type + 's')
        if container is None:
            return

        for item in container:
            yield self.parse(obj_type, item)

    def getTotal(self, obj_type):
        nodes = self.result.find('total-%ss' % obj_type)
        if nodes is None:
            return None

        try:
            return int(nodes.text)
        except:
            return None


class Item(object):
    @staticmethod
    def get_value(root_node, key):
        node = root_node.find(key)
        if node is None:
            print 'unable to find node for "%s"' % key
            return None

        return node.text

    @staticmethod
    def image_url(id, size=160):
        return 'https://%s/%s/%s' % (IMAGE_HOST, size, id)

    def update(self, node=None):
        pass

    def update_dict(self, data):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.update()
        return self

    def update_node(self, node, keys):
        for key in keys:
            if isinstance(key, basestring):
                key = (key, key)

            node_key, obj_key = key
            value = self.get_value(node, node_key)

            if hasattr(self, obj_key):
                setattr(self, obj_key, value)

        self.update(node)
        return self


class Artist(Item):
    def __init__(self):
        self.id = None
        self.uri = None
        self.name = None

        self.portrait = None
        self.popularity = None

    def update(self, node=None):
        self.uri = SpotifyUtil.id2uri('artist', self.id)

    @classmethod
    def parse(cls, node):
        if node is None:
            return None

        o = cls()
        o.portrait = Portrait.parse(node.find('portrait'))

        o.update_node(node, [
            'id',
            'name',
            'popularity',
        ])

        return o


class Album(Item):
    def __init__(self):
        self.id = None
        self.uri = None
        self.name = None
        self.type = None

        self.artist = None

        self.cover = None
        self.cover_small = None
        self.cover_large = None

        self.popularity = None

    def update_covers(self, node):
        self.cover = self.image_url(self.get_value(node, 'cover'))
        self.cover_small = self.image_url(self.get_value(node, 'cover-small'), 60)
        self.cover_large = self.image_url(self.get_value(node, 'cover-large'), 300)

    def update(self, node=None):
        self.uri = SpotifyUtil.id2uri('album', self.id)

        if node:
            self.update_covers(node)

    @classmethod
    def parse(cls, node):
        if node is None:
            return None

        o = cls().update_node(node, [
            'id',
            'name',
            ('album-type', 'type'),

            'popularity'
        ])

        o.artist = Artist().update_node(node, [
            ('artist-id', 'id'),
            ('artist-name', 'name')
        ])

        return o


class Track(Item):
    def __init__(self):
        self.id = None
        self.uri = None
        self.title = None

        self.artist = None
        self.album = None

        self.year = None
        self.number = None
        self.length = None

        self.popularity = None

    def update(self, node=None):
        self.uri = SpotifyUtil.id2uri('track', self.id)

    @classmethod
    def parse(cls, node):
        if node is None:
            return None

        o = cls().update_node(node, [
            'id',
            'title',

            'year',
            ('track-number', 'number'),
            'length',

            'popularity',
        ])

        # Artist
        o.artist = Artist().update_node(node, [])

        # Album
        o.album = Album().update_node(node, [
            ('album', 'name'),
            ('album-id', 'id'),
        ])

        # Album Artist
        o.album.artist = Artist().update_node(node, [
            ('album-artist', 'name'),
            ('album-artist-id', 'id')
        ])

        return o


class Playlist(Item):
    def __init__(self):
        self.uri = None
        self.name = None

        self.image = None

    @classmethod
    def parse(cls, node):
        if node is None:
            return None

        o = cls().update_node(node, [
            'uri',
            'name',
        ])

        image_uri = cls.get_value(node, 'image')

        if image_uri:
            parts = image_uri.split(':')

            if len(parts) == 3 and parts[1] == 'image':
                o.image = cls.image_url(parts[2])

        return o


class Portrait(Item):
    def __init__(self):
        self.id = None
        self.url = None

        self.width = None
        self.height = None

        self.small = None
        self.large = None

    @classmethod
    def parse(cls, node):
        if node is None:
            return None

        o = cls().update_node(node, [
            'id',

            'width',
            'height',
        ])

        o.url = cls.image_url(o.id)

        o.small = cls.image_url(cls.get_value(node, 'small'), 60)
        o.large = cls.image_url(cls.get_value(node, 'large'), 300)

        return o
