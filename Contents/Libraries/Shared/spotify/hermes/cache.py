from spotify.core.helpers import convert
from spotify.core.uri import Uri

from threading import Lock
import logging
import time

log = logging.getLogger(__name__)


class HermesCache(object):
    schema_types = {
        'vnd.spotify/metadata-artist':  ('metadata', 'artist'),
        'vnd.spotify/metadata-album':   ('metadata', 'album'),
        'vnd.spotify/metadata-track':   ('metadata', 'track')
    }

    content_types = [
        'hm://%s/%s' % (group, type)
        for (group, type) in schema_types.values()
    ]

    def __init__(self):
        self._store = {}
        self._store_lock = Lock()

    def get_schema_key(self, content_type):
        key = self.schema_types.get(content_type)

        if key is None:
            log.debug('ignoring item with content_type: "%s"', content_type)
            return None, None

        return key

    def get_object_key(self, content_type, internal):
        group, type = self.get_schema_key(content_type)

        if group is None or type is None:
            return None, None

        uri = Uri.from_gid(type, internal.gid)

        return 'hm://%s/%s' % (group, uri.type), uri.to_id()

    def get_object_uri(self, content_type, internal):
        k_content, k_item = self.get_object_key(content_type, internal)

        if not k_content or not k_item:
            return None

        return '/'.join([k_content, k_item])

    def get_uri_key(self, hm):
        x = hm.rindex('/')

        k_content = hm[:x]

        if k_content not in self.content_types:
            return None, None

        k_item = hm[x + 1:]

        return k_content, k_item

    def store(self, header, content_type, internal):
        if type(internal) is dict:
            return None

        k_content, k_item = self.get_object_key(content_type, internal)

        if not k_content or not k_item:
            return None

        with self._store_lock:
            if self._store.get(k_content) is None:
                self._store[k_content] = {}

            item = HermesCacheObject.create(header, content_type, internal)

            self._store[k_content][k_item] = item

        return item

    def get(self, uri):
        k_content, k_item = self.get_uri_key(uri)

        if not k_content or not k_item:
            return None

        with self._store_lock:
            if self._store.get(k_content) is None:
                return None

            item = self._store[k_content].get(k_item)

            if item is None:
                return None

            log.debug('retrieved "%s" from cache (timestamp: %s, valid: %s)', uri,
                      item.timestamp, item.is_valid())

            if not item.is_valid():
                del self._store[k_content][k_item]
                return None

        return item


class HermesCacheObject(object):
    def __init__(self, ttl, version, policy, content_type, internal):
        self.ttl = ttl
        self.version = version
        self.policy = policy

        self.content_type = content_type
        self.internal = internal
        self.gid = internal.gid

        self.timestamp = time.time()

    def is_valid(self):
        elapsed = (time.time() - self.timestamp) * 1000

        return elapsed < self.ttl

    @classmethod
    def create(cls, header, content_type, internal):
        params = dict([(field.name, field.value) for field in header.user_fields])

        return cls(
            convert(params.get('MC-TTL'), int),
            convert(params.get('MD-Version'), int),
            params.get('MC-Cache-Policy'),

            content_type,
            internal
        )
