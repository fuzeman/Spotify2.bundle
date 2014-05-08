from spotify.components.base import Component
from spotify.core.helpers import etree_convert

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from lxml import etree
import datetime
import logging

log = logging.getLogger(__name__)


class PropertyProxy(object):
    def __init__(self, name=None, type_=None, func=None):
        self.name = name
        self.type = type_
        self.func = func

    def get_value(self, instance, key):
        if type(instance) is dict:
            return instance.get(key)

        if not isinstance(instance, Descriptor):
            return getattr(instance, key, None)

        return None

    def get_attribute(self, instance, path):
        if type(path) is str:
            path = path.split('.')

        key = path.pop(0)

        value = self.get_value(instance, key)
        if value is None:
            return None

        if not len(path):
            return value

        return self.get_attribute(value, path)

    def get(self, key, obj, type_map):
        if key in obj._cache:
            return obj._cache[key]

        # Pull value from instance or protobuf
        original = (
            self.get_attribute(obj, self.name) or
            self.get_attribute(obj._internal, self.name)
        )

        # Transform attribute values
        value = self.parse(obj, original, type_map)

        # Cache for later use
        obj._cache[key] = value

        return value

    def get_type(self, types):
        if self.type in types:
            return types[self.type]

        if self.name in types:
            return types[self.name]

        log.warn('Unable to find type for "%s" or "%s"', self.type, self.name)
        return None

    def parse(self, obj, value, types):
        # Retrieve 'type' from type_map
        if type(self.type) is str:
            if not types:
                return value

            self.type = self.get_type(types)

        # Use 'func' if specified
        if self.func:
            return self.func(value)

        if not self.type:
            return value

        # Convert to 'type'
        if isinstance(value, (list, RepeatedCompositeFieldContainer)):
            return [self.construct(obj.sp, x, types) for x in value]

        return self.construct(obj.sp, value, types)

    def construct(self, sp, value, types):
        if isinstance(value, etree._Element):
            return self.type.from_node(sp, value, types)

        if type(value) is dict:
            return self.type.from_dict(sp, value, types)

        return self.type(sp, value, types)

    @staticmethod
    def parse_date(value):
        try:
            return datetime.date(value.year, value.month, value.day)
        except:
            return None


class Descriptor(Component):
    __protobuf__ = None
    __node__ = None

    def __init__(self, sp, internal=None, type_map=None):
        super(Descriptor, self).__init__(sp)

        self._internal = internal

        self._proxies = self._find_proxies()
        self._type_map = type_map
        self._cache = {}

    def dict_update(self, attributes):
        if not attributes:
            return self

        # Clear cache to ensure we don't use previous values
        self._cache = {}

        # Update 'self' with values from 'obj'
        for key, value in attributes.items():
            setattr(self, key, value)

        return self

    def protobuf_update(self, obj, *args):
        # Clear cache to ensure we don't use previous values
        self._cache = {}

        # Update 'self' with values from 'obj'
        for key in args:
            setattr(self, key, getattr(obj, key))

        return self

    def _find_proxies(self):
        proxies = {}

        for key in dir(self):
            if key.startswith('_'):
                continue

            value = getattr(self, key)

            if value is PropertyProxy:
                proxies[key] = PropertyProxy(key)
            elif isinstance(value, PropertyProxy):
                if value.name is None:
                    value.name = key

                proxies[key] = value

        return proxies

    def __getattribute__(self, name):
        if name.startswith('_'):
            return super(Descriptor, self).__getattribute__(name)

        if name in self.__dict__:
            return self.__dict__[name]

        # Check for property proxy
        proxies = getattr(self, '_proxies', None)

        if proxies and name in proxies:
            proxy = proxies.get(name)

            if isinstance(proxy, PropertyProxy):
                return proxy.get(name, self, self._type_map)

        return super(Descriptor, self).__getattribute__(name)

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_protobuf(cls, sp, defaults, data, types):
        internal = cls.__protobuf__()
        internal.ParseFromString(data)

        return cls(sp, internal, types).dict_update(defaults)

    @classmethod
    def from_node(cls, sp, node, types):
        return cls.from_dict(sp, etree_convert(node), types)

    @classmethod
    def from_dict(cls, sp, data, types):
        raise NotImplementedError()

    @classmethod
    def construct(cls, sp, **kwargs):
        obj = cls(sp)

        for key, value in kwargs.items():
            setattr(obj, key, value)

        return obj
